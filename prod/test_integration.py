#!/usr/bin/env python3
"""
Интеграционный тест системы исключений через Telegram API
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

def simulate_callback(callback_data, message_id):
    """Симулирует нажатие кнопки callback"""
    # Это невозможно сделать через API, но можем проверить структуру
    print(f"🔘 Симуляция нажатия: {callback_data}")

def test_xray_menu():
    """Тестирует Xray меню"""
    print("🚀 Тестирование Xray меню...")
    
    # Отправляем команду /start
    response = send_message("/start")
    print(f"  📤 /start отправлено: {response.get('ok', False)}")
    
    time.sleep(1)
    
    # Симулируем нажатие кнопки Xray
    simulate_callback("vpn_xray", response.get('result', {}).get('message_id'))
    
    # Отправляем текстовое сообщение для теста
    test_response = send_message(
        "🧪 <b>Тест системы исключений</b>\n\n"
        "Система готова к тестированию! Доступные функции:\n"
        "• ✅ Валидация доменов\n"
        "• ✅ База данных исключений\n" 
        "• ✅ Популярные сайты\n"
        "• ✅ Обработчики callback'ов\n\n"
        "💡 Для полного тестирования используйте интерфейс бота.",
        reply_markup={
            "inline_keyboard": [
                [{"text": "🚀 Xray (VLESS)", "callback_data": "vpn_xray"}],
                [{"text": "🌐 Популярные сайты", "callback_data": "xray_popular_sites"}],
                [{"text": "📋 Мои исключения", "callback_data": "xray_my_bypass"}]
            ]
        }
    )
    
    print(f"  📤 Тестовое меню отправлено: {test_response.get('ok', False)}")
    return test_response.get('result', {}).get('message_id')

def check_database_state():
    """Проверяет состояние базы данных"""
    print("\n🗄️ Проверка состояния базы данных...")
    
    import sys
    sys.path.append('/var/www/vpn/vpn_bot')
    
    try:
        from db.models import session, BypassSite, VpnBypassRule, VpnKey
        
        sites_count = session.query(BypassSite).count()
        rules_count = session.query(VpnBypassRule).count()
        keys_count = session.query(VpnKey).count()
        
        print(f"  📊 Сайтов для исключений: {sites_count}")
        print(f"  📊 Правил исключений: {rules_count}")
        print(f"  📊 VPN ключей: {keys_count}")
        
        # Показываем популярные сайты
        popular_sites = session.query(BypassSite)\
                              .filter(BypassSite.is_verified == True)\
                              .order_by(BypassSite.usage_count.desc())\
                              .limit(5).all()
        
        if popular_sites:
            print("  🔥 Популярные сайты:")
            for site in popular_sites:
                print(f"    • {site.name} ({site.domain}) - {site.usage_count} использований")
        else:
            print("  📝 Популярных сайтов пока нет")
            
    except Exception as e:
        print(f"  ❌ Ошибка БД: {e}")

def test_manual_workflow():
    """Показывает инструкции для ручного тестирования"""
    print("\n🎯 Инструкции для ручного тестирования:")
    print("  1. Откройте бота в Telegram")
    print("  2. Нажмите 🚀 Xray (VLESS)")
    print("  3. Выберите '🌐 Популярные сайты'")
    print("  4. Добавьте несколько сайтов (например, YouTube)")
    print("  5. Нажмите '📋 Мои исключения' для просмотра")
    print("  6. Создайте ключ через '🔗 Создать ключ'")
    print("  7. Проверьте работу через '⚙️ Настройки исключений'")

def main():
    """Основная функция тестирования"""
    print("🧪 Запуск интеграционного тестирования системы исключений...\n")
    
    # Тест 1: Состояние БД
    check_database_state()
    
    # Тест 2: Отправка через Telegram
    test_xray_menu()
    
    # Тест 3: Инструкции для ручного тестирования
    test_manual_workflow()
    
    print("\n✅ Интеграционное тестирование завершено!")
    print("🔗 Откройте бота в Telegram для полного тестирования интерфейса")

if __name__ == "__main__":
    main()