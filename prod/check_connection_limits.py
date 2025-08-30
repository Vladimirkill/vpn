#!/usr/bin/env python3
"""
Скрипт для проверки лимитов подключений Xray VLESS клиентов
"""

import subprocess
import json
import os
from datetime import datetime

# Пути к конфигурации
CLIENTS_DIR = "/var/www/vpn/xray/clients"

def get_active_connections():
    """Получает список активных соединений на порту 443"""
    connections = {}
    
    try:
        # Используем ss для подсчета соединений на порту 443
        result = subprocess.run(['ss', '-tn', 'state', 'established'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ':443' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        # Формат: 0 0 146.103.125.210:32800 149.154.167.41:443
                        # Это исходящие соединения, нам нужны входящие на :443
                        if parts[3].endswith(':443'):
                            # Это входящее соединение на порт 443
                            client_ip = parts[2].split(':')[0]
                            if client_ip not in connections:
                                connections[client_ip] = 0
                            connections[client_ip] += 1
        
        # Если ss не работает, пробуем netstat
        if not connections:
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
        print(f"❌ Ошибка получения соединений: {e}")
    
    return connections

def get_client_limits():
    """Читает лимиты клиентов из их конфигурационных файлов"""
    client_limits = {}
    
    if not os.path.exists(CLIENTS_DIR):
        print(f"❌ Директория клиентов не найдена: {CLIENTS_DIR}")
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
                print(f"⚠️ Ошибка чтения файла {filename}: {e}")
    
    return client_limits

def check_disabled_clients():
    """Проверяет отключенных клиентов"""
    disabled_clients = []
    
    if not os.path.exists(CLIENTS_DIR):
        return disabled_clients
    
    for filename in os.listdir(CLIENTS_DIR):
        if filename.startswith('DISABLED_'):
            disabled_clients.append(filename)
    
    return disabled_clients

def main():
    """Главная функция"""
    print("🔍 Проверка лимитов подключений Xray")
    print("=" * 60)
    
    # Получаем активные соединения
    print("📊 Анализ активных соединений...")
    connections = get_active_connections()
    total_connections = sum(connections.values())
    unique_ips = len(connections)
    
    print(f"✅ Найдено {total_connections} активных соединений")
    print(f"✅ Уникальных IP адресов: {unique_ips}")
    
    # Получаем лимиты клиентов
    print("\n📋 Анализ лимитов клиентов...")
    client_limits = get_client_limits()
    total_clients = len(client_limits)
    total_limit = sum(client['max_connections'] for client in client_limits.values())
    
    print(f"✅ Всего клиентов: {total_clients}")
    print(f"✅ Общий лимит соединений: {total_limit}")
    
    # Проверяем отключенных клиентов
    print("\n🚫 Проверка отключенных клиентов...")
    disabled_clients = check_disabled_clients()
    if disabled_clients:
        print(f"⚠️ Найдено {len(disabled_clients)} отключенных клиентов:")
        for client in disabled_clients:
            print(f"   • {client}")
    else:
        print("✅ Отключенных клиентов нет")
    
    # Анализ использования
    print("\n📈 Анализ использования лимитов...")
    usage_percentage = (total_connections / total_limit * 100) if total_limit > 0 else 0
    
    if usage_percentage > 90:
        status = "🔴 КРИТИЧЕСКИЙ"
    elif usage_percentage > 75:
        status = "🟡 ВЫСОКИЙ"
    elif usage_percentage > 50:
        status = "🟠 СРЕДНИЙ"
    else:
        status = "🟢 НОРМАЛЬНЫЙ"
    
    print(f"   Использование: {total_connections}/{total_limit} ({usage_percentage:.1f}%)")
    print(f"   Статус: {status}")
    
    # Детальная информация по клиентам
    print("\n🔍 Детальная информация по клиентам:")
    print("-" * 60)
    
    for client_id, client_data in client_limits.items():
        name = client_data['name']
        max_conn = client_data['max_connections']
        filename = client_data['filename']
        
        # Упрощенная логика: распределяем соединения между клиентами
        # В реальности нужно точное сопоставление UUID -> IP
        estimated_usage = min(total_connections // total_clients, max_conn)
        
        if estimated_usage >= max_conn:
            status = "🔴 ЛИМИТ"
        elif estimated_usage > max_conn * 0.8:
            status = "🟡 ВЫСОКО"
        else:
            status = "🟢 НОРМА"
        
        print(f"{status} {name:20} | {estimated_usage}/{max_conn} | {filename}")
    
    # Рекомендации
    print("\n💡 Рекомендации:")
    if usage_percentage > 90:
        print("   • Критически высокое использование - рассмотрите увеличение лимитов")
        print("   • Проверьте на предмет злоупотреблений")
    elif usage_percentage > 75:
        print("   • Высокое использование - мониторьте внимательно")
        print("   • Рассмотрите создание дополнительных клиентов")
    elif usage_percentage > 50:
        print("   • Среднее использование - система работает нормально")
    else:
        print("   • Низкое использование - можно создавать новых клиентов")
    
    # Информация о системе
    print("\n⚙️ Системная информация:")
    print(f"   • Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   • Директория клиентов: {CLIENTS_DIR}")
    print(f"   • Лимит по умолчанию: 3 соединения на клиента")
    
    # Проверяем systemd лимиты
    try:
        result = subprocess.run(['systemctl', 'show', 'xray'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'LimitNOFILE=' in line:
                    nofile_limit = line.split('=')[1]
                    print(f"   • Systemd NOFILE лимит: {nofile_limit}")
                    break
    except:
        print("   • Systemd лимиты: недоступно")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 