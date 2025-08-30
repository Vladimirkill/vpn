#!/bin/bash

# 🚀 Скрипт накатывания DEV версии на PROD
# Автор: VPN Bot Team
# Версия: 1.0

set -e  # Остановка при любой ошибке

echo "🚀 Начинаем накатывание DEV версии на PROD..."
echo "=================================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка текущей директории
if [ ! -d "dev" ] || [ ! -d "prod" ]; then
    print_error "Скрипт должен запускаться из /var/www/vpn/"
    exit 1
fi

print_status "Текущая директория: $(pwd)"

# Проверка что мы в правильной папке
if [ "$(basename $(pwd))" != "vpn" ]; then
    print_error "Скрипт должен запускаться из папки vpn"
    exit 1
fi

# Функция подтверждения
confirm() {
    read -p "$(echo -e ${YELLOW}$1${NC}) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Операция отменена пользователем"
        exit 1
    fi
}

# Проверка статуса сервисов
check_services() {
    print_status "Проверяем статус сервисов..."
    
    # Проверяем prod бота
    if systemctl is-active --quiet vpn-bot-prod 2>/dev/null; then
        print_warning "PROD бот запущен и будет остановлен"
        PROD_WAS_RUNNING=true
    else
        print_status "PROD бот не запущен"
        PROD_WAS_RUNNING=false
    fi
    
    # Проверяем dev бота
    if systemctl is-active --quiet vpn-bot-dev 2>/dev/null; then
        print_status "DEV бот запущен"
    else
        print_status "DEV бот не запущен"
    fi
}

# Создание бэкапа
create_backup() {
    print_status "Создаем бэкап PROD версии..."
    
    BACKUP_DIR="/var/www/vpn/backups"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_PATH="$BACKUP_DIR/prod_backup_$TIMESTAMP"
    
    mkdir -p "$BACKUP_DIR"
    
    # Копируем prod в бэкап
    cp -r prod "$BACKUP_PATH"
    
    print_success "Бэкап создан: $BACKUP_PATH"
    
    # Оставляем только последние 5 бэкапов
    print_status "Очищаем старые бэкапы (оставляем последние 5)..."
    ls -t "$BACKUP_DIR"/prod_backup_* 2>/dev/null | tail -n +6 | xargs -r rm -rf
}

# Остановка PROD сервиса
stop_prod_service() {
    if [ "$PROD_WAS_RUNNING" = true ]; then
        print_status "Останавливаем PROD бот..."
        systemctl stop vpn-bot-prod || true
        sleep 2
        print_success "PROD бот остановлен"
    fi
}

# Синхронизация файлов
sync_files() {
    print_status "Синхронизируем файлы из DEV в PROD..."
    
    # Исключаем файлы которые не должны копироваться
    EXCLUDE_LIST=(
        "--exclude=.env"
        "--exclude=*.db"
        "--exclude=logs/"
        "--exclude=__pycache__/"
        "--exclude=*.pyc"
        "--exclude=ENV_CONFIG.md"
        "--exclude=start_*.sh"
    )
    
    # Синхронизируем с исключениями
    rsync -av "${EXCLUDE_LIST[@]}" dev/ prod/
    
    print_success "Файлы синхронизированы"
}

# Обновление конфигурации PROD
update_prod_config() {
    print_status "Обновляем конфигурацию PROD..."
    
    # Убеждаемся что в prod/vpn_bot/config.py установлено production по умолчанию
    sed -i 's/ENVIRONMENT = os.getenv("ENVIRONMENT", "development")/ENVIRONMENT = os.getenv("ENVIRONMENT", "production")/g' prod/vpn_bot/config.py
    
    print_success "Конфигурация PROD обновлена"
}

