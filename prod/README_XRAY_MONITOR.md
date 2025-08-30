# 🚀 Автоматический мониторинг и перезапуск Xray

Система автоматического мониторинга конфигурации Xray, которая отслеживает изменения в директории клиентов и автоматически перезапускает сервис при появлении новых клиентов.

## ✨ Возможности

- 🔍 **Автоматическое отслеживание** изменений в директории клиентов
- 🔄 **Автоматический перезапуск** Xray при появлении новых клиентов
- 🛡️ **Безопасный перезапуск** с защитой от утечки IP пользователей
- 📊 **Мониторинг состояния** сервиса
- 📝 **Подробное логирование** всех операций
- ⚡ **Быстрая реакция** на изменения (проверка каждые 5 секунд)

## 🏗️ Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │  Client Creation │    │  Xray Monitor   │
│                 │    │                  │    │                 │
│  /xray command  │───▶│  run_generate.py │───▶│ monitor_clients │
│                 │    │                  │    │      .py        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  build_config.py │    │ safe_restart.py │
                       │                  │    │                 │
                       │  Rebuild Config  │    │  Safe Restart   │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 Установка

### 1. Автоматическая установка (рекомендуется)

```bash
# Сделать скрипт исполняемым
chmod +x setup_xray_monitor.sh

# Запустить установку (требует root прав)
sudo ./setup_xray_monitor.sh
```

### 2. Ручная установка

```bash
# 1. Создать systemd сервис
sudo cp xray-monitor.service /etc/systemd/system/

# 2. Сделать скрипт мониторинга исполняемым
sudo chmod +x xray/monitor_clients.py

# 3. Перезагрузить systemd
sudo systemctl daemon-reload

# 4. Включить автозапуск
sudo systemctl enable xray-monitor

# 5. Запустить сервис
sudo systemctl start xray-monitor
```

## 📋 Управление

### Команды управления

```bash
# Статус мониторинга
xray-monitor status

# Просмотр логов systemd
xray-monitor logs

# Просмотр лог файла
xray-monitor log-file

# Перезапуск мониторинга
xray-monitor restart

# Остановка мониторинга
xray-monitor stop

# Запуск мониторинга
xray-monitor start
```

### Systemd команды

```bash
# Статус сервиса
sudo systemctl status xray-monitor

# Просмотр логов
sudo journalctl -u xray-monitor -f

# Перезапуск
sudo systemctl restart xray-monitor

# Остановка
sudo systemctl stop xray-monitor
```

## 🔧 Конфигурация

### Основные параметры

Файл: `xray/monitor_clients.py`

```python
class XrayClientMonitor:
    def __init__(self):
        self.clients_dir = "/var/www/project987/vpn/xray/clients"      # Директория клиентов
        self.config_file = "/var/www/project987/vpn/xray/final_config.json"  # Файл конфигурации
        self.safe_restart_script = "/var/www/project987/vpn/xray/safe_restart.py"  # Скрипт перезапуска
        self.build_script = "/var/www/project987/vpn/xray/build_config.py"  # Скрипт сборки
```

### Настройка интервалов

```python
# Интервал проверки изменений (в секундах)
time.sleep(5)  # Проверка каждые 5 секунд

# Timeout для операций
timeout=60     # 60 секунд для сборки конфигурации
timeout=120    # 120 секунд для безопасного перезапуска
```

## 📊 Мониторинг и логи

### Логи systemd

```bash
# Просмотр всех логов
sudo journalctl -u xray-monitor

# Просмотр логов за последний час
sudo journalctl -u xray-monitor --since "1 hour ago"

# Просмотр логов в реальном времени
sudo journalctl -u xray-monitor -f
```

### Лог файл

```bash
# Просмотр лог файла
tail -f /var/log/xray-monitor.log

# Поиск ошибок
grep "ERROR" /var/log/xray-monitor.log

# Поиск успешных операций
grep "SUCCESS" /var/log/xray-monitor.log
```

### Примеры логов

