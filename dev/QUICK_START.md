# 🚀 Быстрый запуск системы мониторинга Xray

## ⚡ Установка за 3 шага

### 1. Запуск установки
```bash
sudo ./setup_xray_monitor.sh
```

### 2. Проверка статуса
```bash
xray-monitor status
```

### 3. Тестирование
```bash
python3 test_xray_monitor.py diagnostic
```

## 🔧 Основные команды

```bash
# Управление мониторингом
xray-monitor start      # Запуск
xray-monitor stop       # Остановка
xray-monitor restart    # Перезапуск
xray-monitor status     # Статус
xray-monitor logs       # Логи systemd
xray-monitor log-file   # Лог файл

# Тестирование
python3 test_xray_monitor.py diagnostic  # Диагностика
python3 test_xray_monitor.py test        # Тест интеграции
python3 test_xray_monitor.py logs        # Просмотр логов
```

## 📊 Что происходит автоматически

✅ **Отслеживание изменений** в директории клиентов каждые 5 секунд  
✅ **Автоматическая пересборка** конфигурации при изменениях  
✅ **Безопасный перезапуск** Xray с защитой IP пользователей  
✅ **Fallback механизмы** при ошибках  
✅ **Подробное логирование** всех операций  

## 🧪 Тест работы

```bash
# Создать тестового клиента
python3 run_generate.py test_client

# Проверить логи мониторинга
xray-monitor log-file

# Проверить статус Xray
sudo systemctl status xray
```

## 📁 Созданные файлы

- `xray-monitor.service` - systemd сервис
- `xray/monitor_clients.py` - скрипт мониторинга
- `setup_xray_monitor.sh` - скрипт установки
- `test_xray_monitor.py` - скрипт тестирования
- `/usr/local/bin/xray-monitor` - команда управления
- `/var/log/xray-monitor.log` - лог файл

## 🚨 Если что-то не работает

```bash
# Проверить статус
sudo systemctl status xray-monitor

# Проверить логи
sudo journalctl -u xray-monitor -f

# Перезапустить
sudo systemctl restart xray-monitor
```

## 💡 Интеграция с существующей системой

Система автоматически интегрируется с:
- `run_generate.py` - создание клиентов
- `vpn_bot` - Telegram бот
- `safe_restart.py` - безопасный перезапуск
- `build_config.py` - сборка конфигурации

**Готово! Теперь Xray будет автоматически перезапускаться при появлении новых клиентов.** 🎉 