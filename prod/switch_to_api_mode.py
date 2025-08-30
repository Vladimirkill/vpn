#!/usr/bin/env python3
"""
Скрипт для переключения Xray в API режим
Бэкапит текущий конфиг и устанавливает новый с API
"""

import json
import shutil
import subprocess
import os
from datetime import datetime
import sys
sys.path.append('/var/www/vpn/prod/vpn_bot')
from config import XRAY_CONFIG, PROJECT_ROOT

def backup_current_config():
    """Создает бэкап текущей конфигурации"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{PROJECT_ROOT}/xray/backup_config_{timestamp}.json"
    
    current_config = XRAY_CONFIG['config_path']
    
    if os.path.exists(current_config):
        shutil.copy2(current_config, backup_path)
        print(f"✅ Бэкап создан: {backup_path}")
        return backup_path
    else:
        print(f"⚠️  Текущий конфиг не найден: {current_config}")
        return None

def load_base_api_config():
    """Загружает базовую API конфигурацию"""
    base_config_path = f"{PROJECT_ROOT}/xray/base_config_api.json"
    
    try:
        with open(base_config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки базового конфига: {e}")
        return None

def migrate_existing_clients():
    """Переносит существующих клиентов из старого конфига"""
    
    # Пытаемся прочитать текущий конфиг
    current_config_path = f"{PROJECT_ROOT}/xray/final_config.json"
    
    if not os.path.exists(current_config_path):
        print("ℹ️  Текущий конфиг не найден, создаем чистый")
        return []
    
    try:
        with open(current_config_path, 'r') as f:
            current_config = json.load(f)
        
        # Извлекаем клиентов из первого inbound
        if current_config.get("inbounds") and len(current_config["inbounds"]) > 0:
            first_inbound = current_config["inbounds"][0]
            clients = first_inbound.get("settings", {}).get("clients", [])
            print(f"📊 Найдено {len(clients)} существующих клиентов")
            return clients
        
    except Exception as e:
        print(f"⚠️  Ошибка чтения текущего конфига: {e}")
    
    return []

def create_new_api_config():
    """Создает новую конфигурацию с API"""
    
    # Загружаем базовую конфигурацию
    base_config = load_base_api_config()
    if not base_config:
        return False
    
    # Мигрируем существующих клиентов
    existing_clients = migrate_existing_clients()
    
    # Добавляем существующих клиентов в main inbound
    main_inbound = None
    for inbound in base_config["inbounds"]:
        if inbound.get("tag") == "main":
            main_inbound = inbound
            break
    
    if main_inbound and existing_clients:
        main_inbound["settings"]["clients"] = existing_clients
        print(f"✅ Перенесено {len(existing_clients)} клиентов в main inbound")
    
    # Сохраняем новую конфигурацию
    new_config_path = f"{PROJECT_ROOT}/xray/final_config.json"
    
    try:
        with open(new_config_path, 'w') as f:
            json.dump(base_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Новая API конфигурация сохранена: {new_config_path}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения конфига: {e}")
        return False

def restart_xray():
    """Перезапускает Xray сервис"""
    try:
        result = subprocess.run(['/usr/bin/systemctl', 'restart', 'xray'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Xray перезапущен успешно")
            return True
        else:
            print(f"❌ Ошибка перезапуска Xray: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при перезапуске: {e}")
        return False

def test_api():
    """Тестирует API подключение"""
    import asyncio
    import aiohttp
    
    async def check_api():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://127.0.0.1:10085/stats/sys") as response:
                    if response.status == 200:
                        return True
        except:
            pass
        return False
    
    return asyncio.run(check_api())

def main():
    """Основная функция переключения"""
    print("🔄 Переключение Xray в API режим")
    print("=" * 40)
    
    # 1. Бэкап текущего конфига
    print("💾 Создание бэкапа...")
    backup_path = backup_current_config()
    
    # 2. Создание новой конфигурации
    print("⚙️  Создание API конфигурации...")
    if not create_new_api_config():
        print("❌ Не удалось создать новую конфигурацию")
        return False
    
    # 3. Перезапуск Xray
    print("🔄 Перезапуск Xray...")
    if not restart_xray():
        print("❌ Не удалось перезапустить Xray")
        return False
    
    # 4. Тестирование API
    print("🧪 Тестирование API...")
    if test_api():
        print("✅ API работает!")
        print("🎉 Переключение завершено успешно!")
        print(f"📊 API доступен на: http://127.0.0.1:10085")
        return True
    else:
        print("❌ API не отвечает")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)