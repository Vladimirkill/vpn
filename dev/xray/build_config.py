import json
import os
import subprocess
import random

BASE_PATH = "/var/www/vpn/xray"
CLIENTS_PATH = os.path.join(BASE_PATH, "clients")
OUTPUT_PATH = os.path.join(BASE_PATH, "final_config.json")
TARGET_LINK = "/usr/local/etc/xray/config.json"
REALITY_PATH = os.path.join(BASE_PATH, "reality.json")
ADBLOCK_LIST = os.path.join(BASE_PATH, "adblock_domains.txt")

def generate_x25519_keypair():
    try:
        result = subprocess.run(["xray", "x25519"], capture_output=True, text=True, check=True)
        private, public = None, None
        for line in result.stdout.splitlines():
            if "Private key:" in line:
                private = line.split("Private key:")[1].strip()
            if "Public key:" in line:
                public = line.split("Public key:")[1].strip()
        return private, public
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка генерации ключей x25519: {e}")
        return None, None

def generate_short_id(length=8):
    return ''.join(random.choices("0123456789abcdef", k=length))

def build_config():
    base_config_path = os.path.join(BASE_PATH, "base_config.json")
    if not os.path.exists(base_config_path):
        print(f"❌ Файл base_config.json не найден: {base_config_path}")
        return

    try:
        with open(base_config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка чтения base_config.json: {e}")
        return

    # Добавляем детальное логирование для диагностики
    config["log"] = {
        "loglevel": "info",
        "access": "/var/log/xray/access.log",
        "error": "/var/log/xray/error.log"
    }

    # Загрузка клиентов и формирование shortIds
    clients = []
    short_ids = []

    if os.path.exists(CLIENTS_PATH):
        for filename in os.listdir(CLIENTS_PATH):
            if filename.endswith(".json"):
                filepath = os.path.join(CLIENTS_PATH, filename)
                try:
                    with open(filepath, "r") as cf:
                        client = json.load(cf)

                    # Добавляем shortId клиенту, если отсутствует
                    if "shortId" not in client:
                        client["shortId"] = generate_short_id()
                        with open(filepath, "w") as cf:
                            json.dump(client, cf, indent=2)

                    short_ids.append(client["shortId"])

                    # Убираем shortId из client-конфига (он идёт только в realitySettings)
                    # Используем UUID как email, чтобы уметь таргетировать правила по конкретному клиенту через поле "user"
                    minimal_client = {
                        "id": client["id"],
                        "flow": client.get("flow", "xtls-rprx-vision"),
                        "level": client.get("level", 0),
                        "email": client.get("id", client.get("email", ""))
                    }
                    clients.append(minimal_client)

                except json.JSONDecodeError as e:
                    print(f"⚠️ Ошибка чтения клиента {filename}: {e}")
    else:
        print(f"⚠️ Папка клиентов не найдена: {CLIENTS_PATH}")

    # Вставляем клиентов
    try:
        config["inbounds"][0]["settings"]["clients"] = clients
    except Exception as e:
        print(f"❌ Ошибка вставки клиентов: {e}")
        return

    # Обновление realitySettings
    try:
        stream_settings = config["inbounds"][0].get("streamSettings", {})
        if stream_settings.get("security") == "reality":
            # Проверяем существующие ключи в reality.json
            private_key = None
            public_key = None
            if os.path.exists(REALITY_PATH):
                try:
                    with open(REALITY_PATH, "r") as f:
                        existing_reality = json.load(f)
                    private_key = existing_reality.get("privateKey")
                    public_key = existing_reality.get("publicKey")
                    print(f"🔐 Используем существующие ключи из {REALITY_PATH}")
                except Exception as e:
                    print(f"⚠️ Ошибка чтения {REALITY_PATH}: {e}")
            
            # Генерируем новые ключи только если их нет
            if not private_key or not public_key:
                private_key, public_key = generate_x25519_keypair()
                if not private_key or not public_key:
                    print("❌ Не удалось сгенерировать ключи x25519")
                    return
                print("🔐 Сгенерированы новые REALITY ключи")

            stream_settings["realitySettings"] = {
                "show": False,
                "fingerprint": "chrome",
                "serverNames": [
                    "www.cloudflare.com",
                    "www.microsoft.com", 
                    "www.apple.com",
                    "discord.com",
                    "www.google.com",
                    "www.github.com",
                    "www.amazon.com"
                ],
                "shortIds": short_ids,
                "privateKey": private_key,
                "dest": "www.microsoft.com:8443"
            }

            config["inbounds"][0]["streamSettings"] = stream_settings

            # Сохраняем reality.json
            with open(REALITY_PATH, "w") as f:
                json.dump({
                    "privateKey": private_key,
                    "publicKey": public_key,
                    "shortIds": short_ids
                }, f, indent=2)
            print(f"🔐 Reality-ключи обновлены. Сохранено: {REALITY_PATH}")
    except Exception as e:
        print(f"⚠️ Ошибка обновления realitySettings: {e}")
        return

    # Добавляем routing rules (исключения + блокировка рекламы)
    try:
        # Пробуем импортировать bypass_routing только если доступна база данных
        try:
            from xray.bypass_routing import generate_routing_rules
            routing_from_bypass = generate_routing_rules() or {"domainStrategy": "IPIfNonMatch", "rules": []}
            print("✅ Routing rules из bypass_routing загружены")
        except Exception as bypass_error:
            print(f"⚠️ Ошибка добавления routing rules: {bypass_error}")
            routing_from_bypass = {"domainStrategy": "IPIfNonMatch", "rules": []}

        # Гарантируем, что в конфиге есть секция routing
        routing = config.get("routing", {"domainStrategy": "IPIfNonMatch", "rules": []})
        routing.setdefault("domainStrategy", "IPIfNonMatch")
        routing.setdefault("rules", [])

        # 1) Правила исключений (direct) для пользователей
        if routing_from_bypass.get("rules"):
            routing["rules"].extend(routing_from_bypass["rules"])
            print(f"🔀 Добавлены правила исключений: {len(routing_from_bypass['rules'])}")
        else:
            print("ℹ️ Правил исключений нет")

        # 2) Жесткая блокировка рекламы
        # 2.1 Через geosite:category-ads-all (если есть geosite.dat)
        geosite_candidates = [
            "/usr/local/bin/geosite.dat",
            "/usr/local/share/xray/geosite.dat",
            "/usr/share/xray/geosite.dat",
            "/usr/lib/xray/geosite.dat",
        ]
        has_geosite = any(os.path.exists(p) for p in geosite_candidates)
        if has_geosite:
            ads_rule = {
                "type": "field",
                "domain": ["geosite:category-ads-all"],
                "outboundTag": "block"
            }
            routing["rules"].append(ads_rule)
            print("🧱 Добавлено правило блокировки: geosite:category-ads-all → block")
        else:
            print("ℹ️ geosite.dat не найден — пропускаю geosite:category-ads-all")

        # 2.2 Через локальный список доменов (если присутствует)
        if os.path.exists(ADBLOCK_LIST):
            try:
                with open(ADBLOCK_LIST, "r") as f:
                    raw_lines = [l.strip() for l in f.readlines()]
                domains = []
                for line in raw_lines:
                    if not line or line.startswith("#"):
                        continue
                    # Приводим к формату Xray: domain:example.com
                    if line.startswith("domain:") or line.startswith("keyword:") or line.startswith("regexp:"):
                        domains.append(line)
                    else:
                        domains.append(f"domain:{line}")
                if domains:
                    # Дробим на чанки, чтобы избежать слишком больших правил
                    CHUNK = 500
                    chunks = [domains[i:i+CHUNK] for i in range(0, len(domains), CHUNK)]
                    for idx, chunk in enumerate(chunks, 1):
                        routing["rules"].append({
                            "type": "field",
                            "domain": chunk,
                            "outboundTag": "block"
                        })
                    print(f"🧱 Добавлены локальные правила блокировки рекламы: {len(domains)} доменов, {len(chunks)} правил")
            except Exception as e:
                print(f"⚠️ Ошибка чтения списка рекламы {ADBLOCK_LIST}: {e}")

        # Сохраняем собранную секцию routing обратно в конфиг
        config["routing"] = routing
    except Exception as e:
        print(f"⚠️ Ошибка добавления routing rules: {e}")

    # Убеждаемся, что есть outbound с тегом block (blackhole)
    try:
        outbounds = config.get("outbounds", [])
        has_block = any((o.get("tag") == "block" and o.get("protocol") == "blackhole") for o in outbounds)
        if not has_block:
            outbounds.append({
                "protocol": "blackhole",
                "tag": "block"
            })
            config["outbounds"] = outbounds
            print("➕ Добавлен outbound blackhole: tag=block")
    except Exception as e:
        print(f"⚠️ Ошибка проверки/добавления outbound block: {e}")

    # Сохраняем финальный конфиг
    try:
        with open(OUTPUT_PATH, "w") as out:
            json.dump(config, out, indent=2)
        print(f"✅ Финальный конфиг сохранён: {OUTPUT_PATH}")
    except Exception as e:
        print(f"❌ Ошибка сохранения final_config.json: {e}")
        return

    # Обновляем симлинк
    try:
        if os.path.islink(TARGET_LINK) or os.path.exists(TARGET_LINK):
            os.remove(TARGET_LINK)
        os.symlink(os.path.abspath(OUTPUT_PATH), TARGET_LINK)
        print(f"🔗 Симлинк обновлён: {TARGET_LINK} → {OUTPUT_PATH}")
    except Exception as e:
        print(f"❌ Ошибка создания симлинка: {e}")
        return

    # Перезапуск Xray
    try:
        # Предпочитаем корректный reload через systemd
        result = subprocess.run(["systemctl", "reload", "xray"], capture_output=True, text=True)
        if result.returncode == 0:
            print("🔄 Xray: systemctl reload выполнен")
        else:
            # Fallback: restart, если reload не поддерживается
            print(f"⚠️ systemctl reload не удался: {result.stderr.strip()} — выполняю restart")
            result2 = subprocess.run(["systemctl", "restart", "xray"], capture_output=True, text=True)
            if result2.returncode == 0:
                print("✅ Xray: systemctl restart выполнен")
            else:
                print(f"❌ Не удалось перезапустить Xray: {result2.stderr.strip()}")
    except Exception as e:
        print(f"⚠️ Ошибка при reload/restart Xray: {e}")

if __name__ == "__main__":
    build_config()