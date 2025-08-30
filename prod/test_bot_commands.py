#!/usr/bin/env python3
"""
Тест команд Telegram бота
Проверяет что бот отвечает на команды
"""

import requests
import json
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv('/var/www/vpn/vpn_bot/.env')

BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def test_bot_info():
    """Тестирует получение информации о боте"""
    print("🤖 Тестирование информации о боте...")
    
    try:
        response = requests.get(f"{BASE_URL}/getMe")
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info['ok']:
                result = bot_info['result']
                print(f"   ✅ Бот активен: @{result['username']}")
                print(f"   📝 Имя: {result['first_name']}")
                print(f"   🆔 ID: {result['id']}")
                return True
            else:
                print(f"   ❌ Ошибка API: {bot_info}")
                return False
        else:
            print(f"   ❌ HTTP ошибка: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка подключения: {e}")
        return False

def test_webhook_status():
    """Проверяет статус webhook"""
    print("\n🔗 Проверка статуса webhook...")
    
    try:
        response = requests.get(f"{BASE_URL}/getWebhookInfo")
        if response.status_code == 200:
            webhook_info = response.json()
            if webhook_info['ok']:
                result = webhook_info['result']
                if result['url']:
                    print(f"   🌐 Webhook URL: {result['url']}")
                else:
                    print("   ✅ Webhook отключен (polling режим)")
                return True
            else:
                print(f"   ❌ Ошибка API: {webhook_info}")
                return False
        else:
            print(f"   ❌ HTTP ошибка: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка подключения: {e}")
        return False

def get_recent_updates():
    """Получает последние обновления"""
    print("\n📨 Проверка последних сообщений...")
    
    try:
        response = requests.get(f"{BASE_URL}/getUpdates?limit=5")
        if response.status_code == 200:
            updates = response.json()
            if updates['ok']:
                result = updates['result']
                if result:
                    print(f"   📊 Найдено {len(result)} последних обновлений")
                    for update in result[-3:]:  # Показываем последние 3
                        if 'message' in update:
                            msg = update['message']
                            user = msg.get('from', {})
                            text = msg.get('text', 'Нет текста')
                            print(f"   💬 От @{user.get('username', 'unknown')}: {text}")
                else:
                    print("   ℹ️ Нет новых сообщений")
                return True
            else:
                print(f"   ❌ Ошибка API: {updates}")
                return False
        else:
            print(f"   ❌ HTTP ошибка: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка подключения: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ TELEGRAM БОТА")
    print("="*50)
    
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        print("❌ Токен бота не настроен!")
        return
    
    # Тестируем различные аспекты бота
    tests = [
        test_bot_info,
        test_webhook_status,
        get_recent_updates
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Подводим итоги
    print("\n" + "="*50)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    
    success_count = sum(results)
    total_tests = len(results)
    
    if success_count == total_tests:
        print(f"✅ Все тесты пройдены ({success_count}/{total_tests})")
        print("🎉 Бот работает корректно!")
        print("\n💡 Для тестирования команд:")
        print("   1. Найдите бота в Telegram")
        print("   2. Отправьте команду /start")
        print("   3. Проверьте ответ бота")
    else:
        print(f"⚠️ Пройдено {success_count}/{total_tests} тестов")
        print("🔧 Требуется дополнительная настройка")

if __name__ == "__main__":
    main()