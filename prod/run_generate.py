import subprocess
import sys
import os
from xray.generate_client import generate_vless_client
import time
import json
from pathlib import Path

# === Конфигурация ===
CLIENTS_DIR = "/var/www/vpn/xray/clients"
BUILD_SCRIPT = "/var/www/vpn/xray/build_config.py"
HOST = "146.103.125.210"
PORT = 443
FLOW = "xtls-rprx-vision"

def get_user_existing_keys(client_name):
    """Получает информацию о существующих ключах пользователя"""
    existing_keys = []
    
    if not os.path.exists(CLIENTS_DIR):
        return existing_keys
    
    for filename in os.listdir(CLIENTS_DIR):
        if filename.endswith('.json') and not filename.startswith('REMOVED_'):
            try:
                with open(os.path.join(CLIENTS_DIR, filename), 'r') as f:
                    client_data = json.load(f)
                    metadata = client_data.get('_metadata', {})
                    if metadata.get('client_name') == client_name:
                        existing_keys.append({
                            'uuid': client_data.get('id'),
                            'filename': filename,
                            'created_at': metadata.get('created_at', 'unknown'),
                            'short_id': client_data.get('shortId', 'unknown')
                        })
            except:
                continue
    
    return existing_keys

def show_user_keys_info(client_name):
    """Показывает информацию о существующих ключах пользователя"""
    existing_keys = get_user_existing_keys(client_name)
    
    if not existing_keys:
        return
    
    print(f"\n🔍 Информация о существующих ключах пользователя '{client_name}':")
    print("=" * 80)
    
    for i, key in enumerate(existing_keys, 1):
        print(f"{i}. 🔑 Ключ: {key['uuid']}")
        print(f"   📁 Файл: {key['filename']}")
        print(f"   🆔 Short ID: {key['short_id']}")
        print(f"   📅 Создан: {key['created_at']}")
        print()
    
    print("💡 Для создания нового ключа сначала удалите существующий:")
    print("   python3 manage_user_limits.py")
    print("   Опция 4: Удалить ключ пользователя")
    print()
    print("🔗 Или используйте существующий ключ выше")

# === Получение имени клиента из аргументов ===
client_name = "vpn"  # По умолчанию
if len(sys.argv) > 1:
    client_name = sys.argv[1]

# === Генерация клиента ===
print(f"🔑 Создание VPN ключа для пользователя: {client_name}")
print("=" * 60)

result = generate_vless_client(
    clients_dir=CLIENTS_DIR,
    flow=FLOW,
    host=HOST,
    port=PORT,
    client_name=client_name
)

if "error" in result:
    print("❌ Ошибка создания ключа:")
    print(f"   {result['error']}")
    
    # Показываем детали ошибки, если есть
    if "details" in result:
        details = result["details"]
        if "existing_keys" in details:
            print(f"\n📋 Детали ограничения:")
            existing_keys = details["existing_keys"]
            print(f"   У пользователя уже есть {len(existing_keys)} ключей:")
            for key in existing_keys:
                print(f"   🔑 {key['uuid']} | Создан: {key['created_at']}")
    
    # Показываем существующие ключи пользователя
    show_user_keys_info(client_name)
    
    print(f"\n🚨 Создание ключа отклонено из-за ограничений!")
    print("💡 Система ограничений: 1 ключ для одного пользователя")
    exit(1)

# === Вывод информации ===
print("✅ Новый клиент создан:")
print("UUID:", result["uuid"])
print("Файл:", result["file"])
print("Ссылка:", result["link"])

# Показываем информацию о лимитах
if "limits" in result:
    limits = result["limits"]
    print(f"\n📊 Лимиты ключа:")
    print(f"   Максимум соединений: {limits.get('max_connections', 'N/A')}")
    print(f"   Максимум устройств: {limits.get('max_devices', 'N/A')}")
    print(f"   Ограничения: {'Включены' if limits.get('enforced', True) else 'Отключены'}")

