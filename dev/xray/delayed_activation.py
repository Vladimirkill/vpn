#!/usr/bin/env python3
"""
Система отложенной активации VLESS ключей
Предотвращает частые перезапуски Xray при добавлении новых клиентов
"""

import subprocess
import time
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Конфигурация
CLIENTS_DIR = Path("/var/www/vpn/xray/clients")
BUILD_SCRIPT = "/var/www/vpn/xray/build_config.py"
PENDING_DIR = Path("/var/www/vpn/xray/pending_clients")
ACTIVATION_INTERVAL = 300  # 5 минут в секундах
LOG_FILE = "/var/www/vpn/xray/activation.log"

def log_message(message: str):
    """Логирование с временной меткой"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    
    print(log_entry.strip())

def move_pending_to_active():
    """Перемещает клиентов из pending в активные"""
    if not PENDING_DIR.exists():
        return 0
    
    pending_files = list(PENDING_DIR.glob("*.json"))
    if not pending_files:
        return 0
    
    moved_count = 0
    for pending_file in pending_files:
        try:
            # Перемещаем файл в активную папку
            target_file = CLIENTS_DIR / pending_file.name
            pending_file.rename(target_file)
            moved_count += 1
            log_message(f"✅ Активирован клиент: {pending_file.name}")
        except Exception as e:
            log_message(f"❌ Ошибка активации {pending_file.name}: {e}")
    
    return moved_count

def rebuild_and_reload():
    """Пересобирает конфигурацию и перезагружает Xray"""
    try:
        # Сборка конфигурации
        build_result = subprocess.run(
            ["python3", BUILD_SCRIPT], 
            capture_output=True, text=True
        )
        
        if build_result.returncode != 0:
            log_message(f"❌ Ошибка сборки конфига: {build_result.stderr}")
            return False
        
        # Быстрый перезапуск Xray (restart быстрее reload для нашего случая)
        restart_result = subprocess.run(
            ["systemctl", "restart", "xray"],
            capture_output=True, text=True
        )
        
        if restart_result.returncode != 0:
            log_message(f"❌ Ошибка перезапуска Xray: {restart_result.stderr}")
            return False
        
        log_message("🔄 Xray успешно перезапущен с новыми клиентами")
        return True
        
    except Exception as e:
        log_message(f"❌ Неожиданная ошибка: {e}")
        return False

def create_pending_client(client_uuid: str, client_data: dict):
    """Создает клиента в папке pending для последующей активации"""
    PENDING_DIR.mkdir(exist_ok=True)
    
    pending_file = PENDING_DIR / f"{client_uuid}.json"
    
    try:
        with open(pending_file, "w") as f:
            json.dump(client_data, f, indent=2)
        
        log_message(f"📝 Клиент {client_uuid} добавлен в очередь активации")
        return True
        
    except Exception as e:
        log_message(f"❌ Ошибка создания pending клиента {client_uuid}: {e}")
        return False

def activation_daemon():
    """Демон для периодической активации новых клиентов"""
    log_message("🚀 Запуск демона отложенной активации VLESS ключей")
    log_message(f"⏰ Интервал активации: {ACTIVATION_INTERVAL} секунд")
    
    while True:
        try:
            # Проверяем наличие новых клиентов
            pending_count = move_pending_to_active()
            
            if pending_count > 0:
                log_message(f"🔄 Найдено {pending_count} новых клиентов для активации")
                
                if rebuild_and_reload():
                    log_message(f"✅ Успешно активировано {pending_count} клиентов")
                else:
                    log_message(f"❌ Ошибка активации клиентов")
            
            # Ожидание следующей проверки
            time.sleep(ACTIVATION_INTERVAL)
            
        except KeyboardInterrupt:
            log_message("🛑 Демон остановлен пользователем")
            break
        except Exception as e:
            log_message(f"❌ Ошибка в демоне: {e}")
            time.sleep(30)  # Короткая пауза при ошибке

def get_pending_count():
    """Возвращает количество клиентов в очереди активации"""
    if not PENDING_DIR.exists():
        return 0
    return len(list(PENDING_DIR.glob("*.json")))

def force_activation():
    """Принудительная активация всех pending клиентов"""
    log_message("🔥 Принудительная активация клиентов")
    
    pending_count = move_pending_to_active()
    if pending_count > 0:
        if rebuild_and_reload():
            log_message(f"✅ Принудительно активировано {pending_count} клиентов")
        else:
            log_message(f"❌ Ошибка принудительной активации")
    else:
        log_message("ℹ️ Нет клиентов для активации")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "daemon":
            activation_daemon()
        elif command == "force":
            force_activation()
        elif command == "status":
            pending = get_pending_count()
            print(f"Клиентов в очереди: {pending}")
        else:
            print("Использование:")
            print("  python3 delayed_activation.py daemon   - запуск демона")
            print("  python3 delayed_activation.py force    - принудительная активация")
            print("  python3 delayed_activation.py status   - показать статус")
    else:
        activation_daemon()