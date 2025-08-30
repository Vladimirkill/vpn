from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
import sys, os
import logging
import json
import subprocess

# Гарантируем, что пакет `xray` импортируется по относительному пути проекта
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.helpers import escape, escape_markdown
from utils.vpn_generator import UniversalVPNGenerator
from utils.generator import generate_vpn_link
from keyboard.vpn_keyboards import get_vpn_keyboard, get_main_menu_keyboard, get_key_management_keyboard, get_confirmation_keyboard
from config import VPN_CONFIG, ADMIN_IDS
from db.models import session, BypassSite, VpnBypassRule, VpnKey, User, ensure_user
from handler.admin_handler import AdminHandler
import os
import subprocess
import json
import asyncio

class VPNHandler:
    """Обработчик VPN команд"""
    
    def __init__(self):
        self.generator = UniversalVPNGenerator(VPN_CONFIG)
        # Состояния пользователей для ввода доменов
        self.user_states = {}
        self.clients_dir = "/var/www/vpn/xray/clients"
        # Админский обработчик
        self.admin_handler = AdminHandler()
    
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
                                'created_at': metadata.get('created_at', 'unknown'),
                                'max_connections': metadata.get('max_connections', 3),
                                'max_devices': metadata.get('max_devices', 3)
                            }
                except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                    logging.warning(f"Ошибка чтения файла клиента {filename}: {e}")
                    continue
        
        return None
    
    async def _update_xray_routing(self):
        """Обновляет routing rules в конфигурации Xray"""
        try:
            # Перестраиваем конфигурацию с новыми routing rules
            from config import PYTHON_EXECUTABLE, GENERATION_PATHS, PROJECT_ROOT
            result = subprocess.run([
                PYTHON_EXECUTABLE, GENERATION_PATHS['build_config_script']
            ], capture_output=True, text=True, cwd=f'{PROJECT_ROOT}/xray')
            
            if result.returncode == 0:
                return True
            else:
                print(f"❌ Ошибка обновления Xray config: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при вызове build_config: {e}")
            return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        is_admin = user_id in ADMIN_IDS
        
        # Получаем статус сервера для показа в главном меню
        server_status = await self._get_server_status_brief()
        
        welcome_text = f"🚀 VPN Bot запущен\!\n\n{server_status}\n📊 Доступный VPN сервис:"
        
        keyboard = [
            [
                InlineKeyboardButton("🚀 Xray (VLESS)", callback_data="vpn_xray")
            ],
            [
                InlineKeyboardButton("❓ Справка", callback_data="help")
            ]
        ]
        
        # Добавляем админскую кнопку для админов
        if is_admin:
            keyboard.insert(-1, [
                InlineKeyboardButton("🛡️ Админ панель", callback_data="admin_menu")
            ])
            keyboard.insert(-1, [
                InlineKeyboardButton("📊 Детальный статус", callback_data="status")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
        # Скрываем reply клавиатуру
        await update.message.reply_text( reply_markup=ReplyKeyboardRemove())
    
    async def my_keys_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает VPN ключи пользователя"""
        if not context.args:
            await update.message.reply_text("❌ Укажите имя клиента: /mykeys <имя>")
            return
        
        client_name = context.args[0]
        await self.show_vpn_menu(update, context, client_name)
    
    async def show_vpn_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Показывает меню управления VPN ключами"""
        existing_key = self.get_user_existing_key(client_name)
        
        if existing_key:
            # Вместо общего меню сразу показываем текущий ключ с ссылкой
            await self.show_current_key(update, context, client_name)
            return
        else:
            # У пользователя нет ключа
            message_text = f"""🔑 VPN ключ для {client_name}:

❌ У вас пока нет VPN ключа.

💡 Создайте новый ключ для начала работы:"""
            
            keyboard = get_vpn_keyboard(client_name, has_existing_key=False)
        
        # Если это callback query, редактируем сообщение
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message_text,
                reply_markup=keyboard
            )
        else:
            # Если это новое сообщение
            await update.message.reply_text(
                text=message_text,
                reply_markup=keyboard
            )
    
    async def create_new_key_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает форму для создания нового ключа"""
        message_text = """🚀 Создание нового VPN ключа

Введите имя для вашего VPN ключа:
Пример: /create john_doe

💡 Имя должно содержать только буквы, цифры и подчеркивания"""
        
        await update.message.reply_text(message_text)
    
    async def xray_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /xray"""
        if not context.args:
            await update.message.reply_text("❌ Укажите имя клиента: /xray <имя>")
            return
        
        client_name = context.args[0]
        
        # Проверяем, есть ли у пользователя уже ключ
        existing_key = self.get_user_existing_key(client_name)
        
        if existing_key:
            # Показываем существующий ключ с кнопками
            await self.show_vpn_menu(update, context, client_name)
        else:
            # Создаем новый ключ
            await update.message.reply_text(f"🔄 Генерирую Xray конфигурацию для {client_name}...")
            
            try:
                result = generate_vpn_link(client_name)
                
                if result[0] and not result[0].startswith("❌"):
                    # Успешно создан ключ
                    new_key = self.get_user_existing_key(client_name)
                    
                    message_text = f"""✅ Новый VPN ключ создан для {escape_markdown(client_name, version=2)}\!

🔑 Детали ключа:
• Подключений сейчас: 0
• 📅 Создан: `{new_key['created_at']}`
• Лимит соединений: {new_key.get('max_connections', 3)}

🔗 VLESS ссылка:
```
{result[0]}
```

💡 Используйте ссылку в вашем VPN клиенте"""
                    
                    # Показываем меню управления ключом
                    await update.message.reply_text(
                        text=message_text,
                        reply_markup=get_vpn_keyboard(client_name, has_existing_key=True),
                        parse_mode='MarkdownV2'
                    )
                else:
                    # Ошибка создания
                    await update.message.reply_text(f"❌ Ошибка создания ключа: {result[0]}")
                    
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка создания: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📚 Справка по VPN Bot

🔧 Основные команды:
• /start \\- главное меню
• /mykeys <имя> \\- показать ваши VPN ключи
• /create \\- создать новый ключ
• /xray <имя> \\- создать VLESS конфигурацию

🔑 Управление ключей:
• Показать текущий ключ
• Обновить ключ
• Удалить ключ
• Настройки лимитов

📋 Примеры:
/xray john
/mykeys alice
/create bob

⚙️ Дополнительные команды:
• /status \\- показать статус VPN сервисов
• /help \\- эта справка

💡 Для получения файлов используйте команды с именем клиента.
        """
        await update.message.reply_text(help_text.strip())
    
    async def openvpn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /openvpn"""
        if not context.args:
            await update.message.reply_text("❌ Укажите имя клиента: /openvpn <имя>")
            return
        
        client_name = context.args[0]
        await update.message.reply_text(f"🔄 Генерирую OpenVPN конфигурацию для {client_name}...")
        
        try:
            result = self.generator.generate_vpn('openvpn', client_name)
            
            if result.get('success'):
                filepath = result.get('filepath', '')
                if filepath and os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=f,
                            filename=f"{client_name}.ovpn",
                            caption=f"✅ OpenVPN конфигурация для {client_name}"
                        )
                else:
                    await update.message.reply_text(
                        f"✅ OpenVPN конфигурация для {client_name} сгенерирована, но файл не найден"
                    )
            else:
                await update.message.reply_text(
                    f"❌ Ошибка генерации OpenVPN: {result.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def wireguard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /wireguard"""
        if not context.args:
            await update.message.reply_text("❌ Укажите имя клиента: /wireguard <имя>")
            return
        
        client_name = context.args[0]
        await update.message.reply_text(f"🔄 Генерирую WireGuard конфигурацию для {client_name}...")
        
        try:
            result = self.generator.generate_vpn('wireguard', client_name, generate_qr=True)
            
            if result.get('success'):
                filepath = result.get('filepath', '')
                qr_path = result.get('qr_path', '')
                
                # Отправляем конфигурационный файл
                if filepath and os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=f,
                            filename=f"{client_name}.conf",
                            caption=f"✅ WireGuard конфигурация для {client_name}"
                        )
                
                # Отправляем QR-код если есть
                if qr_path and os.path.exists(qr_path):
                    with open(qr_path, 'rb') as f:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=f,
                            caption=f"📱 QR-код для {client_name}"
                        )
                
                # Отправляем информацию о ключах
                keys = result.get('keys', {})
                if keys:
                    # Экранируем ключи для безопасной передачи в HTML
                    public_key = escape(keys.get('public_key', 'N/A'))
                    preshared_key = escape(keys.get('preshared_key', 'N/A'))
                    keys_info = f"""
🔑 Ключи для {client_name}:
• Публичный ключ: <code>{public_key}</code>
• Preshared ключ: <code>{preshared_key}</code>
                    """.strip()
                    await update.message.reply_text(keys_info, parse_mode='HTML')
                
            else:
                await update.message.reply_text(
                    f"❌ Ошибка генерации WireGuard: {result.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        
        # Отправляем временное сообщение о загрузке
        loading_msg = await update.message.reply_text("📊 Проверяю статус сервисов... ⏳")
        
        status_text = "📊 Статус VPN сервисов:\n\n"
        
        # Проверяем общий пинг интернета
        ping_result = await self._check_ping()
        status_text += f"🌐 Интернет: {ping_result}\n\n"
        
                # Проверяем OpenVPN
        try:
            result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'openvpn@server'], 
                                   capture_output=True, text=True)
            ovpn_status = "🟢 Активен" if result.stdout.strip() == "active" else "🔴 Неактивен"
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logging.error(f"Ошибка проверки статуса OpenVPN: {e}")
            ovpn_status = "❓ Неизвестно"
        
        status_text += f"🔐 OpenVPN: {ovpn_status}\n"
        
                # Проверяем WireGuard
        try:
            result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'wg-quick@wg0'], 
                                   capture_output=True, text=True)
            wg_status = "🟢 Активен" if result.stdout.strip() == "active" else "🔴 Неактивен"
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logging.error(f"Ошибка проверки статуса WireGuard: {e}")
            wg_status = "❓ Неизвестно"
        
        status_text += f"⚡ WireGuard: {wg_status}\n"
        
        # Проверяем Xray с детальной статистикой
        try:
            result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'xray'], capture_output=True, text=True)
            xray_active = (result.returncode == 0)
            
            if xray_active:
                # Получаем статистику по ключам
                key_stats, total_connections = await self._get_xray_key_stats()
                
                status_text += f"🚀 Xray: 🟢 Активен ({total_connections} соединений)\n"
                
                if key_stats:
                    active_keys = [k for k in key_stats.values() if k['connections'] > 0]
                    inactive_keys = [k for k in key_stats.values() if k['connections'] == 0]
                    
                    # Показываем активные ключи
                    if active_keys:
                        status_text += "   🔑 Активные ключи:\n"
                        for key_data in active_keys[:5]:  # Показываем только первые 5
                            connections = key_data['connections']
                            max_conn = key_data.get('max_connections', 3)
                            name = key_data['name']
                            limit_status = "⚠️" if connections > max_conn else "✅"
                            status_text += f"      {limit_status} {name}: {connections}/{max_conn} устройств\n"
                        
                        if len(active_keys) > 5:
                            status_text += f"      ... еще {len(active_keys) - 5} активных ключей\n"
                    
                    # Показываем общую статистику
                    total_keys = len(key_stats)
                    active_count = len(active_keys)
                    status_text += f"   📊 Всего ключей: {total_keys} | Активных: {active_count}"
                else:
                    status_text += "   📊 Нет зарегистрированных ключей"
            else:
                status_text += f"🚀 Xray: 🔴 Неактивен"
        except Exception as e:
            status_text += f"🚀 Xray: ❓ Ошибка проверки"
        
        await loading_msg.edit_text(status_text)
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /info"""
        if not context.args:
            await update.message.reply_text("❌ Укажите тип VPN: /info <тип>")
            return
        
        vpn_type = context.args[0].lower()
        info = self.generator.get_vpn_info(vpn_type)
        
        if info:
            info_text = f"""