# === Сборка конфига ===
build = subprocess.run(["python3", BUILD_SCRIPT], capture_output=True, text=True)
if build.returncode != 0:
    print("❌ Ошибка сборки конфига:\n", build.stderr)
    exit(1)
else:
    print("🔧 Конфиг успешно собран.")

# === Применение конфигурации и автоматический перезапуск Xray ===
try:
    print("🔄 Применение новой конфигурации...")
    
    # Проверяем активен ли Xray
    check_result = subprocess.run(["systemctl", "is-active", "xray"], 
                                capture_output=True, text=True)
    
    if check_result.stdout.strip() == "active":
        print("✅ Xray активен - выполняем перезапуск для применения новой конфигурации")
        
        # Сначала пробуем безопасный перезапуск
        safe_restart_script = "/var/www/vpn/xray/safe_restart.py"
        
        if os.path.exists(safe_restart_script):
            print("🛡️ Используем безопасный перезапуск Xray")
            print("🔒 IP пользователей защищены от утечки")
            
            restart_result = subprocess.run([
                "python3", safe_restart_script, "restart"
            ], capture_output=True, text=True, timeout=60)
            
            if restart_result.returncode == 0:
                print("✅ Xray безопасно перезапущен!")
                print("🛡️ IP пользователей защищены")
                print("🔑 Новый клиент активен и готов к использованию!")
            else:
                print(f"⚠️ Ошибка безопасного перезапуска: {restart_result.stderr}")
                print("🔄 Fallback: используем обычный restart")
                fallback_restart()
        else:
            print("⚠️ Скрипт безопасного перезапуска не найден")
            print("🔄 Fallback: используем обычный restart")
            fallback_restart()
    else:
        # Xray не активен - запускаем его
        print("🚀 Xray не активен - запускаем сервис")
        start_result = subprocess.run(["systemctl", "start", "xray"], 
                                    capture_output=True, text=True)
        if start_result.returncode == 0:
            print("✅ Xray успешно запущен с новым клиентом!")
        else:
            print(f"⚠️ Ошибка запуска Xray: {start_result.stderr}")
    
    # Проверяем, что Xray действительно работает
    print("🔍 Проверка работоспособности Xray...")
    time.sleep(3)  # Даем время на запуск
    
    status_check = subprocess.run(["systemctl", "is-active", "xray"], 
                                capture_output=True, text=True)
    if status_check.stdout.strip() == "active":
        print("✅ Xray активен и работает")
        
        # Проверяем, слушает ли порт 443
        port_check = subprocess.run(["ss", "-tn", "state", "listening"], 
                                  capture_output=True, text=True)
        if ":8443" in port_check.stdout:
            print("✅ Xray слушает порт 443")
            print("🎉 Новый клиент полностью готов к использованию!")
        else:
            print("⚠️ Xray активен, но не слушает порт 443")
            print("💡 Возможно, нужен дополнительный перезапуск")
    else:
        print("❌ Xray не активен после перезапуска")
        print("💡 Проверьте логи: journalctl -u xray -n 20")
    
    # Уведомляем мониторинг о новом клиенте (если запущен)
    try:
        monitor_status = subprocess.run(["systemctl", "is-active", "xray-monitor"], 
                                      capture_output=True, text=True)
        if monitor_status.stdout.strip() == "active":
            print("📡 Мониторинг Xray активен - изменения будут отслежены автоматически")
    except:
        pass
        
except Exception as e:
    print(f"⚠️ Ошибка управления Xray: {e}")
    print("💡 Выполните вручную: systemctl restart xray")
    print("💡 Проверьте логи: journalctl -u xray -n 20")

def fallback_restart():
    """Fallback функция для обычного перезапуска"""
    try:
        restart_result = subprocess.run(["systemctl", "restart", "xray"], 
                                       capture_output=True, text=True)
        if restart_result.returncode == 0:
            print("✅ Xray перезапущен (fallback) - новый клиент активен!")
        else:
            print(f"⚠️ Ошибка fallback restart: {restart_result.stderr}")
    except Exception as e:
        print(f"⚠️ Ошибка fallback: {e}")