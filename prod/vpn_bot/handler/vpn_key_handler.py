from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.helpers import escape, escape_markdown
from utils.generator import generate_vpn_link
from keyboard.vpn_keyboards import (
    get_vpn_keyboard, 
    get_key_management_keyboard, 
    get_confirmation_keyboard,
    get_main_menu_keyboard
)
import os
import json
from datetime import datetime

class VPNKeyHandler:
    """Обработчик для управления VPN ключами"""
    
    def __init__(self):
        self.clients_dir = "/var/www/vpn/xray/clients"
    
    def get_user_existing_key(self, client_name: str):
        """Получает информацию о существующем ключе пользователя"""
        if not os.path.exists(self.clients_dir):
            return None
        
        for filename in os.listdir(self.clients_dir):
            if filename.endswith('.json') and not filename.startswith('REMOVED_'):
                try:
                    with open(os.path.join(self.clients_dir, filename), 'r') as f:
                        client_data = json.load(f)
                        metadata = client_data.get('_metadata', {})
                        if metadata.get('client_name') == client_name:
                            return {
                                'uuid': client_data.get('id'),
                                'filename': filename,
                                'short_id': client_data.get('shortId'),
                                'created_at': metadata.get('created_at', 'unknown')
                            }
                except:
                    continue
        
        return None
    
    async def show_vpn_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Показывает меню управления VPN ключами"""
        existing_key = self.get_user_existing_key(client_name)
        
        if existing_key:
            # У пользователя есть ключ
            message_text = f"""🔑 VPN ключ для {escape(client_name)}:

📋 Информация о ключе:
• Подключений сейчас: 0
• 📅 Создан: `{existing_key['created_at']}`
• Лимит соединений: {existing_key.get('max_connections', 3)}

💡 Выберите действие:"""
            
            keyboard = get_vpn_keyboard(client_name, has_existing_key=True)
        else:
            # У пользователя нет ключа
            message_text = f"""🔑 VPN ключ для {escape(client_name)}:

❌ У вас пока нет VPN ключа.

