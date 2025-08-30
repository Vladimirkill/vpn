#!/usr/bin/env python3
"""
Скрипт для автоматической очистки истекших арендованных IP
Запускается по cron каждый час
"""

import sys
import os
import logging
from datetime import datetime

# Добавляем путь к проекту
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from vpn_bot.utils.vds_ip_manager import VDSIPManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/www/vpn/logs/ip_cleanup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Основная функция очистки"""
    logger.info("🧹 Запуск очистки истекших IP")
    
    try:
        # Создаем директорию для логов
        os.makedirs('/var/www/vpn/logs', exist_ok=True)
        
        # Инициализируем менеджер IP
        vds_manager = VDSIPManager()
        
        # Проверяем и освобождаем истекшие IP
        vds_manager.check_expired_ips()
        
        logger.info("✅ Очистка истекших IP завершена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при очистке IP: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()