#!/usr/bin/env python3
"""
Тест системы аренды IP-адресов
"""

import sys
import os
import json
from datetime import datetime

# Добавляем путь к проекту
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def test_vds_manager():
    """Тестирует VDSIPManager"""
    print("🧪 Тестирование VDSIPManager...")
    
    try:
        from vpn_bot.utils.vds_ip_manager import VDSIPManager
        
        vds_manager = VDSIPManager()
        
        # 1. Проверяем инициализацию
        print("✅ VDSIPManager инициализирован")
        
        # 2. Получаем доступные локации
        locations = vds_manager.get_available_locations()
        print(f"📍 Доступных локаций: {len(locations)}")
        
        for location in locations:
            print(f"   • {location['location_name']} - {location['cost_per_day']}₽/день")
        
        # 3. Тестируем аренду IP (с mock данными)
        if locations:
            print("\n🏢 Тестирование аренды IP...")
            
            test_user_id = 12345
            location = locations[0]
            
            result = vds_manager.rent_ip(
                user_id=test_user_id,
                provider_id=location['provider_id'],
                location_id=location['location_id'],
                days=1
            )
            
            if result["success"]:
                print(f"✅ IP арендован: {result['ip_address']}")
                print(f"💰 Стоимость: {result['cost']}₽")
                
                # 4. Проверяем IP пользователя
                user_ips = vds_manager.get_user_ips(test_user_id)
                print(f"📋 IP пользователя: {len(user_ips)}")
                
                for ip_info in user_ips:
                    print(f"   🌐 {ip_info['ip_address']} - {ip_info.get('days_left', 0)} дн.")
                
                return True
            else:
                print(f"❌ Ошибка аренды: {result['error']}")
                return False
        else:
            print("⚠️ Нет доступных локаций для теста")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка VDSIPManager: {e}")
        return False

def test_server_manager():
    """Тестирует ServerManager"""
    print("\n🖥️ Тестирование ServerManager...")
    
    try:
        from vpn_bot.utils.server_manager import ServerManager
        
        server_manager = ServerManager()
        
        # 1. Проверяем инициализацию
        print("✅ ServerManager инициализирован")
        
        # 2. Создаем тестовый сервер
        test_ip = "192.168.100.50"  # Тестовый IP
        test_user_id = 12345
        
        print(f"🔧 Создание сервера для IP {test_ip}...")
        
        result = server_manager.create_server(
            ip_address=test_ip,
            user_id=test_user_id,
            location="test-location"
        )
        
        if result["success"]:
            print(f"✅ Сервер создан: {result['server_id']}")
            print(f"🔌 Порт: {result['port']}")
            print(f"🔑 VLESS ключ сгенерирован")
            
            # 3. Проверяем информацию о сервере
            server_info = server_manager.get_server_info(result['server_id'])
            if server_info:
                print(f"📊 Статус сервера: {server_info['status']}")
                print(f"👤 UUID пользователя: {server_info['user_uuid']}")
            
            # 4. Проверяем серверы пользователя
            user_servers = server_manager.get_user_servers(test_user_id)
            print(f"🖥️ Серверов пользователя: {len(user_servers)}")
            
            return result['server_id']
        else:
            print(f"❌ Ошибка создания сервера: {result['error']}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка ServerManager: {e}")
        return None

def test_xray_config():
    """Проверяет созданные конфигурации Xray"""
    print("\n⚙️ Проверка конфигураций Xray...")
    
    try:
        configs_dir = "/var/www/vpn/servers/configs"
        
        if not os.path.exists(configs_dir):
            print("❌ Директория конфигураций не найдена")
            return False
        
        config_files = [f for f in os.listdir(configs_dir) if f.endswith('.json')]
        print(f"📁 Найдено конфигураций: {len(config_files)}")
        
        for config_file in config_files:
            config_path = os.path.join(configs_dir, config_file)
            
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Проверяем структуру конфигурации
                if 'inbounds' in config and 'outbounds' in config:
                    inbound = config['inbounds'][0]
                    port = inbound.get('port', 'неизвестен')
                    listen = inbound.get('listen', 'неизвестен')
                    
                    print(f"   ✅ {config_file}: порт {port}, IP {listen}")
                else:
                    print(f"   ❌ {config_file}: неверная структура")
                    
            except Exception as e:
                print(f"   ❌ {config_file}: ошибка чтения - {e}")
        
        return len(config_files) > 0
        
    except Exception as e:
        print(f"❌ Ошибка проверки конфигураций: {e}")
        return False

