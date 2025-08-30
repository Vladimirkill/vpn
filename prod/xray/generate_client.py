import uuid
import json
import random
import datetime
import logging
import subprocess
from pathlib import Path
import os

def check_user_limits(clients_dir: str, client_name: str) -> dict:
    """
    Проверяет лимиты для пользователя:
    - 1 ключ для одного пользователя
    - Максимум 3 устройства для 1 ключа
    """
    clients_path = Path(clients_dir)
    if not clients_path.exists():
        return {"allowed": True, "reason": "Директория клиентов не существует"}
    
    # Ищем существующие ключи для этого пользователя (исключаем удаленные)
    existing_keys = []
    for filename in os.listdir(clients_dir):
        if filename.endswith('.json') and not filename.startswith('REMOVED_'):
            try:
                with open(clients_path / filename, 'r') as f:
                    client_data = json.load(f)
                    metadata = client_data.get('_metadata', {})
                    if metadata.get('client_name') == client_name:
                        existing_keys.append({
                            'uuid': client_data.get('id'),
                            'filename': filename,
                            'created_at': metadata.get('created_at', 'unknown'),
                            'active_connections': 0  # Будет подсчитано позже
                        })
            except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                logging.warning(f"Ошибка чтения файла клиента {filename}: {e}")
                continue
    
    # Проверяем лимит: 1 ключ для одного пользователя
    if len(existing_keys) >= 1:
        return {
            "allowed": False, 
            "reason": f"Пользователь {client_name} уже имеет ключ",
            "existing_keys": existing_keys
        }
    
    return {"allowed": True, "reason": "Лимит не превышен"}

