# 🔧 DEV Environment Configuration

## 📋 **Настройки DEV окружения:**

### **🌐 Порты:**
- **Xray**: 11443 (вместо 10443)
- **Bot**: 8081 (вместо стандартного)
- **Admin Panel**: 5001 (вместо 5000)
- **Nginx Stream**: 8443 (для dev тестирования)

### **📁 Пути:**
- **База данных**: `dev_vpn.db`
- **Логи**: `logs/dev_*`
- **Конфиги**: `configs/dev_*`

### **🔑 Переменные окружения:**
- `ENVIRONMENT=development`
- `DEBUG=true`
- `LOG_LEVEL=DEBUG`

### **🚀 Запуск DEV версии:**
```bash
cd /var/www/vpn/dev
source venv/bin/activate
export ENVIRONMENT=development
python vpn_bot/bot.py
```

### **⚠️ Важно:**
- DEV версия использует отдельные порты
- Отдельная база данных
- Расширенное логирование
- Тестовые конфигурации