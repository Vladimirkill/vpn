#!/usr/bin/env python3
"""
Проверка возможности аренды дополнительных IP через VDSina API
"""

import requests
import json

def check_vdsina_api():
    """Проверяет API VDSina для аренды IP"""
    print("🔍 Проверка API VDSina.ru...")
    
    # Базовая информация об API
    api_info = {
        "base_url": "https://userapi.vdsina.ru/v1",
        "docs": "https://userapi.vdsina.ru/docs",
        "endpoints": {
            "floating_ips": "/floating-ips",
            "servers": "/servers", 
            "account": "/account"
        }
    }
    
    print(f"📋 API URL: {api_info['base_url']}")
    print(f"📖 Документация: {api_info['docs']}")
    
    # Проверяем доступность API
    try:
        response = requests.get(f"{api_info['base_url']}/ping", timeout=10)
        if response.status_code == 200:
            print("✅ API VDSina доступен")
        else:
            print(f"⚠️ API ответил с кодом: {response.status_code}")
    except Exception as e:
        print(f"❌ API недоступен: {e}")
    
    return api_info

def show_manual_steps():
    """Показывает ручные шаги для получения IP"""
    print("\n📋 РУЧНЫЕ ШАГИ ДЛЯ ПОЛУЧЕНИЯ IP:")
    print("=" * 50)
    
    print("1️⃣ **Через панель VDSina.ru:**")
    print("   • Войдите в личный кабинет")
    print("   • Выберите ваш сервер v452799")
    print("   • Перейдите в 'Сетевые настройки'")
    print("   • Нажмите 'Заказать дополнительный IP'")
    print("   • Выберите количество IP (обычно 1-5)")
    print("   • Подтвердите заказ")
    
    print("\n2️⃣ **Через техподдержку:**")
    print("   • Создайте тикет в поддержку")
    print("   • Укажите ID сервера: v452799")
    print("   • Запросите дополнительные IPv4")
    print("   • Укажите количество нужных IP")
    
    print("\n3️⃣ **Через API (требует токен):**")
    print("   • Получите API токен в панели")
    print("   • Используйте endpoint /floating-ips")
    print("   • POST запрос для создания IP")

def estimate_costs():
    """Показывает примерную стоимость"""
    print("\n💰 ПРИМЕРНАЯ СТОИМОСТЬ IP У VDSINA:")
    print("=" * 50)
    
    costs = {
        "Дополнительный IPv4": "~150-300₽/месяц",
        "Floating IP": "~200-400₽/месяц", 
        "Dedicated IP": "~300-500₽/месяц"
    }
    
    for ip_type, cost in costs.items():
        print(f"   • {ip_type}: {cost}")
    
    print("\n💡 Точную стоимость уточните в панели управления")

def show_integration_plan():
    """Показывает план интеграции с ботом"""
    print("\n🤖 ИНТЕГРАЦИЯ С VPN БОТОМ:")
    print("=" * 50)
    
    print("После получения дополнительных IP:")
    print("1. Добавьте IP в конфигурацию сервера")
    print("2. Настройте API ключ VDSina в боте")
    print("3. Система автоматически создаст отдельные серверы")
    print("4. Пользователи смогут арендовать IP через бота")
    
    print("\n🔧 Команды для настройки:")
    print("   python3 setup_vds_providers.py")
    print("   systemctl restart vpn-bot")

def main():
    """Основная функция"""
    print("🏢 ПРОВЕРКА ВОЗМОЖНОСТИ АРЕНДЫ IP У VDSINA")
    print("=" * 60)
    
    # Проверяем API
    api_info = check_vdsina_api()
    
    # Показываем ручные шаги
    show_manual_steps()
    
    # Показываем стоимость
    estimate_costs()
    
    # План интеграции
    show_integration_plan()
    
    print("\n" + "=" * 60)
    print("✅ Проверка завершена!")
    print("\n💡 Рекомендация:")
    print("1. Сначала закажите 2-3 дополнительных IP через панель")
    print("2. Затем настройте API для автоматизации")
    print("3. Интегрируйте с VPN ботом")

if __name__ == "__main__":
    main()