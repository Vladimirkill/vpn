#!/usr/bin/env python3
"""
Тест автоматического перезапуска Xray после создания клиента
"""

import subprocess
import time
import json
import os
from datetime import datetime

def get_xray_status():
    """Получает статус Xray"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'xray'], 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "unknown"

def get_xray_pid():
    """Получает PID Xray"""
    try:
        result = subprocess.run(['systemctl', 'show', 'xray', '--property=MainPID'], 
                              capture_output=True, text=True)
        pid_line = result.stdout.strip()
        if 'MainPID=' in pid_line:
            return pid_line.split('=')[1]
        return None
    except:
        return None

def check_port_listening():
    """Проверяет, слушает ли Xray порт 443"""
    try:
        result = subprocess.run(['ss', '-tn', 'state', 'listening'], 
                              capture_output=True, text=True)
        return ':443' in result.stdout
    except:
        return False

def count_clients():
    """Подсчитывает количество клиентов"""
    clients_dir = "xray/clients"
    if not os.path.exists(clients_dir):
        return 0
    
    count = 0
    for filename in os.listdir(clients_dir):
        if filename.endswith('.json'):
            count += 1
    return count

def get_latest_client():
    """Получает информацию о последнем созданном клиенте"""
    clients_dir = "xray/clients"
    if not os.path.exists(clients_dir):
        return None
    
    latest_client = None
    latest_time = 0
    
    for filename in os.listdir(clients_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(clients_dir, filename)
            try:
                file_time = os.path.getmtime(file_path)
                if file_time > latest_time:
                    latest_time = file_time
                    latest_client = filename
            except:
                continue
    
    if latest_client:
        try:
            with open(os.path.join(clients_dir, latest_client), 'r') as f:
                client_data = json.load(f)
                return {
                    'filename': latest_client,
                    'uuid': client_data.get('id'),
                    'created_time': datetime.fromtimestamp(latest_time).strftime('%Y-%m-%d %H:%M:%S')
                }
        except:
            pass
    
    return None

def test_auto_restart():
    """Тестирует автоматический перезапуск Xray"""
    print("🧪 Тест автоматического перезапуска Xray")
    print("=" * 60)
    
    # Шаг 1: Проверяем начальное состояние
    print("📊 Шаг 1: Проверка начального состояния")
    initial_status = get_xray_status()
    initial_pid = get_xray_pid()
    initial_port = check_port_listening()
    initial_clients = count_clients()
    
    print(f"   Статус Xray: {initial_status}")
    print(f"   PID Xray: {initial_pid}")
    print(f"   Порт 443: {'✅ Слушает' if initial_port else '❌ Не слушает'}")
    print(f"   Количество клиентов: {initial_clients}")
    
    if initial_status != "active":
        print("❌ Xray не активен - тест невозможен")
        return False
    
    # Шаг 2: Создаем тестового клиента
    print(f"\n🔑 Шаг 2: Создание тестового клиента")
    test_client_name = f"test_auto_restart_{int(time.time())}"
    
    print(f"   Имя клиента: {test_client_name}")
    
    # Запускаем создание клиента
    start_time = time.time()
    result = subprocess.run([
        "python3", "run_generate.py", test_client_name
    ], capture_output=True, text=True, timeout=120)
    
    creation_time = time.time() - start_time
    
    if result.returncode != 0:
        print(f"❌ Ошибка создания клиента: {result.stderr}")
        return False
    
    print(f"✅ Клиент создан за {creation_time:.1f} секунд")
    
    # Шаг 3: Проверяем изменения
    print(f"\n🔍 Шаг 3: Проверка изменений")
    time.sleep(5)  # Даем время на применение изменений
    
    final_status = get_xray_status()
    final_pid = get_xray_pid()
    final_port = check_port_listening()
    final_clients = count_clients()
    latest_client = get_latest_client()
    
    print(f"   Статус Xray: {final_status}")
    print(f"   PID Xray: {final_pid}")
    print(f"   Порт 443: {'✅ Слушает' if final_port else '❌ Не слушает'}")
    print(f"   Количество клиентов: {final_clients}")
    
    if latest_client:
        print(f"   Последний клиент: {latest_client['filename']}")
        print(f"   UUID: {latest_client['uuid']}")
        print(f"   Создан: {latest_client['created_time']}")
    
    # Шаг 4: Анализ результатов
    print(f"\n📈 Шаг 4: Анализ результатов")
    
    pid_changed = initial_pid != final_pid
    clients_increased = final_clients > initial_clients
    port_listening = final_port
    status_active = final_status == "active"
    
    print(f"   PID изменился: {'✅ Да' if pid_changed else '❌ Нет'}")
    print(f"   Клиентов стало больше: {'✅ Да' if clients_increased else '❌ Нет'}")
    print(f"   Порт 443 слушает: {'✅ Да' if port_listening else '❌ Нет'}")
    print(f"   Xray активен: {'✅ Да' if status_active else '❌ Нет'}")
    
    # Шаг 5: Проверяем логи
    print(f"\n📋 Шаг 5: Проверка логов")
    try:
        log_result = subprocess.run([
            'journalctl', '-u', 'xray', '-n', '10', '--no-pager'
        ], capture_output=True, text=True, timeout=30)
        
        if log_result.returncode == 0:
            print("✅ Логи получены:")
            for line in log_result.stdout.split('\n')[-5:]:
                if line.strip():
                    print(f"   {line}")
        else:
            print("⚠️ Не удалось получить логи")
    except Exception as e:
        print(f"⚠️ Ошибка получения логов: {e}")
    
    # Итоговый результат
    print(f"\n🎯 ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("=" * 60)
    
    success_criteria = [
        pid_changed,      # Xray перезапустился
        clients_increased, # Клиент добавлен
        port_listening,    # Порт слушает
        status_active      # Сервис активен
    ]
    
    success_count = sum(success_criteria)
    total_criteria = len(success_criteria)
    
    if success_count == total_criteria:
        print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("✅ Автоматический перезапуск Xray работает корректно")
        print("✅ Новые клиенты добавляются автоматически")
        print("✅ Сервис остается стабильным")
    elif success_count >= total_criteria * 0.75:
        print("⚠️ ТЕСТ ПРОЙДЕН ЧАСТИЧНО")
        print(f"✅ Выполнено {success_count}/{total_criteria} критериев")
        print("💡 Есть небольшие проблемы, но основная функциональность работает")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН")
        print(f"❌ Выполнено только {success_count}/{total_criteria} критериев")
        print("💡 Требуется дополнительная диагностика")
    
    # Рекомендации
    print(f"\n💡 Рекомендации:")
    if not pid_changed:
        print("   • Xray не перезапустился - проверьте скрипт safe_restart.py")
    if not clients_increased:
        print("   • Клиент не добавлен - проверьте права доступа к директории")
    if not port_listening:
        print("   • Порт 443 не слушает - проверьте конфигурацию")
    if not status_active:
        print("   • Xray не активен - проверьте логи systemd")
    
    return success_count == total_criteria

def main():
    """Главная функция"""
    print("🚀 Запуск теста автоматического перезапуска Xray")
    print("=" * 60)
    
    success = test_auto_restart()
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 Тест завершен успешно!")
        print("💡 Автоматический перезапуск Xray работает корректно")
    else:
        print("⚠️ Тест завершен с проблемами")
        print("💡 Проверьте логи и настройки")
    
    print(f"\n📅 Время тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 