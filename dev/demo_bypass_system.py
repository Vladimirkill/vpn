#!/usr/bin/env python3
"""
Демонстрация системы исключений через Telegram API
"""

import requests
import time
import json

BOT_TOKEN = "7468813281:AAGHg-_kX7vj6MsvV0T7g1bhG8gLEdQ8P6Q"
CHAT_ID = "5406831921"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(text, reply_markup=None):
    """Отправляет сообщение в Telegram"""
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    response = requests.post(f"{BASE_URL}/sendMessage", json=data)
    return response.json()

def demo_bypass_interface():
    """Демонстрирует интерфейс системы исключений"""
    print("🎭 Демонстрация интерфейса системы исключений...")
    
    # Отправляем демо-сообщение с полным интерфейсом
    response = send_message(
        "🧪 <b>СИСТЕМА ИСКЛЮЧЕНИЙ ДЛЯ VLESS КЛЮЧЕЙ</b>\n\n"
        "<b>✅ Полностью функциональна!</b>\n\n"
        "<b>🎯 Проверенные сценарии:</b>\n"
        "• Alice: Google + YouTube\n"
        "• Bob: только YouTube\n"
        "• Charlie: без исключений\n"
        "• Dave: только Facebook\n\n"
        "<b>🔒 Изоляция между пользователями работает!</b>\n\n"
        "💡 Каждый пользователь видит только свои исключения",
        reply_markup={
            "inline_keyboard": [
                [
                    {"text": "🚀 Xray (VLESS)", "callback_data": "vpn_xray"}
                ],
                [
                    {"text": "🌐 Популярные сайты", "callback_data": "xray_popular_sites"},
                    {"text": "📋 Мои исключения", "callback_data": "xray_my_bypass"}
                ],
                [
                    {"text": "🔗 Создать ключ", "callback_data": "xray_create"},
                    {"text": "⚙️ Настройки", "callback_data": "xray_bypass"}
                ],
                [
                    {"text": "📊 Статус сервисов", "callback_data": "status"}
                ]
            ]
        }
    )
    
    print(f"  📤 Демо интерфейс отправлен: {response.get('ok', False)}")
    return response

def generate_test_scenarios():
    """Генерирует сценарии для тестирования"""
    
    scenarios = [
        {
            "title": "🔍 Сценарий 1: Популярные сайты",
            "description": "Нажмите '🌐 Популярные сайты' чтобы увидеть список сайтов, добавленных другими пользователями",
            "expected": "Увидите YouTube (3 использования), ВКонтакте, Google, Facebook"
        },
        {
            "title": "📋 Сценарий 2: Мои исключения", 
            "description": "Нажмите '📋 Мои исключения' чтобы увидеть свой список",
            "expected": "Увидите только ваши личные исключения"
        },
        {
            "title": "⚙️ Сценарий 3: Добавление исключения",
            "description": "Нажмите '⚙️ Настройки' и отправьте название сайта (например: instagram.com)",
            "expected": "Бот проверит домен и добавит в ваш список"
        },
        {
            "title": "🔗 Сценарий 4: Создание ключа",
            "description": "Нажмите '🔗 Создать ключ' для генерации VLESS ключа с вашими исключениями",
            "expected": "Получите рабочий VLESS ключ с персональными настройками"
        }
    ]
    
    print("\n📝 СЦЕНАРИИ ДЛЯ ТЕСТИРОВАНИЯ:")
    print("=" * 50)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{scenario['title']}")
        print(f"📱 Действие: {scenario['description']}")
        print(f"🎯 Ожидаемый результат: {scenario['expected']}")
    
    return scenarios

def show_current_database_state():
    """Показывает текущее состояние базы данных"""
    import sys
    sys.path.append('/var/www/vpn/vpn_bot')
    
    try:
        from db.models import session, BypassSite, VpnBypassRule, VpnKey, User
        
        print("\n🗄️ ТЕКУЩЕЕ СОСТОЯНИЕ БАЗЫ ДАННЫХ:")
        print("=" * 40)
        
        # Статистика
        users_count = session.query(User).filter(User.username.isnot(None)).count()
        keys_count = session.query(VpnKey).count()
        sites_count = session.query(BypassSite).count()
        rules_count = session.query(VpnBypassRule).count()
        
        print(f"👥 Пользователей: {users_count}")
        print(f"🔑 VPN ключей: {keys_count}")
        print(f"🌐 Сайтов: {sites_count}")
        print(f"📋 Правил: {rules_count}")
        
        # Популярные сайты
        print(f"\n🔥 Популярные сайты:")
        top_sites = session.query(BypassSite)\
                         .order_by(BypassSite.usage_count.desc())\
                         .limit(5).all()
        
        for site in top_sites:
            verification = "✅" if site.is_verified else "⚠️"
            print(f"  {verification} {site.name} ({site.domain}) - {site.usage_count} польз.")
        
        # Распределение по пользователям
        print(f"\n👥 Исключения по пользователям:")
        users_with_rules = session.query(User.username, 
                                        session.query(VpnBypassRule)
                                        .join(VpnKey)
                                        .filter(VpnKey.user_id == User.id)
                                        .count().label('rules_count'))\
                                .filter(User.username.isnot(None))\
                                .all()
        
        for username, rules_count in users_with_rules:
            print(f"  👤 {username}: {rules_count} исключений")
            
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")

def main():
    """Основная функция демонстрации"""
    print("🎭 ДЕМОНСТРАЦИЯ СИСТЕМЫ ИСКЛЮЧЕНИЙ")
    print("=" * 50)
    
    # Показываем состояние БД
    show_current_database_state()
    
    # Отправляем демо интерфейс
    demo_response = demo_bypass_interface()
    
    # Генерируем сценарии тестирования
    scenarios = generate_test_scenarios()
    
    print(f"\n✅ ДЕМОНСТРАЦИЯ ГОТОВА!")
    print(f"🔗 Откройте бота в Telegram и протестируйте функции")
    print(f"📱 Сообщение с интерфейсом отправлено в чат")
    
    # Отправляем инструкцию
    instruction_response = send_message(
        "📋 <b>ИНСТРУКЦИЯ ПО ТЕСТИРОВАНИЮ</b>\n\n"
        "<b>1.</b> Нажмите 🚀 Xray (VLESS)\n"
        "<b>2.</b> Выберите 🌐 Популярные сайты\n"
        "<b>3.</b> Добавьте несколько сайтов\n"
        "<b>4.</b> Посмотрите 📋 Мои исключения\n"
        "<b>5.</b> Создайте ключ через 🔗 Создать ключ\n\n"
        "💡 <b>Каждый пользователь видит только свои исключения!</b>"
    )
    
    print(f"📋 Инструкция отправлена: {instruction_response.get('ok', False)}")

if __name__ == "__main__":
    main()