💡 Создайте новый ключ для начала работы:"""
            
            keyboard = get_vpn_keyboard(client_name, has_existing_key=False)
        
        # Если это callback query, редактируем сообщение
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message_text,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            # Если это новое сообщение
            await update.message.reply_text(
                text=message_text,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
    
    async def show_current_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Показывает текущий VPN ключ пользователя"""
        existing_key = self.get_user_existing_key(client_name)
        
        if not existing_key:
            await update.callback_query.answer("❌ У вас нет VPN ключа")
            return
        
        # Генерируем полную VLESS ссылку
        try:
            from xray.generate_client import generate_vless_client
            
            result = generate_vless_client(
                clients_dir=self.clients_dir,
                flow="xtls-rprx-vision",
                host="146.103.125.210",
                port=443,
                sni="www.cloudflare.com",
                client_name=client_name,
                enforce_limits=False  # Не проверяем лимиты, просто показываем ключ
            )
            
            if "error" not in result:
                vless_link = result.get("link", "")
                
                message_text = f"""🔑 Текущий VPN ключ для {escape(client_name)}:

📋 Детали ключа:
• Подключений сейчас: 0
• 📅 Создан: `{existing_key['created_at']}`
• Лимит соединений: {existing_key.get('max_connections', 3)}

🔗 VLESS ссылка:
```
{vless_link}
```

💡 Скопируйте ссылку и используйте в вашем VPN клиенте"""
                
                keyboard = get_key_management_keyboard(client_name)
                
                await update.callback_query.edit_message_text(
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                await update.callback_query.answer(f"❌ Ошибка: {result['error']}")
                
        except Exception as e:
            await update.callback_query.answer(f"❌ Ошибка генерации: {e}")
    
    async def update_vpn_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Обновляет VPN ключ пользователя"""
        existing_key = self.get_user_existing_key(client_name)
        
        if not existing_key:
            await update.callback_query.answer("❌ У вас нет VPN ключа для обновления")
            return
        
        # Показываем подтверждение
        message_text = f"""🔄 Обновление VPN ключа для {escape_markdown(client_name, version=2)}:

⚠️ Внимание! При обновлении ключа:
• Старый ключ будет удален
• Все активные соединения будут разорваны
• Нужно будет обновить конфигурацию на всех устройствах

📋 Текущий ключ:
• 🔑 UUID: `{existing_key['uuid'][:8]}...`
• 📅 Создан: `{existing_key['created_at']}`

❓ Вы уверены, что хотите обновить ключ?"""
        
        keyboard = get_confirmation_keyboard("update", client_name)
        
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )
    
    async def confirm_update_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Подтверждает обновление ключа"""
        await update.callback_query.answer("🔄 Обновляю ключ...")
        
        try:
            # Удаляем старый ключ
            existing_key = self.get_user_existing_key(client_name)
            if existing_key:
                old_file = os.path.join(self.clients_dir, existing_key['filename'])
                if os.path.exists(old_file):
                    os.remove(old_file)
            
            # Создаем новый ключ
            result = generate_vpn_link(client_name)
            
            if result[0] and not result[0].startswith("❌"):
                # Успешно создан новый ключ
                new_key = self.get_user_existing_key(client_name)
                
                message_text = f"""✅ VPN ключ успешно обновлен для {escape_markdown(client_name, version=2)}\!

🔑 Новый ключ:
• Подключений сейчас: 0
• 📅 Создан: `{new_key['created_at']}`
• Лимит соединений: {new_key.get('max_connections', 3)}

🔗 VLESS ссылка:
```
{result[0]}
```

💡 Используйте новую ссылку в вашем VPN клиенте"""
                
                keyboard = get_key_management_keyboard(client_name)
                
                await update.callback_query.edit_message_text(
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                # Ошибка создания
                await update.callback_query.edit_message_text(
                    text=f"❌ Ошибка обновления ключа: {result[0]}",
                    reply_markup=get_vpn_keyboard(client_name, has_existing_key=True)
                )
                
        except Exception as e:
            await update.callback_query.edit_message_text(
                text=f"❌ Ошибка обновления: {e}",
                reply_markup=get_vpn_keyboard(client_name, has_existing_key=True)
            )
    
    async def delete_vpn_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Удаляет VPN ключ пользователя"""
        existing_key = self.get_user_existing_key(client_name)
        
        if not existing_key:
            await update.callback_query.answer("❌ У вас нет VPN ключа для удаления")
            return
        
        # Показываем подтверждение
        message_text = f"""🗑️ Удаление VPN ключа для {escape_markdown(client_name, version=2)}:

⚠️ Внимание! При удалении ключа:
• Ключ будет полностью удален
• Все активные соединения будут разорваны
• Восстановить ключ будет невозможно

📋 Ключ для удаления:
• 🔑 UUID: `{existing_key['uuid'][:8]}...`
• 📅 Создан: `{existing_key['created_at']}`

❓ Вы уверены, что хотите удалить ключ?"""
        
        keyboard = get_confirmation_keyboard("delete", client_name)
        
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )
    
    async def confirm_delete_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Подтверждает удаление ключа"""
        await update.callback_query.answer("🗑️ Удаляю ключ...")
        
        try:
            # Удаляем ключ
            existing_key = self.get_user_existing_key(client_name)
            if existing_key:
                old_file = os.path.join(self.clients_dir, existing_key['filename'])
                if os.path.exists(old_file):
                    os.remove(old_file)
                
                message_text = f"""✅ VPN ключ успешно удален для {escape_markdown(client_name, version=2)}\!

🗑️ Удаленный ключ:
• 🔑 UUID: `{existing_key['uuid'][:8]}...`
• 📅 Создан: `{existing_key['created_at']}`

💡 Теперь вы можете создать новый ключ"""
                
                keyboard = get_vpn_keyboard(client_name, has_existing_key=False)
                
                await update.callback_query.edit_message_text(
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                await update.callback_query.edit_message_text(
                    text="❌ Ключ не найден",
                    reply_markup=get_vpn_keyboard(client_name, has_existing_key=False)
                )
                
        except Exception as e:
            await update.callback_query.edit_message_text(
                text=f"❌ Ошибка удаления: {e}",
                reply_markup=get_vpn_keyboard(client_name, has_existing_key=True)
            )
    
    async def create_new_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Создает новый VPN ключ"""
        await update.callback_query.answer("🔑 Создаю новый ключ...")
        
        try:
            result = generate_vpn_link(client_name)
            
            if result[0] and not result[0].startswith("❌"):
                # Успешно создан ключ
                new_key = self.get_user_existing_key(client_name)
                
                message_text = f"""✅ Новый VPN ключ создан для {escape_markdown(client_name, version=2)}\!

🔑 Детали ключа:
• 🔑 UUID: `{new_key['uuid'][:8]}...`
• 🆔 Short ID: `{new_key['short_id']}`
• 📅 Создан: `{new_key['created_at']}`

🔗 VLESS ссылка:
```
{result[0]}
```

💡 Используйте ссылку в вашем VPN клиенте"""

                keyboard = get_key_management_keyboard(client_name)
                await update.callback_query.edit_message_text(
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )
            else:
                # Ошибка создания
                await update.callback_query.edit_message_text(
                    text=f"❌ Ошибка создания ключа: {result[0]}",
                    reply_markup=get_vpn_keyboard(client_name, has_existing_key=False)
                )
            
        except Exception as e:
            await update.callback_query.edit_message_text(
                text=f"❌ Ошибка создания: {e}",
                reply_markup=get_vpn_keyboard(client_name, has_existing_key=False)
            )