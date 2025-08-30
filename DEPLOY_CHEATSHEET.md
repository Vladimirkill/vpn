# 🚀 Шпаргалка по развертыванию VPN проекта

## 📋 **Основные команды**

### **🔍 Перед развертыванием:**
```bash
# Сравнить DEV и PROD версии
./compare_versions.sh

# Проверить статус сервисов
./deploy_dev_to_prod.sh --status
```

### **🚀 Развертывание:**
```bash
# Интерактивное развертывание (с подтверждениями)
./deploy_dev_to_prod.sh

# Быстрое развертывание (автоматическое)
./quick_deploy.sh
```

### **🔄 Откат и восстановление:**
```bash
# Откат к предыдущей версии
./deploy_dev_to_prod.sh --rollback

# Показать справку
./deploy_dev_to_prod.sh --help
```

## 🎯 **Типичный workflow**

1. **Разработка в DEV:**
   ```bash
   cd /var/www/vpn/dev
   ./start_dev.sh
   # ... разработка и тестирование ...
   ```

2. **Сравнение изменений:**
   ```bash
   cd /var/www/vpn
   ./compare_versions.sh
   ```

3. **Развертывание на PROD:**
   ```bash
   ./deploy_dev_to_prod.sh
   ```

4. **Проверка результата:**
   ```bash
   ./deploy_dev_to_prod.sh --status
   journalctl -u vpn-bot-prod -f
   ```

## ⚠️ **Важные моменты**

### **Что сохраняется при развертывании:**
- ✅ `.env` файлы (не копируются)
- ✅ Базы данных (не копируются)
- ✅ Логи (не копируются)
- ✅ Виртуальные окружения (не копируются)

### **Что копируется:**
- 📁 Весь код проекта
- 📁 Конфигурационные файлы
- 📁 Скрипты и утилиты
- 📁 Документация

### **Автоматические проверки:**
- 🔍 Синтаксис Python файлов
- 🔍 Наличие критически важных файлов
- 🔍 Статус сервисов
- 🔍 Права доступа

## 🛡️ **Безопасность**

### **Бэкапы:**
- Создаются автоматически перед каждым развертыванием
- Хранятся в `/var/www/vpn/backups/`
- Автоматическая очистка (оставляются последние 5)

### **Откат:**
- Мгновенный откат к предыдущей версии
- Автоматическое восстановление сервисов
- Сохранение всех данных

## 📊 **Мониторинг**

### **Логи сервисов:**
```bash
# PROD бот
journalctl -u vpn-bot-prod -f

# DEV бот
journalctl -u vpn-bot-dev -f
```

### **Статус сервисов:**
```bash
# Проверить статус
systemctl status vpn-bot-prod
systemctl status vpn-bot-dev

# Перезапустить
systemctl restart vpn-bot-prod
systemctl restart vpn-bot-dev
```

### **Размеры и статистика:**
```bash
# Размеры папок
du -sh dev prod

# Количество файлов
find dev -type f | wc -l
find prod -type f | wc -l

# Последние бэкапы
ls -lt /var/www/vpn/backups/
```

## 🚨 **Экстренные ситуации**

### **Если PROD сломался:**
```bash
# Быстрый откат
./deploy_dev_to_prod.sh --rollback

# Или ручное восстановление
systemctl stop vpn-bot-prod
cp -r /var/www/vpn/backups/prod_backup_YYYYMMDD_HHMMSS prod
systemctl start vpn-bot-prod
```

### **Если нужно срочно остановить:**
```bash
# Остановить все боты
systemctl stop vpn-bot-prod vpn-bot-dev

# Или убить процессы
pkill -f "python vpn_bot/bot.py"
```

### **Проверка целостности:**
```bash
# Проверить синтаксис
cd /var/www/vpn/prod
python3 -m py_compile vpn_bot/bot.py
python3 -m py_compile vpn_bot/config.py

# Проверить конфигурации
ls -la vpn_bot/.env
ls -la *.db
```

## 📞 **Контакты и поддержка**

- 📖 Полная документация: `/var/www/vpn/README.md`
- 🔧 Конфигурации DEV: `/var/www/vpn/dev/ENV_CONFIG.md`
- 🏭 Конфигурации PROD: `/var/www/vpn/prod/ENV_CONFIG.md`
- 📊 Статус развертывания: `./deploy_dev_to_prod.sh --status`