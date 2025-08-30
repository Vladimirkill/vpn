# 🏭 PROD Environment Configuration

## 📋 **Настройки PROD окружения:**

### **🌐 Порты:**
- **Xray**: 10443 (текущий рабочий)
- **Bot**: стандартный
- **Admin Panel**: 5000
- **Nginx Stream**: 443 (основной)

### **📁 Пути:**
- **База данных**: `vpn.db`
- **Логи**: `logs/prod_*`
- **Конфиги**: `configs/prod_*`

### **🔑 Переменные окружения:**
- `ENVIRONMENT=production`
- `DEBUG=false`
- `LOG_LEVEL=INFO`

### **🚀 Запуск PROD версии:**
```bash
cd /var/www/vpn/prod
source venv/bin/activate
export ENVIRONMENT=production
python vpn_bot/bot.py
```

### **⚠️ Важно:**
- PROD версия использует рабочие порты
- Основная база данных
- Минимальное логирование
- Боевые конфигурации