# Проверка целостности
verify_deployment() {
    print_status "Проверяем целостность развертывания..."
    
    # Проверяем что основные файлы на месте
    REQUIRED_FILES=(
        "prod/vpn_bot/bot.py"
        "prod/vpn_bot/config.py"
        "prod/start_prod.sh"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "Отсутствует файл: $file"
            exit 1
        fi
    done
    
    # Проверяем синтаксис Python
    print_status "Проверяем синтаксис Python файлов..."
    cd prod
    python3 -m py_compile vpn_bot/bot.py
    python3 -m py_compile vpn_bot/config.py
    cd ..
    
    print_success "Проверка целостности пройдена"
}

# Запуск PROD сервиса
start_prod_service() {
    if [ "$PROD_WAS_RUNNING" = true ]; then
        print_status "Запускаем PROD бот..."
        systemctl start vpn-bot-prod
        sleep 3
        
        # Проверяем что сервис запустился
        if systemctl is-active --quiet vpn-bot-prod; then
            print_success "PROD бот успешно запущен"
        else
            print_error "Не удалось запустить PROD бот"
            print_status "Проверьте логи: journalctl -u vpn-bot-prod -f"
            exit 1
        fi
    else
        print_status "PROD бот не был запущен, оставляем остановленным"
    fi
}

# Показать статус развертывания
show_deployment_status() {
    print_status "Статус развертывания:"
    echo "================================"
    
    # Показываем статус сервисов
    echo "🔧 DEV бот:  $(systemctl is-active vpn-bot-dev 2>/dev/null || echo 'не настроен')"
    echo "🏭 PROD бот: $(systemctl is-active vpn-bot-prod 2>/dev/null || echo 'не настроен')"
    
    # Показываем размеры папок
    echo ""
    echo "📁 Размеры папок:"
    du -sh dev prod 2>/dev/null || echo "Не удалось получить размеры"
    
    # Показываем последние бэкапы
    echo ""
    echo "💾 Последние бэкапы:"
    ls -lt /var/www/vpn/backups/prod_backup_* 2>/dev/null | head -3 || echo "Бэкапы не найдены"
}

# Функция отката
rollback() {
    print_warning "Выполняем откат к предыдущей версии..."
    
    LATEST_BACKUP=$(ls -t /var/www/vpn/backups/prod_backup_* 2>/dev/null | head -1)
    
    if [ -z "$LATEST_BACKUP" ]; then
        print_error "Бэкап для отката не найден!"
        exit 1
    fi
    
    print_status "Откатываемся к: $LATEST_BACKUP"
    
    # Останавливаем сервис
    systemctl stop vpn-bot-prod 2>/dev/null || true
    
    # Удаляем текущий prod
    rm -rf prod
    
    # Восстанавливаем из бэкапа
    cp -r "$LATEST_BACKUP" prod
    
    # Запускаем сервис если он был запущен
    if [ "$PROD_WAS_RUNNING" = true ]; then
        systemctl start vpn-bot-prod
    fi
    
    print_success "Откат выполнен успешно"
}

# Основная функция
main() {
    print_status "🚀 Скрипт накатывания DEV → PROD"
    echo "Дата: $(date)"
    echo "Пользователь: $(whoami)"
    echo ""
    
    # Проверяем права root
    if [ "$EUID" -ne 0 ]; then
        print_error "Скрипт должен запускаться от root"
        exit 1
    fi
    
    # Проверяем параметры командной строки
    case "${1:-}" in
        --rollback)
            check_services
            rollback
            exit 0
            ;;
        --status)
            show_deployment_status
            exit 0
            ;;
        --help|-h)
            echo "Использование: $0 [опции]"
            echo ""
            echo "Опции:"
            echo "  (без параметров)  Накатить DEV на PROD"
            echo "  --rollback        Откатиться к предыдущей версии"
            echo "  --status          Показать статус развертывания"
            echo "  --help, -h        Показать эту справку"
            exit 0
            ;;
    esac
    
    # Основной процесс развертывания
    confirm "🚀 Накатить DEV версию на PROD?"
    
    check_services
    create_backup
    stop_prod_service
    sync_files
    update_prod_config
    verify_deployment
    start_prod_service
    
    echo ""
    print_success "🎉 Накатывание DEV → PROD завершено успешно!"
    echo ""
    show_deployment_status
    
    echo ""
    print_status "📋 Полезные команды:"
    echo "  Логи PROD:     journalctl -u vpn-bot-prod -f"
    echo "  Статус:        systemctl status vpn-bot-prod"
    echo "  Откат:         $0 --rollback"
    echo "  Статус:        $0 --status"
}

# Обработка сигналов для корректного завершения
trap 'print_error "Скрипт прерван пользователем"; exit 1' INT TERM

# Запуск основной функции
main "$@"