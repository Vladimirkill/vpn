#!/bin/bash
# Скрипт для настройки переменных окружения VPN Bot

ENV_FILE="/var/www/vpn/vpn_bot/.env"

echo "🔧 Настройка переменных окружения для VPN Bot"
echo "=============================================="

# Функция для безопасного ввода токена
read_token() {
    echo -n "Введите BOT_TOKEN (Telegram Bot Token): "
    read -s token
    echo
    if [ -z "$token" ]; then
        echo "❌ Токен не может быть пустым!"
        return 1
    fi
    echo "$token"
}

# Функция для обновления переменной в .env файле
update_env_var() {
    local var_name="$1"
    local var_value="$2"
    
    if grep -q "^${var_name}=" "$ENV_FILE"; then
        # Обновляем существующую переменную
        sed -i "s|^${var_name}=.*|${var_name}=${var_value}|" "$ENV_FILE"
    else
        # Добавляем новую переменную
        echo "${var_name}=${var_value}" >> "$ENV_FILE"
    fi
}

# Основная логика
case "$1" in
    bot-token)
        echo "Настройка BOT_TOKEN..."
        token=$(read_token)
        if [ $? -eq 0 ]; then
            update_env_var "BOT_TOKEN" "$token"
            echo "✅ BOT_TOKEN обновлен!"
        fi
        ;;
    server-ip)
        echo -n "Введите IP адрес сервера: "
        read server_ip
        if [ ! -z "$server_ip" ]; then
            update_env_var "OPENVPN_SERVER_IP" "$server_ip"
            update_env_var "WIREGUARD_SERVER_ENDPOINT" "$server_ip"
            echo "✅ IP адрес сервера обновлен!"
        fi
        ;;
    payment-wallet)
        echo -n "Введите адрес кошелька для оплаты: "
        read wallet
        if [ ! -z "$wallet" ]; then
            update_env_var "PAYMENT_WALLET" "$wallet"
            echo "✅ Кошелек для оплаты обновлен!"
        fi
        ;;
    database)
        echo -n "Введите DATABASE_URL (postgresql://user:pass@host:port/db): "
        read db_url
        if [ ! -z "$db_url" ]; then
            update_env_var "DATABASE_URL" "$db_url"
            echo "✅ URL базы данных обновлен!"
        fi
        ;;
    show)
        echo "📋 Текущие настройки (без секретных данных):"
        echo "=============================================="
        if [ -f "$ENV_FILE" ]; then
            grep -E "^[A-Z_]+=.*" "$ENV_FILE" | while read line; do
                var_name=$(echo "$line" | cut -d'=' -f1)
                if [[ "$var_name" == *"TOKEN"* ]] || [[ "$var_name" == *"KEY"* ]] || [[ "$var_name" == *"WALLET"* ]]; then
                    echo "$var_name=***"
                else
                    echo "$line"
                fi
            done
        else
            echo "❌ Файл .env не найден!"
        fi
        ;;
    validate)
        echo "🔍 Проверка конфигурации..."
        echo "============================"
        
        # Проверяем обязательные переменные
        required_vars=("BOT_TOKEN")
        all_good=true
        
        for var in "${required_vars[@]}"; do
            value=$(grep "^${var}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2-)
            if [ -z "$value" ] || [ "$value" = "your_bot_token_here" ]; then
                echo "❌ $var не настроен!"
                all_good=false
            else
                echo "✅ $var настроен"
            fi
        done
        
        if [ "$all_good" = true ]; then
            echo ""
            echo "✅ Конфигурация готова для запуска бота!"
            echo "Используйте: ./manage_vpn_bot.sh start"
        else
            echo ""
            echo "❌ Необходимо настроить обязательные переменные!"
        fi
        ;;
    *)
        echo "Использование: $0 {bot-token|server-ip|payment-wallet|database|show|validate}"
        echo ""
        echo "Команды:"
        echo "  bot-token      - Настроить токен Telegram бота"
        echo "  server-ip      - Настроить IP адрес сервера"
        echo "  payment-wallet - Настроить кошелек для оплаты"
        echo "  database       - Настроить подключение к базе данных"
        echo "  show           - Показать текущие настройки"
        echo "  validate       - Проверить корректность настроек"
        echo ""
        echo "Пример:"
        echo "  $0 bot-token    # Настроить токен бота"
        echo "  $0 validate     # Проверить настройки"
        exit 1
        ;;
esac