# 🤖 VPN Bot - Настройка SystemD сервиса

## ✅ Установка завершена!

SystemD сервис для VPN Bot успешно создан и настроен.

## 📁 Созданные файлы:

- `/etc/systemd/system/vpn-bot.service` - Файл сервиса SystemD
- `/var/www/vpn/manage_vpn_bot.sh` - Скрипт управления сервисом
- `/var/www/vpn/setup_env.sh` - Скрипт настройки переменных окружения
- `/var/www/vpn/activate_venv.sh` - Скрипт активации виртуального окружения

## 🚀 Быстрый старт:

### 1. Настройте переменные окружения:
```bash
cd /var/www/vpn
./setup_env.sh bot-token    # Настроить токен Telegram бота
./setup_env.sh validate     # Проверить настройки
```

### 2. Запустите сервис:
```bash
./manage_vpn_bot.sh start   # Запустить бота
./manage_vpn_bot.sh status  # Проверить статус
```

## 📋 Управление сервисом:

### Основные команды:
```bash
# Управление сервисом
./manage_vpn_bot.sh start      # Запустить
./manage_vpn_bot.sh stop       # Остановить  
./manage_vpn_bot.sh restart    # Перезапустить
./manage_vpn_bot.sh status     # Статус

# Логи
./manage_vpn_bot.sh logs       # Логи в реальном времени
./manage_vpn_bot.sh logs-tail  # Последние 50 строк

# Автозапуск
./manage_vpn_bot.sh enable     # Включить автозапуск
./manage_vpn_bot.sh disable    # Отключить автозапуск

# Диагностика
./manage_vpn_bot.sh check-config  # Проверить конфигурацию
```

### Настройка переменных окружения:
```bash
# Настройка основных параметров
./setup_env.sh bot-token       # Токен Telegram бота
./setup_env.sh server-ip       # IP адрес сервера
./setup_env.sh payment-wallet  # Кошелек для оплаты
./setup_env.sh database        # База данных

# Просмотр и проверка
./setup_env.sh show           # Показать настройки
./setup_env.sh validate       # Проверить корректность
```

## 🔧 SystemD команды (альтернативный способ):

```bash
# Прямое управление через systemctl
systemctl start vpn-bot      # Запустить
systemctl stop vpn-bot       # Остановить
systemctl restart vpn-bot    # Перезапустить
systemctl status vpn-bot     # Статус
systemctl enable vpn-bot     # Автозапуск
systemctl disable vpn-bot    # Отключить автозапуск

# Логи
journalctl -u vpn-bot -f     # Логи в реальном времени
journalctl -u vpn-bot -n 50  # Последние 50 строк
```

## 📊 Статус сервиса:

- ✅ **Сервис создан**: `/etc/systemd/system/vpn-bot.service`
- ✅ **Автозапуск включен**: Сервис будет запускаться при загрузке системы
- ✅ **Виртуальное окружение**: `/var/www/vpn/venv`
- ⚠️ **Требует настройки**: BOT_TOKEN в файле `.env`

## 🔍 Диагностика проблем:

### Если сервис не запускается:
1. Проверьте логи: `./manage_vpn_bot.sh logs-tail`
2. Проверьте конфигурацию: `./setup_env.sh validate`
3. Убедитесь что BOT_TOKEN настроен
4. Проверьте права доступа к файлам

### Проверка файлов:
```bash
# Проверка основных файлов
ls -la /var/www/vpn/venv/          # Виртуальное окружение
ls -la /var/www/vpn/vpn_bot/.env   # Переменные окружения
ls -la /etc/systemd/system/vpn-bot.service  # Файл сервиса
```

## 📝 Примечания:

- Сервис работает от пользователя `root`
- Логи сохраняются в systemd journal
- Автоматический перезапуск при сбоях включен
- Рабочая директория: `/var/www/vpn`
- Python путь: `/var/www/vpn/venv/bin/python`

## 🎯 Следующие шаги:

1. **Настройте BOT_TOKEN**: `./setup_env.sh bot-token`
2. **Проверьте настройки**: `./setup_env.sh validate`
3. **Запустите бота**: `./manage_vpn_bot.sh start`
4. **Проверьте логи**: `./manage_vpn_bot.sh logs-tail`

---
*Создано автоматически при настройке SystemD сервиса*