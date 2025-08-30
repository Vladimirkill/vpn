#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы VPN бота
"""

from vpn_bot.keyboard.vpn_keyboards import (
    get_vpn_keyboard, 
    get_key_management_keyboard, 
    get_confirmation_keyboard,
    get_main_menu_keyboard
)

def test_keyboards():
    """Тестирует создание клавиатур"""
    print("🧪 Тестирование клавиатур VPN бота")
    print("=" * 60)
    
    # Тест главного меню
    print("1. Главное меню:")
    main_kb = get_main_menu_keyboard()
    print(f"   Кнопок: {len(main_kb.inline_keyboard)}")
    for row in main_kb.inline_keyboard:
        for button in row:
            print(f"   • {button.text} -> {button.callback_data}")
    print()
    
    # Тест клавиатуры для пользователя с ключом
    print("2. Клавиатура для пользователя с ключом:")
    kb_with_key = get_vpn_keyboard("test_user", has_existing_key=True)
    print(f"   Кнопок: {len(kb_with_key.inline_keyboard)}")
    for row in kb_with_key.inline_keyboard:
        for button in row:
            print(f"   • {button.text} -> {button.callback_data}")
    print()
    
    # Тест клавиатуры для нового пользователя
    print("3. Клавиатура для нового пользователя:")
    kb_new_user = get_vpn_keyboard("new_user", has_existing_key=False)
    print(f"   Кнопок: {len(kb_new_user.inline_keyboard)}")
    for row in kb_new_user.inline_keyboard:
        for button in row:
            print(f"   • {button.text} -> {button.callback_data}")
    print()
    
    # Тест клавиатуры управления ключом
    print("4. Клавиатура управления ключом:")
    kb_manage = get_key_management_keyboard("test_user")
    print(f"   Кнопок: {len(kb_manage.inline_keyboard)}")
    for row in kb_manage.inline_keyboard:
        for button in row:
            print(f"   • {button.text} -> {button.callback_data}")
    print()
    
    # Тест клавиатуры подтверждения
    print("5. Клавиатура подтверждения:")
    kb_confirm = get_confirmation_keyboard("delete", "test_user")
    print(f"   Кнопок: {len(kb_confirm.inline_keyboard)}")
    for row in kb_confirm.inline_keyboard:
        for button in row:
            print(f"   • {button.text} -> {button.callback_data}")
    print()

if __name__ == "__main__":
    test_keyboards()
    print("✅ Тестирование завершено")