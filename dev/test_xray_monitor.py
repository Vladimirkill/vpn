#!/usr/bin/env python3
"""
Скрипт для тестирования системы автоматического мониторинга Xray
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime

def log_message(message: str):
    """Логирование с временной меткой"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_systemd_service(service_name: str) -> bool:
    """Проверяет статус systemd сервиса"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip() == "active"
    except Exception as e:
        log_message(f"❌ Ошибка проверки {service_name}: {e}")
        return False

def check_file_exists(filepath: str) -> bool:
    """Проверяет существование файла"""
    return os.path.exists(filepath)

def create_test_client(client_name: str = "test_client") -> bool:
    """Создает тестового клиента"""
    try:
        log_message(f"🔄 Создание тестового клиента: {client_name}")
        
        result = subprocess.run([
            "python3", "run_generate.py", client_name
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            log_message("✅ Тестовый клиент создан успешно")
            return True
        else:
            log_message(f"❌ Ошибка создания клиента: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log_message("⏰ Timeout при создании клиента")
        return False
    except Exception as e:
        log_message(f"❌ Ошибка: {e}")
        return False

def check_monitor_logs() -> bool:
    """Проверяет логи мониторинга"""
    log_file = "/var/log/xray-monitor.log"
    
    if not check_file_exists(log_file):
        log_message(f"⚠️ Лог файл не найден: {log_file}")
        return False
    
    try:
        # Читаем последние строки лога
        with open(log_file, 'r') as f:
            lines = f.readlines()
            last_lines = lines[-10:] if len(lines) >= 10 else lines
        
        log_message("📝 Последние записи в логе мониторинга:")
        for line in last_lines:
            print(f"   {line.strip()}")
        
        return True
        
    except Exception as e:
        log_message(f"❌ Ошибка чтения лога: {e}")
        return False

def check_xray_status() -> bool:
    """Проверяет статус Xray"""
    try:
        result = subprocess.run(
            ["systemctl", "status", "xray", "--no-pager", "-l"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            log_message("✅ Xray активен")
            return True
        else:
            log_message(f"⚠️ Xray не активен: {result.stderr}")
            return False
            
    except Exception as e:
        log_message(f"❌ Ошибка проверки Xray: {e}")
        return False

def count_clients() -> int:
    """Подсчитывает количество клиентов"""
    clients_dir = "xray/clients"
    
    if not check_file_exists(clients_dir):
        return 0
    
    try:
        client_files = [f for f in os.listdir(clients_dir) if f.endswith('.json')]
        return len(client_files)
    except Exception as e:
        log_message(f"❌ Ошибка подсчета клиентов: {e}")
        return 0

def test_monitor_integration():
    """Тестирует интеграцию мониторинга"""
    log_message("🧪 Тестирование интеграции мониторинга...")
    
    # Проверяем статус мониторинга
    monitor_active = check_systemd_service("xray-monitor")
    if monitor_active:
        log_message("✅ Мониторинг Xray активен")
    else:
        log_message("❌ Мониторинг Xray не активен")
        return False
    
    # Проверяем статус Xray
    xray_active = check_xray_status()
    if not xray_active:
        log_message("❌ Xray не активен, тест прерван")
        return False
    
    # Подсчитываем клиентов до теста
    clients_before = count_clients()
    log_message(f"📊 Клиентов до теста: {clients_before}")
    
    # Создаем тестового клиента
    if not create_test_client():
        log_message("❌ Не удалось создать тестового клиента")
        return False
    
    # Ждем обработки мониторингом
    log_message("⏳ Ожидание обработки мониторингом (10 секунд)...")
    time.sleep(10)
    
    # Проверяем количество клиентов после теста
    clients_after = count_clients()
    log_message(f"📊 Клиентов после теста: {clients_after}")
    
    if clients_after > clients_before:
        log_message("✅ Новый клиент добавлен")
    else:
        log_message("⚠️ Количество клиентов не изменилось")
    
    # Проверяем логи мониторинга
    log_message("📝 Проверка логов мониторинга...")
    check_monitor_logs()
    
    return True

def run_diagnostic():
    """Запускает диагностику системы"""
    log_message("🔍 Диагностика системы мониторинга Xray...")
    
    print("\n" + "="*60)
    print("📋 СТАТУС СИСТЕМЫ")
    print("="*60)
    
    # Проверяем основные сервисы
    services = ["xray", "xray-monitor"]
    for service in services:
        status = "🟢 Активен" if check_systemd_service(service) else "🔴 Неактивен"
        print(f"{service:15} : {status}")
    
    print("\n" + "="*60)
    print("📁 ФАЙЛЫ СИСТЕМЫ")
    print("="*60)
    
    # Проверяем ключевые файлы
    files = [
        ("xray/monitor_clients.py", "Скрипт мониторинга"),
        ("xray/safe_restart.py", "Скрипт безопасного перезапуска"),
        ("xray/build_config.py", "Скрипт сборки конфигурации"),
        ("xray/clients/", "Директория клиентов"),
        ("/var/log/xray-monitor.log", "Лог мониторинга")
    ]
    
    for filepath, description in files:
        exists = "✅" if check_file_exists(filepath) else "❌"
        print(f"{exists} {description:30} : {filepath}")
    
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА")
    print("="*60)
    
    # Статистика клиентов
    client_count = count_clients()
    print(f"Клиентов в системе: {client_count}")
    
    # Проверяем размер лога
    log_file = "/var/log/xray-monitor.log"
    if check_file_exists(log_file):
        try:
            size = os.path.getsize(log_file)
            print(f"Размер лога: {size} байт")
        except:
            print("Размер лога: недоступен")
    
    print("\n" + "="*60)

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 test_xray_monitor.py diagnostic  - диагностика системы")
        print("  python3 test_xray_monitor.py test       - тест интеграции")
        print("  python3 test_xray_monitor.py logs       - просмотр логов")
        return
    
    command = sys.argv[1]
    
    if command == "diagnostic":
        run_diagnostic()
    elif command == "test":
        test_monitor_integration()
    elif command == "logs":
        check_monitor_logs()
    else:
        print(f"❌ Неизвестная команда: {command}")

if __name__ == "__main__":
    main() 