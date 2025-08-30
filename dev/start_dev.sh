#!/bin/bash

# 🔧 Скрипт запуска DEV версии VPN бота

echo "🔧 Запуск DEV версии VPN бота..."

# Переходим в папку dev
cd /var/www/vpn/dev

# Активируем виртуальное окружение из корня
source ../venv/bin/activate

# Устанавливаем переменные окружения для DEV
export ENVIRONMENT=development
export DEBUG=true
export LOG_LEVEL=DEBUG

# Проверяем наличие .env файла
if [ ! -f "vpn_bot/.env" ]; then
    echo "❌ Файл .env не найден в vpn_bot/"
    echo "📋 Создайте файл .env на основе env_example.txt"
    exit 1
fi

echo "✅ Окружение: $ENVIRONMENT"
echo "🔧 Порт Xray: 11443 (DEV)"
echo "📊 База данных: dev_vpn.db"
echo "🚀 Запуск бота..."

# Запускаем бота
python vpn_bot/bot.py