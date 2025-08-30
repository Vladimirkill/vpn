#!/bin/bash

# ⚡ Быстрое накатывание DEV на PROD (без подтверждений)
# Для использования в CI/CD или автоматических скриптах

echo "⚡ Быстрое развертывание DEV → PROD"
echo "=================================="

# Проверяем что мы в правильной директории
if [ ! -d "dev" ] || [ ! -d "prod" ]; then
    echo "❌ Ошибка: Скрипт должен запускаться из /var/www/vpn/"
    exit 1
fi

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Ошибка: Скрипт должен запускаться от root"
    exit 1
fi

echo "🔄 Запускаем автоматическое развертывание..."

# Создаем бэкап с временной меткой
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/www/vpn/backups"
mkdir -p "$BACKUP_DIR"

echo "💾 Создаем бэкап: prod_backup_$TIMESTAMP"
cp -r prod "$BACKUP_DIR/prod_backup_$TIMESTAMP"

# Останавливаем PROD сервис если запущен
if systemctl is-active --quiet vpn-bot-prod 2>/dev/null; then
    echo "⏹️  Останавливаем PROD бот..."
    systemctl stop vpn-bot-prod
    RESTART_PROD=true
else
    RESTART_PROD=false
fi

# Синхронизируем файлы (исключаем конфиги и данные)
echo "📁 Синхронизируем файлы..."
rsync -av \
    --exclude=.env \
    --exclude=*.db \
    --exclude=logs/ \
    --exclude=__pycache__/ \
    --exclude=*.pyc \
    --exclude=ENV_CONFIG.md \
    --exclude=start_*.sh \
    dev/ prod/

# Убеждаемся что в prod конфиге установлено production
sed -i 's/ENVIRONMENT = os.getenv("ENVIRONMENT", "development")/ENVIRONMENT = os.getenv("ENVIRONMENT", "production")/g' prod/vpn_bot/config.py

# Проверяем синтаксис
echo "🔍 Проверяем синтаксис..."
cd prod
python3 -m py_compile vpn_bot/bot.py || {
    echo "❌ Ошибка синтаксиса в bot.py"
    exit 1
}
cd ..

# Запускаем PROD сервис если он был запущен
if [ "$RESTART_PROD" = true ]; then
    echo "▶️  Запускаем PROD бот..."
    systemctl start vpn-bot-prod
    sleep 2
    
    if systemctl is-active --quiet vpn-bot-prod; then
        echo "✅ PROD бот запущен успешно"
    else
        echo "❌ Не удалось запустить PROD бот"
        exit 1
    fi
fi

# Очищаем старые бэкапы (оставляем последние 5)
ls -t "$BACKUP_DIR"/prod_backup_* 2>/dev/null | tail -n +6 | xargs -r rm -rf

echo ""
echo "🎉 Быстрое развертывание завершено успешно!"
echo "📊 Статус: PROD бот $(systemctl is-active vpn-bot-prod 2>/dev/null || echo 'остановлен')"
echo "💾 Бэкап: $BACKUP_DIR/prod_backup_$TIMESTAMP"