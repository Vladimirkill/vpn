#!/usr/bin/env python3
"""
API клиент для динамического управления пользователями Xray через gRPC API
Позволяет добавлять/удалять пользователей без перезапуска сервера
"""

import subprocess
import json
import tempfile
import os
from datetime import datetime

API_SERVER = "127.0.0.1:10085"  # Management port
INBOUND_TAG = "vless-main"  # Главный inbound для VLESS

def log_message(message: str):
    """Логирование с временной меткой"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def add_user_to_inbound(user_uuid: str, user_email: str = "") -> bool:
    """
    Добавляет пользователя в inbound через API без перезапуска
    
    Args:
        user_uuid: UUID пользователя
        user_email: Email пользователя (опционально)
    
    Returns:
        bool: True если успешно добавлен
    """
    try:
        # Создаем JSON с данными пользователя
        user_data = {
            "id": user_uuid,
            "flow": "xtls-rprx-vision",
            "level": 0,
            "email": user_email or f"user_{user_uuid[:8]}"
        }
        
        # Создаем временный файл с данными пользователя
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(user_data, f, indent=2)
            temp_file = f.name
        
        try:
            # Выполняем команду добавления пользователя
            result = subprocess.run([
                "xray", "api", "adi", 
                f"--server={API_SERVER}",
                f"--tag={INBOUND_TAG}",
                temp_file
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                log_message(f"✅ Пользователь {user_uuid[:8]}... добавлен через API")
                return True
            else:
                log_message(f"❌ Ошибка добавления пользователя: {result.stderr}")
                return False
                
        finally:
            # Удаляем временный файл
            os.unlink(temp_file)
            
    except subprocess.TimeoutExpired:
        log_message(f"⏰ Timeout при добавлении пользователя {user_uuid[:8]}...")
        return False
    except Exception as e:
        log_message(f"❌ Исключение при добавлении пользователя: {e}")
        return False

def remove_user_from_inbound(user_email: str) -> bool:
    """
    Удаляет пользователя из inbound через API
    
    Args:
        user_email: Email пользователя для удаления
    
    Returns:
        bool: True если успешно удален
    """
    try:
        # Выполняем команду удаления пользователя
        result = subprocess.run([
            "xray", "api", "rmi",
            f"--server={API_SERVER}",
            f"--tag={INBOUND_TAG}",
            f"--email={user_email}"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            log_message(f"✅ Пользователь {user_email} удален через API")
            return True
        else:
            log_message(f"❌ Ошибка удаления пользователя: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log_message(f"⏰ Timeout при удалении пользователя {user_email}")
        return False
    except Exception as e:
        log_message(f"❌ Исключение при удалении пользователя: {e}")
        return False

def list_inbound_users() -> list:
    """
    Получает список пользователей в inbound
    
    Returns:
        list: Список пользователей
    """
    try:
        result = subprocess.run([
            "xray", "api", "inbounduser",
            f"--server={API_SERVER}",
            f"--tag={INBOUND_TAG}"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            # Парсим вывод (формат может отличаться)
            users = []
            for line in result.stdout.splitlines():
                if line.strip():
                    users.append(line.strip())
            log_message(f"📊 Найдено пользователей в {INBOUND_TAG}: {len(users)}")
            return users
        else:
            log_message(f"❌ Ошибка получения списка: {result.stderr}")
            return []
            
    except Exception as e:
        log_message(f"❌ Исключение при получении списка: {e}")
        return []

def test_api_connection() -> bool:
    """
    Тестирует подключение к API
    
    Returns:
        bool: True если API доступен
    """
    try:
        result = subprocess.run([
            "xray", "api", "stats",
            f"--server={API_SERVER}"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            log_message("✅ API соединение работает")
            return True
        else:
            log_message(f"❌ API недоступен: {result.stderr}")
            return False
            
    except Exception as e:
        log_message(f"❌ Ошибка соединения с API: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование:")
        print(f"  {sys.argv[0]} test                    # Тест соединения")
        print(f"  {sys.argv[0]} add <uuid> [email]      # Добавить пользователя") 
        print(f"  {sys.argv[0]} remove <email>          # Удалить пользователя")
        print(f"  {sys.argv[0]} list                    # Список пользователей")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test":
        test_api_connection()
    elif command == "add" and len(sys.argv) >= 3:
        user_uuid = sys.argv[2]
        user_email = sys.argv[3] if len(sys.argv) > 3 else ""
        add_user_to_inbound(user_uuid, user_email)
    elif command == "remove" and len(sys.argv) >= 3:
        user_email = sys.argv[2]
        remove_user_from_inbound(user_email)
    elif command == "list":
        users = list_inbound_users()
        for user in users:
            print(user)
    else:
        print("❌ Неверная команда")
        sys.exit(1)