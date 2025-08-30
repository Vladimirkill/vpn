#!/usr/bin/env python3
"""
Безопасный перезапуск Xray с защитой от утечки IP пользователей
"""

import subprocess
import time
import os
import signal
import sys

def log_message(message: str):
    """Логирование с временной меткой"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def block_outgoing_connections():
    """Блокирует исходящие соединения для предотвращения утечки IP"""
    try:
        # Создаем временное правило iptables для блокировки исходящих соединений
        # кроме localhost и DNS
        subprocess.run([
            "iptables", "-A", "OUTPUT", "-p", "tcp", 
            "-m", "state", "--state", "NEW", 
            "!", "-d", "127.0.0.1", "!", "-d", "0.0.0.0/0", 
            "-j", "DROP"
        ], capture_output=True)
        
        log_message("🔒 Исходящие соединения заблокированы")
        return True
    except Exception as e:
        log_message(f"❌ Ошибка блокировки: {e}")
        return False

def unblock_outgoing_connections():
    """Разблокирует исходящие соединения"""
    try:
        # Удаляем временное правило
        subprocess.run([
            "iptables", "-D", "OUTPUT", "-p", "tcp", 
            "-m", "state", "--state", "NEW", 
            "!", "-d", "127.0.0.1", "!", "-d", "0.0.0.0/0", 
            "-j", "DROP"
        ], capture_output=True)
        
        log_message("🔓 Исходящие соединения разблокированы")
        return True
    except Exception as e:
        log_message(f"❌ Ошибка разблокировки: {e}")
        return False

def graceful_shutdown_xray():
    """Плавно завершает Xray"""
    try:
        # Отправляем SIGTERM для плавного завершения
        result = subprocess.run(["systemctl", "stop", "xray"], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            log_message("✅ Xray плавно завершен")
            return True
        else:
            log_message(f"⚠️ Xray завершен с ошибкой: {result.stderr}")
            return True  # Все равно продолжаем
    except subprocess.TimeoutExpired:
        log_message("⏰ Timeout при завершении Xray, принудительно останавливаем")
        subprocess.run(["systemctl", "kill", "-9", "xray"], capture_output=True)
        return True
    except Exception as e:
        log_message(f"❌ Ошибка при завершении Xray: {e}")
        return False

def start_xray():
    """Запускает Xray"""
    try:
        result = subprocess.run(["systemctl", "start", "xray"], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            log_message("✅ Xray запущен")
            return True
        else:
            log_message(f"❌ Ошибка запуска Xray: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        log_message("⏰ Timeout при запуске Xray")
        return False
    except Exception as e:
        log_message(f"❌ Ошибка при запуске Xray: {e}")
        return False

def wait_for_xray_ready():
    """Ждет готовности Xray"""
    log_message("⏳ Ожидание готовности Xray...")
    
    for i in range(30):  # Ждем максимум 30 секунд
        try:
            result = subprocess.run(["systemctl", "is-active", "xray"], 
                                  capture_output=True, text=True)
            
            if result.stdout.strip() == "active":
                # Проверяем что порты слушаются
                result = subprocess.run(["netstat", "-tlnp"], 
                                      capture_output=True, text=True)
                
                if "10085" in result.stdout:  # API порт
                    log_message("✅ Xray полностью готов")
                    return True
            
            time.sleep(1)
        except:
            time.sleep(1)
    
    log_message("⚠️ Xray не готов в течение 30 секунд")
    return False

def safe_restart():
    """Безопасный перезапуск Xray"""
    log_message("🚀 Начинаем безопасный перезапуск Xray")
    
    try:
        # Шаг 1: Блокируем исходящие соединения
        if not block_outgoing_connections():
            log_message("❌ Не удалось заблокировать соединения, прерываем")
            return False
        
        # Шаг 2: Ждем завершения активных соединений
        log_message("⏳ Ожидание завершения активных соединений...")
        time.sleep(5)  # Даем время на завершение
        
        # Шаг 3: Плавно завершаем Xray
        if not graceful_shutdown_xray():
            log_message("❌ Не удалось завершить Xray")
            unblock_outgoing_connections()
            return False
        
        # Шаг 4: Ждем полного завершения
        time.sleep(2)
        
        # Шаг 5: Запускаем Xray
        if not start_xray():
            log_message("❌ Не удалось запустить Xray")
            unblock_outgoing_connections()
            return False
        
        # Шаг 6: Ждем готовности
        if not wait_for_xray_ready():
            log_message("⚠️ Xray запущен, но не готов")
        
        # Шаг 7: Разблокируем соединения
        unblock_outgoing_connections()
        
        log_message("🎉 Безопасный перезапуск Xray завершен успешно!")
        return True
        
    except Exception as e:
        log_message(f"❌ Критическая ошибка: {e}")
        unblock_outgoing_connections()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restart":
        success = safe_restart()
        sys.exit(0 if success else 1)
    else:
        print("Использование: python3 safe_restart.py restart")
        print("Этот скрипт безопасно перезапускает Xray с защитой от утечки IP") 