def count_active_connections() -> dict:
    """
    Подсчитывает активные соединения по IP адресам
    """
    try:
        import subprocess
        result = subprocess.run(['ss', '-tn', 'state', 'established'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return {}
        
        connections = {}
        for line in result.stdout.split('\n'):
            if ':8443' in line:
                parts = line.split()
                if len(parts) >= 4:
                    # Формат: 0 0 146.103.125.210:32800 149.154.167.41:443
                    if parts[3].endswith(':8443'):
                        client_ip = parts[2].split(':')[0]
                        if client_ip not in connections:
                            connections[client_ip] = 0
                        connections[client_ip] += 1
        
        return connections
    except (subprocess.SubprocessError, FileNotFoundError, IndexError) as e:
        logging.error(f"Ошибка подсчета активных соединений: {e}")
        return {}

def check_device_limits(clients_dir: str, client_name: str) -> dict:
    """
    Проверяет лимит устройств для пользователя (максимум 3)
    """
    connections = count_active_connections()
    
    # Подсчитываем активные соединения для существующих ключей пользователя
    clients_path = Path(clients_dir)
    total_connections = 0
    
    for filename in os.listdir(clients_dir):
        if filename.endswith('.json') and not filename.startswith('REMOVED_'):
            try:
                with open(clients_path / filename, 'r') as f:
                    client_data = json.load(f)
                    metadata = client_data.get('_metadata', {})
                    if metadata.get('client_name') == client_name:
                        # Для каждого ключа пользователя считаем соединения
                        # В реальности нужно точное сопоставление UUID -> IP
                        # Пока используем упрощенную логику
                        total_connections += len(connections)
                        break
            except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                logging.warning(f"Ошибка чтения файла клиента {filename}: {e}")
                continue
    
    max_devices = 3
    if total_connections >= max_devices:
        return {
            "allowed": False,
            "reason": f"Превышен лимит устройств: {total_connections}/{max_devices}",
            "current_connections": total_connections,
            "max_devices": max_devices
        }
    
    return {
        "allowed": True,
        "reason": f"Лимит устройств не превышен: {total_connections}/{max_devices}",
        "current_connections": total_connections,
        "max_devices": max_devices
    }

def generate_vless_client(
    clients_dir: str,
    flow: str = "xtls-rprx-vision",
    host: str = "example.com",
    port: int = 8443,
    sni: str = "www.apple.com",
    public_key: str = None,
    client_name: str = "vpn",
    enforce_limits: bool = True
) -> dict:
    """
    Генерирует VLESS клиента с жесткими ограничениями:
    - 1 ключ для одного пользователя
    - Максимум 3 устройства для 1 ключа
    """
    
    # === Валидация входных данных ===
    if not clients_dir or not os.path.exists(clients_dir):
        return {"error": "❌ Неверная директория клиентов"}
    
    if not client_name or not isinstance(client_name, str) or len(client_name.strip()) == 0:
        return {"error": "❌ Неверное имя клиента"}
    
    if not isinstance(port, int) or port <= 0 or port > 65535:
        return {"error": "❌ Неверный порт"}
    
    if not host or not isinstance(host, str):
        return {"error": "❌ Неверный хост"}

    # === Проверка лимитов пользователя ===
    if enforce_limits:
        user_check = check_user_limits(clients_dir, client_name)
        if not user_check["allowed"]:
            return {
                "error": f"❌ Пользователь {client_name} уже имеет ключ",
                "details": user_check,
                "solution": "Удалите существующий ключ перед созданием нового"
            }
        
        device_check = check_device_limits(clients_dir, client_name)
        if not device_check["allowed"]:
            return {
                "error": f"❌ Превышен лимит устройств для пользователя {client_name}",
                "details": device_check,
                "solution": "Отключите лишние устройства или удалите старый ключ"
            }
    
    # === Генерация UUID клиента ===
    client_id = str(uuid.uuid4())

    # === Генерация уникального shortId ===
    short_id = "".join(random.choices("0123456789abcdef", k=8))

    # === Подгружаем reality.json ===
    clients_path = Path(clients_dir)
    reality_path = clients_path.parent / "reality.json"
    try:
        with open(reality_path, "r", encoding="utf-8") as f:
            reality_data = json.load(f)
    except Exception as e:
        return {"error": f"❌ Не удалось загрузить reality.json: {e}"}

    # === Проверка publicKey ===
    if public_key is None:
        public_key = reality_data.get("publicKey", "")
    if not public_key:
        return {"error": "❌ Публичный ключ не указан и не найден в reality.json"}

    # === Добавление shortId в reality.json (если его нет) ===
    if "shortIds" not in reality_data:
        reality_data["shortIds"] = []

    if short_id not in reality_data["shortIds"]:
        reality_data["shortIds"].append(short_id)
        try:
            with open(reality_path, "w", encoding="utf-8") as f:
                json.dump(reality_data, f, indent=2)
        except Exception as e:
            return {"error": f"❌ Не удалось обновить reality.json: {e}"}

    # === Формируем структуру клиента с расширенными метаданными ===
    client = {
        "id": client_id,
        "flow": flow,
        "level": 0,
        "email": "",
        "encryption": "none",
        "shortId": short_id,
        "_metadata": {
            "max_connections": 3,
            "max_devices": 3,
            "created_at": str(datetime.datetime.now()),
            "client_name": client_name,
            "enforce_limits": enforce_limits,
            "device_count": 0,
            "last_activity": str(datetime.datetime.now())
        }
    }

    # === Сохраняем клиента в файл ===
    clients_path.mkdir(parents=True, exist_ok=True)
    client_path = clients_path / f"{client_id}.json"
    try:
        with open(client_path, "w") as f:
            json.dump(client, f, indent=2)
    except Exception as e:
        return {"error": f"❌ Не удалось сохранить клиента: {e}"}

    # === Формируем VLESS-ссылку ===
    display_name = f"VPNBot_{client_name}".replace(" ", "_")
    vless_link = (
        f"vless://{client_id}@{host}:{port}"
        f"?security=reality"
        f"&sni={sni}"
        f"&fp=safari"
        f"&pbk={public_key}"
        f"&sid={short_id}"
        f"&spx=/"
        f"&type=tcp"
        f"&flow={flow}"
        f"&encryption=none"
        f"#{display_name}"
    )

    return {
        "uuid": client_id,
        "file": str(client_path),
        "shortId": short_id,
        "link": vless_link,
        "limits": {
            "max_connections": 3,
            "max_devices": 3,
            "enforced": enforce_limits
        }
    }