#!/bin/bash
# Скрипт управления VPN Bot сервисом

SERVICE_NAME="vpn-bot"
PROJECT_DIR="/var/www/vpn"

case "$1" in
    start)
        echo "🚀 Запуск VPN Bot сервиса..."
        systemctl start $SERVICE_NAME
        systemctl status $SERVICE_NAME --no-pager
        ;;
    stop)
        echo "⏹️ Остановка VPN Bot сервиса..."
        systemctl stop $SERVICE_NAME
        systemctl status $SERVICE_NAME --no-pager
        ;;
    restart)
        echo "🔄 Перезапуск VPN Bot сервиса..."
        systemctl restart $SERVICE_NAME
        systemctl status $SERVICE_NAME --no-pager
        ;;
    status)
        echo "📊 Статус VPN Bot сервиса:"
        systemctl status $SERVICE_NAME --no-pager
        ;;
    logs)
        echo "📋 Логи VPN Bot сервиса:"
        journalctl -u $SERVICE_NAME -f --no-pager
        ;;
    logs-tail)
        echo "📋 Последние 50 строк логов:"
        journalctl -u $SERVICE_NAME -n 50 --no-pager
        ;;
    enable)
        echo "✅ Включение автозапуска сервиса..."
        systemctl enable $SERVICE_NAME
        ;;
    disable)
        echo "❌ Отключение автозапуска сервиса..."
        systemctl disable $SERVICE_NAME
        ;;
    check-config)
        echo "🔍 Проверка конфигурации..."
        echo "Файл .env:"
        if [ -f "$PROJECT_DIR/vpn_bot/.env" ]; then
            echo "✅ Файл .env существует"
            echo "Содержимое (без секретных данных):"
            grep -E "^[A-Z_]+=.*" "$PROJECT_DIR/vpn_bot/.env" | sed 's/=.*/=***/'
        else
            echo "❌ Файл .env не найден!"
        fi
        echo ""
        echo "Виртуальное окружение:"
        if [ -d "$PROJECT_DIR/venv" ]; then
            echo "✅ Виртуальное окружение существует"
        else
            echo "❌ Виртуальное окружение не найдено!"
        fi
        ;;
    *)
        echo "🤖 Управление VPN Bot сервисом"
        echo "Использование: $0 {start|stop|restart|status|logs|logs-tail|enable|disable|check-config}"
        echo ""
        echo "Команды:"
        echo "  start       - Запустить сервис"
        echo "  stop        - Остановить сервис"
        echo "  restart     - Перезапустить сервис"
        echo "  status      - Показать статус сервиса"
        echo "  logs        - Показать логи в реальном времени"
        echo "  logs-tail   - Показать последние 50 строк логов"
        echo "  enable      - Включить автозапуск"
        echo "  disable     - Отключить автозапуск"
        echo "  check-config - Проверить конфигурацию"
        exit 1
        ;;
esac