#!/usr/bin/env python3
"""
Скрипт для тестирования существующих VLESS ключей
"""

import json
import subprocess
import socket
import time
from pathlib import Path

def load_reality_config():
    """Загружает конфигурацию REALITY"""
    try:
        with open('xray/reality.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки REALITY конфигурации: {e}")
        return None

def generate_vless_url(client_id, short_id, host, public_key, client_name, port=443):
    """Генерирует VLESS URL для клиента"""
    display_name = f"VPNBot_{client_name}".replace(" ", "_")
    vless_link = (
        f"vless://{client_id}@{host}:8443"
        f"?type=tcp"
        f"&security=reality"
        f"&encryption=none"
        f"&flow=xtls-rprx-vision"
        f"&sni=www.apple.com"
        f"&fp=safari"
        f"&pbk={public_key}"
        f"&sid={short_id}"
        f"#{display_name}"
    )
    return vless_link

def test_tcp_connection(host, port, timeout=5):
    """Тестирует TCP подключение"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_xray_status():
    """Проверяет статус Xray сервиса"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'xray'], 
                              capture_output=True, text=True, timeout=10)
        return result.stdout.strip() == 'active'
    except Exception:
        return False

def check_port_listening(port=443):
    """Проверяет, слушается ли порт"""
    try:
        result = subprocess.run(['netstat', '-tlnp'], 
                              capture_output=True, text=True, timeout=10)
        return f':{port}' in result.stdout and 'xray' in result.stdout
    except Exception:
        return False

def test_client(client_file, reality_config, server_ip='146.103.125.210'):
    """Тестирует одного клиента"""
    try:
        with open(client_file, 'r') as f:
            client_data = json.load(f)
        
        client_id = client_data['id']
        short_id = client_data['shortId']
        client_name = client_data.get('_metadata', {}).get('client_name', 'unknown')
        
        print(f"\n🔍 Тестирование клиента: {client_name}")
        print(f"   UUID: {client_id}")
        print(f"   Short ID: {short_id}")
        
        # Генерируем VLESS URL
        vless_url = generate_vless_url(
            client_id, 
            short_id, 
            server_ip, 
            reality_config['publicKey'], 
            client_name
        )
        
        print(f"   VLESS URL: {vless_url[:80]}...")
        
        # Проверяем конфигурацию
        issues = []
        
        # Проверяем наличие в final_config.json
        try:
            with open('xray/final_config.json', 'r') as f:
                config = json.load(f)
            
            clients = config.get('inbounds', [{}])[0].get('settings', {}).get('clients', [])
            client_found = any(client.get('id') == client_id for client in clients)
            
            if client_found:
                print(f"   ✅ Клиент найден в конфигурации")
            else:
                print(f"   ❌ Клиент НЕ найден в конфигурации")
                issues.append("Клиент не в конфигурации")
            
            # Проверяем Short ID
            reality_settings = config.get('inbounds', [{}])[0].get('streamSettings', {}).get('realitySettings', {})
            short_ids = reality_settings.get('shortIds', [])
            
            if short_id in short_ids:
                print(f"   ✅ Short ID найден в REALITY настройках")
            else:
                print(f"   ❌ Short ID НЕ найден в REALITY настройках")
                issues.append("Short ID не в REALITY")
                
        except Exception as e:
            print(f"   ❌ Ошибка проверки конфигурации: {e}")
            issues.append("Ошибка конфигурации")
        
        return {
            'client_name': client_name,
            'uuid': client_id,
            'short_id': short_id,
            'vless_url': vless_url,
            'issues': issues,
            'status': 'OK' if not issues else 'ISSUES'
        }
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования клиента: {e}")
        return None

def main():
    """Главная функция"""
    print("🚀 Тестирование работоспособности VLESS ключей")
    print("=" * 60)
    
    # Проверяем статус Xray
    print("🔍 Проверка статуса Xray...")
    if check_xray_status():
        print("✅ Xray сервис активен")
    else:
        print("❌ Xray сервис НЕ активен")
        return
    
    # Проверяем прослушивание порта
    if check_port_listening(443):
        print("✅ Xray слушает порт 443")
    else:
        print("❌ Xray НЕ слушает порт 443")
    
    # Проверяем TCP подключение
    server_ip = '146.103.125.210'
    if test_tcp_connection(server_ip, 8443):
        print(f"✅ TCP подключение к {server_ip}:8443 успешно")
    else:
        print(f"❌ TCP подключение к {server_ip}:8443 не удалось")
    
    # Загружаем REALITY конфигурацию
    reality_config = load_reality_config()
    if not reality_config:
        print("❌ Не удалось загрузить REALITY конфигурацию")
        return
    
    print(f"✅ REALITY конфигурация загружена")
    print(f"   Публичный ключ: {reality_config['publicKey'][:20]}...")
    
    # Получаем список клиентов
    clients_dir = Path('xray/clients')
    client_files = list(clients_dir.glob('*.json'))
    
    # Исключаем удаленных клиентов
    active_clients = [f for f in client_files if not f.name.startswith('REMOVED_')]
    
    print(f"\n📊 Найдено клиентов: {len(active_clients)}")
    
    # Тестируем первые 5 клиентов
    test_count = min(5, len(active_clients))
    print(f"🧪 Тестируем первых {test_count} клиентов...")
    
    results = []
    for i, client_file in enumerate(active_clients[:test_count]):
        result = test_client(client_file, reality_config, server_ip)
        if result:
            results.append(result)
    
    # Выводим итоги
    print("\n" + "=" * 60)
    print("📋 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    successful = [r for r in results if r['status'] == 'OK']
    with_issues = [r for r in results if r['status'] == 'ISSUES']
    
    print(f"✅ Успешно: {len(successful)}")
    print(f"❌ С проблемами: {len(with_issues)}")
    
    if with_issues:
        print(f"\n⚠️ Клиенты с проблемами:")
        for result in with_issues:
            print(f"   • {result['client_name']}: {', '.join(result['issues'])}")
    
    if successful:
        print(f"\n🎉 Рабочие VLESS ключи:")
        for result in successful[:2]:  # Показываем первые 2
            print(f"\n👤 {result['client_name']}:")
            print(f"   UUID: {result['uuid']}")
            print(f"   VLESS: {result['vless_url']}")
    
    # Рекомендации
    if with_issues:
        print(f"\n💡 Рекомендации для исправления проблем:")
        print(f"   1. Пересоберите конфигурацию: python3 xray/build_config.py")
        print(f"   2. Перезапустите Xray: systemctl restart xray")
        print(f"   3. Проверьте логи: journalctl -u xray -f")
    
    print(f"\n🔗 Для тестирования конкретного ключа используйте:")
    print(f"   python3 test_vless_key.py")

if __name__ == "__main__":
    main()