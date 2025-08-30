#!/bin/bash

# 🔧 Скрипт инициализации DEV базы данных
# Копирует структуру и данные из PROD в DEV

echo "🔧 Инициализация DEV базы данных"
echo "================================="

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Скрипт должен запускаться от root"
    exit 1
fi

# Проверяем что базы данных существуют
echo "🔍 Проверяем базы данных..."

PROD_DB_EXISTS=$(sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -w vpn_db | wc -l)
DEV_DB_EXISTS=$(sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -w vpn_db_dev | wc -l)

if [ "$PROD_DB_EXISTS" -eq 0 ]; then
    echo "❌ PROD база данных vpn_db не найдена"
    exit 1
fi

if [ "$DEV_DB_EXISTS" -eq 0 ]; then
    echo "❌ DEV база данных vpn_db_dev не найдена"
    echo "💡 Создаем DEV базу данных..."
    sudo -u postgres psql -c "CREATE DATABASE vpn_db_dev;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vpn_db_dev TO username;"
fi

echo "✅ Базы данных найдены"

# Функция подтверждения
confirm() {
    read -p "$1 [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Операция отменена"
        exit 1
    fi
}

# Предупреждение
echo ""
echo "⚠️  ВНИМАНИЕ!"
echo "Эта операция:"
echo "1. Очистит DEV базу данных vpn_db_dev"
echo "2. Скопирует всю структуру и данные из PROD (vpn_db)"
echo "3. DEV база будет идентична PROD базе"
echo ""

confirm "🚀 Продолжить инициализацию DEV базы данных?"

# Создаем дамп PROD базы
echo "📦 Создаем дамп PROD базы данных..."
DUMP_FILE="/tmp/vpn_prod_dump_$(date +%Y%m%d_%H%M%S).sql"

sudo -u postgres pg_dump vpn_db > "$DUMP_FILE"

if [ $? -ne 0 ]; then
    echo "❌ Ошибка создания дампа PROD базы"
    exit 1
fi

echo "✅ Дамп создан: $DUMP_FILE"

# Очищаем DEV базу
echo "🧹 Очищаем DEV базу данных..."
sudo -u postgres psql -d vpn_db_dev -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO username; GRANT ALL ON SCHEMA public TO public;"

# Восстанавливаем дамп в DEV базу
echo "📥 Восстанавливаем данные в DEV базу..."
sudo -u postgres psql -d vpn_db_dev < "$DUMP_FILE"

if [ $? -ne 0 ]; then
    echo "❌ Ошибка восстановления данных в DEV базу"
    echo "💾 Дамп сохранен: $DUMP_FILE"
    exit 1
fi

# Удаляем временный дамп
rm -f "$DUMP_FILE"

echo ""
echo "🎉 Инициализация DEV базы данных завершена успешно!"
echo ""
echo "📊 Информация:"
echo "  🏭 PROD база: vpn_db"
echo "  🔧 DEV база:  vpn_db_dev"
echo ""
echo "📋 Теперь можно запускать DEV версию:"
echo "  cd /var/www/vpn/dev"
echo "  ./start_dev.sh"