def test_systemd_services():
    """Проверяет созданные systemd сервисы"""
    print("\n🔧 Проверка systemd сервисов...")
    
    try:
        import subprocess
        
        # Ищем сервисы xray_*
        result = subprocess.run(
            ["systemctl", "list-unit-files", "--type=service", "--no-pager"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            xray_services = [line for line in result.stdout.split('\n') if 'xray_' in line]
            
            print(f"🔧 Найдено Xray сервисов: {len(xray_services)}")
            
            for service_line in xray_services:
                service_name = service_line.split()[0]
                
                # Проверяем статус сервиса
                status_result = subprocess.run(
                    ["systemctl", "is-active", service_name],
                    capture_output=True,
                    text=True
                )
                
                status = status_result.stdout.strip()
                status_emoji = "🟢" if status == "active" else "🔴"
                
                print(f"   {status_emoji} {service_name}: {status}")
            
            return len(xray_services) > 0
        else:
            print("❌ Ошибка получения списка сервисов")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки сервисов: {e}")
        return False

def test_bot_integration():
    """Тестирует интеграцию с ботом"""
    print("\n🤖 Проверка интеграции с ботом...")
    
    try:
        # Проверяем импорты
        from vpn_bot.handler.rental_handler import RentalHandler
        from vpn_bot.utils.vds_ip_manager import VDSIPManager
        from vpn_bot.utils.server_manager import ServerManager
        
        print("✅ Все модули импортируются успешно")
        
        # Проверяем инициализацию обработчика
        rental_handler = RentalHandler()
        print("✅ RentalHandler инициализирован")
        
        # Проверяем методы
        methods_to_check = [
            'show_rental_menu',
            'show_rental_locations', 
            'execute_rental',
            'show_rented_key',
            'manage_specific_ip'
        ]
        
        for method_name in methods_to_check:
            if hasattr(rental_handler, method_name):
                print(f"   ✅ Метод {method_name} найден")
            else:
                print(f"   ❌ Метод {method_name} отсутствует")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграции с ботом: {e}")
        return False

def cleanup_test_data():
    """Очищает тестовые данные"""
    print("\n🧹 Очистка тестовых данных...")
    
    try:
        from vpn_bot.utils.server_manager import ServerManager
        
        server_manager = ServerManager()
        
        # Получаем все серверы
        all_servers = server_manager.get_all_servers()
        
        # Удаляем тестовые серверы
        for server_id, server_info in all_servers.items():
            if server_info.get('user_id') == 12345:  # Тестовый пользователь
                print(f"🗑️ Удаление тестового сервера {server_id}")
                server_manager.remove_server(server_id)
        
        print("✅ Тестовые данные очищены")
        
    except Exception as e:
        print(f"⚠️ Ошибка очистки: {e}")

def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ АРЕНДЫ IP")
    print("=" * 60)
    
    results = {}
    
    # 1. Тест VDSIPManager
    results['vds_manager'] = test_vds_manager()
    
    # 2. Тест ServerManager
    server_id = test_server_manager()
    results['server_manager'] = server_id is not None
    
    # 3. Тест конфигураций Xray
    results['xray_configs'] = test_xray_config()
    
    # 4. Тест systemd сервисов
    results['systemd_services'] = test_systemd_services()
    
    # 5. Тест интеграции с ботом
    results['bot_integration'] = test_bot_integration()
    
    # Результаты
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    
    for test_name, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"   {test_name}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n🎯 Успешно: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к использованию.")
    else:
        print("⚠️ Есть проблемы, требующие исправления.")
    
    # Очистка тестовых данных
    cleanup_test_data()
    
    print("\n💡 Для использования системы:")
    print("1. Настройте провайдеров: python3 setup_vds_providers.py")
    print("2. Перезапустите бота: systemctl restart vpn-bot")
    print("3. Используйте команду /rent в боте")

if __name__ == "__main__":
    main()