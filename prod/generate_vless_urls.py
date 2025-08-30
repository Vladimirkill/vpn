#!/usr/bin/env python3
"""
Скрипт для генерации VLESS URL для трех последних ключей
"""

import json
import os

def generate_vless_url(uuid, short_id, name):
    """Генерирует VLESS URL для ключа"""
    print(f"🔑 {name}")
    print(f"   UUID: {uuid}")
    print(f"   Short ID: {short_id}")
    
    # Параметры сервера
    server = "146.103.125.210:8443"
    public_key = "kjMnAzgwvHmjpbRvOaGj4viE0WVw2kLxodbC1e0GunQ"
    
    # Формируем VLESS URL (обновлено для iOS Safari совместимости)
    vless_url = f"vless://{uuid}@{server}?security=reality&sni=www.apple.com&fp=safari&pbk={public_key}&sid={short_id}&spx=/&type=tcp&flow=xtls-rprx-vision&encryption=none#{name}"
    
    print(f"   📋 VLESS URL:")
    print(f"   {vless_url}")
    print()
    
    return vless_url

def main():
    """Главная функция"""
    print("🔗 Генерация VLESS URL для трех последних ключей")
    print("=" * 80)
    
    # Данные трех последних ключей
    keys = [
        {
            "uuid": "f4677c51-0526-42dc-b5cd-aee5fe62aeec",
            "short_id": "77885889",
            "name": "VPNBot_user_5406831921_1"
        },
        {
            "uuid": "f97d57f3-1003-450e-bc6b-249ee39dccb1",
            "short_id": "339c3a5c",
            "name": "VPNBot_user_5406831921_2"
        },
        {
            "uuid": "fcf88867-00d2-43f0-9eab-c29005c18b53",
            "short_id": "20e9faf8",
            "name": "VPNBot_user_5406831921_3"
        }
    ]
    
    urls = []
    
    # Генерируем URL для каждого ключа
    for key in keys:
        url = generate_vless_url(key['uuid'], key['short_id'], key['name'])
        urls.append((key['name'], url))
    
    # Инструкции по тестированию
    print("🧪 ИНСТРУКЦИИ ПО ТЕСТИРОВАНИЮ")
    print("=" * 80)
    print("1. Скопируйте каждый VLESS URL выше")
    print("2. Вставьте в клиентское приложение (V2rayN, V2rayA, V2rayNG)")
    print("3. Попробуйте подключиться")
    print("4. Определите, какой именно ключ не работает")
    print()
    print("📱 Рекомендуемые клиенты:")
    print("   • Windows: V2rayN")
    print("   • macOS: V2rayA")
    print("   • Android: V2rayNG")
    print("   • iOS: Shadowrocket")
    print()
    print("🔍 Если ключ не работает:")
    print("   1. Проверьте версию клиента (должна поддерживать REALITY)")
    print("   2. Убедитесь, что SNI = www.cloudflare.com")
    print("   3. Проверьте, что Flow = xtls-rprx-vision")
    print("   4. Попробуйте другой клиент")
    print()
    print("📊 ОТЧЕТ О ТЕСТИРОВАНИИ")
    print("=" * 80)
    
    for i, (name, url) in enumerate(urls, 1):
        print(f"{i}. {name}: {'✅ РАБОТАЕТ' if i <= 2 else '❌ НЕ РАБОТАЕТ'} (по вашему сообщению)")
    
    print()
    print("💡 После тестирования сообщите, какой именно ключ не работает,")
    print("   и мы сможем более точно диагностировать проблему.")

if __name__ == "__main__":
    main() 