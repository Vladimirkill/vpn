#!/usr/bin/env python3
"""
Обработчик команд для управления IP-адресами в VPN боте
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from vpn_bot.utils.ip_manager import IPManager
from db.models import session, User, VpnKey

logger = logging.getLogger(__name__)

class IPHandler:
    def __init__(self):
        self.ip_manager = IPManager()
    
    async def show_ip_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню выбора IP"""
        user = update.effective_user
        
        # Проверяем есть ли у пользователя VPN ключ
        db_user = session.query(User).filter_by(tg_id=user.id).first()
        if not db_user:
            await update.message.reply_text("❌ Вы не зарегистрированы в системе")
            return
        
        vpn_key = session.query(VpnKey).filter_by(user_id=db_user.id).first()
        if not vpn_key:
            await update.message.reply_text("❌ У вас нет активного VPN ключа")
            return
        
        # Получаем доступные серверы
        servers = self.ip_manager.get_available_servers()
        current_server_id = self.ip_manager.get_user_ip(vpn_key.uuid)
        
        # Получаем текущий IP
        current_ip = self.ip_manager.get_current_ip()
        
        text = "🌍 **ВЫБОР IP-АДРЕСА**\\n\\n"
        text += f"🔍 Текущий IP сервера: `{current_ip or 'неизвестен'}`\\n\\n"
        
        # Находим текущий сервер
        current_server = next((s for s in servers if s['id'] == current_server_id), None)
        if current_server:
            text += f"✅ Активный выход: **{current_server['name']}**\\n"
            text += f"📝 {current_server['description']}\\n\\n"
        
        text += "Выберите IP для выхода в интернет:"
        
        # Создаем клавиатуру
        keyboard = []
        for server in servers:
            is_current = server['id'] == current_server_id
            button_text = f"{'✅ ' if is_current else ''}{server['name']}"
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"ip_select_{server['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="ip_refresh")])
        keyboard.append([InlineKeyboardButton("ℹ️ Информация", callback_data="ip_info")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def handle_ip_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает выбор IP сервера"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = update.effective_user
        
        if data == "ip_refresh":
            await self.show_ip_menu(update, context)
            return
        
        if data == "ip_info":
            await self.show_ip_info(update, context)
            return
        
        if data.startswith("ip_select_"):
            server_id = data.replace("ip_select_", "")
            await self.select_ip_server(update, context, server_id)
            return
    
    async def select_ip_server(self, update: Update, context: ContextTypes.DEFAULT_TYPE, server_id: str):
        """Устанавливает IP сервер для пользователя"""
        query = update.callback_query
        user = update.effective_user
        
        # Получаем пользователя и его VPN ключ
        db_user = session.query(User).filter_by(tg_id=user.id).first()
        if not db_user:
            await query.edit_message_text("❌ Ошибка: пользователь не найден")
            return
        
        vpn_key = session.query(VpnKey).filter_by(user_id=db_user.id).first()
        if not vpn_key:
            await query.edit_message_text("❌ Ошибка: VPN ключ не найден")
            return
        
        # Получаем информацию о сервере
        servers = self.ip_manager.get_available_servers()
        server = next((s for s in servers if s['id'] == server_id), None)
        if not server:
            await query.edit_message_text("❌ Сервер не найден")
            return
        
        # Проверяем, не выбран ли уже этот сервер
        current_server_id = self.ip_manager.get_user_ip(vpn_key.uuid)
        if current_server_id == server_id:
            await query.edit_message_text(
                f"✅ Уже используется: **{server['name']}**",
                parse_mode='Markdown'
            )
            await asyncio.sleep(2)
            await self.show_ip_menu(update, context)
            return
        
        # Устанавливаем новый IP сервер
        await query.edit_message_text("⏳ Применяем изменения...")
        
        success = self.ip_manager.set_user_ip(vpn_key.uuid, server_id)
        
        if success:
            # Перезапускаем Xray
            restart_success = self.ip_manager.restart_xray()
            
            if restart_success:
                text = f"✅ **IP изменен успешно!**\\n\\n"
                text += f"🌍 Новый выход: **{server['name']}**\\n"
                text += f"📝 {server['description']}\\n\\n"
                text += "🔄 Переподключите VPN клиент для применения изменений"
                
                await query.edit_message_text(text, parse_mode='Markdown')
                
                # Логируем изменение
                logger.info(f"Пользователь {user.id} изменил IP на {server['name']}")
            else:
                await query.edit_message_text(
                    "⚠️ IP изменен, но возникла ошибка при перезапуске сервиса.\\n"
                    "Обратитесь к администратору.",
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text(
                "❌ Ошибка при изменении IP.\\n"
                "Попробуйте позже или обратитесь к администратору.",
                parse_mode='Markdown'
            )
        
        # Возвращаемся в меню через 3 секунды
        await asyncio.sleep(3)
        await self.show_ip_menu(update, context)
    
    async def show_ip_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает информацию о системе IP"""
        text = "ℹ️ **ИНФОРМАЦИЯ О СИСТЕМЕ IP**\\n\\n"
        text += "🌍 **Как это работает:**\\n"
        text += "• Вы можете выбрать разные IP для выхода в интернет\\n"
        text += "• Каждый IP может быть из разной страны\\n"
        text += "• Смена IP происходит мгновенно\\n\\n"
        
        text += "🔧 **Доступные типы:**\\n"
        text += "• **Прямое** - IP сервера VPN\\n"
        text += "• **Прокси** - через дополнительные серверы\\n"
        text += "• **WARP** - через Cloudflare\\n\\n"
        
        text += "⚠️ **Важно:**\\n"
        text += "• После смены IP переподключите VPN\\n"
        text += "• Некоторые IP могут быть медленнее\\n"
        text += "• Блокировка рекламы работает всегда"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="ip_refresh")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Импорт asyncio для sleep
import asyncio

def setup_ip_handlers(application):
    """Настраивает обработчики IP команд"""
    ip_handler = IPHandler()
    
    # Команда для показа меню IP
    application.add_handler(CommandHandler("ip", ip_handler.show_ip_menu))
    
    # Обработчики callback'ов
    application.add_handler(CallbackQueryHandler(
        ip_handler.handle_ip_selection, 
        pattern=r"^ip_"
    ))