#!/bin/bash
# Скрипт для активации виртуального окружения VPN проекта

echo "🔧 Активация виртуального окружения..."
cd /var/www/vpn
source venv/bin/activate

echo "✅ Виртуальное окружение активировано!"
echo "📦 Установленные пакеты:"
pip list

echo ""
echo "💡 Для работы с проектом используйте:"
echo "   cd /var/www/vpn"
echo "   source venv/bin/activate"
echo ""
echo "📋 Не забудьте создать файл .env на основе env_example.txt"