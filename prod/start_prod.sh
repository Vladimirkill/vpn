#!/bin/bash

# 🏭 Скрипт запуска PROD версии VPN бота

echo "🏭 Запуск PROD версии VPN бота..."

# Переходим в папку prod
cd /var/www/vpn/prod

# Активируем виртуальное окружение из корня
source ../venv/bin/activate

# Устанавливаем переменные окружения для PROD
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=INFO

# Проверяем наличие .env файла
if [ ! -f "vpn_bot/.env" ]; then
    echo "❌ Файл .env не найден в vpn_bot/"
    echo "📋 Создайте файл .env на основе env_example.txt"
    exit 1
fi

echo "✅ Окружение: $ENVIRONMENT"
echo "🏭 Порт Xray: 10443 (PROD)"
echo "📊 База данных: vpn.db"
echo "🚀 Запуск бота..."

# Запускаем бота
python vpn_bot/bot.py