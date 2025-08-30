#!/usr/bin/env python3
"""
Обработчик аренды IP-адресов в VPN боте
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from vpn_bot.utils.vds_ip_manager import VDSIPManager
from db.models import session, User, VpnKey

logger = logging.getLogger(__name__)

class RentalHandler:
    def __init__(self):
        self.vds_manager = VDSIPManager()
    
    async def show_rental_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню аренды IP"""
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
        
        # Получаем арендованные IP пользователя
        user_ips = self.vds_manager.get_user_ips(user.id)
        
        text = "🏢 **АРЕНДА IP-АДРЕСОВ**\\n\\n"
        text += "💡 Арендуйте дополнительные IP из разных стран\\n"
        text += "🌍 Каждый IP - это отдельный выход в интернет\\n\\n"
        
        if user_ips:
            text += "📋 **Ваши арендованные IP:**\\n"
            for ip_info in user_ips:
                days_left = ip_info.get('days_left', 0)
                status_emoji = "🟢" if days_left > 3 else "🟡" if days_left > 0 else "🔴"
                text += f"{status_emoji} `{ip_info['ip_address']}` - {days_left} дн.\\n"
            text += "\\n"
        
        text += "Выберите действие:"
        
        # Создаем клавиатуру
        keyboard = [
            [InlineKeyboardButton("➕ Арендовать новый IP", callback_data="rent_new_ip")],
        ]
        
        if user_ips:
            keyboard.append([InlineKeyboardButton("📋 Управление IP", callback_data="manage_ips")])
        
        keyboard.extend([
            [InlineKeyboardButton("💰 Тарифы", callback_data="rental_prices")],
            [InlineKeyboardButton("ℹ️ Как это работает", callback_data="rental_info")],
            [InlineKeyboardButton("🔙 Назад", callback_data="ip_refresh")]
        ])
        
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
    
    async def show_rental_locations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает доступные локации для аренды"""
        query = update.callback_query
        await query.answer()
        
        locations = self.vds_manager.get_available_locations()
        
        if not locations:
            await query.edit_message_text(
                "❌ Нет доступных локаций для аренды\\n"
                "Обратитесь к администратору для настройки провайдеров.",
                parse_mode='Markdown'
            )
            return
        
        text = "🌍 **ВЫБОР ЛОКАЦИИ IP**\\n\\n"
        text += "Выберите страну для аренды IP-адреса:\\n\\n"
        
        # Группируем по провайдерам
        providers = {}
        for location in locations:
            provider = location['provider_name']
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(location)
        
        for provider, locs in providers.items():
            text += f"**{provider}:**\\n"
            for loc in locs:
                text += f"• {loc['location_name']} - {loc['cost_per_day']}₽/день\\n"
            text += "\\n"
        
        # Создаем клавиатуру
        keyboard = []
        for location in locations:
            button_text = f"{location['location_name']} ({location['cost_per_day']}₽/день)"
            callback_data = f"rent_location_{location['provider_id']}_{location['location_id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="rental_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_rental_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, provider_id: str, location_id: str):
        """Показывает выбор срока аренды"""
        query = update.callback_query
        await query.answer()
        
        # Находим информацию о локации
        locations = self.vds_manager.get_available_locations()
        location = next((l for l in locations if l['provider_id'] == provider_id and l['location_id'] == location_id), None)
        
        if not location:
            await query.edit_message_text("❌ Локация не найдена")
            return
        
        text = f"⏰ **СРОК АРЕНДЫ IP**\\n\\n"
        text += f"📍 Локация: {location['location_name']}\\n"
        text += f"💰 Стоимость: {location['cost_per_day']}₽/день\\n\\n"
        text += "Выберите срок аренды:"
        
        # Варианты сроков аренды
        durations = [
            (1, "1 день"),
            (3, "3 дня"),
            (7, "1 неделя"),
            (14, "2 недели"),
            (30, "1 месяц")
        ]
        
        keyboard = []
        for days, label in durations:
            total_cost = location['cost_per_day'] * days
            button_text = f"{label} - {total_cost}₽"
            callback_data = f"rent_confirm_{provider_id}_{location_id}_{days}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="rent_new_ip")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def confirm_rental(self, update: Update, context: ContextTypes.DEFAULT_TYPE, provider_id: str, location_id: str, days: int):
        """Подтверждает аренду IP"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        
        # Находим информацию о локации
        locations = self.vds_manager.get_available_locations()
        location = next((l for l in locations if l['provider_id'] == provider_id and l['location_id'] == location_id), None)
        
        if not location:
            await query.edit_message_text("❌ Локация не найдена")
            return
        
        total_cost = self.vds_manager.get_rental_cost(provider_id, days)
        
        text = f"✅ **ПОДТВЕРЖДЕНИЕ АРЕНДЫ**\\n\\n"
        text += f"📍 Локация: {location['location_name']}\\n"
        text += f"⏰ Срок: {days} дн.\\n"
        text += f"💰 Стоимость: {total_cost}₽\\n\\n"
        text += "⚠️ **Внимание:**\\n"
        text += "• Оплата будет списана с баланса\\n"
        text += "• IP активируется сразу после оплаты\\n"
        text += "• Возврат средств не предусмотрен\\n\\n"
        text += "Подтвердить аренду?"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"rent_execute_{provider_id}_{location_id}_{days}"),
                InlineKeyboardButton("❌ Отмена", callback_data="rental_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def execute_rental(self, update: Update, context: ContextTypes.DEFAULT_TYPE, provider_id: str, location_id: str, days: int):
        """Выполняет аренду IP"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        
        await query.edit_message_text("⏳ Арендуем IP-адрес...")
        
        # Выполняем аренду
        result = self.vds_manager.rent_ip(user.id, provider_id, location_id, days)
        
        if result["success"]:
            text = f"🎉 **IP УСПЕШНО АРЕНДОВАН!**\\n\\n"
            text += f"🌐 IP-адрес: `{result['ip_address']}`\\n"
            text += f"🔌 Порт: `{result.get('port', 'неизвестен')}`\\n"
            text += f"💰 Стоимость: {result['cost']}₽\\n"
            text += f"⏰ Действует до: {result['expires'][:10]}\\n\\n"
            text += "🔑 **Отдельный VLESS ключ создан!**\\n"
            text += "✅ Готов к использованию\\n\\n"
            text += "💡 Этот IP работает как отдельный сервер"
            
            keyboard = [
                [InlineKeyboardButton("🔑 Получить ключ", callback_data=f"get_rented_key_{result['ip_address'].replace('.', '_')}")],
                [InlineKeyboardButton("📋 Мои IP", callback_data="manage_ips")]
            ]
            
            # Логируем успешную аренду
            logger.info(f"Пользователь {user.id} арендовал IP {result['ip_address']}")
            
        else:
            text = f"❌ **ОШИБКА АРЕНДЫ**\\n\\n"
            text += f"Причина: {result['error']}\\n\\n"
            text += "Попробуйте позже или обратитесь к администратору."
            
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="rent_new_ip")],
                [InlineKeyboardButton("🔙 Назад", callback_data="rental_menu")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_user_ips(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает управление IP пользователя"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        
        user_ips = self.vds_manager.get_user_ips(user.id)
        
        if not user_ips:
            await query.edit_message_text(
                "📋 У вас нет арендованных IP-адресов\\n\\n"
                "Арендуйте первый IP для расширения возможностей VPN!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Арендовать IP", callback_data="rent_new_ip")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="rental_menu")]
                ])
            )
            return
        
        text = "📋 **ВАШИ IP-АДРЕСА**\\n\\n"
        
        keyboard = []
        for ip_info in user_ips:
            days_left = ip_info.get('days_left', 0)
            status_emoji = "🟢" if days_left > 3 else "🟡" if days_left > 0 else "🔴"
            
            text += f"{status_emoji} **{ip_info['ip_address']}**\\n"
            text += f"   📍 {ip_info['location_id']}\\n"
            text += f"   ⏰ Осталось: {days_left} дн.\\n"
            text += f"   💰 {ip_info['cost_per_day']}₽/день\\n\\n"
            
            # Кнопка для управления конкретным IP
            button_text = f"⚙️ {ip_info['ip_address']}"
            callback_data = f"manage_ip_{ip_info['ip_address'].replace('.', '_')}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="rental_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_rental_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает информацию об аренде IP"""
        text = "ℹ️ **КАК РАБОТАЕТ АРЕНДА IP**\\n\\n"
        text += "🌍 **Что это дает:**\\n"
        text += "• Выход в интернет с IP разных стран\\n"
        text += "• Обход географических блокировок\\n"
        text += "• Дополнительная анонимность\\n"
        text += "• Распределение нагрузки\\n\\n"
        
        text += "💰 **Как оплачивается:**\\n"
        text += "• Оплата за каждый день использования\\n"
        text += "• Автоматическое списание с баланса\\n"
        text += "• Возможность продления\\n\\n"
        
        text += "⚙️ **Как использовать:**\\n"
        text += "1. Арендуйте IP в нужной стране\\n"
        text += "2. IP автоматически добавится в систему\\n"
        text += "3. Выберите его в меню 'Смена IP'\\n"
        text += "4. Переподключите VPN клиент\\n\\n"
        
        text += "⚠️ **Важно знать:**\\n"
        text += "• Максимум 3 IP на пользователя\\n"
        text += "• IP освобождается автоматически\\n"
        text += "• Возврат средств не предусмотрен"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="rental_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_rented_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ip_address: str):
        """Показывает VLESS ключ для арендованного IP"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        
        # Получаем информацию об арендованном IP
        user_ips = self.vds_manager.get_user_ips(user.id)
        ip_info = next((ip for ip in user_ips if ip['ip_address'] == ip_address), None)
        
        if not ip_info:
            await query.edit_message_text("❌ IP не найден или не принадлежит вам")
            return
        
        # Получаем VLESS ключ из ServerManager
        from vpn_bot.utils.server_manager import ServerManager
        server_manager = ServerManager()
        
        server_id = f"xray_{ip_address.replace('.', '_')}"
        server_info = server_manager.get_server_info(server_id)
        
        if not server_info:
            await query.edit_message_text("❌ Сервер для этого IP не найден")
            return
        
        vless_key = server_info.get('vless_key', '')
        
        if not vless_key:
            await query.edit_message_text("❌ VLESS ключ не найден")
            return
        
        text = f"🔑 **VLESS КЛЮЧ ДЛЯ IP {ip_address}**\\n\\n"
        text += f"📍 Локация: {ip_info['location_id']}\\n"
        text += f"🔌 Порт: {server_info['port']}\\n"
        text += f"⏰ Действует до: {ip_info['rental_end'][:10]}\\n\\n"
        text += f"🔐 **Ваш ключ:**\\n"
        text += f"`{vless_key}`\\n\\n"
        text += "📱 **Как использовать:**\\n"
        text += "1. Скопируйте ключ выше\\n"
        text += "2. Вставьте в VPN клиент\\n"
        text += "3. Подключитесь\\n\\n"
        text += "💡 Этот ключ работает только с данным IP"
        
        keyboard = [
            [InlineKeyboardButton("📋 Скопировать", callback_data="noop")],
            [InlineKeyboardButton("📊 Статус сервера", callback_data=f"server_status_{server_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="manage_ips")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def manage_specific_ip(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ip_address: str):
        """Управление конкретным арендованным IP"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        
        # Получаем информацию об IP
        user_ips = self.vds_manager.get_user_ips(user.id)
        ip_info = next((ip for ip in user_ips if ip['ip_address'] == ip_address), None)
        
        if not ip_info:
            await query.edit_message_text("❌ IP не найден")
            return
        
        # Получаем статус сервера
        from vpn_bot.utils.server_manager import ServerManager
        server_manager = ServerManager()
        
        server_id = f"xray_{ip_address.replace('.', '_')}"
        server_status = server_manager.get_server_status(server_id)
        
        days_left = ip_info.get('days_left', 0)
        status_emoji = "🟢" if server_status == "active" else "🔴"
        
        text = f"⚙️ **УПРАВЛЕНИЕ IP {ip_address}**\\n\\n"
        text += f"📍 Локация: {ip_info['location_id']}\\n"
        text += f"⏰ Осталось: {days_left} дн.\\n"
        text += f"💰 Стоимость: {ip_info['cost_per_day']}₽/день\\n"
        text += f"{status_emoji} Статус: {server_status}\\n\\n"
        text += "Выберите действие:"
        
        keyboard = [
            [InlineKeyboardButton("🔑 Показать ключ", callback_data=f"get_rented_key_{ip_address.replace('.', '_')}")],
            [InlineKeyboardButton("🔄 Перезапустить", callback_data=f"restart_server_{server_id}")],
            [InlineKeyboardButton("📊 Статистика", callback_data=f"server_stats_{server_id}")],
        ]
        
        if days_left <= 3:
            keyboard.append([InlineKeyboardButton("💰 Продлить", callback_data=f"extend_rental_{ip_address.replace('.', '_')}")])
        
        keyboard.append([InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_rental_{ip_address.replace('.', '_')}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="manage_ips")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_rental_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback'ы аренды"""
        query = update.callback_query
        data = query.data
        
        if data == "rental_menu":
            await self.show_rental_menu(update, context)
        elif data == "rent_new_ip":
            await self.show_rental_locations(update, context)
        elif data == "manage_ips":
            await self.show_user_ips(update, context)
        elif data == "rental_info":
            await self.show_rental_info(update, context)
        elif data.startswith("rent_location_"):
            parts = data.split("_")
            provider_id = parts[2]
            location_id = parts[3]
            await self.show_rental_duration(update, context, provider_id, location_id)
        elif data.startswith("rent_confirm_"):
            parts = data.split("_")
            provider_id = parts[2]
            location_id = parts[3]
            days = int(parts[4])
            await self.confirm_rental(update, context, provider_id, location_id, days)
        elif data.startswith("rent_execute_"):
            parts = data.split("_")
            provider_id = parts[2]
            location_id = parts[3]
            days = int(parts[4])
            await self.execute_rental(update, context, provider_id, location_id, days)
        elif data.startswith("get_rented_key_"):
            ip_key = data.replace("get_rented_key_", "").replace("_", ".")
            await self.show_rented_key(update, context, ip_key)
        elif data.startswith("manage_ip_"):
            ip_key = data.replace("manage_ip_", "").replace("_", ".")
            await self.manage_specific_ip(update, context, ip_key)

def setup_rental_handlers(application):
    """Настраивает обработчики аренды IP"""
    rental_handler = RentalHandler()
    
    # Команда для показа меню аренды
    application.add_handler(CommandHandler("rent", rental_handler.show_rental_menu))
    
    # Обработчики callback'ов
    application.add_handler(CallbackQueryHandler(
        rental_handler.handle_rental_callback, 
        pattern=r"^(rental_|rent_)"
    ))