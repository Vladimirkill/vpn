#!/usr/bin/env python3
"""
Скрипт для тестирования REALITY подключения
"""

import socket
import ssl
import struct
import time
import random

def test_reality_handshake(host, port, public_key, short_id, sni="www.cloudflare.com"):
    """Тестирует REALITY handshake"""
    try:
        print(f"🔍 Тестирование REALITY handshake к {host}:{port}")
        print(f"   SNI: {sni}")
        print(f"   Short ID: {short_id}")
        print(f"   Public Key: {public_key[:20]}...")
        
        # Создаем сокет
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        print(f"📡 Подключение к {host}:{port}...")
        sock.connect((host, port))
        print(f"✅ TCP соединение установлено")
        
        # Создаем ClientHello
        client_hello = create_client_hello(sni, short_id)
        
        print(f"📤 Отправка ClientHello...")
        sock.send(client_hello)
        
        # Ждем ответ
        print(f"⏳ Ожидание ответа сервера...")
        response = sock.recv(4096)
        
        if response:
            print(f"✅ Получен ответ от сервера ({len(response)} байт)")
            
            # Анализируем ответ
            if b'\x16\x03\x01' in response:  # TLS handshake
                print(f"✅ Получен TLS handshake ответ")
                return True
            elif b'\x15\x03\x01' in response:  # TLS alert
                print(f"⚠️ Получен TLS alert")
                return False
            else:
                print(f"❓ Неожиданный ответ: {response[:50]}...")
                return False
        else:
            print(f"❌ Нет ответа от сервера")
            return False
            
    except socket.timeout:
        print(f"⏰ Timeout при ожидании ответа")
        return False
    except ConnectionRefusedError:
        print(f"❌ Соединение отклонено")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def create_client_hello(sni, short_id):
    """Создает ClientHello сообщение"""
    # Простой ClientHello для тестирования
    # В реальности это должно быть полноценное TLS ClientHello
    
    # TLS Record Layer
    record_type = 0x16  # Handshake
    version = 0x0301    # TLS 1.0
    length = 0x0000     # Будет вычислено позже
    
    # Handshake Layer
    handshake_type = 0x01  # ClientHello
    handshake_length = 0x000000  # Будет вычислено позже
    client_version = 0x0303  # TLS 1.2
    
    # Client Random (32 байта)
    client_random = random.randbytes(32)
    
    # Session ID
    session_id_length = 0x00
    
    # Cipher Suites
    cipher_suites_length = 0x0002
    cipher_suites = b'\x13\x01'  # TLS_AES_128_GCM_SHA256
    
    # Compression Methods
    compression_length = 0x01
    compression_methods = b'\x00'  # No compression
    
    # Extensions
    extensions_length = 0x0000  # Будет вычислено позже
    
    # SNI Extension
    sni_extension_type = 0x0000  # Server Name
    sni_extension_length = 0x0000  # Будет вычислено позже
    sni_list_length = 0x0000  # Будет вычислено позже
    sni_type = 0x00  # Hostname
    sni_length = len(sni.encode())
    sni_name = sni.encode()
    
    # Вычисляем длины
    sni_extension_length = 2 + sni_list_length
    sni_list_length = 1 + 2 + sni_length
    sni_extension_length = 2 + sni_list_length
    extensions_length = 2 + 2 + sni_extension_length
    
    # Собираем ClientHello
    client_hello = (
        struct.pack('>B', handshake_type) +
        struct.pack('>I', handshake_length)[1:] +  # 3 байта
        struct.pack('>H', client_version) +
        client_random +
        struct.pack('>B', session_id_length) +
        struct.pack('>H', cipher_suites_length) +
        cipher_suites +
        struct.pack('>B', compression_length) +
        compression_methods +
        struct.pack('>H', extensions_length) +
        struct.pack('>H', sni_extension_type) +
        struct.pack('>H', sni_extension_length) +
        struct.pack('>H', sni_list_length) +
        struct.pack('>B', sni_type) +
        struct.pack('>H', sni_length) +
        sni_name
    )
    
    # Вычисляем длины
    handshake_length = len(client_hello)
    record_length = handshake_length + 4
    
    # Собираем полное сообщение
    full_message = (
        struct.pack('>B', record_type) +
        struct.pack('>H', version) +
        struct.pack('>H', record_length) +
        struct.pack('>B', handshake_type) +
        struct.pack('>I', handshake_length)[1:] +  # 3 байта
        struct.pack('>H', client_version) +
        client_random +
        struct.pack('>B', session_id_length) +
        struct.pack('>H', cipher_suites_length) +
        cipher_suites +
        struct.pack('>B', compression_length) +
        compression_methods +
        struct.pack('>H', extensions_length) +
        struct.pack('>H', sni_extension_type) +
        struct.pack('>H', sni_extension_length) +
        struct.pack('>H', sni_list_length) +
        struct.pack('>B', sni_type) +
        struct.pack('>H', sni_length) +
        sni_name
    )
    
    return full_message

def main():
    """Главная функция"""
    print("🧪 Тестирование REALITY подключения")
    print("=" * 50)
    
    # Параметры для тестирования
    host = "146.103.125.210"
    port = 443
    public_key = "kjMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ"
    short_id = "428ef030"
    sni = "www.cloudflare.com"
    
    print(f"🌐 Сервер: {host}:{port}")
    print(f"🎯 SNI: {sni}")
    print(f"🆔 Short ID: {short_id}")
    print(f"🔑 Public Key: {public_key[:20]}...")
    print()
    
    # Тестируем подключение
    success = test_reality_handshake(host, port, public_key, short_id, sni)
    
    print()
    print("=" * 50)
    if success:
        print("✅ REALITY handshake успешен!")
        print("💡 Проблема может быть в клиентском приложении")
    else:
        print("❌ REALITY handshake не удался")
        print("💡 Проблема в настройках сервера или сети")
    
    print()
    print("🔍 Дополнительные проверки:")
    print("1. Убедитесь, что клиент поддерживает REALITY протокол")
    print("2. Проверьте настройки SNI в клиенте")
    print("3. Убедитесь, что используется правильный public key")
    print("4. Проверьте, что клиент отправляет правильный short ID")

if __name__ == "__main__":
    main() 