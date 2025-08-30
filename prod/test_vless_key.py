#!/usr/bin/env python3
"""
Скрипт для тестирования VLESS ключа
"""

import json
import subprocess
import time
from urllib.parse import urlparse, parse_qs

def parse_vless_url(vless_url):
    """Парсит VLESS URL и извлекает параметры"""
    try:
        # Убираем префикс vless://
        if vless_url.startswith('vless://'):
            vless_url = vless_url[8:]
        
        # Разделяем на адрес и параметры
        if '?' in vless_url:
            address_part, params_part = vless_url.split('?', 1)
        else:
            address_part = vless_url
            params_part = ""
        
        # Парсим адрес
        if '@' in address_part:
            uuid, server_part = address_part.split('@', 1)
        else:
            uuid = address_part
            server_part = ""
        
        if ':' in server_part:
            host, port = server_part.split(':', 1)
            port = int(port)
        else:
            host = server_part
            port = 443
        
        # Парсим параметры
        params = parse_qs(params_part)
        
        # Извлекаем значения
        result = {
            'uuid': uuid,
            'host': host,
            'port': port,
            'type': params.get('type', ['tcp'])[0],
            'security': params.get('security', [''])[0],
            'encryption': params.get('encryption', [''])[0],
            'flow': params.get('flow', [''])[0],
            'sni': params.get('sni', [''])[0],
            'fp': params.get('fp', [''])[0],
            'pbk': params.get('pbk', [''])[0],
            'sid': params.get('sid', [''])[0]
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка парсинга VLESS URL: {e}")
        return None

def test_connection(host, port, timeout=5):
    """Тестирует TCP подключение к серверу"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"❌ Ошибка тестирования подключения: {e}")
        return False

def check_client_file(uuid):
    """Проверяет существование файла клиента"""
    client_file = f"xray/clients/{uuid}.json"
    try:
        with open(client_file, 'r') as f:
            client_data = json.load(f)
        return client_data
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"❌ Ошибка чтения файла клиента: {e}")
        return None

def check_reality_config(uuid, short_id):
    """Проверяет конфигурацию REALITY"""
    try:
        # Проверяем final_config.json
        with open('xray/final_config.json', 'r') as f:
            config = json.load(f)
        
        # Проверяем наличие клиента
        clients = config.get('inbounds', [{}])[0].get('settings', {}).get('clients', [])
        client_found = any(client.get('id') == uuid for client in clients)
        
        # Проверяем REALITY настройки
        reality_settings = config.get('inbounds', [{}])[0].get('streamSettings', {}).get('realitySettings', {})
        short_ids = reality_settings.get('shortIds', [])
        # Убираем комментарий из short_id для сравнения
        clean_short_id = short_id.split('#')[0] if '#' in short_id else short_id
        short_id_found = clean_short_id in short_ids
        
        # Проверяем публичный ключ
        public_key = reality_settings.get('publicKey', '')
        
        return {
            'client_found': client_found,
            'short_id_found': short_id_found,
            'public_key': public_key,
            'reality_enabled': bool(reality_settings)
        }
        
    except Exception as e:
        print(f"❌ Ошибка проверки конфигурации: {e}")
        return None

def main():
    """Главная функция"""
    # VLESS ключ для тестирования
    vless_url = "vless://2b1fea4d-8273-471e-8d2d-8f3fa58ddfe3@146.103.125.210:443?type=tcp&security=reality&encryption=none&flow=xtls-rprx-vision&sni=www.cloudflare.com&fp=random&pbk=kjMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ&sid=428ef030#VPNBot_user_5406831921"
    
    print("🔍 Анализ VLESS ключа")
    print("=" * 50)
    
    # Парсим URL
    params = parse_vless_url(vless_url)
    if not params:
        return
    
    print(f"🔑 UUID: {params['uuid']}")
    print(f"🌐 Сервер: {params['host']}:{params['port']}")
    print(f"🔒 Безопасность: {params['security']}")
    print(f"📡 Тип: {params['type']}")
    print(f"🔐 Шифрование: {params['encryption']}")
    print(f"🌊 Flow: {params['flow']}")
    print(f"🎯 SNI: {params['sni']}")
    print(f"👆 Fingerprint: {params['fp']}")
    print(f"🔑 Публичный ключ: {params['pbk'][:20]}...")
    print(f"🆔 Short ID: {params['sid']}")
    
    print("\n" + "=" * 50)
    print("🔍 ПРОВЕРКА КОНФИГУРАЦИИ")
    print("=" * 50)
    
    # Проверяем файл клиента
    client_data = check_client_file(params['uuid'])
    if client_data:
        print(f"✅ Файл клиента найден")
        print(f"   Flow: {client_data.get('flow')}")
        print(f"   Short ID: {client_data.get('shortId')}")
        print(f"   Создан: {client_data.get('_metadata', {}).get('created_at')}")
        print(f"   Имя: {client_data.get('_metadata', {}).get('client_name')}")
    else:
        print(f"❌ Файл клиента не найден")
        return
    
    # Проверяем конфигурацию REALITY
    reality_config = check_reality_config(params['uuid'], params['sid'])
    if reality_config:
        print(f"\n🔒 REALITY конфигурация:")
        print(f"   Клиент в конфиге: {'✅' if reality_config['client_found'] else '❌'}")
        print(f"   Short ID в конфиге: {'✅' if reality_config['short_id_found'] else '❌'}")
        print(f"   REALITY включен: {'✅' if reality_config['reality_enabled'] else '❌'}")
        # Публичный ключ не должен быть в конфигурации сервера
        print(f"   ℹ️ Публичный ключ не включен в конфигурацию сервера (это нормально)")
        print(f"   ℹ️ Клиент использует публичный ключ: {params['pbk'][:20]}...")
    
    print("\n" + "=" * 50)
    print("🌐 ПРОВЕРКА ПОДКЛЮЧЕНИЯ")
    print("=" * 50)
    
    # Тестируем подключение
    if test_connection(params['host'], params['port']):
        print(f"✅ TCP подключение к {params['host']}:{params['port']} успешно")
    else:
        print(f"❌ TCP подключение к {params['host']}:{params['port']} не удалось")
    
    # Проверяем статус Xray
    try:
        result = subprocess.run(['systemctl', 'is-active', 'xray'], 
                              capture_output=True, text=True, timeout=10)
        if result.stdout.strip() == 'active':
            print(f"✅ Xray сервис активен")
        else:
            print(f"❌ Xray сервис не активен: {result.stdout.strip()}")
    except Exception as e:
        print(f"⚠️ Не удалось проверить статус Xray: {e}")
    
    # Проверяем прослушивание порта
    try:
        result = subprocess.run(['netstat', '-tlnp'], 
                              capture_output=True, text=True, timeout=10)
        if ':443' in result.stdout and 'xray' in result.stdout:
            print(f"✅ Xray слушает порт 443")
        else:
            print(f"❌ Xray не слушает порт 443")
    except Exception as e:
        print(f"⚠️ Не удалось проверить прослушивание порта: {e}")
    
    print("\n" + "=" * 50)
    print("📋 ЗАКЛЮЧЕНИЕ")
    print("=" * 50)
    
    # Формируем заключение
    issues = []
    
    if not client_data:
        issues.append("Файл клиента не найден")
    
    if reality_config:
        if not reality_config['client_found']:
            issues.append("Клиент не найден в конфигурации")
        if not reality_config['short_id_found']:
            issues.append("Short ID не найден в REALITY настройках")
        if not reality_config['reality_enabled']:
            issues.append("REALITY не включен")
        # Публичный ключ не проверяем, так как его не должно быть в конфигурации сервера
    
    if not test_connection(params['host'], params['port']):
        issues.append("Не удается подключиться к серверу")
    
    if issues:
        print(f"❌ Обнаружены проблемы:")
        for issue in issues:
            print(f"   • {issue}")
        print(f"\n💡 Рекомендации:")
        print(f"   1. Пересоберите конфигурацию: python3 xray/build_config.py")
        print(f"   2. Перезапустите Xray: systemctl restart xray")
        print(f"   3. Проверьте логи: journalctl -u xray -f")
    else:
        print(f"✅ VLESS ключ настроен корректно!")
        print(f"   Все компоненты на месте")
        print(f"   Конфигурация актуальна")
        print(f"   Сервер доступен")
        print(f"\n🎉 Ключ готов к использованию!")

if __name__ == "__main__":
    main() 