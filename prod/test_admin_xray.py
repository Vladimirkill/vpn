#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации новой функциональности управления Xray в админке
"""

import subprocess
import sys
import time
sys.path.append('/var/www/vpn')

from manage_user_limits import reload_xray_config, cleanup_expired_keys

def test_xray_status():
    """Тестирует проверку статуса Xray"""
    print("📊 Проверка статуса Xray...")
    
    try:
        # Проверяем статус службы
        status_result = subprocess.run([
            'systemctl', 'is-active', 'xray'
        ], capture_output=True, text=True, timeout=10)
        
        is_active = status_result.returncode == 0
        status_text = "🟢 Активен" if is_active else "🔴 Неактивен"
        
        # Получаем PID процесса
        pid_result = subprocess.run([
            'systemctl', 'show', 'xray', '--property=MainPID'
        ], capture_output=True, text=True, timeout=10)
        
        pid = "Неизвестен"
        if pid_result.returncode == 0:
            pid_line = pid_result.stdout.strip()
            if "MainPID=" in pid_line:
                pid = pid_line.split("=")[1]
                if pid == "0":
                    pid = "Не запущен"
        
        print(f"   Статус: {status_text}")
        print(f"   PID: {pid}")
        
        return is_active
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_xray_reload():
    """Тестирует перезагрузку конфигурации Xray"""
    print("🔧 Тестирование перезагрузки конфигурации...")
    
    try:
        success = reload_xray_config()
        if success:
            print("   ✅ Конфигурация успешно перезагружена")
        else:
            print("   ❌ Ошибка перезагрузки конфигурации")
        return success
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_xray_restart():
    """Тестирует перезапуск Xray"""
    print("🔄 Тестирование перезапуска Xray...")
    
    try:
        # Перезапускаем Xray
        restart_result = subprocess.run([
            'systemctl', 'restart', 'xray'
        ], capture_output=True, text=True, timeout=30)
        
        if restart_result.returncode == 0:
            # Ждем немного и проверяем статус
            time.sleep(2)
            
            status_result = subprocess.run([
                'systemctl', 'is-active', 'xray'
            ], capture_output=True, text=True, timeout=10)
            
            if status_result.returncode == 0:
                print("   ✅ Xray успешно перезапущен")
                return True
            else:
                print("   ⚠️ Xray перезапущен, но не активен")
                return False
        else:
            error_msg = restart_result.stderr.strip() if restart_result.stderr else "Неизвестная ошибка"
            print(f"   ❌ Ошибка перезапуска: {error_msg}")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_cleanup_expired():
    """Тестирует очистку просроченных ключей"""
    print("🧹 Тестирование очистки просроченных ключей...")
    
    try:
        removed_keys = cleanup_expired_keys()
        
        if removed_keys:
            print(f"   ✅ Удалено {len(removed_keys)} просроченных ключей")
            for key_info in removed_keys[:3]:  # Показываем первые 3
                print(f"      • {key_info}")
            if len(removed_keys) > 3:
                print(f"      ... и еще {len(removed_keys) - 3} ключей")
        else:
            print("   ✅ Просроченных ключей не найдено")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_xray_logs():
    """Тестирует получение логов Xray"""
    print("📋 Тестирование получения логов Xray...")
    
    try:
        logs_result = subprocess.run([
            'journalctl', '-u', 'xray', '--no-pager', '-n', '5', '--reverse'
        ], capture_output=True, text=True, timeout=15)
        
        if logs_result.returncode == 0:
            logs = logs_result.stdout.strip()
            if logs:
                print("   ✅ Логи получены успешно")
                print("   Последние записи:")
                for line in logs.split('\n')[:3]:
                    if line.strip():
                        print(f"      {line[:80]}...")
            else:
                print("   ⚠️ Логи пусты")
            return True
        else:
            print(f"   ❌ Ошибка получения логов")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🧪 Тестирование функций управления Xray для админки бота")
    print("=" * 60)
    
    tests = [
        ("Статус Xray", test_xray_status),
        ("Перезагрузка конфигурации", test_xray_reload),
        ("Перезапуск Xray", test_xray_restart),
        ("Очистка просроченных ключей", test_cleanup_expired),
        ("Получение логов", test_xray_logs)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"   ❌ Критическая ошибка: {e}")
    
    print(f"\n📊 Результаты тестирования:")
    print(f"   Пройдено: {passed}/{total}")
    print(f"   Статус: {'✅ Все тесты пройдены' if passed == total else '⚠️ Есть проблемы'}")
    
    if passed == total:
        print("\n🎉 Функциональность управления Xray готова к использованию в админке бота!")
    else:
        print(f"\n⚠️ Необходимо исправить {total - passed} проблем(ы)")

if __name__ == "__main__":
    main()