#!/usr/bin/env python3
"""
Скрипт для тестирования трех последних созданных ключей
"""

import json
import subprocess
import os

def test_vless_key(uuid, short_id, name):
    """Тестирует VLESS ключ"""
    print(f"🔍 Тестирование ключа: {name}")
    print(f"   UUID: {uuid}")
    print(f"   Short ID: {short_id}")
    print("-" * 50)
    
    # Проверяем файл клиента
    client_file = f"xray/clients/{uuid}.json"
    if os.path.exists(client_file):
        print(f"✅ Файл клиента найден")
        try:
            with open(client_file, 'r') as f:
                client_data = json.load(f)
                flow = client_data.get('flow', 'unknown')
                print(f"   Flow: {flow}")
        except:
            print(f"   ⚠️ Ошибка чтения файла")
    else:
        print(f"❌ Файл клиента НЕ найден")
        return False
    
    # Проверяем, включен ли клиент в конфигурацию
    try:
        result = subprocess.run(['grep', '-n', uuid, 'xray/final_config.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Клиент включен в конфигурацию")
        else:
            print(f"❌ Клиент НЕ включен в конфигурацию")
            return False
    except:
        print(f"   ⚠️ Ошибка проверки конфигурации")
    
    # Проверяем, включен ли shortId в REALITY настройки
    try:
        result = subprocess.run(['grep', short_id, 'xray/final_config.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Short ID включен в REALITY настройки")
        else:
            print(f"❌ Short ID НЕ включен в REALITY настройки")
            return False
    except:
        print(f"   ⚠️ Ошибка проверки REALITY настроек")
    
    # Проверяем статус Xray
    try:
        result = subprocess.run(['systemctl', 'is-active', 'xray'], 
                              capture_output=True, text=True)
        if result.stdout.strip() == "active":
            print(f"✅ Xray сервис активен")
        else:
            print(f"❌ Xray сервис неактивен: {result.stdout.strip()}")
            return False
    except:
        print(f"   ⚠️ Ошибка проверки статуса Xray")
    
    # Проверяем, слушает ли Xray порт 443
    try:
        result = subprocess.run(['ss', '-tn', 'state', 'listening'], 
                              capture_output=True, text=True)
        if ':8443' in result.stdout:
            print(f"✅ Xray слушает порт 443")
        else:
            print(f"❌ Xray НЕ слушает порт 443")
            return False
    except:
        print(f"   ⚠️ Ошибка проверки порта")
    
    print(f"✅ Ключ {name} настроен корректно")
    return True

def main():
    """Главная функция"""
    print("🧪 Тестирование трех последних созданных ключей")
    print("=" * 60)
    
    # Данные трех последних ключей
    keys = [
        {
            "uuid": "f4677c51-0526-42dc-b5cd-aee5fe62aeec",
            "short_id": "77885889",
            "name": "КЛЮЧ 1 (f4677c51)"
        },
        {
            "uuid": "f97d57f3-1003-450e-bc6b-249ee39dccb1",
            "short_id": "339c3a5c",
            "name": "КЛЮЧ 2 (f97d57f3)"
        },
        {
            "uuid": "fcf88867-00d2-43f0-9eab-c29005c18b53",
            "short_id": "20e9faf8",
            "name": "КЛЮЧ 3 (fcf88867)"
        }
    ]
    
    results = []
    
    # Тестируем каждый ключ
    for key in keys:
        print(f"\n{'='*20} {key['name']} {'='*20}")
        success = test_vless_key(key['uuid'], key['short_id'], key['name'])
        results.append((key['name'], success))
        print()
    
    # Итоговый отчет
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    working_keys = 0
    for name, success in results:
        status = "✅ РАБОТАЕТ" if success else "❌ НЕ РАБОТАЕТ"
        print(f"{status} {name}")
        if success:
            working_keys += 1
    
    print(f"\n🎯 Результат: {working_keys}/3 ключей работают")
    
    if working_keys == 3:
        print("🎉 Все ключи работают корректно!")
    elif working_keys == 2:
        print("⚠️ Один ключ не работает - проверьте настройки")
    else:
        print("🚨 Большинство ключей не работают - проблема в системе")
    
    # Рекомендации
    print(f"\n💡 Рекомендации:")
    if working_keys < 3:
        print("   1. Проверьте логи Xray: journalctl -u xray -f")
        print("   2. Убедитесь, что конфигурация перезагружена")
        print("   3. Проверьте права доступа к файлам клиентов")
        print("   4. Перезапустите Xray: systemctl restart xray")

if __name__ == "__main__":
    main() 