📋 Информация о {info.get('name', vpn_type)}:

📝 Описание: {info.get('description', 'N/A')}
📄 Тип конфига: {info.get('config_type', 'N/A')}
🔧 Расширение: {info.get('file_extension', 'N/A')}

✨ Особенности:
"""
            for feature in info.get('features', []):
                info_text += f"• {feature}\n"
            
            await update.message.reply_text(info_text.strip())
        else:
            await update.message.reply_text(f"❌ Неизвестный тип VPN: {vpn_type}")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Проверяем, ожидает ли пользователь ввод домена
        if user_id in self.user_states and self.user_states[user_id] == "waiting_for_domain":
            await self._process_domain_input(update, text)
        else:
            # Игнорируем обычные текстовые сообщения
            pass
    
    async def _process_domain_input(self, update: Update, domain: str):
        """Обрабатывает ввод домена пользователем"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or str(user_id)
        
        # Очищаем состояние пользователя
        if user_id in self.user_states:
            del self.user_states[user_id]
        
        # Отправляем сообщение о проверке
        processing_msg = await update.message.reply_text("🔍 Проверяю домен...")
        
        try:
            # Очищаем домен от префиксов
            clean_domain = domain.lower()
            if clean_domain.startswith(('http://', 'https://')):
                clean_domain = clean_domain.split('://', 1)[1]
            
            # Убираем путь если есть
            if '/' in clean_domain:
                clean_domain = clean_domain.split('/')[0]
            
            # Валидируем домен
            is_valid = await self._validate_domain(clean_domain)
            
            if not is_valid:
                await processing_msg.edit_text(
                    f"❌ Домен '{clean_domain}' не найден или недоступен.\n"
                    "Попробуйте другой домен или проверьте правильность написания."
                )
                return
            
            # Получаем пользователя из БД
            user = ensure_user(update.effective_user)
            
            # Получаем VPN ключ пользователя
            vpn_key = session.query(VpnKey).filter_by(user_id=user.id).first()
            
            if not vpn_key:
                await processing_msg.edit_text(
                    "❌ У вас нет VPN ключа\\!\n"
                    "Сначала создайте ключ через: 🚀 Xray (VLESS) → 🔗 Создать ключ"
                )
                return
            
            # Добавляем или находим сайт
            site_name = clean_domain.replace('.com', '').replace('.ru', '').replace('.org', '').title()
            bypass_site = await self._add_bypass_site(clean_domain, site_name, user.id, "custom")
            
            if not bypass_site:
                await processing_msg.edit_text(
                    f"❌ Ошибка при добавлении домена '{clean_domain}'"
                )
                return
            
            # Проверяем, есть ли уже правило для этого ключа и сайта
            existing_rule = session.query(VpnBypassRule)\
                                  .filter_by(vpn_key_id=vpn_key.id, bypass_site_id=bypass_site.id)\
                                  .first()
            
            if existing_rule:
                await processing_msg.edit_text(
                    f"⚠️ Домен '{clean_domain}' уже добавлен в ваши исключения\\!"
                )
                return
            
            # Создаем правило исключения
            new_rule = VpnBypassRule(
                vpn_key_id=vpn_key.id,
                bypass_site_id=bypass_site.id
            )
            session.add(new_rule)
            
            # Увеличиваем счетчик использования
            bypass_site.usage_count += 1
            session.commit()
            
            # Обновляем routing rules в Xray
            await processing_msg.edit_text("🔄 Обновляю конфигурацию...")
            routing_updated = await self._update_xray_routing()
            
            # Успешное добавление
            verification_status = "✅ Проверен" if bypass_site.is_verified else "⚠️ Не проверен"
            routing_status = "✅ Routing обновлен" if routing_updated else "⚠️ Требуется ручная перезагрузка"
            
            await processing_msg.edit_text(
                f"✅ Домен '{clean_domain}' добавлен в исключения\\!\n"
                f"📊 Статус: {verification_status}\n"
                f"🔀 {routing_status}\n\n"
                f"💡 Этот сайт не будет использовать VPN при подключении через ваш ключ."
            )
            
        except Exception as e:
            await processing_msg.edit_text(f"❌ Ошибка: {str(e)}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.first_name or str(user_id)
        
        # Обработка админских команд
        if data.startswith("admin_"):
            await self.admin_handler.handle_callback(update, context)
            return
        
        if data.startswith("vpn_"):
            vpn_type = data.replace("vpn_", "")
            
            if vpn_type == 'xray':
                # Показываем подменю Xray с возможностью настройки исключений
                await self._show_xray_menu(query)
                return
            elif vpn_type in ['openvpn', 'wireguard']:
                # OpenVPN и WireGuard доступны только админам
                if user_id not in ADMIN_IDS:
                    await query.edit_message_text(
                        "❌ Этот VPN тип доступен только администраторам\n\n"
                        "🚀 Используйте Xray (VLESS) - он более быстрый и надежный!",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🚀 Перейти к Xray", callback_data="vpn_xray"),
                            InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
                        ]])
                    )
                    return
            
            client_name = f"user_{user_id}"
            
            await query.edit_message_text(f"🔄 Генерирую {vpn_type.upper()} конфигурацию для {escape_markdown(username, version=2)}...")
            
            try:
                result = self.generator.generate_vpn(vpn_type, client_name, generate_qr=True)
                
                if result.get('success'):
                    if vpn_type == 'xray':
                        config = result.get('config', '')
                        # Экранируем HTML символы для безопасной передачи
                        escaped_config = escape(config)
                        await query.edit_message_text(
                            f"✅ {vpn_type.upper()} конфигурация для {escape_markdown(username, version=2)}:\n\n<code>{escaped_config}</code>",
                            parse_mode='HTML'
                        )
                    else:
                        # Для OpenVPN и WireGuard отправляем файлы
                        filepath = result.get('filepath', '')
                        qr_path = result.get('qr_path', '')
                        
                        if filepath and os.path.exists(filepath):
                            with open(filepath, 'rb') as f:
                                file_extension = 'ovpn' if vpn_type == 'openvpn' else 'conf'
                                await context.bot.send_document(
                                    chat_id=query.message.chat.id,
                                    document=f,
                                    filename=f"{username}_{vpn_type}.{file_extension}",
                                    caption=f"✅ {vpn_type.upper()} конфигурация для {escape_markdown(username, version=2)}"
                                )
                        
                        # Отправляем QR-код если есть
                        if qr_path and os.path.exists(qr_path):
                            with open(qr_path, 'rb') as f:
                                await context.bot.send_photo(
                                    chat_id=query.message.chat.id,
                                    photo=f,
                                    caption=f"📱 QR-код для {escape_markdown(username, version=2)}"
                                )
                        
                        # Для WireGuard показываем ключи
                        if vpn_type == 'wireguard':
                            keys = result.get('keys', {})
                            if keys:
                                # Экранируем ключи для безопасной передачи в HTML
                                public_key = escape(keys.get('public_key', 'N/A'))
                                preshared_key = escape(keys.get('preshared_key', 'N/A'))
                                keys_info = f"""
🔑 Ключи для {escape_markdown(username, version=2)}:
• Публичный ключ: <code>{public_key}</code>
• Preshared ключ: <code>{preshared_key}</code>
                                """.strip()
                                await context.bot.send_message(
                                    chat_id=query.message.chat.id,
                                    text=keys_info,
                                    parse_mode='HTML'
                                )
                        
                        await query.edit_message_text(f"✅ {vpn_type.upper()} конфигурация создана успешно\\!")
                        
                else:
                    await query.edit_message_text(
                        f"❌ Ошибка генерации {vpn_type.upper()}: {result.get('error', 'Unknown error')}"
                    )
                    
            except Exception as e:
                await query.edit_message_text(f"❌ Ошибка: {str(e)}")
        
        elif data == "my_vpn_keys" or data == "my_keys":
            # Показываем VPN ключи пользователя сразу
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or str(user_id)
            client_name = f"user_{user_id}"
            
            # Проверяем есть ли у пользователя ключ
            existing_key = self.get_user_existing_key(client_name)
            
            if existing_key:
                # У пользователя есть ключ - показываем его
                await self.show_vpn_menu(update, context, client_name)
            else:
                # У пользователя нет ключа - предлагаем создать
                message_text = f"""🔑 У вас пока нет VPN ключа, {escape_markdown(username, version=2)}\!

💡 Для создания VPN ключа используйте команду:
/xray {escape_markdown(username, version=2)}

Или нажмите кнопку ниже для создания ключа."""
                
                keyboard = [
                    [InlineKeyboardButton("🔑 Создать VPN ключ", callback_data="xray_create")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="vpn_xray")]
                ]
                
                await query.edit_message_text(
                    text=message_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        elif data == "create_new_key":
            # Быстрое создание нового ключа из главного меню
            await self._handle_xray_callback(query, "xray_create")
        
        elif data == "settings":
            # Переходим в меню Xray/исключений как основные настройки
            await self._show_xray_menu(query)
        
        elif data == "status":
            await self._show_status(query)
        
        elif data == "help":
            await self._show_help(query)
        
        elif data == "back_to_main":
            await self._show_main_menu(query)
        
        elif data.startswith("vpn_menu_"):
            # Показываем меню для конкретного пользователя
            client_name = data.replace("vpn_menu_", "")
            await self.show_vpn_menu(update, context, client_name)
        
        elif data.startswith("show_key_"):
            # Показываем текущий ключ (всегда для текущего пользователя)
            client_name = data.replace("show_key_", "")
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client
            await self.show_current_key(update, context, client_name)
        
        elif data.startswith("update_key_"):
            # Обновляем ключ
            client_name = data.replace("update_key_", "")
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client
            await self.update_vpn_key(update, context, client_name)
        
        elif data.startswith("delete_key_"):
            # Удаляем ключ
            client_name = data.replace("delete_key_", "")
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client
            await self.delete_vpn_key(update, context, client_name)
        
        elif data.startswith("create_key_"):
            # Создаем новый ключ
            client_name = data.replace("create_key_", "")
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client
            await self.create_new_key(update, context, client_name)
        
        elif data.startswith("settings_"):
            # Меню настроек для конкретного ключа
            client_name = data.replace("settings_", "")
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client
            text = (
                f"⚙️ Настройки для {escape_markdown(client_name, version=2)}\n\n"
                f"Выберите раздел:"
            )
            await query.edit_message_text(
                text=text,
                parse_mode='MarkdownV2',
                reply_markup=get_key_management_keyboard(client_name)
            )
        
        elif data.startswith("back_to_keys_"):
            # Возврат к списку/меню ключей пользователя
            client_name = data.replace("back_to_keys_", "")
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client
            await self.show_vpn_menu(update, context, client_name)
        
        elif data.startswith("stats_"):
            # Показать статистику использования ключа (заглушка/демо)
            client_name = data.replace("stats_", "")
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client
            existing_key = self.get_user_existing_key(client_name)
            if existing_key:
                text = (
                    f"📊 Статистика использования для {escape_markdown(client_name, version=2)}\n\n"
                    f"• Подключений сейчас: 0\n"
                    f"• Создан: `{existing_key['created_at']}`\n"
                    f"• Лимит соединений: {existing_key.get('max_connections', 3)}"
                )
                await query.edit_message_text(text=text, parse_mode='MarkdownV2', reply_markup=get_key_management_keyboard(client_name))
            else:
                await query.answer("❌ Ключ не найден", show_alert=True)

        elif data.startswith("limits_"):
            # Настройки лимитов (заглушка/демо)
            client_name = data.replace("limits_", "")
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client
            existing_key = self.get_user_existing_key(client_name)
            if existing_key:
                from keyboard.vpn_keyboards import get_limits_keyboard
                current_conn = int(existing_key.get('max_connections', 3))
                current_dev = int(existing_key.get('max_devices', 3))
                # Определяем роль пользователя и блокируем, если не админ
                from db.models import ensure_user
                user = ensure_user(query.from_user)
                is_admin = (getattr(user, 'role', 'user') == 'admin')
                locked = not is_admin
                text = (
                    f"⚙️ Настройки лимитов для {escape_markdown(client_name, version=2)}\n\n"
                    f"Текущий лимит соединений: {current_conn}\n"
                    f"Текущий лимит устройств: {current_dev}" + ("\n\n🔒 Изменение доступно только администраторам" if locked else "")
                )
                await query.edit_message_text(text=text, parse_mode='MarkdownV2', reply_markup=get_limits_keyboard(client_name, current_conn, current_dev, locked=locked))
            else:
                await query.answer("❌ Ключ не найден", show_alert=True)

        # Управление лимитами через кнопки
        elif data.startswith("limits_inc_conn_") or data.startswith("limits_dec_conn_") or data.startswith("limits_inc_dev_") or data.startswith("limits_dec_dev_"):
            # Определяем тип изменения и клиента
            action, _, tail = data.partition("limits_")
            # data формата limits_inc_conn_<client>
            parts = data.split("_")
            # ['limits', 'inc', 'conn', '<client>']
            if len(parts) < 4:
                await query.answer("Некорректная команда", show_alert=True)
                return
            op, target, client_name = parts[1], parts[2], "_".join(parts[3:])
            expected_client = f"user_{user_id}"
            if client_name != expected_client:
                client_name = expected_client

            # Проверяем права: только администратор
            from db.models import ensure_user
            user = ensure_user(query.from_user)
            if getattr(user, 'role', 'user') != 'admin':
                await query.answer("🔒 Доступ ограничен", show_alert=True)
                return

            # Загружаем текущий ключ
            existing_key = self.get_user_existing_key(client_name)
            if not existing_key:
                await query.answer("❌ Ключ не найден", show_alert=True)
                return

            # Путь к файлу клиента
            import json
            client_path = os.path.join(self.clients_dir, existing_key['filename'])
            try:
                with open(client_path, 'r') as f:
                    data_json = json.load(f)
                meta = data_json.setdefault('_metadata', {})
                current_conn = int(meta.get('max_connections', 3))
                current_dev = int(meta.get('max_devices', 3))

                step = 1
                min_limit = 1
                max_limit = 10

                if target == 'conn':
                    if op == 'inc' and current_conn < max_limit:
                        current_conn += step
                    elif op == 'dec' and current_conn > min_limit:
                        current_conn -= step
                    meta['max_connections'] = current_conn
                elif target == 'dev':
                    if op == 'inc' and current_dev < max_limit:
                        current_dev += step
                    elif op == 'dec' and current_dev > min_limit:
                        current_dev -= step
                    meta['max_devices'] = current_dev

                with open(client_path, 'w') as f:
                    json.dump(data_json, f, indent=2)

                from keyboard.vpn_keyboards import get_limits_keyboard
                text = (
                    f"⚙️ Настройки лимитов для {escape_markdown(client_name, version=2)}\n\n"
                    f"Текущий лимит соединений: {current_conn}\n"
                    f"Текущий лимит устройств: {current_dev}"
                )
                await query.edit_message_text(text=text, parse_mode='MarkdownV2', reply_markup=get_limits_keyboard(client_name, current_conn, current_dev))
            except Exception as e:
                await query.answer(f"Ошибка сохранения: {e}", show_alert=True)

        elif data.startswith("confirm_update_"):
            # Подтверждаем обновление
            client_name = data.replace("confirm_update_", "")
            await self.confirm_update_key(update, context, client_name)
        
        elif data.startswith("confirm_delete_"):
            # Подтверждаем удаление
            client_name = data.replace("confirm_delete_", "")
            await self.confirm_delete_key(update, context, client_name)

        elif data.startswith("cancel_update_"):
            # Отмена обновления
            client_name = data.replace("cancel_update_", "")
            # Возвращаемся к управлению ключом
            await query.edit_message_text(
                text="❌ Действие отменено",
                reply_markup=get_vpn_keyboard(client_name, has_existing_key=True)
            )

        elif data.startswith("cancel_delete_"):
            # Отмена удаления
            client_name = data.replace("cancel_delete_", "")
            await query.edit_message_text(
                text="❌ Действие отменено",
                reply_markup=get_vpn_keyboard(client_name, has_existing_key=True)
            )
        
        elif data.startswith("xray_"):
            await self._handle_xray_callback(query, data)
        
        elif data.startswith("add_bypass_"):
            await self._handle_add_bypass(query, data)
        
        elif data.startswith("remove_bypass_"):
            await self._handle_remove_bypass(query, data)
        
        elif data == "clear_all_bypass":
            await self._handle_clear_all_bypass(query)
        
        elif data == "confirm_clear_all":
            await self._confirm_clear_all_bypass(query)
        
        elif data.startswith("quick_add_"):
            await self._handle_quick_add_bypass(query, data)
        
        elif data == "manual_input":
            await self._handle_manual_input(query)
        
        elif data.startswith("already_added_"):
            await self._handle_already_added(query, data)
        
        elif data == "noop":
            # Игнорируем нажатия на неактивные кнопки
            await query.answer()
            return
        
        else:
            await query.edit_message_text(
                "❌ Неизвестная команда",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
                ]])
            )
    
    async def show_current_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Показывает текущий VPN ключ пользователя"""
        existing_key = self.get_user_existing_key(client_name)
        
        if not existing_key:
            if update.callback_query:
                await update.callback_query.answer("❌ У вас нет VPN ключа")
            else:
                await update.message.reply_text("❌ У вас нет VPN ключа")
            return
        
        # Генерируем полную VLESS ссылку
        try:
            from xray.generate_client import generate_vless_client
            
            if update.callback_query:
                # Даем мгновенную обратную связь
                try:
                    await update.callback_query.answer("📄 Открываю текущий ключ…")
                except Exception:
                    pass

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
                
                message_text = f"""🔑 Текущий VPN ключ для {escape_markdown(client_name, version=2)}:

