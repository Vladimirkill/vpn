#!/bin/bash
# Скрипт управления Nginx для VPN сервиса

DOMAIN="v452799.hosted-by-vdsina.com"
NGINX_CONFIG="/etc/nginx/sites-available/vpn-service"
WEB_ROOT="/var/www/vpn/web"
CONFIGS_DIR="/var/www/vpn/configs"

case "$1" in
    status)
        echo "📊 Статус Nginx сервера:"
        systemctl status nginx --no-pager
        echo ""
        echo "🔍 Активные сайты:"
        ls -la /etc/nginx/sites-enabled/
        echo ""
        echo "🌐 Тест подключения:"
        curl -I https://$DOMAIN 2>/dev/null | head -5
        ;;
    test)
        echo "🧪 Тестирование конфигурации Nginx..."
        nginx -t
        if [ $? -eq 0 ]; then
            echo "✅ Конфигурация корректна"
        else
            echo "❌ Ошибка в конфигурации"
        fi
        ;;
    reload)
        echo "🔄 Перезагрузка конфигурации Nginx..."
        nginx -t && systemctl reload nginx
        if [ $? -eq 0 ]; then
            echo "✅ Конфигурация перезагружена"
        else
            echo "❌ Ошибка перезагрузки"
        fi
        ;;
    restart)
        echo "🔄 Перезапуск Nginx..."
        systemctl restart nginx
        systemctl status nginx --no-pager
        ;;
    ssl-status)
        echo "🔐 Статус SSL сертификата:"
        certbot certificates
        echo ""
        echo "📅 Информация о сертификате:"
        openssl x509 -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem -text -noout | grep -A2 "Validity"
        ;;
    ssl-renew)
        echo "🔄 Обновление SSL сертификата..."
        certbot renew --dry-run
        if [ $? -eq 0 ]; then
            echo "✅ Тест обновления прошел успешно"
            certbot renew
        else
            echo "❌ Ошибка при тесте обновления"
        fi
        ;;
    ssl-test)
        echo "🔍 Тестирование SSL конфигурации..."
        echo "Проверка через SSL Labs (может занять несколько минут):"
        echo "https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
        echo ""
        echo "Быстрая проверка SSL:"
        openssl s_client -connect $DOMAIN:443 -servername $DOMAIN < /dev/null 2>/dev/null | openssl x509 -noout -dates
        ;;
    logs)
        echo "📋 Логи Nginx:"
        echo "=== Access Log ==="
        tail -20 /var/log/nginx/vpn-access.log
        echo ""
        echo "=== Error Log ==="
        tail -20 /var/log/nginx/vpn-error.log
        ;;
    logs-live)
        echo "📋 Логи Nginx в реальном времени:"
        tail -f /var/log/nginx/vpn-access.log /var/log/nginx/vpn-error.log
        ;;
    security-headers)
        echo "🛡️ Проверка заголовков безопасности:"
        curl -I https://$DOMAIN 2>/dev/null | grep -E "(Strict-Transport-Security|X-Frame-Options|X-Content-Type-Options|X-XSS-Protection|Referrer-Policy)"
        ;;
    add-user)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "❌ Использование: $0 add-user <username> <password>"
            exit 1
        fi
        echo "👤 Добавление пользователя $2..."
        htpasswd -b /etc/nginx/.htpasswd "$2" "$3"
        echo "✅ Пользователь $2 добавлен"
        ;;
    list-users)
        echo "👥 Список пользователей для защищенных разделов:"
        if [ -f /etc/nginx/.htpasswd ]; then
            cut -d: -f1 /etc/nginx/.htpasswd
        else
            echo "❌ Файл паролей не найден"
        fi
        ;;
    backup-config)
        backup_file="/var/backups/nginx-vpn-config-$(date +%Y%m%d_%H%M%S).tar.gz"
        echo "💾 Создание резервной копии конфигурации..."
        tar -czf "$backup_file" /etc/nginx/sites-available/vpn-service /etc/nginx/.htpasswd "$WEB_ROOT" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✅ Резервная копия создана: $backup_file"
            ls -lh "$backup_file"
        else
            echo "❌ Ошибка создания резервной копии"
        fi
        ;;
    performance)
        echo "⚡ Тест производительности:"
        echo "Время отклика HTTPS:"
        curl -o /dev/null -s -w "Время подключения: %{time_connect}s\nВремя до первого байта: %{time_starttransfer}s\nОбщее время: %{time_total}s\n" https://$DOMAIN
        echo ""
        echo "Размер главной страницы:"
        curl -s https://$DOMAIN | wc -c | awk '{print $1 " байт"}'
        ;;
    firewall)
        echo "🔥 Настройка базового файрвола для Nginx:"
        ufw allow 'Nginx Full'
        ufw allow ssh
        echo "✅ Правила файрвола обновлены"
        ufw status
        ;;
    *)
        echo "🌐 Управление Nginx для VPN сервиса"
        echo "Использование: $0 {status|test|reload|restart|ssl-status|ssl-renew|ssl-test|logs|logs-live|security-headers|add-user|list-users|backup-config|performance|firewall}"
        echo ""
        echo "Команды:"
        echo "  status           - Показать статус Nginx"
        echo "  test             - Проверить конфигурацию"
        echo "  reload           - Перезагрузить конфигурацию"
        echo "  restart          - Перезапустить Nginx"
        echo "  ssl-status       - Статус SSL сертификата"
        echo "  ssl-renew        - Обновить SSL сертификат"
        echo "  ssl-test         - Тестировать SSL конфигурацию"
        echo "  logs             - Показать последние логи"
        echo "  logs-live        - Логи в реальном времени"
        echo "  security-headers - Проверить заголовки безопасности"
        echo "  add-user         - Добавить пользователя для защищенных разделов"
        echo "  list-users       - Список пользователей"
        echo "  backup-config    - Создать резервную копию конфигурации"
        echo "  performance      - Тест производительности"
        echo "  firewall         - Настроить базовый файрвол"
        echo ""
        echo "Домен: $DOMAIN"
        echo "Конфигурация: $NGINX_CONFIG"
        echo "Веб-корень: $WEB_ROOT"
        exit 1
        ;;
esac