```
[2024-01-15 10:30:15] - INFO - 🚀 Xray Client Monitor запущен
[2024-01-15 10:30:15] - INFO - 📁 Мониторинг директории: /var/www/project987/vpn/xray/clients
[2024-01-15 10:30:15] - INFO - 📊 Найдено 25 клиентов
[2024-01-15 10:35:20] - INFO - 🆕 Новый клиент обнаружен: test_client.json
[2024-01-15 10:35:20] - INFO - 🔄 Обнаружены изменения в конфигурации клиентов
[2024-01-15 10:35:20] - INFO - 🔧 Пересборка конфигурации Xray...
[2024-01-15 10:35:22] - INFO - ✅ Конфигурация успешно пересобрана
[2024-01-15 10:35:22] - INFO - 🔄 Безопасный перезапуск Xray...
[2024-01-15 10:35:45] - INFO - ✅ Xray успешно перезапущен
[2024-01-15 10:35:45] - INFO - 🎉 Обработка изменений завершена успешно
```

## 🧪 Тестирование

### 1. Создание тестового клиента

```bash
# Создать тестового клиента
python3 run_generate.py test_client

# Проверить логи мониторинга
xray-monitor log-file
```

### 2. Проверка автоматического перезапуска

```bash
# Создать клиента через бота
# Или вручную добавить файл в xray/clients/

# Проверить статус Xray
sudo systemctl status xray

# Проверить логи мониторинга
tail -f /var/log/xray-monitor.log
```

### 3. Проверка fallback механизмов

```bash
# Остановить safe_restart.py
sudo mv xray/safe_restart.py xray/safe_restart.py.bak

# Создать клиента
python3 run_generate.py test_client2

# Проверить что использовался fallback
grep "fallback" /var/log/xray-monitor.log
```

## 🚨 Устранение неполадок

### Проблема: Мониторинг не запускается

```bash
# Проверить статус
sudo systemctl status xray-monitor

# Проверить логи
sudo journalctl -u xray-monitor -n 50

# Проверить права доступа
ls -la xray/monitor_clients.py
```

### Проблема: Xray не перезапускается

```bash
# Проверить статус Xray
sudo systemctl status xray

# Проверить права на safe_restart.py
ls -la xray/safe_restart.py

# Проверить логи мониторинга
tail -f /var/log/xray-monitor.log
```

### Проблема: Множественные перезапуски

```bash
# Проверить флаг restart_in_progress
grep "restart_in_progress" /var/log/xray-monitor.log

# Проверить cron задачу
cat /etc/cron.d/xray-monitor-check
```

## 🔒 Безопасность

### Защита от утечки IP

- ✅ Использование `safe_restart.py` для безопасного перезапуска
- ✅ Блокировка исходящих соединений во время перезапуска
- ✅ Fallback механизмы при ошибках

### Права доступа

- ✅ Запуск от root для доступа к systemctl
- ✅ Ограниченные права на файлы логов
- ✅ Безопасное выполнение команд

## 📈 Производительность

### Оптимизация

- ⚡ Проверка изменений каждые 5 секунд
- 🔍 Использование MD5 хешей для быстрого сравнения
- 🚫 Предотвращение множественных перезапусков
- 📊 Логирование только важных событий

### Мониторинг ресурсов

```bash
# Использование памяти
ps aux | grep monitor_clients

# Использование CPU
top -p $(pgrep -f monitor_clients)

# Использование диска
du -sh /var/log/xray-monitor.log*
```

## 🔄 Интеграция с существующей системой

### run_generate.py

Автоматически интегрируется с системой мониторинга:

```python
# Уведомляем мониторинг о новом клиенте (если запущен)
try:
    monitor_status = subprocess.run(["systemctl", "is-active", "xray-monitor"], 
                                  capture_output=True, text=True)
    if monitor_status.stdout.strip() == "active":
        print("📡 Мониторинг Xray активен - изменения будут отслежены автоматически")
except:
    pass
```

### Telegram Bot

Бот автоматически создает клиентов, которые отслеживаются мониторингом:

```python
# В vpn_handler.py
result = self.generator.generate_vpn('xray', client_name, generate_qr=True)
```

## 📝 Лицензия

Проект распространяется под лицензией MIT.

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи: `xray-monitor logs`
2. Проверьте статус: `xray-monitor status`
3. Проверьте systemd логи: `sudo journalctl -u xray-monitor`
4. Убедитесь в корректности конфигурации
5. Проверьте права доступа к файлам 