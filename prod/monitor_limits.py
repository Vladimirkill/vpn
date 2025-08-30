#!/usr/bin/env python3
"""
Скрипт мониторинга лимитов подключений Xray VLESS клиентов.
Проверяет количество активных соединений для каждого клиента
и принимает действия при превышении лимитов.
"""

import subprocess
import json
import os
import sys
from datetime import datetime

# Пути к конфигурации
CLIENTS_DIR = "/var/www/vpn/xray/clients"
LOG_FILE = "/var/www/vpn/monitor_limits.log"

def log_message(message):
    """Записывает сообщение в лог с временной меткой"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except:
        pass  # Игнорируем ошибки записи в лог
    
    print(log_entry.strip())

def get_active_connections():
    """Получает список активных соединений на порту 443"""
    connections = {}
    
    try:
        result = subprocess.run(['netstat', '-tn'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ':443' in line and 'ESTABLISHED' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        local_addr = parts[3]
                        remote_addr = parts[4]
                        
                        if ':443' in local_addr:
                            client_ip = remote_addr.split(':')[0]
                            if client_ip not in connections:
                                connections[client_ip] = 0
                            connections[client_ip] += 1
    except Exception as e:
        log_message(f"Ошибка получения соединений: {e}")
    
    return connections

def get_client_limits():
    """Читает лимиты клиентов из их конфигурационных файлов"""
    client_limits = {}
    
    if not os.path.exists(CLIENTS_DIR):
        log_message(f"Директория клиентов не найдена: {CLIENTS_DIR}")
        return client_limits
    
    for filename in os.listdir(CLIENTS_DIR):
        if filename.endswith('.json'):
            client_file = os.path.join(CLIENTS_DIR, filename)
            try:
                with open(client_file, 'r') as f:
                    client_data = json.load(f)
                    client_id = client_data.get('id')
                    metadata = client_data.get('_metadata', {})
                    max_connections = metadata.get('max_connections', 3)
                    client_name = metadata.get('client_name', 'unknown')
                    
                    if client_id:
                        client_limits[client_id] = {
                            'max_connections': max_connections,
                            'name': client_name,
                            'filename': filename
                        }
            except Exception as e:
                log_message(f"Ошибка чтения файла {filename}: {e}")
    
    return client_limits

def disable_client(client_id, filename):
    """Временно отключает клиента, переименовав его файл"""
    try:
        client_file = os.path.join(CLIENTS_DIR, filename)
        disabled_file = os.path.join(CLIENTS_DIR, f"DISABLED_{filename}")
        
        if os.path.exists(client_file):
            os.rename(client_file, disabled_file)
            log_message(f"Клиент {client_id} отключен (превышен лимит)")
            return True
    except Exception as e:
        log_message(f"Ошибка отключения клиента {client_id}: {e}")
    
    return False

def enable_client(client_id, filename):
    """Включает отключенного клиента"""
    try:
        disabled_file = os.path.join(CLIENTS_DIR, f"DISABLED_{filename}")
        client_file = os.path.join(CLIENTS_DIR, filename)
        
        if os.path.exists(disabled_file):
            os.rename(disabled_file, client_file)
            log_message(f"Клиент {client_id} включен")
            return True
    except Exception as e:
        log_message(f"Ошибка включения клиента {client_id}: {e}")
    
    return False

def reload_xray():
    """Перезагружает конфигурацию Xray"""
    try:
        result = subprocess.run(['systemctl', 'reload', 'xray'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            log_message("Конфигурация Xray перезагружена")
            return True
        else:
            log_message(f"Ошибка перезагрузки Xray: {result.stderr}")
    except Exception as e:
        log_message(f"Ошибка перезагрузки Xray: {e}")
    
    return False

def main():
    """Основная функция мониторинга"""
    log_message("=== Запуск мониторинга лимитов ===")
    
    # Получаем активные соединения
    connections = get_active_connections()
    log_message(f"Найдено {len(connections)} уникальных IP с соединениями")
    
    # Получаем лимиты клиентов
    client_limits = get_client_limits()
    log_message(f"Загружено {len(client_limits)} клиентов с лимитами")
    
    # Проверяем нарушения (упрощенная логика)
    # В реальности нужно точное сопоставление UUID -> IP соединения
    violations = []
    
    # Простой алгоритм: если общее количество соединений больше суммы лимитов
    total_connections = sum(connections.values())
    total_limit = sum(client['max_connections'] for client in client_limits.values())
    
    if total_connections > total_limit:
        log_message(f"⚠️ Превышен общий лимит: {total_connections} > {total_limit}")
        # Можно добавить более сложную логику управления
    
    # Для демонстрации просто выводим статистику
    for ip, conn_count in connections.items():
        log_message(f"IP {ip}: {conn_count} соединений")
    
    log_message("=== Мониторинг завершен ===")

if __name__ == "__main__":
    main()