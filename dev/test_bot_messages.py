#!/usr/bin/env python3
"""
Тестовый скрипт для проверки сообщений бота
"""

from vpn_bot.utils.generator import generate_vpn_link

def test_existing_user():
    """Тестирует сообщение для пользователя с существующим ключом"""
    print("🧪 Тест: Пользователь с существующим ключом")
    print("=" * 60)
    
    result = generate_vpn_link('user_5406831921')
    print("Сообщение:")
    print(result[0] if result[0] else 'None')
    print(f"UUID: {result[1] if result[1] else 'None'}")
    print()

def test_new_user():
    """Тестирует создание ключа для нового пользователя"""
    print("🧪 Тест: Новый пользователь")
    print("=" * 60)
    
    result = generate_vpn_link('test_bot_user_new')
    print("Результат:")
    print(result[0] if result[0] else 'None')
    print(f"UUID: {result[1] if result[1] else 'None'}")
    print()

if __name__ == "__main__":
    print("🔍 Тестирование сообщений бота")
    print("=" * 60)
    print()
    
    test_existing_user()
    test_new_user()
    
    print("✅ Тестирование завершено") 