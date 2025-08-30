#!/usr/bin/env python3
"""
Демонстрация системы аренды IP-адресов
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Добавляем путь к проекту
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from vpn_bot.utils.vds_ip_manager import VDSIPManager
from vpn_bot.utils.ip_manager import IPManager

def create_demo_data():
    """Создает демонстрационные данные"""
    print("🎭 Создание демонстрационных данных...")
    
    # Создаем директории
    os.makedirs("/var/www/vpn/data", exist_ok=True)
    
    # Создаем конфигурацию провайдеров
    demo_config = {
        "providers": {
            "demo_provider": {
                "name": "Demo VDS Provider",
                "api_url": "https://api.demo-vds.com/v1",
                "api_key": "demo_key_12345",
                "cost_per_day": 30.0,
                "available_locations": [
                    {"id": "ru-msk", "name": "🇷🇺 Москва", "country": "RU"},
                    {"id": "de-fra", "name": "🇩🇪 Франкфурт", "country": "DE"},
                    {"id": "nl-ams", "name": "🇳🇱 Амстердам", "country": "NL"},
                    {"id": "us-nyc", "name": "🇺🇸 Нью-Йорк", "country": "US"}
                ]
            }
        },
        "settings": {
            "max_ips_per_user": 3,
            "min_rental_days": 1,
            "max_rental_days": 30,
            "auto_renewal": False,
            "payment_required": True
        }
    }
    
    config_file = "/var/www/vpn/data/vds_config.json"
    with open(config_file, 'w') as f:
        json.dump(demo_config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Конфигурация создана: {config_file}")

def demo_rental_process():
    """Демонстрирует процесс аренды IP"""
    print("\n🏢 ДЕМОНСТРАЦИЯ АРЕНДЫ IP")
    print("=" * 50)
    
    vds_manager = VDSIPManager()
    
    # 1. Показываем доступные локации
    print("1️⃣ Доступные локации:")
    locations = vds_manager.get_available_locations()
    for i, location in enumerate(locations, 1):
        print(f"   {i}. {location['location_name']} - {location['cost_per_day']}₽/день")
    
    if not locations:
        print("   ❌ Нет доступных локаций (настройте провайдеров)")
        return
    
    # 2. Арендуем IP для демо пользователя
    print("\n2️⃣ Аренда IP для пользователя 12345:")
    
    demo_user_id = 12345
    location = locations[0]  # Берем первую доступную
    
    print(f"   Локация: {location['location_name']}")
    print(f"   Срок: 7 дней")
    print(f"   Стоимость: {location['cost_per_day'] * 7}₽")
    
    result = vds_manager.rent_ip(
        user_id=demo_user_id,
        provider_id=location['provider_id'],
        location_id=location['location_id'],
        days=7
    )
    
    if result["success"]:
        print(f"   ✅ IP арендован: {result['ip_address']}")
        print(f"   💰 Стоимость: {result['cost']}₽")
        print(f"   ⏰ Действует до: {result['expires'][:10]}")
    else:
        print(f"   ❌ Ошибка: {result['error']}")
    
    # 3. Показываем IP пользователя
    print("\n3️⃣ IP пользователя:")
    user_ips = vds_manager.get_user_ips(demo_user_id)
    
    if user_ips:
        for ip_info in user_ips:
            print(f"   🌐 {ip_info['ip_address']}")
            print(f"      📍 {ip_info['location_id']}")
            print(f"      ⏰ Осталось: {ip_info.get('days_left', 0)} дн.")
            print(f"      💰 {ip_info['cost_per_day']}₽/день")
    else:
        print("   ❌ Нет арендованных IP")

def demo_ip_management():
    """Демонстрирует управление IP в системе"""
    print("\n🌍 ДЕМОНСТРАЦИЯ СИСТЕМЫ IP")
    print("=" * 50)
    
    ip_manager = IPManager()
    
    # Показываем доступные серверы
    print("1️⃣ Доступные IP серверы:")
    servers = ip_manager.get_available_servers()
    
    for i, server in enumerate(servers, 1):
        print(f"   {i}. {server['name']}")
        print(f"      Тип: {server['type']}")
        print(f"      Описание: {server['description']}")
    
    # Демонстрируем установку IP для пользователя
    print("\n2️⃣ Установка IP для пользователя:")
    
    if servers:
        demo_uuid = "demo-user-uuid-12345"
        server_id = servers[0]['id']
        
        success = ip_manager.set_user_ip(demo_uuid, server_id)
        
        if success:
            print(f"   ✅ IP установлен: {servers[0]['name']}")
            current_ip = ip_manager.get_user_ip(demo_uuid)
            print(f"   📍 Текущий IP: {current_ip}")
        else:
            print("   ❌ Ошибка установки IP")

def show_system_architecture():
    """Показывает архитектуру системы"""
    print("\n🏗️ АРХИТЕКТУРА СИСТЕМЫ")
    print("=" * 50)
    
    print("📋 Компоненты системы:")
    print()
    
    print("1️⃣ VDSIPManager:")
    print("   • Управление арендой IP через API провайдеров")
    print("   • Автоматическое освобождение истекших IP")
    print("   • Интеграция с VDSina, Timeweb и другими")
    print()
    
    print("2️⃣ IPManager:")
    print("   • Управление outbound соединениями в Xray")
    print("   • Маршрутизация пользователей по IP")
    print("   • Интеграция с Telegram ботом")
    print()
    
    print("3️⃣ RentalHandler:")
    print("   • Telegram интерфейс для аренды IP")
    print("   • Меню выбора локаций и сроков")
    print("   • Управление арендованными IP")
    print()
    
    print("4️⃣ Xray Integration:")
    print("   • Автоматическое добавление outbound'ов")
    print("   • Routing rules для пользователей")
    print("   • Поддержка множественных IP")
    print()
    
    print("🔄 Процесс работы:")
    print("   1. Пользователь выбирает локацию в боте")
    print("   2. VDSIPManager арендует IP через API")
    print("   3. IP добавляется в Xray конфигурацию")
    print("   4. Пользователь может выбрать IP в меню")
    print("   5. Трафик маршрутизируется через выбранный IP")

def show_bot_commands():
    """Показывает команды бота"""
    print("\n🤖 КОМАНДЫ TELEGRAM БОТА")
    print("=" * 50)
    
    commands = [
        ("/start", "Главное меню VPN бота"),
        ("/ip", "Меню смены IP-адреса"),
        ("/rent", "Меню аренды дополнительных IP"),
        ("🌍 Смена IP", "Кнопка выбора активного IP"),
        ("🏢 Аренда IP", "Кнопка аренды новых IP"),
        ("📋 Мои IP", "Управление арендованными IP"),
        ("💰 Тарифы", "Просмотр стоимости аренды")
    ]
    
    for command, description in commands:
        print(f"   {command:<15} - {description}")

def main():
    """Основная функция демонстрации"""
    print("🎯 ДЕМОНСТРАЦИЯ СИСТЕМЫ АРЕНДЫ IP")
    print("=" * 60)
    
    # Создаем демо данные
    create_demo_data()
    
    # Демонстрируем функции
    demo_rental_process()
    demo_ip_management()
    show_system_architecture()
    show_bot_commands()
    
    print("\n" + "=" * 60)
    print("✅ Демонстрация завершена!")
    print()
    print("📋 Для запуска системы:")
    print("1. Настройте провайдеров: python3 setup_vds_providers.py")
    print("2. Перезапустите бота: systemctl restart vpn-bot")
    print("3. Добавьте cron задачу: crontab -e")
    print("   0 * * * * /usr/bin/python3 /var/www/vpn/cleanup_expired_ips.py")
    print()
    print("🎉 Система готова к использованию!")

if __name__ == "__main__":
    main()