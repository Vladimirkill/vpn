# 🚀 VPN Project - Dev/Prod Environment

## 📁 **Структура проекта:**

```
/var/www/vpn/
├── dev/          # 🔧 Development версия
├── prod/         # 🏭 Production версия
└── README.md     # 📖 Этот файл
```

## 🔧 **DEV Environment**

### **Особенности DEV версии:**
- 🌐 **Порт Xray**: `11443` (вместо 10443)
- 📊 **База данных**: `vpn_db_dev` (PostgreSQL)
- 🔍 **Логирование**: DEBUG уровень
- 🧪 **Тестовые порты**: OpenVPN 1195, WireGuard 51821
- 🔗 **Подсеть**: 10.1.0.0/24

### **Запуск DEV версии:**
```bash
cd /var/www/vpn/dev
./start_dev.sh
```

## 🏭 **PROD Environment**

### **Особенности PROD версии:**
- 🌐 **Порт Xray**: `10443` (рабочий)
- 📊 **База данных**: `vpn_db` (PostgreSQL)
- 📝 **Логирование**: INFO уровень
- 🚀 **Рабочие порты**: OpenVPN 1194, WireGuard 51820
- 🔗 **Подсеть**: 10.0.0.0/24

### **Запуск PROD версии:**
```bash
cd /var/www/vpn/prod
./start_prod.sh
```

## ⚙️ **Конфигурация**

### **Переменные окружения:**
- `ENVIRONMENT=development` - для DEV
- `ENVIRONMENT=production` - для PROD

### **Файлы конфигурации:**
- `vpn_bot/config.py` - автоматически определяет окружение
- `vpn_bot/.env` - переменные окружения (одинаковые для обеих версий)

## 🔄 **Переключение между версиями**

1. **Остановить текущую версию**:
   ```bash
   pkill -f "python vpn_bot/bot.py"
   ```

2. **Запустить нужную версию**:
   ```bash
   # DEV версия
   cd /var/www/vpn/dev && ./start_dev.sh
   
   # PROD версия  
   cd /var/www/vpn/prod && ./start_prod.sh
   ```

## 📋 **Системные сервисы**

### **Создание systemd сервисов:**

**DEV сервис:**
```bash
sudo tee /etc/systemd/system/vpn-bot-dev.service > /dev/null << 'EOF'
[Unit]
Description=VPN Bot DEV
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/vpn/dev
ExecStart=/var/www/vpn/dev/start_dev.sh
Restart=always
Environment=ENVIRONMENT=development

[Install]
WantedBy=multi-user.target
EOF
```

**PROD сервис:**
```bash
sudo tee /etc/systemd/system/vpn-bot-prod.service > /dev/null << 'EOF'
[Unit]
Description=VPN Bot PROD
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/vpn/prod
ExecStart=/var/www/vpn/prod/start_prod.sh
Restart=always
Environment=ENVIRONMENT=production

[Install]
WantedBy=multi-user.target
EOF
```

### **Управление сервисами:**
```bash
# Перезагрузить systemd
sudo systemctl daemon-reload

# Запустить DEV версию
sudo systemctl start vpn-bot-dev
sudo systemctl enable vpn-bot-dev

# Запустить PROD версию
sudo systemctl start vpn-bot-prod
sudo systemctl enable vpn-bot-prod

# Проверить статус
sudo systemctl status vpn-bot-dev
sudo systemctl status vpn-bot-prod
```

## ⚠️ **Важные замечания**

1. **Не запускайте обе версии одновременно** - они могут конфликтовать
2. **DEV и PROD используют разные порты** и базы данных
3. **Файл .env должен быть в каждой версии** (vpn_bot/.env)
4. **Виртуальные окружения независимы** для каждой версии

## 🔍 **Мониторинг**

### **Логи:**
```bash
# DEV логи
tail -f /var/www/vpn/dev/logs/*

# PROD логи  
tail -f /var/www/vpn/prod/logs/*

# Systemd логи
journalctl -u vpn-bot-dev -f
journalctl -u vpn-bot-prod -f
```

## 🚀 **Развертывание (Deploy)**

### **📋 Скрипты развертывания:**

1. **🔍 Сравнение версий** (перед развертыванием):
   ```bash
   ./compare_versions.sh
   ```

2. **🚀 Интерактивное развертывание** DEV → PROD:
   ```bash
   ./deploy_dev_to_prod.sh
   ```

3. **⚡ Быстрое развертывание** (без подтверждений):
   ```bash
   ./quick_deploy.sh
   ```

4. **🔄 Откат к предыдущей версии**:
   ```bash
   ./deploy_dev_to_prod.sh --rollback
   ```

5. **📊 Статус развертывания**:
   ```bash
   ./deploy_dev_to_prod.sh --status
   ```

### **🛡️ Безопасность развертывания:**

- ✅ **Автоматический бэкап** PROD версии перед развертыванием
- ✅ **Проверка синтаксиса** Python файлов
- ✅ **Сохранение конфигураций** (.env, базы данных)
- ✅ **Откат в один клик** при проблемах
- ✅ **Логирование всех операций**

### **📁 Что НЕ копируется при развертывании:**
- `.env` файлы (остаются уникальными для каждой версии)
- Базы данных (каждая версия использует свою БД)
- Логи (`logs/`)
- Кэш Python (`__pycache__/`, `*.pyc`)
- Скрипты запуска (`start_*.sh`)

### **🔗 Общие ресурсы:**
- **Виртуальное окружение** (`venv/`) - общее для dev и prod
- **Скрипты развертывания** - в корневой папке
- **Документация** - в корневой папке

## 🎯 **Быстрый старт**

1. **Скопируйте .env файл в обе версии:**
   ```bash
   cp /path/to/.env /var/www/vpn/dev/vpn_bot/
   cp /path/to/.env /var/www/vpn/prod/vpn_bot/
   ```

2. **Инициализируйте DEV базу данных:**
   ```bash
   ./init_dev_db.sh
   ```

3. **Запустите нужную версию:**
   ```bash
   # Для разработки
   cd /var/www/vpn/dev && ./start_dev.sh
   
   # Для продакшена
   cd /var/www/vpn/prod && ./start_prod.sh
   ```

4. **Разрабатывайте в DEV и накатывайте на PROD:**
   ```bash
   # Сравните изменения
   ./compare_versions.sh
   
   # Накатите изменения
   ./deploy_dev_to_prod.sh
   ```

✅ **Готово! Теперь у вас есть полноценные dev и prod версии с системой развертывания.**