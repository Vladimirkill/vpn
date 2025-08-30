#!/usr/bin/env python3
"""
Скрипт для настройки провайдеров VDS и их API ключей
"""

import json
import os
import sys
from vpn_bot.utils.vds_ip_manager import VDSIPManager

def setup_vdsina():
    """Настройка VDSina.ru"""
    print("🔧 Настройка VDSina.ru")
    print("=" * 40)
    
    print("📋 Для настройки VDSina вам нужно:")
    print("1. Зайти в личный кабинет VDSina.ru")
    print("2. Перейти в раздел 'API'")
    print("3. Создать новый API ключ")
    print("4. Скопировать ключ")
    print()
    
    api_key = input("Введите API ключ VDSina (или Enter для пропуска): ").strip()
    
    if api_key:
        return {
            "name": "VDSina.ru",
            "api_url": "https://userapi.vdsina.ru/v1",
            "api_key": api_key,
            "cost_per_day": 50.0,
            "available_locations": [
                {"id": "msk", "name": "🇷🇺 Москва", "country": "RU"},
                {"id": "spb", "name": "🇷🇺 СПб", "country": "RU"},
                {"id": "fra", "name": "🇩🇪 Франкфурт", "country": "DE"},
                {"id": "ams", "name": "🇳🇱 Амстердам", "country": "NL"}
            ]
        }
    return None

def setup_timeweb():
    """Настройка Timeweb"""
    print("🔧 Настройка Timeweb")
    print("=" * 40)
    
    print("📋 Для настройки Timeweb вам нужно:")
    print("1. Зайти в панель управления Timeweb")
    print("2. Перейти в 'API токены'")
    print("3. Создать новый токен")
    print("4. Скопировать токен")
    print()
    
    api_key = input("Введите API токен Timeweb (или Enter для пропуска): ").strip()
    
    if api_key:
        return {
            "name": "Timeweb",
            "api_url": "https://api.timeweb.cloud/api/v1",
            "api_key": api_key,
            "cost_per_day": 45.0,
            "available_locations": [
                {"id": "ru-1", "name": "🇷🇺 Москва", "country": "RU"},
                {"id": "pl-1", "name": "🇵🇱 Польша", "country": "PL"},
                {"id": "kz-1", "name": "🇰🇿 Казахстан", "country": "KZ"}
            ]
        }
    return None

def setup_custom_provider():
    """Настройка кастомного провайдера"""
    print("🔧 Настройка кастомного провайдера")
    print("=" * 40)
    
    provider_name = input("Название провайдера: ").strip()
    if not provider_name:
        return None
    
    api_url = input("API URL: ").strip()
    api_key = input("API ключ: ").strip()
    
    try:
        cost_per_day = float(input("Стоимость за день (₽): "))
    except:
        cost_per_day = 50.0
    
    return {
        "name": provider_name,
        "api_url": api_url,
        "api_key": api_key,
        "cost_per_day": cost_per_day,
        "available_locations": [
            {"id": "custom", "name": "🌍 Кастомная локация", "country": "XX"}
        ]
    }

def update_config(providers_config):
    """Обновляет конфигурацию провайдеров"""
    try:
        vds_manager = VDSIPManager()
        
        # Загружаем текущую конфигурацию
        config_file = "/var/www/vpn/data/vds_config.json"
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {
                "providers": {},
                "settings": {
                    "max_ips_per_user": 3,
                    "min_rental_days": 1,
                    "max_rental_days": 30,
                    "auto_renewal": True,
                    "payment_required": True
                }
            }
        
        # Обновляем провайдеров
        config["providers"].update(providers_config)
        
        # Сохраняем
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Конфигурация сохранена: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения конфигурации: {e}")
        return False

def test_providers(providers_config):
    """Тестирует подключение к провайдерам"""
    print("\n🧪 Тестирование провайдеров...")
    
    for provider_id, provider in providers_config.items():
        print(f"Тестирование {provider['name']}...")
        
        try:
            # Простой тест API (можно расширить)
            import requests
            
            headers = {"Authorization": f"Bearer {provider['api_key']}"}
            response = requests.get(
                f"{provider['api_url']}/account", 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ {provider['name']}: подключение успешно")
            else:
                print(f"⚠️ {provider['name']}: код ответа {response.status_code}")
                
        except Exception as e:
            print(f"❌ {provider['name']}: ошибка подключения - {e}")

def show_current_config():
    """Показывает текущую конфигурацию"""
    config_file = "/var/www/vpn/data/vds_config.json"
    
    if not os.path.exists(config_file):
        print("ℹ️ Конфигурация еще не создана")
        return
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print("📋 Текущая конфигурация:")
        print("=" * 40)
        
        providers = config.get("providers", {})
        if providers:
            for provider_id, provider in providers.items():
                print(f"🔧 {provider['name']}:")
                print(f"   API: {'✅ настроен' if provider.get('api_key') else '❌ не настроен'}")
                print(f"   Стоимость: {provider['cost_per_day']}₽/день")
                print(f"   Локации: {len(provider.get('available_locations', []))}")
                print()
        else:
            print("❌ Провайдеры не настроены")
        
        settings = config.get("settings", {})
        print(f"⚙️ Настройки:")
        print(f"   Макс. IP на пользователя: {settings.get('max_ips_per_user', 3)}")
        print(f"   Мин. срок аренды: {settings.get('min_rental_days', 1)} дн.")
        print(f"   Макс. срок аренды: {settings.get('max_rental_days', 30)} дн.")
        
    except Exception as e:
        print(f"❌ Ошибка чтения конфигурации: {e}")

def main():
    """Основная функция"""
    print("🏢 НАСТРОЙКА ПРОВАЙДЕРОВ VDS")
    print("=" * 50)
    
    # Создаем директорию для данных
    os.makedirs("/var/www/vpn/data", exist_ok=True)
    
    while True:
        print("\nВыберите действие:")
        print("1. Показать текущую конфигурацию")
        print("2. Настроить VDSina.ru")
        print("3. Настроить Timeweb")
        print("4. Добавить кастомного провайдера")
        print("5. Тестировать провайдеров")
        print("6. Выход")
        
        choice = input("\nВаш выбор (1-6): ").strip()
        
        if choice == "1":
            show_current_config()
        
        elif choice == "2":
            provider_config = setup_vdsina()
            if provider_config:
                if update_config({"vdsina": provider_config}):
                    print("✅ VDSina настроен успешно")
        
        elif choice == "3":
            provider_config = setup_timeweb()
            if provider_config:
                if update_config({"timeweb": provider_config}):
                    print("✅ Timeweb настроен успешно")
        
        elif choice == "4":
            provider_config = setup_custom_provider()
            if provider_config:
                provider_id = input("ID провайдера (латиницей): ").strip().lower()
                if provider_id:
                    if update_config({provider_id: provider_config}):
                        print(f"✅ Провайдер {provider_config['name']} добавлен")
        
        elif choice == "5":
            config_file = "/var/www/vpn/data/vds_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                test_providers(config.get("providers", {}))
            else:
                print("❌ Сначала настройте провайдеров")
        
        elif choice == "6":
            break
        
        else:
            print("❌ Неверный выбор")
    
    print("\n✅ Настройка завершена!")
    print("\n💡 Следующие шаги:")
    print("1. Перезапустите VPN бота")
    print("2. Используйте команду /rent в боте")
    print("3. Или кнопку '🏢 Аренда IP' в VPN меню")

if __name__ == "__main__":
    main()