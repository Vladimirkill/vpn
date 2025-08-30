#!/bin/bash
# Скрипт управления базой данных VPN Bot

DB_NAME="vpn_db"
DB_USER="username"
DB_PASSWORD="bhjbsjcvbsjbcvjbs467586"
PROJECT_DIR="/var/www/vpn"

case "$1" in
    status)
        echo "📊 Статус базы данных PostgreSQL:"
        systemctl status postgresql --no-pager
        echo ""
        echo "🔍 Информация о базе данных:"
        sudo -u postgres psql -c "\l" | grep "$DB_NAME"
        echo ""
        echo "👥 Пользователи базы данных:"
        sudo -u postgres psql -c "\du" | grep "$DB_USER"
        ;;
    test)
        echo "🧪 Тестирование подключения к базе данных..."
        cd "$PROJECT_DIR"
        source venv/bin/activate
        python3 -c "
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('vpn_bot/.env')
database_url = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    cur.execute('SELECT current_database(), current_user, version();')
    result = cur.fetchone()
    print(f'✅ Подключение успешно!')
    print(f'🗄️ База данных: {result[0]}')
    print(f'👤 Пользователь: {result[1]}')
    print(f'📊 Версия: {result[2][:50]}...')
    cur.close()
    conn.close()
except Exception as e:
    print(f'❌ Ошибка подключения: {e}')
"
        ;;
    backup)
        echo "💾 Создание резервной копии базы данных..."
        backup_file="/var/backups/vpn_db_$(date +%Y%m%d_%H%M%S).sql"
        sudo -u postgres pg_dump "$DB_NAME" > "$backup_file"
        if [ $? -eq 0 ]; then
            echo "✅ Резервная копия создана: $backup_file"
            ls -lh "$backup_file"
        else
            echo "❌ Ошибка создания резервной копии"
        fi
        ;;
    restore)
        if [ -z "$2" ]; then
            echo "❌ Укажите путь к файлу резервной копии"
            echo "Использование: $0 restore /path/to/backup.sql"
            exit 1
        fi
        echo "🔄 Восстановление базы данных из $2..."
        sudo -u postgres psql "$DB_NAME" < "$2"
        if [ $? -eq 0 ]; then
            echo "✅ База данных восстановлена"
        else
            echo "❌ Ошибка восстановления"
        fi
        ;;
    reset)
        echo "⚠️ ВНИМАНИЕ: Это удалит все данные в базе данных!"
        read -p "Вы уверены? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo "🗑️ Пересоздание базы данных..."
            sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"
            sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
            echo "✅ База данных пересоздана"
        else
            echo "❌ Операция отменена"
        fi
        ;;
    logs)
        echo "📋 Логи PostgreSQL:"
        sudo tail -f /var/log/postgresql/postgresql-14-main.log
        ;;
    psql)
        echo "🔗 Подключение к базе данных через psql..."
        PGPASSWORD="$DB_PASSWORD" psql -h localhost -U "$DB_USER" -d "$DB_NAME"
        ;;
    tables)
        echo "📋 Таблицы в базе данных:"
        PGPASSWORD="$DB_PASSWORD" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "\dt"
        ;;
    size)
        echo "📏 Размер базы данных:"
        sudo -u postgres psql -c "
        SELECT 
            pg_database.datname as database_name,
            pg_size_pretty(pg_database_size(pg_database.datname)) as size
        FROM pg_database 
        WHERE pg_database.datname = '$DB_NAME';
        "
        ;;
    *)
        echo "🗄️ Управление базой данных VPN Bot"
        echo "Использование: $0 {status|test|backup|restore|reset|logs|psql|tables|size}"
        echo ""
        echo "Команды:"
        echo "  status    - Показать статус PostgreSQL и информацию о БД"
        echo "  test      - Тестировать подключение к базе данных"
        echo "  backup    - Создать резервную копию базы данных"
        echo "  restore   - Восстановить базу данных из резервной копии"
        echo "  reset     - Пересоздать базу данных (УДАЛИТ ВСЕ ДАННЫЕ!)"
        echo "  logs      - Показать логи PostgreSQL"
        echo "  psql      - Подключиться к базе данных через psql"
        echo "  tables    - Показать список таблиц в базе данных"
        echo "  size      - Показать размер базы данных"
        echo ""
        echo "База данных: $DB_NAME"
        echo "Пользователь: $DB_USER"
        exit 1
        ;;
esac