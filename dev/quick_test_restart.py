#!/usr/bin/env python3
"""
Быстрый тест перезапуска Xray
"""

import subprocess
import time

def quick_test():
    """Быстрый тест перезапуска"""
    print("🚀 Быстрый тест перезапуска Xray")
    print("=" * 40)
    
    # Проверяем текущий статус
    print("📊 Текущий статус:")
    status = subprocess.run(['systemctl', 'is-active', 'xray'], 
                          capture_output=True, text=True)
    print(f"   Xray: {status.stdout.strip()}")
    
    pid = subprocess.run(['systemctl', 'show', 'xray', '--property=MainPID'], 
                        capture_output=True, text=True)
    current_pid = pid.stdout.strip().split('=')[1] if 'MainPID=' in pid.stdout else 'unknown'
    print(f"   PID: {current_pid}")
    
    # Создаем тестового клиента
    print(f"\n🔑 Создание тестового клиента...")
    test_name = f"quick_test_{int(time.time())}"
    
    result = subprocess.run([
        "python3", "run_generate.py", test_name
    ], capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        print("✅ Клиент создан успешно")
        
        # Проверяем, изменился ли PID
        time.sleep(3)
        new_pid = subprocess.run(['systemctl', 'show', 'xray', '--property=MainPID'], 
                               capture_output=True, text=True)
        new_pid_value = new_pid.stdout.strip().split('=')[1] if 'MainPID=' in new_pid.stdout else 'unknown'
        
        print(f"\n📈 Результат:")
        print(f"   Старый PID: {current_pid}")
        print(f"   Новый PID: {new_pid_value}")
        
        if current_pid != new_pid_value:
            print("✅ Xray перезапустился!")
        else:
            print("⚠️ PID не изменился")
        
        # Проверяем порт
        port_check = subprocess.run(['ss', '-tn', 'state', 'listening'], 
                                  capture_output=True, text=True)
        if ':443' in port_check.stdout:
            print("✅ Порт 443 слушает")
        else:
            print("❌ Порт 443 не слушает")
            
    else:
        print(f"❌ Ошибка создания клиента: {result.stderr}")

if __name__ == "__main__":
    quick_test() 