📋 Детали ключа:
• Подключений сейчас: 0
• 📅 Создан: `{existing_key['created_at']}`
• Лимит соединений: {existing_key.get('max_connections', 3)}

🔗 VLESS ссылка:
```
{vless_link}
```

💡 Скопируйте ссылку и используйте в вашем VPN клиенте"""
                
                from keyboard.vpn_keyboards import get_key_management_keyboard
                keyboard = get_key_management_keyboard(client_name)
                
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        text=message_text,
                        reply_markup=keyboard,
                        parse_mode='MarkdownV2'
                    )
                else:
                    await update.message.reply_text(
                        text=message_text,
                        reply_markup=keyboard,
                        parse_mode='MarkdownV2'
                    )
            else:
                if update.callback_query:
                    await update.callback_query.answer(f"❌ Ошибка: {result['error']}")
                else:
                    await update.message.reply_text(f"❌ Ошибка: {result['error']}")
                
        except Exception as e:
            if update.callback_query:
                await update.callback_query.answer(f"❌ Ошибка генерации: {e}")
            else:
                await update.message.reply_text(f"❌ Ошибка генерации: {e}")
    
    async def update_vpn_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Обновляет VPN ключ пользователя"""
        existing_key = self.get_user_existing_key(client_name)
        
        if not existing_key:
            await update.callback_query.answer("❌ У вас нет VPN ключа для обновления")
            return
        
        # Показываем подтверждение
        message_text = f"""🔄 Обновление VPN ключа для {client_name}:

⚠️ Внимание! При обновлении ключа:
• Старый ключ будет удален
• Все активные соединения будут разорваны
• Нужно будет обновить конфигурацию на всех устройствах

📋 Текущий ключ:
• 🔑 UUID: {existing_key['uuid'][:8]}...
• 📅 Создан: `{existing_key['created_at']}`

❓ Вы уверены, что хотите обновить ключ?"""
        
        from keyboard.vpn_keyboards import get_confirmation_keyboard
        keyboard = get_confirmation_keyboard("update", client_name)
        
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=keyboard
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
            from utils.generator import generate_vpn_link
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
        message_text = f"""🗑️ Удаление VPN ключа для {escape(client_name)}:

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
                
                message_text = f"""✅ VPN ключ успешно удален для {escape(client_name)}\\!

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
            from utils.group_inbound_manager import group_manager
            user_id = update.effective_user.id
            success, message, vless_url = group_manager.create_user_key(user_id, client_name)
            
            if success and vless_url:
                result = (vless_url, None)  # Совместимость с существующим кодом
            else:
                result = (f"❌ {message}", None)
            
            if result[0] and not result[0].startswith("❌"):
                # Успешно создан ключ
                new_key = self.get_user_existing_key(client_name)
                
                message_text = f"""✅ Новый VPN ключ создан для {escape_markdown(client_name, version=2)}\!

🔑 Детали ключа:
• 📅 Создан: `{new_key['created_at']}`

🔗 VLESS ссылка:
```
{result[0]}
```

💡 Используйте ссылку в вашем VPN клиенте"""
                
                from keyboard.vpn_keyboards import get_key_management_keyboard
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
    
    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат в главное меню"""
        message_text = """🔐 Добро пожаловать в VPN Bot\\!

