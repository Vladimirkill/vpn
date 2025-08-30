from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
import sys, os

# Добавляем корень проекта в sys.path, чтобы модуль `xray` был доступен
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from handler.vpn_handler import VPNHandler
from handler.ip_handler import setup_ip_handlers
from handler.rental_handler import setup_rental_handlers
from utils.masking_manager import start_integrated_masking
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def post_init(application):
    """Инициализация после запуска бота"""
    print("🎭 Инициализация интегрированной маскировки...")
    await start_integrated_masking()
    print("✅ Маскировка VPN активирована")

def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Создаем обработчик
    vpn_handler = VPNHandler()
    
    # Добавляем команды
    app.add_handler(CommandHandler("start", vpn_handler.start_command))
    app.add_handler(CommandHandler("help", vpn_handler.help_command))
    app.add_handler(CommandHandler("xray", vpn_handler.xray_command))
    app.add_handler(CommandHandler("mykeys", vpn_handler.my_keys_command))
    app.add_handler(CommandHandler("create", vpn_handler.create_new_key_command))
    
    # Добавляем обработчик callback query для кнопок
    app.add_handler(CallbackQueryHandler(vpn_handler.button_callback))
    
    # Настраиваем обработчики IP
    setup_ip_handlers(app)
    
    # Настраиваем обработчики аренды IP
    setup_rental_handlers(app)
    
    # Обработчик текстовых сообщений (ручной ввод домена)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, vpn_handler.handle_text_message))
    
    print("🚀 VPN Bot запущен!")
    print("📊 Доступные команды:")
    print("   • /start - главное меню")
    print("   • /xray <имя> - создать VLESS ключ")
    print("   • /mykeys <имя> - показать ключи")
    print("   • /help - справка")
    print("   • Кнопки теперь работают!")
    
    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()