#!/bin/bash
# Генератор фонового веб-трафика для маскировки VPN
# Имитирует обычную активность пользователя

DOMAINS=(
    "www.google.com"
    "www.youtube.com" 
    "www.github.com"
    "www.stackoverflow.com"
    "www.wikipedia.org"
    "www.reddit.com"
    "news.ycombinator.com"
    "www.cloudflare.com"
)

USER_AGENTS=(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
)

generate_background_traffic() {
    while true; do
        # Случайная пауза между запросами (1-30 минут)
        sleep $((RANDOM % 1800 + 60))
        
        # Выбираем случайный домен и User-Agent
        domain=${DOMAINS[$RANDOM % ${#DOMAINS[@]}]}
        ua=${USER_AGENTS[$RANDOM % ${#USER_AGENTS[@]}]}
        
        # Делаем несколько запросов для имитации браузера
        for i in {1..3}; do
            curl -s -A "$ua" -H "Accept: text/html,application/xhtml+xml" \
                 -H "Accept-Language: en-US,en;q=0.9" \
                 -H "Cache-Control: no-cache" \
                 --connect-timeout 10 --max-time 30 \
                 "https://$domain/" > /dev/null 2>&1
            
            # Пауза между запросами в сессии
            sleep $((RANDOM % 5 + 1))
        done
        
        echo "$(date): Generated background traffic to $domain"
    done
}

# Запуск в фоне
if [ "$1" = "start" ]; then
    echo "Запуск генератора фонового трафика..."
    generate_background_traffic &
    echo $! > /var/run/traffic-mixer.pid
    echo "PID: $(cat /var/run/traffic-mixer.pid)"
elif [ "$1" = "stop" ]; then
    if [ -f /var/run/traffic-mixer.pid ]; then
        kill $(cat /var/run/traffic-mixer.pid) 2>/dev/null
        rm /var/run/traffic-mixer.pid
        echo "Генератор фонового трафика остановлен"
    fi
elif [ "$1" = "status" ]; then
    if [ -f /var/run/traffic-mixer.pid ] && kill -0 $(cat /var/run/traffic-mixer.pid) 2>/dev/null; then
        echo "Генератор работает (PID: $(cat /var/run/traffic-mixer.pid))"
    else
        echo "Генератор не запущен"
    fi
else
    echo "Использование: $0 {start|stop|status}"
fi
