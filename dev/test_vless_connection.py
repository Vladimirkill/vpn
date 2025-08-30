#!/usr/bin/env python3
"""
Реальный тест VLESS подключения
"""

import socket
import ssl
import struct
import uuid
import json
import time
from urllib.parse import urlparse, parse_qs

def parse_vless_url(vless_url):
    """Парсит VLESS URL"""
    if not vless_url.startswith('vless://'):
        return None
    
    # Убираем префикс vless://
    url_part = vless_url[8:]
    
    # Парсим как обычный URL
    parsed = urlparse(f'http://{url_part}')
    params = parse_qs(parsed.query)
    
    return {
        'uuid': parsed.username,
        'host': parsed.hostname,
        'port': parsed.port or 443,
        'sni': params.get('sni', [''])[0],
        'sid': params.get('sid', [''])[0],
        'pbk': params.get('pbk', [''])[0],
        'flow': params.get('flow', [''])[0],
        'fp': params.get('fp', ['random'])[0]
    }

def create_vless_request(uuid_str, host):
    """Создает VLESS запрос"""
    # VLESS протокол версия 0
    version = b'\x00'
    
    # UUID (16 байт)
    uuid_bytes = uuid.UUID(uuid_str).bytes
    
    # Дополнительная информация (0 байт)
    addon_len = b'\x00'
    
    # Команда TCP (0x01)
    command = b'\x01'
    
    # Порт (2 байта, big endian)
    port = struct.pack('>H', 80)  # HTTP порт для теста
    
    # Адрес типа домен (0x02)
    addr_type = b'\x02'
    
    # Длина домена
    domain = host.encode('utf-8')
    domain_len = struct.pack('B', len(domain))
    
    # Собираем запрос
    request = version + uuid_bytes + addon_len + command + port + addr_type + domain_len + domain
    
    return request

def test_vless_connection(vless_url):
    """Тестирует VLESS подключение"""
    print(f"🧪 Тестирование VLESS подключения")
    print("=" * 50)
    
    # Парсим URL
    params = parse_vless_url(vless_url)
    if not params:
        print("❌ Неверный VLESS URL")
        return False
    
    print(f"📋 Параметры подключения:")
    print(f"   Host: {params['host']}:{params['port']}")
    print(f"   UUID: {params['uuid']}")
    print(f"   SNI: {params['sni']}")
    print(f"   Short ID: {params['sid']}")
    
    try:
        # Создаем TCP подключение
        print(f"\n🔌 Подключение к {params['host']}:{params['port']}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((params['host'], params['port']))
        print("✅ TCP подключение установлено")
        
        # Создаем TLS контекст
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Устанавливаем TLS с правильным SNI
        print(f"🔐 TLS handshake с SNI: {params['sni']}...")
        tls_sock = context.wrap_socket(sock, server_hostname=params['sni'])
        print("✅ TLS handshake успешен")
        
        # Отправляем VLESS запрос
        print("📤 Отправка VLESS запроса...")
        vless_request = create_vless_request(params['uuid'], 'httpbin.org')
        tls_sock.send(vless_request)
        
        # Отправляем HTTP запрос через VLESS туннель
        http_request = b"GET /ip HTTP/1.1\r\nHost: httpbin.org\r\n\r\n"
        tls_sock.send(http_request)
        
        # Читаем ответ
        print("📥 Ожидание ответа...")
        response = tls_sock.recv(4096)
        
        if response:
            print("✅ Получен ответ от сервера!")
            print(f"   Длина ответа: {len(response)} байт")
            
            # Проверяем содержимое ответа
            response_str = response.decode('utf-8', errors='ignore')
            if 'HTTP/' in response_str:
                print("✅ VLESS туннель работает!")
                return True
            elif 'cloudflare' in response_str.lower():
                print("⚠️ Получен ответ от Cloudflare (fallback)")
                print("   Это означает что VLESS не работает")
                return False
            else:
                print(f"⚠️ Неожиданный ответ: {response_str[:200]}...")
                return False
        else:
            print("❌ Ответ не получен")
            return False
            
    except socket.timeout:
        print("❌ Таймаут подключения")
        return False
    except ssl.SSLError as e:
        print(f"❌ SSL ошибка: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def main():
    """Главная функция"""
    # Тестируем наш VLESS ключ
    vless_url = "vless://032af41a-ae83-4980-bd2b-b7c845cfe2d0@146.103.125.210:443?type=tcp&security=reality&encryption=none&flow=xtls-rprx-vision&sni=www.cloudflare.com&fp=random&pbk=kjMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ&sid=70a6f0f7#VPNBot_user_5406831921"
    
    success = test_vless_connection(vless_url)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 VLESS ПОДКЛЮЧЕНИЕ РАБОТАЕТ!")
    else:
        print("❌ VLESS ПОДКЛЮЧЕНИЕ НЕ РАБОТАЕТ")
        print("\n💡 Возможные причины:")
        print("   1. Проблема в серверной конфигурации")
        print("   2. Неправильные параметры Reality")
        print("   3. Блокировка сети")
        print("   4. Ошибка в VLESS протоколе")

if __name__ == "__main__":
    main()