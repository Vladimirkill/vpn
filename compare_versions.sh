#!/bin/bash

# 🔍 Скрипт сравнения DEV и PROD версий
# Показывает различия между версиями перед развертыванием

echo "🔍 Сравнение DEV и PROD версий"
echo "==============================="

# Проверяем что мы в правильной директории
if [ ! -d "dev" ] || [ ! -d "prod" ]; then
    echo "❌ Ошибка: Скрипт должен запускаться из /var/www/vpn/"
    exit 1
fi

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_diff() {
    echo -e "${YELLOW}$1${NC}"
}

# Функция для сравнения файлов
compare_files() {
    local file="$1"
    
    if [ ! -f "dev/$file" ] && [ ! -f "prod/$file" ]; then
        return 0
    elif [ ! -f "dev/$file" ]; then
        echo -e "${RED}[-]${NC} $file (только в PROD)"
    elif [ ! -f "prod/$file" ]; then
        echo -e "${GREEN}[+]${NC} $file (только в DEV)"
    elif ! diff -q "dev/$file" "prod/$file" >/dev/null 2>&1; then
        echo -e "${YELLOW}[M]${NC} $file (изменен)"
        
        # Показываем краткую статистику изменений
        local added=$(diff "prod/$file" "dev/$file" | grep "^>" | wc -l)
        local removed=$(diff "prod/$file" "dev/$file" | grep "^<" | wc -l)
        echo "     +$added строк, -$removed строк"
    fi
}

print_section "📊 Общая статистика"

# Подсчитываем файлы
DEV_FILES=$(find dev -type f | wc -l)
PROD_FILES=$(find prod -type f | wc -l)

echo "📁 Файлов в DEV:  $DEV_FILES"
echo "📁 Файлов в PROD: $PROD_FILES"

# Размеры папок
echo "💾 Размер DEV:  $(du -sh dev | cut -f1)"
echo "💾 Размер PROD: $(du -sh prod | cut -f1)"

print_section "🔍 Основные файлы проекта"

# Список важных файлов для сравнения
IMPORTANT_FILES=(
    "vpn_bot/bot.py"
    "vpn_bot/config.py"
    "vpn_bot/handler/admin_handler.py"
    "vpn_bot/handler/vpn_handler.py"
    "vpn_bot/handler/rental_handler.py"
    "vpn_bot/utils/masking_manager.py"
    "vpn_bot/utils/vds_ip_manager.py"
    "xray/generate_client.py"
    "manage_user_limits.py"
    "requirements.txt"
)

for file in "${IMPORTANT_FILES[@]}"; do
    compare_files "$file"
done

print_section "🐍 Python файлы с изменениями"

# Находим все измененные Python файлы
find dev -name "*.py" -type f | while read dev_file; do
    prod_file="${dev_file/dev\//prod/}"
    if [ -f "$prod_file" ]; then
        if ! diff -q "$dev_file" "$prod_file" >/dev/null 2>&1; then
            rel_path="${dev_file#dev/}"
            echo -e "${YELLOW}[M]${NC} $rel_path"
        fi
    else
        rel_path="${dev_file#dev/}"
        echo -e "${GREEN}[+]${NC} $rel_path (новый файл)"
    fi
done

print_section "📝 Конфигурационные файлы"

CONFIG_FILES=(
    "vpn_bot/.env"
    "xray/config.json"
    "configs/nginx.conf"
)

for file in "${CONFIG_FILES[@]}"; do
    if [ -f "dev/$file" ] || [ -f "prod/$file" ]; then
        compare_files "$file"
    fi
done

print_section "🔧 Детальные изменения в ключевых файлах"

# Показываем детальные изменения для критически важных файлов
CRITICAL_FILES=(
    "vpn_bot/bot.py"
    "vpn_bot/config.py"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "dev/$file" ] && [ -f "prod/$file" ]; then
        if ! diff -q "dev/$file" "prod/$file" >/dev/null 2>&1; then
            echo -e "\n${YELLOW}📄 Изменения в $file:${NC}"
            diff -u "prod/$file" "dev/$file" | head -20
            
            local total_lines=$(diff -u "prod/$file" "dev/$file" | wc -l)
            if [ $total_lines -gt 20 ]; then
                echo "... (показаны первые 20 строк из $total_lines)"
            fi
        fi
    fi
done

print_section "⚠️  Потенциальные проблемы"

# Проверяем потенциальные проблемы
ISSUES_FOUND=false

# Проверяем наличие .env файлов
if [ ! -f "dev/vpn_bot/.env" ]; then
    echo -e "${RED}⚠️${NC}  Отсутствует dev/vpn_bot/.env"
    ISSUES_FOUND=true
fi

if [ ! -f "prod/vpn_bot/.env" ]; then
    echo -e "${RED}⚠️${NC}  Отсутствует prod/vpn_bot/.env"
    ISSUES_FOUND=true
fi

# Проверяем синтаксис Python файлов в DEV
echo "🔍 Проверяем синтаксис Python файлов в DEV..."
cd dev
if ! python3 -m py_compile vpn_bot/bot.py 2>/dev/null; then
    echo -e "${RED}⚠️${NC}  Ошибка синтаксиса в dev/vpn_bot/bot.py"
    ISSUES_FOUND=true
fi

if ! python3 -m py_compile vpn_bot/config.py 2>/dev/null; then
    echo -e "${RED}⚠️${NC}  Ошибка синтаксиса в dev/vpn_bot/config.py"
    ISSUES_FOUND=true
fi
cd ..

if [ "$ISSUES_FOUND" = false ]; then
    echo -e "${GREEN}✅ Проблем не обнаружено${NC}"
fi

print_section "📋 Рекомендации"

echo "1. 📊 Проверьте изменения в критически важных файлах"
echo "2. 🧪 Протестируйте DEV версию перед развертыванием"
echo "3. 💾 Убедитесь что создан бэкап PROD версии"
echo "4. 🔄 Используйте ./deploy_dev_to_prod.sh для безопасного развертывания"

print_section "🚀 Команды для развертывания"

echo "Интерактивное развертывание:"
echo "  ./deploy_dev_to_prod.sh"
echo ""
echo "Быстрое развертывание:"
echo "  ./quick_deploy.sh"
echo ""
echo "Откат к предыдущей версии:"
echo "  ./deploy_dev_to_prod.sh --rollback"