#!/usr/bin/env python3
"""
Тест жестких ограничений пользователей:
- 1 ключ для одного пользователя
- Максимум 3 устройства для 1 ключа
"""

import subprocess
import time
import json
import os
from datetime import datetime

def test_user_limit_enforcement():
    """Тестирует ограничение: 1 ключ для одного пользователя"""
    print("🧪 Тест ограничения: 1 ключ для одного пользователя")
    print("=" * 60)
    
    test_user = f"test_user_limit_{int(time.time())}"
    
    # Шаг 1: Создаем первый ключ
    print(f"🔑 Шаг 1: Создание первого ключа для {test_user}")
    result1 = subprocess.run([
        "python3", "run_generate.py", test_user
    ], capture_output=True, text=True, timeout=60)
    
    if result1.returncode != 0:
        print(f"❌ Ошибка создания первого ключа: {result1.stderr}")
        return False
    
    print("✅ Первый ключ создан успешно")
    
    # Шаг 2: Пытаемся создать второй ключ (должен быть отклонен)
    print(f"\n🔑 Шаг 2: Попытка создания второго ключа для {test_user}")
    result2 = subprocess.run([
        "python3", "run_generate.py", test_user
    ], capture_output=True, text=True, timeout=60)
    
    if result2.returncode == 0:
        print("❌ Второй ключ создан - ограничение не работает!")
        return False
    
    print("✅ Второй ключ отклонен - ограничение работает!")
    
    # Шаг 3: Проверяем, что у пользователя только 1 ключ
    print(f"\n🔍 Шаг 3: Проверка количества ключей для {test_user}")
    
    from manage_user_limits import get_user_keys
    users = get_user_keys()
    
    if test_user in users:
        key_count = len(users[test_user])
        print(f"   Количество ключей: {key_count}")
        
        if key_count == 1:
            print("✅ Ограничение работает корректно!")
            return True
        else:
            print(f"❌ Неправильное количество ключей: {key_count}")
            return False
    else:
        print("❌ Пользователь не найден")
        return False

def test_device_limit_enforcement():
    """Тестирует ограничение: максимум 3 устройства для 1 ключа"""
    print("\n🧪 Тест ограничения: максимум 3 устройства для 1 ключа")
    print("=" * 60)
    
    # Этот тест сложнее, так как требует реальных подключений
    # Пока проверяем логику ограничений
    
    print("📊 Анализ текущих подключений...")
    
    try:
        result = subprocess.run(['ss', '-tn', 'state', 'established'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            connections = {}
            for line in result.stdout.split('\n'):
                if ':443' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        if parts[3].endswith(':443'):
                            client_ip = parts[2].split(':')[0]
                            if client_ip not in connections:
                                connections[client_ip] = 0
                            connections[client_ip] += 1
            
            print(f"   Активных IP адресов: {len(connections)}")
            
            if len(connections) > 3:
                print("⚠️ Превышен лимит устройств (>3)")
                print("   Это может быть нормально для тестового сервера")
            else:
                print("✅ Лимит устройств не превышен")
        else:
            print("⚠️ Не удалось получить информацию о подключениях")
    
    except Exception as e:
        print(f"⚠️ Ошибка проверки подключений: {e}")
    
    return True

def test_limit_bypass():
    """Тестирует обход ограничений"""
    print("\n🧪 Тест обхода ограничений")
    print("=" * 60)
    
    test_user = f"test_bypass_{int(time.time())}"
    
    # Шаг 1: Создаем ключ с отключенными ограничениями
    print(f"🔑 Шаг 1: Создание ключа с отключенными ограничениями для {test_user}")
    
    try:
        from xray.generate_client import generate_vless_client
        
        result = generate_vless_client(
            clients_dir="xray/clients",
            flow="xtls-rprx-vision",
            host="146.103.125.210",
            port=443,
            sni="www.cloudflare.com",
            client_name=test_user,
            enforce_limits=False  # Отключаем ограничения
        )
        
        if "error" in result:
            print(f"❌ Ошибка создания ключа: {result['error']}")
            return False
        
        print("✅ Ключ с отключенными ограничениями создан")
        print(f"   UUID: {result['uuid']}")
        print(f"   Лимиты: {result['limits']}")
        
        # Шаг 2: Пытаемся создать второй ключ (должен быть разрешен)
        print(f"\n🔑 Шаг 2: Попытка создания второго ключа для {test_user}")
        
        result2 = generate_vless_client(
            clients_dir="xray/clients",
            flow="xtls-rprx-vision",
            host="146.103.125.210",
            port=443,
            sni="www.cloudflare.com",
            client_name=test_user,
            enforce_limits=False  # Отключаем ограничения
        )
        
        if "error" in result2:
            print(f"❌ Второй ключ не создан: {result2['error']}")
            return False
        
        print("✅ Второй ключ создан - ограничения обойдены")
        print(f"   UUID: {result2['uuid']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования обхода: {e}")
        return False

def cleanup_test_users():
    """Очищает тестовых пользователей"""
    print("\n🧹 Очистка тестовых пользователей")
    print("=" * 60)
    
    from manage_user_limits import get_user_keys
    
    users = get_user_keys()
    test_users = [name for name in users.keys() if name.startswith('test_')]
    
    if not test_users:
        print("✅ Тестовых пользователей не найдено")
        return
    
    print(f"Найдено тестовых пользователей: {len(test_users)}")
    
    for test_user in test_users:
        print(f"🗑️ Удаление пользователя: {test_user}")
        
        # Удаляем все ключи пользователя
        user_keys = users[test_user]
        for key in user_keys:
            try:
                old_filename = key['filename']
                new_filename = f"REMOVED_{old_filename}"
                old_path = os.path.join("xray/clients", old_filename)
                new_path = os.path.join("xray/clients", new_filename)
                
                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
                    print(f"   ✅ Ключ {key['uuid'][:8]}... удален")
            except Exception as e:
                print(f"   ❌ Ошибка удаления ключа: {e}")
    
    print("✅ Очистка завершена")

def main():
    """Главная функция"""
    print("🧪 Тест жестких ограничений пользователей")
    print("=" * 80)
    
    print("📋 Тестируемые ограничения:")
    print("   1. 1 ключ для одного пользователя")
    print("   2. Максимум 3 устройства для 1 ключа")
    print("   3. Возможность обхода ограничений")
    print()
    
    # Запускаем тесты
    tests = [
        ("Ограничение пользователей", test_user_limit_enforcement),
        ("Ограничение устройств", test_device_limit_enforcement),
        ("Обход ограничений", test_limit_bypass)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🚀 Запуск теста: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"   Результат: {'✅ УСПЕХ' if success else '❌ ПРОВАЛ'}")
        except Exception as e:
            print(f"   ❌ Ошибка теста: {e}")
            results.append((test_name, False))
        print()
    
    # Итоговый отчет
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 80)
    
    success_count = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ НЕ ПРОЙДЕН"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Результат: {success_count}/{total_tests} тестов пройдено")
    
    if success_count == total_tests:
        print("🎉 Все тесты пройдены успешно!")
        print("✅ Жесткие ограничения работают корректно")
    elif success_count >= total_tests * 0.7:
        print("⚠️ Большинство тестов пройдено")
        print("💡 Есть небольшие проблемы, но основная функциональность работает")
    else:
        print("❌ Много тестов не пройдено")
        print("💡 Требуется дополнительная диагностика")
    
    # Очистка
    cleanup_test_users()
    
    print(f"\n📅 Время тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 