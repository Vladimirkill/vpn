#!/bin/bash

# Скрипт для установки и настройки системы автоматического мониторинга Xray
# Запускать с правами root

set -e

echo "🚀 Установка системы автоматического мониторинга Xray..."

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Этот скрипт должен быть запущен с правами root"
    exit 1
fi

# Проверяем существование директории проекта
PROJECT_DIR="/var/www/vpn"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Директория проекта не найдена: $PROJECT_DIR"
    exit 1
fi

# Переходим в директорию проекта
cd "$PROJECT_DIR"

echo "📁 Директория проекта: $PROJECT_DIR"

# 1. Делаем скрипт мониторинга исполняемым
echo "🔧 Настройка скрипта мониторинга..."
chmod +x xray/monitor_clients.py

# 2. Создаем systemd сервис
echo "📋 Создание systemd сервиса..."
cat > /etc/systemd/system/xray-monitor.service << 'EOF'
[Unit]
Description=Xray Configuration Monitor
After=network.target xray.service
Wants=xray.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/project987/vpn/xray
ExecStart=/usr/bin/python3 /var/www/project987/vpn/xray/monitor_clients.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 3. Создаем директорию для логов
echo "📝 Создание директории для логов..."
mkdir -p /var/log
touch /var/log/xray-monitor.log
chmod 644 /var/log/xray-monitor.log

# 4. Перезагружаем systemd
echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload

# 5. Включаем автозапуск
echo "✅ Включение автозапуска..."
systemctl enable xray-monitor

# 6. Запускаем сервис
echo "🚀 Запуск сервиса мониторинга..."
systemctl start xray-monitor

# 7. Проверяем статус
echo "📊 Проверка статуса..."
sleep 3
systemctl status xray-monitor --no-pager -l

# 8. Проверяем логи
echo "📝 Проверка логов..."
if [ -f /var/log/xray-monitor.log ]; then
    echo "Последние записи в логе:"
    tail -n 10 /var/log/xray-monitor.log
else
    echo "⚠️ Лог файл не создан"
fi

# 9. Создаем скрипт для управления
echo "🔧 Создание скрипта управления..."
cat > /usr/local/bin/xray-monitor << 'EOF'
#!/bin/bash

case "$1" in
    start)
        systemctl start xray-monitor
        echo "✅ Мониторинг Xray запущен"
        ;;
    stop)
        systemctl stop xray-monitor
        echo "🛑 Мониторинг Xray остановлен"
        ;;
    restart)
        systemctl restart xray-monitor
        echo "🔄 Мониторинг Xray перезапущен"
        ;;
    status)
        systemctl status xray-monitor --no-pager -l
        ;;
    logs)
        journalctl -u xray-monitor -f
        ;;
    log-file)
        tail -f /var/log/xray-monitor.log
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|log-file}"
        echo ""
        echo "Команды:"
        echo "  start     - запустить мониторинг"
        echo "  stop      - остановить мониторинг"
        echo "  restart   - перезапустить мониторинг"
        echo "  status    - показать статус"
        echo "  logs      - показать логи systemd"
        echo "  log-file  - показать лог файл"
        exit 1
        ;;
esac
EOF

chmod +x /usr/local/bin/xray-monitor

# 10. Создаем cron задачу для проверки состояния
echo "⏰ Создание cron задачи..."
cat > /etc/cron.d/xray-monitor-check << 'EOF'
# Проверка состояния мониторинга Xray каждые 5 минут
*/5 * * * * root /usr/local/bin/xray-monitor status > /dev/null 2>&1 || systemctl restart xray-monitor
EOF

# 11. Проверяем интеграцию с существующими скриптами
echo "🔍 Проверка интеграции..."

# Проверяем run_generate.py
if grep -q "xray-monitor" run_generate.py; then
    echo "✅ run_generate.py интегрирован с мониторингом"
else
    echo "⚠️ run_generate.py не интегрирован с мониторингом"
fi

# Проверяем safe_restart.py
if [ -f "xray/safe_restart.py" ]; then
    echo "✅ safe_restart.py найден"
else
    echo "⚠️ safe_restart.py не найден"
fi

# Проверяем build_config.py
if [ -f "xray/build_config.py" ]; then
    echo "✅ build_config.py найден"
else
    echo "⚠️ build_config.py не найден"
fi

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Полезные команды:"
echo "  Статус мониторинга: xray-monitor status"
echo "  Просмотр логов: xray-monitor logs"
echo "  Просмотр лог файла: xray-monitor log-file"
echo "  Перезапуск: xray-monitor restart"
echo ""
echo "📁 Файлы:"
echo "  Сервис: /etc/systemd/system/xray-monitor.service"
echo "  Логи: /var/log/xray-monitor.log"
echo "  Скрипт управления: /usr/local/bin/xray-monitor"
echo ""
echo "🔍 Мониторинг будет автоматически:"
echo "  • Отслеживать изменения в директории клиентов"
echo "  • Пересобирать конфигурацию при изменениях"
echo "  • Безопасно перезапускать Xray"
echo "  • Защищать IP пользователей от утечки"
echo ""
echo "💡 Для тестирования создайте нового клиента:"
echo "  python3 run_generate.py test_client" 