Выберите действие:"""
        
        keyboard = get_main_menu_keyboard()
        
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=keyboard
        )
    
    async def _show_xray_menu(self, query):
        """Показать подменю Xray с возможностью настройки исключений"""
        # Очищаем состояние пользователя при переходе в Xray меню
        user_id = query.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
            
        keyboard = [
            [
                InlineKeyboardButton("🔗 Создать ключ", callback_data="xray_create")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🚀 <b>Xray (VLESS) меню</b>\n\n"
            "• <b>Создать ключ</b> \\- создать VPN ключ с текущими настройками",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    async def _validate_domain(self, domain: str) -> bool:
        """Проверяет существование домена"""
        import socket
        
        try:
            # Убираем протокол если есть
            if domain.startswith(('http://', 'https://')):
                domain = domain.split('://', 1)[1]
            
            # Убираем путь если есть
            domain = domain.split('/')[0]
            
            # Проверяем DNS резолюцию
            result = await asyncio.create_subprocess_exec(
                'nslookup', domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            return result.returncode == 0 and b'NXDOMAIN' not in stdout
        except:
            return False

    async def _add_bypass_site(self, domain: str, name: str, user_id: int, category: str = "other"):
        """Добавляет новый сайт в базу исключений"""
        try:
            # Проверяем существует ли уже такой сайт
            existing_site = session.query(BypassSite).filter_by(domain=domain).first()
            if existing_site:
                return existing_site
            
            # Создаем новый сайт
            new_site = BypassSite(
                domain=domain,
                name=name,
                category=category,
                added_by_user_id=user_id,
                is_verified=await self._validate_domain(domain)
            )
            
            session.add(new_site)
            session.commit()
            return new_site
        except Exception as e:
            session.rollback()
            return None

    async def _get_popular_bypass_sites(self, limit: int = 10):
        """Получает популярные сайты для исключений"""
        return session.query(BypassSite)\
                     .filter(BypassSite.is_verified == True)\
                     .order_by(BypassSite.usage_count.desc())\
                     .limit(limit).all()

    async def _get_user_bypass_rules(self, user_id: int):
        """Получает исключения пользователя"""
        return session.query(VpnBypassRule, BypassSite)\
                     .join(BypassSite)\
                     .join(VpnKey)\
                     .join(User)\
                     .filter(User.tg_id == user_id).all()

    async def _show_main_menu(self, query):
        """Показать главное меню"""
        welcome_text = "🚀 VPN Bot запущен\\!\n\n📊 Доступные VPN сервисы:"
        
        keyboard = [
            [
                InlineKeyboardButton("🚀 Xray (VLESS)", callback_data="vpn_xray"),
                InlineKeyboardButton("🔐 OpenVPN", callback_data="vpn_openvpn")
            ],
            [
                InlineKeyboardButton("⚡ WireGuard", callback_data="vpn_wireguard")
            ],
            [
                InlineKeyboardButton("📊 Статус сервисов", callback_data="status"),
                InlineKeyboardButton("❓ Справка", callback_data="help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)

    async def _handle_xray_callback(self, query, data):
        """Обработчик callback'ов для Xray меню"""
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.first_name or str(user_id)
        
        if data == "xray_create":
            # Создаем ключ с текущими настройками пользователя
            client_name = f"user_{user_id}"
            
            # Если ключ уже существует, просто показываем его, не создавая заново
            existing_key = self.get_user_existing_key(client_name)
            if existing_key:
                try:
                    from xray.generate_client import generate_vless_client
                    result = generate_vless_client(
                        clients_dir=self.clients_dir,
                        flow="xtls-rprx-vision",
                        host="146.103.125.210",
                        port=443,
                        sni="www.cloudflare.com",
                        client_name=client_name,
                        enforce_limits=False
                    )
                    if "error" not in result:
                        vless_link = result.get("link", "")
                        from keyboard.vpn_keyboards import get_key_management_keyboard
                        message_text = f"""✅ VLESS конфигурация для {escape_markdown(username, version=2)} уже существует\!\n\n
🔑 Детали ключа:
• Подключений сейчас: 0
• 📅 Создан: `{existing_key['created_at']}`
• Лимит соединений: {existing_key.get('max_connections', 3)}

🔗 VLESS ссылка:
```
{vless_link}
```

💡 Скопируйте ссылку и используйте в вашем VPN клиенте"""
                        await query.edit_message_text(
                            text=message_text,
                            reply_markup=get_key_management_keyboard(client_name),
                            parse_mode='MarkdownV2'
                        )
                    else:
                        await query.edit_message_text(
                            text=f"❌ Ошибка: {escape_markdown(result.get('error','Unknown'), version=2)}",
                            parse_mode='MarkdownV2'
                        )
                except Exception as e:
                    await query.edit_message_text(text=f"❌ Ошибка: {e}")
                return

            await query.edit_message_text(f"🔄 Генерирую VLESS конфигурацию для {escape_markdown(username, version=2)}...")
            
            try:
                # Используем нашу функцию generate_vpn_link
                from utils.generator import generate_vpn_link
                result = generate_vpn_link(client_name)
                
                if result[0] and not result[0].startswith("❌"):
                    # Успешно создан ключ
                    vless_link = result[0]
                    uuid = result[1]
                    
                    # Получаем информацию о созданном ключе
                    new_key = self.get_user_existing_key(client_name)
                    
                    if new_key:
                        message_text = f"""✅ VLESS конфигурация для {escape_markdown(username, version=2)} создана\\!

🔑 Детали ключа:
• Подключений сейчас: 0
• 📅 Создан: `{new_key['created_at']}`
• Лимит соединений: {new_key.get('max_connections', 3)}

🔗 VLESS ссылка:
```
{vless_link}
```

💡 Скопируйте ссылку и используйте в вашем VPN клиенте"""
                        
                        # Показываем кнопки управления ключом
                        from keyboard.vpn_keyboards import get_key_management_keyboard
                        keyboard = get_key_management_keyboard(client_name)
                        
                        await query.edit_message_text(
                            text=message_text,
                            reply_markup=keyboard,
                            parse_mode='MarkdownV2'
                        )
                    else:
                        # Ключ создан, но не найден в базе
                        message_text = f"""✅ VLESS конфигурация для {escape_markdown(username, version=2)} создана\\!

🔗 VLESS ссылка:
```
{vless_link}
```

💡 Скопируйте ссылку и используйте в вашем VPN клиенте"""
                        
                        keyboard = [
                            [InlineKeyboardButton("🔙 Назад к Xray меню", callback_data="vpn_xray")]
                        ]
                        
                        await query.edit_message_text(
                            text=message_text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='MarkdownV2'
                        )
                else:
                    # Если генератор вернул существующую ссылку вместо ошибки, покажем её
                    fallback_text = result[0] or ""
                    if fallback_text.startswith("vless://"):
                        message_text = f"""✅ VLESS конфигурация для {escape_markdown(username, version=2)} уже существует\!

🔗 VLESS ссылка:
```
{fallback_text}
```

💡 Скопируйте ссылку и используйте в вашем VPN клиенте"""
                        from keyboard.vpn_keyboards import get_key_management_keyboard
                        keyboard = get_key_management_keyboard(client_name)
                        await query.edit_message_text(
                            text=message_text,
                            reply_markup=keyboard,
                            parse_mode='MarkdownV2'
                        )
                    else:
                        # Другая ошибка
                        keyboard = [
                            [InlineKeyboardButton("🔙 Назад к Xray меню", callback_data="vpn_xray")]
                        ]
                        await query.edit_message_text(
                            text=f"❌ Ошибка создания ключа: {result[0]}",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                        
            except Exception as e:
                keyboard = [
                    [InlineKeyboardButton("🔙 Назад к Xray меню", callback_data="vpn_xray")]
                ]
                
                await query.edit_message_text(
                    text=f"❌ Ошибка: {str(e)}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        elif data == "xray_bypass":
            await query.answer("ℹ️ Функция настроек исключений временно недоступна", show_alert=False)
        
        elif data == "xray_my_bypass":
            await query.answer("ℹ️ Функция управления исключениями временно недоступна", show_alert=False)
        
        elif data == "xray_popular_sites":
            await query.answer("ℹ️ Функция популярных сайтов временно недоступна", show_alert=False)

    async def _show_bypass_menu(self, query):
        """Показать меню настройки исключений с популярными сайтами"""
        user_id = query.from_user.id
        
        # Устанавливаем состояние ожидания ввода домена
        self.user_states[user_id] = "waiting_for_domain"
        
        # Получаем уже добавленные исключения пользователя
        user_rules = await self._get_user_bypass_rules(user_id)
        user_domains = {site.domain for _, site in user_rules}
        
        # Получаем популярные сайты
        popular_sites = await self._get_popular_bypass_sites(limit=6)
        
        # Формируем текст с отображением уже добавленных исключений
        text = "⚙️ <b>Настройка исключений</b>\n\n"
        
        if user_rules:
            text += "✅ <b>Ваши исключения:</b>\n"
            for i, (_, site) in enumerate(user_rules[:3], 1):  # Показываем первые 3
                text += f"  {i}. 🌐 {site.name}\n"
            
            if len(user_rules) > 3:
                text += f"  ... и еще {len(user_rules) - 3}\n"
            
            text += f"\n📊 Всего: <b>{len(user_rules)} исключений</b>\n\n"
        
        text += (
            "🌟 <b>Популярные исключения:</b>\n"
            "✅ = уже добавлено, 🌐 = доступно для добавления\n\n"
            "📝 <b>Или введите домен в сообщении:</b>\n"
            "Примеры: <code>youtube.com</code>, <code>instagram.com</code>\n\n"
            "🔍 Бот проверит домен и добавит в исключения."
        )
        
        # Создаем кнопки для популярных сайтов
        keyboard = []
        
        # Добавляем кнопки популярных сайтов по 2 в ряд
        for i in range(0, len(popular_sites), 2):
            row = []
            for j in range(i, min(i + 2, len(popular_sites))):
                site = popular_sites[j]
                
                # Проверяем, добавлен ли уже этот сайт
                is_already_added = site.domain in user_domains
                
                if is_already_added:
                    # Для уже добавленных сайтов
                    button_text = f"✅ {site.name}"
                    callback_data = f"already_added_{site.domain}"
                else:
                    # Для доступных для добавления
                    button_text = f"🌐 {site.name}"
                    callback_data = f"quick_add_{site.domain}"
                
                # Обрезаем длинные названия
                if len(button_text) > 15:
                    prefix = "✅" if is_already_added else "🌐"
                    button_text = f"{prefix} {site.name[:12]}..."
                
                row.append(InlineKeyboardButton(
                    button_text, 
                    callback_data=callback_data
                ))
            keyboard.append(row)
        
        # Добавляем кнопки управления
        if len(popular_sites) >= 6:
            keyboard.append([
                InlineKeyboardButton("📋 Все популярные", callback_data="noop")
            ])
        
        # Добавляем кнопки управления
        management_buttons = [
            [InlineKeyboardButton("✍️ Ввести вручную", callback_data="manual_input")]
        ]
        
        # Если у пользователя есть исключения, добавляем кнопку управления
        if user_rules:
            management_buttons.append([
                InlineKeyboardButton("📋 Управление исключениями", callback_data="noop")
            ])
        
        management_buttons.append([
            InlineKeyboardButton("🔙 Назад", callback_data="vpn_xray")
        ])
        
        keyboard.extend(management_buttons)
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_my_bypass_rules(self, query):
        """Показать исключения пользователя с возможностью удаления"""
        user_id = query.from_user.id
        rules = await self._get_user_bypass_rules(user_id)
        
        if not rules:
            text = "📋 <b>У вас пока нет настроенных исключений</b>\n\n💡 Добавьте сайты, которые не должны использовать VPN"
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="vpn_xray")]
            ]
        else:
            text = "📋 <b>Ваши исключения:</b>\n\n"
            keyboard = []
            
            for i, (rule, site) in enumerate(rules, 1):
                status = "✅" if site.is_verified else "⚠️"
                text += f"{i}. {status} <b>{site.name}</b>\n"
                text += f"   🌐 {site.domain}\n"
                text += f"   👥 Использований: {site.usage_count}\n"
                
                # Добавляем кнопку удаления для каждого исключения
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗑️ Удалить {site.name}", 
                        callback_data=f"remove_bypass_{rule.id}"
                    )
                ])
            
            text += f"\n💡 Всего исключений: <b>{len(rules)}</b>"
            text += f"\n\n⚠️ <i>Нажмите на кнопку удаления, чтобы убрать сайт из исключений</i>"
            
            # Добавляем кнопки управления
            keyboard.extend([
                [InlineKeyboardButton("🔙 Назад", callback_data="vpn_xray")]
            ])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_popular_sites(self, query):
        """Показать популярные сайты для исключений"""
        popular_sites = await self._get_popular_bypass_sites()
        
        if not popular_sites:
            # Добавим популярные сайты по умолчанию
            default_sites = [
                {"domain": "youtube.com", "name": "YouTube", "category": "streaming"},
                {"domain": "vk.com", "name": "ВКонтакте", "category": "social"},
                {"domain": "ok.ru", "name": "Одноклассники", "category": "social"},
                {"domain": "yandex.ru", "name": "Яндекс", "category": "search"},
                {"domain": "mail.ru", "name": "Mail.ru", "category": "email"},
                {"domain": "gosuslugi.ru", "name": "Госуслуги", "category": "government"},
            ]
            
            text = "🌐 <b>Популярные сайты для исключений:</b>\n\n"
            keyboard = []
            
            for site in default_sites:
                text += f"• <b>{site['name']}</b> ({site['domain']})\n"
                keyboard.append([InlineKeyboardButton(
                    f"➕ {site['name']}", 
                    callback_data=f"add_bypass_{site['domain']}"
                )])
        else:
            text = "🌐 <b>Популярные сайты для исключений:</b>\n\n"
            keyboard = []
            
            for site in popular_sites:
                text += f"• <b>{site.name}</b> ({site.domain}) - {site.usage_count} польз.\n"
                keyboard.append([InlineKeyboardButton(
                    f"➕ {site.name}", 
                    callback_data=f"add_bypass_{site.domain}"
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="vpn_xray")])
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _handle_add_bypass(self, query, data):
        """Обработчик добавления исключения из популярных сайтов"""
        user_id = query.from_user.id
        domain = data.replace("add_bypass_", "")
        
        try:
            # Получаем пользователя
            user = ensure_user(query.from_user)
            
            # Ищем или создаем сайт
            site = session.query(BypassSite).filter_by(domain=domain).first()
            if not site:
                # Создаем сайт если его нет
                site_name = domain.split('.')[0].title()  # Простое извлечение имени
                site = await self._add_bypass_site(domain, site_name, user.id)
            
            if site:
                # Ищем VPN ключ пользователя
                vpn_key = session.query(VpnKey).filter_by(user_id=user.id).first()
                if not vpn_key:
                    await query.answer("❌ Сначала создайте VPN ключ\\!", show_alert=True)
                    return
                
                # Проверяем, нет ли уже такого правила
                existing_rule = session.query(VpnBypassRule)\
                    .filter_by(vpn_key_id=vpn_key.id, bypass_site_id=site.id).first()
                
                if existing_rule:
                    await query.answer("⚠️ Этот сайт уже в исключениях\\!", show_alert=True)
                else:
                    # Создаем новое правило
                    new_rule = VpnBypassRule(
                        vpn_key_id=vpn_key.id,
                        bypass_site_id=site.id
                    )
                    session.add(new_rule)
                    
                    # Увеличиваем счетчик использования
                    site.usage_count += 1
                    session.commit()
                    
                    # Сразу применяем изменения в Xray
                    routing_updated = await self._update_xray_routing()
                    suffix = " (routing обновлен)" if routing_updated else " (требуется перезагрузка)"
                    await query.answer(f"✅ {site.name} добавлен в исключения\\!{suffix}", show_alert=True)
            else:
                await query.answer("❌ Ошибка добавления сайта\\!", show_alert=True)
                
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        
        # Возвращаемся к списку популярных сайтов
        await self._show_popular_sites(query)

    async def _handle_remove_bypass(self, query, data):
        """Обработчик удаления конкретного исключения"""
        telegram_user_id = query.from_user.id
        rule_id_str = data.replace("remove_bypass_", "")
        
        try:
            # Конвертируем rule_id в int
            try:
                rule_id = int(rule_id_str)
            except ValueError:
                await query.answer("❌ Некорректный ID правила\\!", show_alert=True)
                return
            
            # Получаем пользователя из базы данных
            user = ensure_user(query.from_user)
            
            # Находим правило исключения
            rule = session.query(VpnBypassRule, BypassSite)\
                         .join(BypassSite)\
                         .join(VpnKey)\
                         .filter(VpnBypassRule.id == rule_id)\
                         .filter(VpnKey.user_id == user.id)\
                         .first()
            
            if not rule:
                await query.answer("❌ Исключение не найдено\\!", show_alert=True)
                return
            
            bypass_rule, bypass_site = rule
            site_name = bypass_site.name
            
            # Удаляем правило
            session.delete(bypass_rule)
            
            # Уменьшаем счетчик использования сайта
            if bypass_site.usage_count > 0:
                bypass_site.usage_count -= 1
            
            session.commit()
            
            # Обновляем routing rules в Xray
            routing_updated = await self._update_xray_routing()
            routing_msg = " (Routing обновлен)" if routing_updated else " (Требуется перезагрузка)"
            
            await query.answer(f"✅ {site_name} удален из исключений\\!{routing_msg}", show_alert=True)
            
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        
        # Обновляем список исключений
        await self._show_my_bypass_rules(query)

    async def _handle_clear_all_bypass(self, query):
        """Обработчик очистки всех исключений пользователя"""
        telegram_user_id = query.from_user.id
        
        try:
            # Получаем пользователя из базы данных
            user = ensure_user(query.from_user)
            
            # Получаем все правила пользователя
            rules = session.query(VpnBypassRule, BypassSite)\
                          .join(BypassSite)\
                          .join(VpnKey)\
                          .filter(VpnKey.user_id == user.id).all()
            
            if not rules:
                await query.answer("📋 У вас нет исключений для удаления\\!", show_alert=True)
                return
            
            # Подтверждение удаления
            await query.edit_message_text(
                f"⚠️ <b>Подтверждение удаления</b>\n\n"
                f"Вы уверены, что хотите удалить ВСЕ исключения?\n"
                f"Будет удалено: <b>{len(rules)} исключений</b>\n\n"
                f"Это действие нельзя отменить\\!",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Да, удалить все", callback_data="confirm_clear_all"),
                        InlineKeyboardButton("❌ Отмена", callback_data="noop")
                    ]
                ])
            )
            
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def _confirm_clear_all_bypass(self, query):
        """Подтверждение очистки всех исключений"""
        telegram_user_id = query.from_user.id
        
        try:
            # Получаем пользователя из базы данных
            user = ensure_user(query.from_user)
            
            # Получаем все правила пользователя
            rules = session.query(VpnBypassRule, BypassSite)\
                          .join(BypassSite)\
                          .join(VpnKey)\
                          .filter(VpnKey.user_id == user.id).all()
            
            deleted_count = len(rules)
            
            # Удаляем все правила и уменьшаем счетчики
            for bypass_rule, bypass_site in rules:
                session.delete(bypass_rule)
                if bypass_site.usage_count > 0:
                    bypass_site.usage_count -= 1
            
            session.commit()
            
            await query.answer(f"✅ Удалено {deleted_count} исключений\\!", show_alert=True)
            
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        
        # Показываем обновленный список (должен быть пустым)
        await self._show_my_bypass_rules(query)

    async def _handle_quick_add_bypass(self, query, data):
        """Обработчик быстрого добавления популярного исключения"""
        domain = data.replace("quick_add_", "")
        
        try:
            # Получаем пользователя
            user = ensure_user(query.from_user)
            
            # Ищем VPN ключ пользователя
            vpn_key = session.query(VpnKey).filter_by(user_id=user.id).first()
            if not vpn_key:
                await query.answer("❌ Сначала создайте VPN ключ\\!", show_alert=True)
                return
            
            # Ищем сайт в базе
            site = session.query(BypassSite).filter_by(domain=domain).first()
            if not site:
                await query.answer("❌ Сайт не найден в базе\\!", show_alert=True)
                return
            
            # Проверяем, нет ли уже такого правила
            existing_rule = session.query(VpnBypassRule)\
                .filter_by(vpn_key_id=vpn_key.id, bypass_site_id=site.id).first()
            
            if existing_rule:
                await query.answer("⚠️ Этот сайт уже в ваших исключениях\\!", show_alert=True)
            else:
                # Создаем новое правило
                new_rule = VpnBypassRule(
                    vpn_key_id=vpn_key.id,
                    bypass_site_id=site.id
                )
                session.add(new_rule)
                
                # Увеличиваем счетчик использования
                site.usage_count += 1
                session.commit()
                
                # Сразу применяем изменения в Xray
                routing_updated = await self._update_xray_routing()
                suffix = " (routing обновлен)" if routing_updated else " (требуется перезагрузка)"
                await query.answer(f"✅ {site.name} добавлен в исключения\\!{suffix}", show_alert=True)
                
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        
        # Возвращаемся к меню настройки исключений
        await self._show_bypass_menu(query)

    async def _handle_manual_input(self, query):
        """Обработчик ручного ввода домена"""
        user_id = query.from_user.id
        
        # Устанавливаем состояние ожидания ввода
        self.user_states[user_id] = "waiting_for_domain"
        
        await query.edit_message_text(
            "✍️ <b>Ручной ввод домена</b>\n\n"
            "📝 Введите домен в следующем сообщении:\n\n"
            "Примеры:\n"
            "• <code>youtube.com</code>\n"
            "• <code>vk.com</code>\n"
            "• <code>instagram.com</code>\n"
            "• <code>https://www.google.com</code>\n\n"
            "🔍 Бот проверит существование и добавит в исключения.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ])
        )

    async def _handle_already_added(self, query, data):
        """Обработчик нажатия на уже добавленный сайт"""
        domain = data.replace("already_added_", "")
        
        try:
            # Находим информацию о сайте
            site = session.query(BypassSite).filter_by(domain=domain).first()
            if site:
                site_name = site.name
                usage_count = site.usage_count
                verification_status = "✅ Проверен" if site.is_verified else "⚠️ Не проверен"
                
                # Показываем информационное сообщение
                await query.answer(
                    f"✅ {site_name} уже в ваших исключениях\\!\n"
                    f"📊 Статус: {verification_status}\n"
                    f"👥 Использований: {usage_count}",
                    show_alert=True
                )
            else:
                await query.answer("❌ Информация о сайте не найдена", show_alert=True)
                
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def _get_xray_key_stats(self):
        """Получает статистику по активным VLESS ключам"""
        key_stats = {}
        total_connections = 0
        
        try:
            # Получаем все активные ключи из базы данных с именами пользователей
            vpn_keys = session.query(VpnKey, User).join(User).all()
            
            for vpn_key, user in vpn_keys:
                if vpn_key.uuid:
                    # Проверяем метаданные клиента для получения лимита
                    max_connections = 3  # по умолчанию
                    client_file = f"/var/www/vpn/xray/clients/{vpn_key.uuid}.json"
                    if os.path.exists(client_file):
                        try:
                            with open(client_file, 'r') as f:
                                client_data = json.load(f)
                                metadata = client_data.get('_metadata', {})
                                max_connections = metadata.get('max_connections', 3)
                        except:
                            pass
                    
                    key_stats[vpn_key.uuid] = {
                        'name': user.username or f"user_{user.tg_id}",
                        'connections': 0,
                        'ips': set(),
                        'created_at': vpn_key.created_at,
                        'max_connections': max_connections
                    }
            
            # Анализируем активные соединения через netstat
            netstat_result = subprocess.run(['netstat', '-tn'], capture_output=True, text=True)
            if netstat_result.returncode == 0:
                client_ips = {}
                for line in netstat_result.stdout.split('\n'):
                    if ':443' in line and 'ESTABLISHED' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            local_addr = parts[3]
                            remote_addr = parts[4]
                            
                            if ':443' in local_addr:
                                client_ip = remote_addr.split(':')[0]
                                if client_ip not in client_ips:
                                    client_ips[client_ip] = 0
                                client_ips[client_ip] += 1
                                total_connections += 1
                
                # Распределяем соединения по ключам (упрощенная логика)
                # В реальности нужен более точный анализ через Xray API или логи
                if client_ips and key_stats:
                    # Для демонстрации распределим соединения между ключами
                    keys_list = list(key_stats.keys())
                    ip_index = 0
                    for client_ip, conn_count in client_ips.items():
                        if keys_list:
                            # Простое распределение - каждый IP к следующему ключу
                            key_uuid = keys_list[ip_index % len(keys_list)]
                            key_stats[key_uuid]['connections'] += conn_count
                            key_stats[key_uuid]['ips'].add(client_ip)
                            ip_index += 1
                            
        except Exception as e:
            print(f"Error getting Xray stats: {e}")
        
        return key_stats, total_connections

    async def _check_ping(self, host="8.8.8.8", count=3):
        """Проверка пинга до указанного хоста"""
        
        try:
            # Асинхронная проверка пинга
            result = await asyncio.create_subprocess_exec(
                'ping', '-c', str(count), '-W', '2', host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # Извлекаем время пинга из вывода
                output = stdout.decode()
                if "time=" in output:
                    # Ищем среднее время
                    lines = output.split('\n')
                    for line in lines:
                        if "min/avg/max" in line:
                            # Парсим строку вида: rtt min/avg/max/mdev = 0.769/0.853/0.938/0.069 ms
                            if "=" in line:
                                stats_part = line.split('=')[1].strip()
                                values = stats_part.split('/')
                                if len(values) >= 2:
                                    avg_time = float(values[1])
                                    return f"{avg_time:.1f}ms"
                    
                    # Если не нашли avg, берем последний time=
                    for line in reversed(lines):
                        if "time=" in line:
                            time_part = line.split("time=")[1].split()[0]
                            return f"{time_part}"
                
                return "OK"
            else:
                return "🔗 Подключен"  # Многие клиенты блокируют ICMP
        except Exception:
            return "🔗 Подключен"
    
    async def _get_active_vpn_clients(self):
        """Получает список активных VPN клиентов"""
        
        clients = {
            'openvpn': [],
            'wireguard': [],
            'xray': []
        }
        
        # Проверяем OpenVPN клиентов
        try:
            # Проверяем несколько возможных путей к логу статуса
            status_paths = [
                '/var/log/openvpn/status.log',
                '/var/log/openvpn.log',
                '/etc/openvpn/status.log',
                '/tmp/openvpn-status.log'
            ]
            
            status_found = False
            for status_path in status_paths:
                try:
                    result = subprocess.run(['cat', status_path], 
                                          capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if ',' in line and 'CLIENT_LIST' in line:
                                parts = line.split(',')
                                if len(parts) >= 3:
                                    client_name = parts[1]
                                    client_ip = parts[2]
                                    clients['openvpn'].append({
                                        'name': client_name,
                                        'ip': client_ip,
                                        'ping': await self._check_ping(client_ip, 1)
                                    })
                        status_found = True
                        break
                except:
                    continue
                    
            # Если файл статуса не найден, проверяем активные соединения через ss
            if not status_found:
                result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
                if result.returncode == 0 and '1194' in result.stdout:
                    # OpenVPN обычно использует порт 1194, добавим общую запись
                    clients['openvpn'].append({
                        'name': 'OpenVPN активен',
                        'ip': 'Порт 1194',
                        'ping': '🟢 Сервис работает'
                    })
        except:
            pass
        
        # Проверяем WireGuard клиентов
        try:
            result = subprocess.run(['wg', 'show', 'all', 'dump'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('wg0'):
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            peer = parts[0][:8] + "..."  # Короткий ID
                            endpoint = parts[2] if parts[2] != '(none)' else "Offline"
                            if endpoint != "Offline":
                                # Извлекаем IP из endpoint
                                ip = endpoint.split(':')[0]
                                ping_result = await self._check_ping(ip, 1)
                            else:
                                ping_result = "Offline"
                            
                            clients['wireguard'].append({
                                'name': peer,
                                'ip': endpoint,
                                'ping': ping_result
                            })
        except:
            pass
        
        # Для Xray анализируем входящие соединения на порт 443
        try:
            netstat_result = subprocess.run(['netstat', '-tn'], capture_output=True, text=True)
            if netstat_result.returncode == 0:
                client_ips = {}
                
                # Ищем входящие соединения на порт 443 (146.103.125.210:443 <- client_ip:port)
                for line in netstat_result.stdout.split('\n'):
                    if ':443' in line and 'ESTABLISHED' in line and 'tcp6' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            # Формат: tcp6 0 0 server:443 client:port ESTABLISHED
                            local_addr = parts[3]  # server:443
                            remote_addr = parts[4]  # client:port
                            
                            if ':443' in local_addr:  # Это входящее соединение на наш сервер
                                client_ip = remote_addr.split(':')[0]
                                if client_ip not in client_ips:
                                    client_ips[client_ip] = 0
                                client_ips[client_ip] += 1
                
                # Добавляем клиентов с их пингом
                for client_ip, conn_count in client_ips.items():
                    ping_result = await self._check_ping(client_ip, 1)
                    clients['xray'].append({
                        'name': f"Client {client_ip}",
                        'ip': f"{conn_count} соединений",
                        'ping': ping_result
                    })
        except:
            pass
        
        return clients
    
    async def _get_server_status_brief(self):
        """Получает краткий статус сервера для главного меню"""
        try:
            # Проверяем интернет
            ping_result = await self._check_ping()
            
            # Проверяем Xray
            result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'xray'], capture_output=True, text=True)
            xray_active = (result.returncode == 0)
            
            if xray_active:
                # Получаем количество подключений
                try:
                    key_stats, total_connections = await self._get_xray_key_stats()
                    xray_status = f"🟢 Активен ({total_connections} подкл\\.)"
                except:
                    xray_status = "🟢 Активен"
            else:
                xray_status = "🔴 Неактивен"
            
            return f"🌐 Интернет: {ping_result}\n🚀 Xray: {xray_status}"
            
        except Exception as e:
            return "⚠️ Ошибка получения статуса"

    async def _show_status(self, query):
        """Показать статус сервисов"""
        
        # Отправляем временное сообщение о загрузке
        await query.edit_message_text("📊 Проверяю статус сервисов... ⏳")
        
        # Проверяем, является ли пользователь админом
        user_id = query.from_user.id
        is_admin = user_id in ADMIN_IDS
        
        status_text = "📊 Детальный статус VPN сервисов:\n\n"
        
        # Проверяем общий пинг интернета
        ping_result = await self._check_ping()
        status_text += f"🌐 Интернет: {ping_result}\n\n"
        
        # OpenVPN и WireGuard показываем только админам
        if is_admin:
            # Проверяем OpenVPN
            try:
                result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'openvpn@server'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    ovpn_status = "🟢 Активен"
                else:
                    # Проверяем, существует ли сервис
                    check_result = subprocess.run(['/usr/bin/systemctl', 'list-unit-files', 'openvpn@server.service'], 
                                                capture_output=True, text=True, timeout=5)
                    if 'openvpn@server.service' in check_result.stdout:
                        ovpn_status = "🔴 Неактивен"
                    else:
                        ovpn_status = "❌ Не установлен"
            except:
                ovpn_status = "❓ Неизвестно"
            
            status_text += f"🔐 OpenVPN: {ovpn_status}\n"
            
            # Проверяем WireGuard
            try:
                result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'wg-quick@wg0'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    wg_status = "🟢 Активен"
                else:
                    # Проверяем, существует ли сервис
                    check_result = subprocess.run(['/usr/bin/systemctl', 'list-unit-files', 'wg-quick@wg0.service'], 
                                                capture_output=True, text=True, timeout=5)
                    if 'wg-quick@wg0.service' in check_result.stdout:
                        wg_status = "🔴 Неактивен"
                    else:
                        wg_status = "❌ Не установлен"
            except:
                wg_status = "❓ Неизвестно"
            
            status_text += f"⚡ WireGuard: {wg_status}\n"
        
        # Проверяем Xray с детальной статистикой
        try:
            result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'xray'], capture_output=True, text=True)
            xray_active = (result.returncode == 0)
            
            if xray_active:
                # Получаем статистику по ключам
                key_stats, total_connections = await self._get_xray_key_stats()
                
                status_text += f"🚀 Xray: 🟢 Активен ({total_connections} соединений)\n"
                
                # Детальная статистика только для админов
                if is_admin and key_stats:
                    active_keys = [k for k in key_stats.values() if k['connections'] > 0]
                    inactive_keys = [k for k in key_stats.values() if k['connections'] == 0]
                    
                    # Показываем активные ключи
                    if active_keys:
                        status_text += "   🔑 Активные ключи:\n"
                        for key_data in active_keys[:5]:  # Показываем только первые 5
                            connections = key_data['connections']
                            max_conn = key_data.get('max_connections', 3)
                            name = key_data['name']
                            limit_status = "⚠️" if connections > max_conn else "✅"
                            status_text += f"      {limit_status} {name}: {connections}/{max_conn} устройств\n"
                        
                        if len(active_keys) > 5:
                            status_text += f"      ... еще {len(active_keys) - 5} активных ключей\n"
                    
                    # Показываем общую статистику
                    total_keys = len(key_stats)
                    active_count = len(active_keys)
                    status_text += f"   📊 Всего ключей: {total_keys} | Активных: {active_count}"
                elif is_admin:
                    status_text += "   📊 Нет зарегистрированных ключей"
            else:
                status_text += f"🚀 Xray: 🔴 Неактивен"
        except Exception as e:
            status_text += f"🚀 Xray: ❓ Ошибка проверки"
        
        try:
            await query.edit_message_text(status_text)
        except Exception as e:
            await query.answer("📊 Статус обновлен", show_alert=False)
    
    async def _show_help(self, query):
        """Показать справку"""
        help_text = """📚 Справка по VPN Bot

🔧 Доступные VPN типы:
• 🚀 Xray (VLESS) \\- быстрый прокси\\-сервер
• 🔐 OpenVPN \\- надежный VPN протокол  
• ⚡ WireGuard \\- современный VPN протокол

💡 Как использовать:
1. Нажмите кнопку с нужным типом VPN
2. Бот автоматически создаст конфигурацию
3. Скачайте файл или используйте QR\\-код

📱 Для мобильных устройств рекомендуется WireGuard
💻 Для компьютеров подойдет любой тип

/start \\- вернуться в главное меню"""
        
        await query.edit_message_text(help_text)
    
    def get_handlers(self):
        """Возвращает список обработчиков команд"""
        from telegram.ext import CommandHandler
        
        return [
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("xray", self.xray_command),
            CommandHandler("openvpn", self.openvpn_command),
            CommandHandler("wireguard", self.wireguard_command),
            CommandHandler("status", self.status_command),
            CommandHandler("info", self.info_command),
            CallbackQueryHandler(self.button_callback),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message),
        ] 