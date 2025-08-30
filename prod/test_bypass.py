#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы исключений
"""

import sys
import os
import asyncio

# Добавляем путь к проекту
sys.path.append('/var/www/vpn')
sys.path.append('/var/www/vpn/vpn_bot')

from vpn_bot.handler.vpn_handler import VPNHandler
from vpn_bot.db.models import session, BypassSite, VpnBypassRule, VpnKey, User, ensure_user

async def test_domain_validation():
    """Тестирует валидацию доменов"""
    print("🔍 Тестирование валидации доменов...")
    
    handler = VPNHandler()
    
    test_domains = [
        "google.com",
        "youtube.com", 
        "vk.com",
        "nonexistentdomain12345.com",
        "https://www.yandex.ru",
        "mail.ru/inbox"
    ]
    
    for domain in test_domains:
        is_valid = await handler._validate_domain(domain)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {domain}")

async def test_bypass_site_creation():
    """Тестирует создание сайтов для исключений"""
    print("\n📝 Тестирование создания сайтов...")
    
    handler = VPNHandler()
    
    # Создаем тестового пользователя
    class MockUser:
        def __init__(self):
            self.id = 1
            self.username = "test_user"
    
    mock_user = MockUser()
    user = ensure_user(mock_user)
    
    test_sites = [
        {"domain": "youtube.com", "name": "YouTube", "category": "streaming"},
        {"domain": "vk.com", "name": "ВКонтакте", "category": "social"},
        {"domain": "invalid-test-domain.fake", "name": "Тестовый домен", "category": "test"}
    ]
    
    for site_data in test_sites:
        site = await handler._add_bypass_site(
            domain=site_data["domain"],
            name=site_data["name"], 
            user_id=user.id,
            category=site_data["category"]
        )
        
        if site:
            verification = "✅ Проверен" if site.is_verified else "⚠️ Не проверен"
            print(f"  ✅ Создан: {site.name} ({site.domain}) - {verification}")
        else:
            print(f"  ❌ Ошибка создания: {site_data['name']}")

def test_database_structure():
    """Тестирует структуру базы данных"""
    print("\n🗄️ Тестирование структуры БД...")
    
    try:
        # Проверяем таблицы
        sites_count = session.query(BypassSite).count()
        print(f"  📊 Сайтов в БД: {sites_count}")
        
        # Показываем все сайты
        sites = session.query(BypassSite).all()
        for site in sites:
            verification = "✅" if site.is_verified else "⚠️"
            print(f"    {verification} {site.name} ({site.domain}) - {site.category}")
            
    except Exception as e:
        print(f"  ❌ Ошибка БД: {e}")

async def test_popular_sites():
    """Тестирует получение популярных сайтов"""
    print("\n🌐 Тестирование популярных сайтов...")
    
    handler = VPNHandler()
    popular_sites = await handler._get_popular_bypass_sites()
    
    if popular_sites:
        print(f"  📊 Найдено популярных сайтов: {len(popular_sites)}")
        for site in popular_sites:
            print(f"    🔥 {site.name} ({site.domain}) - {site.usage_count} использований")
    else:
        print("  📝 Популярных сайтов пока нет, будут использованы сайты по умолчанию")

async def main():
    """Основная функция тестирования"""
    print("🧪 Запуск тестирования системы исключений...\n")
    
    # Тест 1: Валидация доменов
    await test_domain_validation()
    
    # Тест 2: Структура БД
    test_database_structure()
    
    # Тест 3: Создание сайтов
    await test_bypass_site_creation()
    
    # Тест 4: Популярные сайты
    await test_popular_sites()
    
    # Финальная проверка БД
    print("\n📊 Финальное состояние БД:")
    test_database_structure()
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main())