from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
import sys, os

# Добавляем путь к проекту
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import ADMIN_IDS
from keyboard.vpn_keyboards import (
    get_admin_keyboard, get_admin_users_keyboard, 
    get_user_admin_keyboard, get_main_menu_keyboard,
    get_admin_xray_keyboard
)
from db.models import session, User, ensure_user
import json
import os
from datetime import datetime

# Импортируем функции управления лимитами
sys.path.append('/var/www/vpn')
from manage_user_limits import (
    get_user_keys, analyze_user_usage, enforce_user_limits,
    create_user_key, remove_user_key, count_active_connections,
    reset_user_limits, update_user_limits, reset_and_update_user_limits,
    reload_xray_config, cleanup_expired_keys, show_key_pools,
    CLIENTS_DIR
)

class AdminHandler:
    """Обработчик админских команд"""
    
    def __init__(self):
        self.clients_dir = CLIENTS_DIR
    
    async def safe_edit_message(self, query, text, parse_mode='MarkdownV2', reply_markup=None):
        """Безопасное редактирование сообщения с обработкой ошибок"""
        try:
            await query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except Exception as e:
            # Если не удалось отредактировать сообщение (например, содержимое не изменилось)
            await query.answer("✅ Обновлено", show_alert=False)
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь админом"""
        return user_id in ADMIN_IDS
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает админское меню"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        text = (
            "🛡️ **Админ панель**\n\n"
            "Добро пожаловать в панель администратора\\!\n"
            "Выберите нужное действие:"
        )
        
        await query.edit_message_text(
            text=text,
            parse_mode='MarkdownV2',
            reply_markup=get_admin_keyboard()
        )
    
    async def show_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику системы"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            # Получаем данные
            users = get_user_keys()
            connections = count_active_connections()
            violations = analyze_user_usage()
            
            # Статистика
            total_users = len(users)
            total_keys = sum(len(user_keys) for user_keys in users.values())
            active_connections = len(connections)
            violations_count = len(violations) if violations else 0
            
            # Пользователи с нарушениями
            violators = []
            for client_name, keys in users.items():
                if len(keys) > 1:
                    violators.append(f"• {escape_markdown(client_name, version=2)}: {len(keys)} ключей")
            
            text = (
                "📊 **Статистика системы**\n\n"
                f"👥 Всего пользователей: `{total_users}`\n"
                f"🔑 Всего ключей: `{total_keys}`\n"
                f"🌐 Активных соединений: `{active_connections}`\n"
                f"⚠️ Нарушений лимитов: `{violations_count}`\n\n"
            )
            
            if violators:
                text += "🚨 **Пользователи с превышением лимитов:**\n"
                text += "\n".join(violators[:10])  # Показываем первых 10
                if len(violators) > 10:
                    text += f"\n\\.\\.\\. и еще {len(violators) - 10} пользователей"
            else:
                text += "✅ Все пользователи соблюдают лимиты"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
                [InlineKeyboardButton("🔙 Админ меню", callback_data="admin_menu")]
            ]
            
            await query.edit_message_text(
                text=text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.answer(f"❌ Ошибка получения статистики: {str(e)}", show_alert=True)
    
    async def show_users_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает управление пользователями"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            users = get_user_keys()
            total_users = len(users)
            
            text = (
                "👥 **Управление пользователями**\n\n"
                f"Всего пользователей: `{total_users}`\n\n"
                "Выберите действие:"
            )
            
            await query.edit_message_text(
                text=text,
                parse_mode='MarkdownV2',
                reply_markup=get_admin_users_keyboard()
            )
            
        except Exception as e:
            await query.answer(f"❌ Ошибка загрузки пользователей: {str(e)}", show_alert=True)
    
    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
        """Показывает список пользователей"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            users = get_user_keys()
            users_list = list(users.items())
            
            users_per_page = 5
            start_idx = page * users_per_page
            end_idx = start_idx + users_per_page
            page_users = users_list[start_idx:end_idx]
            
            if not page_users:
                text = "👥 **Список пользователей**\n\nПользователи не найдены\\."
                keyboard = [[InlineKeyboardButton("🔙 К управлению", callback_data="admin_users")]]
            else:
                text = f"👥 **Список пользователей** \\(страница {page + 1}\\)\n\n"
                
                keyboard = []
                for client_name, keys in page_users:
                    keys_count = len(keys)
                    status = "⚠️" if keys_count > 1 else "✅"
                    button_text = f"{status} {client_name} ({keys_count})"
                    keyboard.append([
                        InlineKeyboardButton(button_text, callback_data=f"admin_user_{client_name}")
                    ])
                
                # Навигация
                nav_buttons = []
                if page > 0:
                    nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"admin_list_users_{page-1}"))
                if end_idx < len(users_list):
                    nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"admin_list_users_{page+1}"))
                
                if nav_buttons:
                    keyboard.append(nav_buttons)
                
                keyboard.append([InlineKeyboardButton("🔙 К управлению", callback_data="admin_users")])
            
            await query.edit_message_text(
                text=text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.answer(f"❌ Ошибка загрузки списка: {str(e)}", show_alert=True)
    
    async def show_user_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Показывает детали пользователя"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            users = get_user_keys()
            
            if client_name not in users:
                await query.answer("❌ Пользователь не найден", show_alert=True)
                return
            
            user_keys = users[client_name]
            keys_count = len(user_keys)
            
            text = (
                f"👤 **Пользователь:** `{escape_markdown(client_name, version=2)}`\n\n"
                f"🔑 Количество ключей: `{keys_count}`\n"
                f"📊 Статус: {'⚠️ Превышен лимит' if keys_count > 1 else '✅ В норме'}\n\n"
            )
            
            if user_keys:
                text += "**Ключи пользователя:**\n"
                for i, key in enumerate(user_keys[:5], 1):  # Показываем первые 5
                    created_date = key.get('created_at', 'unknown')
                    if created_date != 'unknown':
                        try:
                            # Пытаемся распарсить дату
                            if isinstance(created_date, str):
                                created_date = created_date.split('.')[0]  # Убираем микросекунды
                        except Exception:
                            # Если не удается распарсить дату, оставляем как есть
                            pass
                    
                    text += f"{i}\\. `{key['uuid'][:8]}...` \\({escape_markdown(str(created_date), version=2)}\\)\n"
                
                if len(user_keys) > 5:
                    text += f"\\.\\.\\. и еще {len(user_keys) - 5} ключей\n"
            
            await query.edit_message_text(
                text=text,
                parse_mode='MarkdownV2',
                reply_markup=get_user_admin_keyboard(client_name)
            )
            
        except Exception as e:
            await query.answer(f"❌ Ошибка загрузки пользователя: {str(e)}", show_alert=True)
    
    async def reset_user_limits(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Сбрасывает лимиты пользователя"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            users = get_user_keys()
            
            if client_name not in users:
                await query.answer("❌ Пользователь не найден", show_alert=True)
                return
            
            user_keys = users[client_name]
            
            if len(user_keys) <= 1:
                await query.answer("✅ У пользователя только 1 ключ, сброс не требуется", show_alert=True)
                return
            
            # Сортируем по времени создания и оставляем только самый новый
            user_keys.sort(key=lambda x: x['created_at'], reverse=True)
            keys_to_remove = user_keys[1:]
            
            removed_count = 0
            for key in keys_to_remove:
                try:
                    old_filename = key['filename']
                    new_filename = f"REMOVED_{old_filename}"
                    old_path = os.path.join(CLIENTS_DIR, old_filename)
                    new_path = os.path.join(CLIENTS_DIR, new_filename)
                    
                    os.rename(old_path, new_path)
                    removed_count += 1
                except Exception as e:
                    print(f"Ошибка удаления ключа {key['uuid']}: {e}")
            
            await query.answer(
                f"✅ Лимиты сброшены! Удалено {removed_count} ключей", 
                show_alert=True
            )
            
            # Обновляем информацию о пользователе
            await self.show_user_detail(update, context, client_name)
            
        except Exception as e:
            await query.answer(f"❌ Ошибка сброса лимитов: {str(e)}", show_alert=True)
    
    async def enforce_all_limits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Применяет лимиты ко всем пользователям"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            actions = enforce_user_limits()
            
            if actions:
                message = f"✅ Выполнено действий: {len(actions)}\n\n" + "\n".join(actions[:10])
                if len(actions) > 10:
                    message += f"\n... и еще {len(actions) - 10} действий"
            else:
                message = "✅ Все пользователи соблюдают лимиты, действия не требуются"
            
            await query.answer(message, show_alert=True)
            
            # Обновляем статистику
            await self.show_admin_stats(update, context)
            
        except Exception as e:
            await query.answer(f"❌ Ошибка применения лимитов: {str(e)}", show_alert=True)
    
    async def show_limits_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Показывает меню управления лимитами пользователя"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            users = get_user_keys()
            
            if client_name not in users:
                await query.answer("❌ Пользователь не найден", show_alert=True)
                return
            
            user_keys = users[client_name]
            
            if not user_keys:
                await query.answer("❌ У пользователя нет ключей", show_alert=True)
                return
            
            # Получаем текущие лимиты из первого ключа
            current_key = user_keys[0]
            current_conn = current_key.get('max_connections', 3)
            current_dev = current_key.get('max_devices', 3)
            
            text = (
                "⚙️ **Управление лимитами**\n\n"
                f"👤 Пользователь: `{escape_markdown(client_name, version=2)}`\n"
                f"🔑 Ключей: `{len(user_keys)}`\n\n"
                "**Текущие лимиты:**\n"
                f"🔗 Соединения: `{current_conn}`\n"
                f"📱 Устройства: `{current_dev}`\n\n"
                "Выберите действие:"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Сбросить лимиты", callback_data=f"admin_reset_only_{client_name}")
                ],
                [
                    InlineKeyboardButton("⚙️ Изменить лимиты", callback_data=f"admin_change_limits_{client_name}")
                ],
                [
                    InlineKeyboardButton("🔄⚙️ Сбросить + Изменить", callback_data=f"admin_reset_and_change_{client_name}")
                ],
                [
                    InlineKeyboardButton("🔙 К пользователю", callback_data=f"admin_user_{client_name}")
                ]
            ]
            
            await query.edit_message_text(
                text=text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.answer(f"❌ Ошибка загрузки лимитов: {str(e)}", show_alert=True)
    
    async def show_limits_editor(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Показывает редактор лимитов"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            users = get_user_keys()
            
            if client_name not in users:
                await query.answer("❌ Пользователь не найден", show_alert=True)
                return
            
            user_keys = users[client_name]
            current_key = user_keys[0] if user_keys else {}
            current_conn = current_key.get('max_connections', 3)
            current_dev = current_key.get('max_devices', 3)
            
            text = (
                "⚙️ **Редактор лимитов**\n\n"
                f"👤 Пользователь: `{escape_markdown(client_name, version=2)}`\n\n"
                "**Настройка лимитов:**"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("➖", callback_data=f"admin_conn_dec_{client_name}_{current_conn}_{current_dev}"),
                    InlineKeyboardButton(f"🔗 {current_conn}", callback_data="noop"),
                    InlineKeyboardButton("➕", callback_data=f"admin_conn_inc_{client_name}_{current_conn}_{current_dev}")
                ],
                [
                    InlineKeyboardButton("➖", callback_data=f"admin_dev_dec_{client_name}_{current_conn}_{current_dev}"),
                    InlineKeyboardButton(f"📱 {current_dev}", callback_data="noop"),
                    InlineKeyboardButton("➕", callback_data=f"admin_dev_inc_{client_name}_{current_conn}_{current_dev}")
                ],
                [
                    InlineKeyboardButton("✅ Применить", callback_data=f"admin_apply_limits_{client_name}_{current_conn}_{current_dev}")
                ],
                [
                    InlineKeyboardButton("🔙 Назад", callback_data=f"admin_manage_limits_{client_name}")
                ]
            ]
            
            await query.edit_message_text(
                text=text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.answer(f"❌ Ошибка редактора лимитов: {str(e)}", show_alert=True)
    
    async def apply_user_limits(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               client_name: str, max_connections: int, max_devices: int, reset_first: bool = False):
        """Применяет новые лимиты к пользователю"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            if reset_first:
                # Сбрасываем и обновляем лимиты
                success = reset_and_update_user_limits(client_name, max_connections, max_devices)
                action = "сброшены и обновлены"
            else:
                # Только обновляем лимиты
                success = update_user_limits(client_name, max_connections, max_devices)
                action = "обновлены"
            
            if success:
                await query.answer(
                    f"✅ Лимиты {action}!\n"
                    f"🔗 Соединения: {max_connections}\n"
                    f"📱 Устройства: {max_devices}", 
                    show_alert=True
                )
            else:
                await query.answer("⚠️ Лимиты не изменены", show_alert=True)
            
            # Возвращаемся к управлению лимитами
            await self.show_limits_management(update, context, client_name)
            
        except Exception as e:
            await query.answer(f"❌ Ошибка применения лимитов: {str(e)}", show_alert=True)
    
    async def create_user_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Создает новый ключ для пользователя"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            # Создаем новый ключ
            success = create_user_key(client_name)
            
            if success:
                await query.answer(
                    f"✅ Новый ключ создан для пользователя {client_name}!", 
                    show_alert=True
                )
                # Обновляем информацию о пользователе
                await self.show_user_detail(update, context, client_name)
            else:
                await query.answer(
                    f"❌ Не удалось создать ключ для {client_name}", 
                    show_alert=True
                )
        except Exception as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def remove_all_user_keys(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_name: str):
        """Удаляет все ключи пользователя"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            # Получаем все ключи пользователя
            users = get_user_keys()
            if client_name not in users:
                await query.answer(f"❌ Пользователь {client_name} не найден", show_alert=True)
                return
            
            user_keys = users[client_name]
            removed_count = 0
            
            # Удаляем все ключи
            for key_info in user_keys:
                key_id = key_info.get('id')
                if key_id:
                    success = remove_user_key(client_name, key_id)
                    if success:
                        removed_count += 1
            
            if removed_count > 0:
                await query.answer(
                    f"✅ Удалено {removed_count} ключей пользователя {client_name}!", 
                    show_alert=True
                )
                # Обновляем информацию о пользователе
                await self.show_user_detail(update, context, client_name)
            else:
                await query.answer(
                    f"❌ Не удалось удалить ключи пользователя {client_name}", 
                    show_alert=True
                )
        except Exception as e:
            await query.answer(f"❌ Ошибка удаления ключей: {str(e)}", show_alert=True)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback запросы админки"""
        query = update.callback_query
        data = query.data
        
        if not self.is_admin(query.from_user.id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        if data == "admin_menu":
            await self.show_admin_menu(update, context)
        elif data == "admin_stats":
            await self.show_admin_stats(update, context)
        elif data == "admin_users":
            await self.show_users_management(update, context)
        elif data == "admin_enforce_limits":
            await self.enforce_all_limits(update, context)
        elif data.startswith("admin_list_users_"):
            page = int(data.split("_")[-1])
            await self.list_users(update, context, page)
        elif data.startswith("admin_user_"):
            client_name = data.replace("admin_user_", "")
            await self.show_user_detail(update, context, client_name)
        elif data.startswith("admin_reset_limits_"):
            client_name = data.replace("admin_reset_limits_", "")
            await self.reset_user_limits(update, context, client_name)
        elif data.startswith("admin_manage_limits_"):
            client_name = data.replace("admin_manage_limits_", "")
            await self.show_limits_management(update, context, client_name)
        elif data.startswith("admin_reset_only_"):
            client_name = data.replace("admin_reset_only_", "")
            try:
                success = reset_user_limits(client_name)
                if success:
                    await query.answer("✅ Лимиты сброшены! Удалены лишние ключи", show_alert=True)
                else:
                    await query.answer("⚠️ Сброс не требуется - у пользователя 1 ключ", show_alert=True)
                await self.show_limits_management(update, context, client_name)
            except Exception as e:
                await query.answer(f"❌ Ошибка сброса: {str(e)}", show_alert=True)
        elif data.startswith("admin_change_limits_"):
            client_name = data.replace("admin_change_limits_", "")
            # Очищаем флаг сброса, так как это обычное изменение
            context.user_data['reset_before_apply'] = False
            await self.show_limits_editor(update, context, client_name)
        elif data.startswith("admin_reset_and_change_"):
            client_name = data.replace("admin_reset_and_change_", "")
            # Сохраняем информацию о том, что нужно сбросить лимиты
            context.user_data['reset_before_apply'] = True
            await self.show_limits_editor(update, context, client_name)
        elif data.startswith("admin_conn_inc_") or data.startswith("admin_conn_dec_") or \
             data.startswith("admin_dev_inc_") or data.startswith("admin_dev_dec_"):
            # Обработка изменения лимитов
            if data.startswith("admin_conn_inc_"):
                action = "conn_inc"
                remaining = data.replace("admin_conn_inc_", "")
            elif data.startswith("admin_conn_dec_"):
                action = "conn_dec"
                remaining = data.replace("admin_conn_dec_", "")
            elif data.startswith("admin_dev_inc_"):
                action = "dev_inc"
                remaining = data.replace("admin_dev_inc_", "")
            elif data.startswith("admin_dev_dec_"):
                action = "dev_dec"
                remaining = data.replace("admin_dev_dec_", "")
            
            # Разделяем по последним двум подчеркиваниям (лимиты всегда в конце)
            parts = remaining.rsplit("_", 2)
            client_name = parts[0]
            current_conn = int(parts[1])
            current_dev = int(parts[2])
            
            if action == "conn_inc":
                new_conn = min(current_conn + 1, 10)  # Максимум 10 соединений
                new_dev = current_dev
            elif action == "conn_dec":
                new_conn = max(current_conn - 1, 1)   # Минимум 1 соединение
                new_dev = current_dev
            elif action == "dev_inc":
                new_conn = current_conn
                new_dev = min(current_dev + 1, 10)    # Максимум 10 устройств
            elif action == "dev_dec":
                new_conn = current_conn
                new_dev = max(current_dev - 1, 1)     # Минимум 1 устройство
            
            # Обновляем редактор с новыми значениями
            users = get_user_keys()
            if client_name in users:
                text = (
                    "⚙️ **Редактор лимитов**\n\n"
                    f"👤 Пользователь: `{escape_markdown(client_name, version=2)}`\n\n"
                    "**Настройка лимитов:**\n\n"
                    f"🔗 Соединения: {new_conn}\n"
                    f"📱 Устройства: {new_dev}"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("➖", callback_data=f"admin_conn_dec_{client_name}_{new_conn}_{new_dev}"),
                        InlineKeyboardButton(f"🔗 {new_conn}", callback_data="noop"),
                        InlineKeyboardButton("➕", callback_data=f"admin_conn_inc_{client_name}_{new_conn}_{new_dev}")
                    ],
                    [
                        InlineKeyboardButton("➖", callback_data=f"admin_dev_dec_{client_name}_{new_conn}_{new_dev}"),
                        InlineKeyboardButton(f"📱 {new_dev}", callback_data="noop"),
                        InlineKeyboardButton("➕", callback_data=f"admin_dev_inc_{client_name}_{new_conn}_{new_dev}")
                    ],
                    [
                        InlineKeyboardButton("✅ Применить", callback_data=f"admin_apply_limits_{client_name}_{new_conn}_{new_dev}")
                    ],
                    [
                        InlineKeyboardButton("🔙 Назад", callback_data=f"admin_manage_limits_{client_name}")
                    ]
                ]
                
                await query.edit_message_text(
                    text=text,
                    parse_mode='MarkdownV2',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        elif data.startswith("admin_apply_limits_"):
            # Убираем префикс "admin_apply_limits_"
            remaining = data.replace("admin_apply_limits_", "")
            # Разделяем по последним двум подчеркиваниям (лимиты всегда в конце)
            parts = remaining.rsplit("_", 2)
            client_name = parts[0]
            max_connections = int(parts[1])
            max_devices = int(parts[2])
            
            # Определяем, нужно ли сбрасывать лимиты
            reset_first = context.user_data.get('reset_before_apply', False)
            
            # Очищаем флаг после использования
            if 'reset_before_apply' in context.user_data:
                del context.user_data['reset_before_apply']
            
            await self.apply_user_limits(update, context, client_name, max_connections, max_devices, reset_first)
        elif data.startswith("admin_create_key_"):
            client_name = data.replace("admin_create_key_", "")
            await self.create_user_key(update, context, client_name)
        elif data.startswith("admin_remove_all_keys_"):
            client_name = data.replace("admin_remove_all_keys_", "")
            await self.remove_all_user_keys(update, context, client_name)
        elif data == "admin_xray_menu":
            await self.show_xray_menu(update, context)
        elif data == "admin_xray_status":
            await self.show_xray_status(update, context)
        elif data == "admin_xray_restart":
            await self.restart_xray(update, context)
        elif data == "admin_xray_reload":
            await self.reload_xray(update, context)
        elif data == "admin_xray_logs":
            await self.show_xray_logs(update, context)
        elif data == "admin_cleanup_expired":
            await self.cleanup_expired_keys(update, context)
        elif data == "noop":
            # Игнорируем нажатия на неактивные кнопки
            await query.answer()
        else:
            await query.answer("❌ Неизвестная команда", show_alert=True)
    
    async def show_xray_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню управления Xray"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        text = (
            "🔧 **Управление Xray**\n\n"
            "Выберите действие для управления сервером Xray:"
        )
        
        await query.edit_message_text(
            text=text,
            parse_mode='MarkdownV2',
            reply_markup=get_admin_xray_keyboard()
        )
    
    async def show_xray_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статус Xray"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            import subprocess
            
            # Проверяем статус службы
            status_result = subprocess.run([
                '/usr/bin/systemctl', 'is-active', 'xray'
            ], capture_output=True, text=True, timeout=10)
            
            is_active = status_result.returncode == 0
            status_text = "🟢 Активен" if is_active else "🔴 Неактивен"
            
            # Получаем детальную информацию
            info_result = subprocess.run([
                '/usr/bin/systemctl', 'status', 'xray', '--no-pager', '-l'
            ], capture_output=True, text=True, timeout=10)
            
            # Получаем PID процесса
            pid_result = subprocess.run([
                '/usr/bin/systemctl', 'show', 'xray', '--property=MainPID'
            ], capture_output=True, text=True, timeout=10)
            
            pid = "Неизвестен"
            if pid_result.returncode == 0:
                pid_line = pid_result.stdout.strip()
                if "MainPID=" in pid_line:
                    pid = pid_line.split("=")[1]
                    if pid == "0":
                        pid = "Не запущен"
            
            # Получаем время работы
            uptime_result = subprocess.run([
                '/usr/bin/systemctl', 'show', 'xray', '--property=ActiveEnterTimestamp'
            ], capture_output=True, text=True, timeout=10)
            
            uptime = "Неизвестно"
            if uptime_result.returncode == 0:
                uptime_line = uptime_result.stdout.strip()
                if "ActiveEnterTimestamp=" in uptime_line:
                    uptime = uptime_line.split("=")[1]
            
            text = (
                f"📊 **Статус Xray**\n\n"
                f"🔹 Статус: {escape_markdown(status_text, version=2)}\n"
                f"🔹 PID: `{pid}`\n"
                f"🔹 Запущен: {escape_markdown(uptime, version=2)}\n\n"
            )
            
            if is_active:
                text += "✅ Сервис работает нормально"
            else:
                text += "❌ Сервис не работает\\!"
                
        except Exception as e:
            text = f"❌ **Ошибка получения статуса**\n\n`{escape_markdown(str(e), version=2)}`"
        
        await self.safe_edit_message(query, text, 'MarkdownV2', get_admin_xray_keyboard())
    
    async def restart_xray(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перезапускает Xray"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await query.answer("🔄 Перезапускаю Xray...", show_alert=False)
        
        try:
            import subprocess
            
            # Перезапускаем Xray
            restart_result = subprocess.run([
                '/usr/bin/systemctl', 'restart', 'xray'
            ], capture_output=True, text=True, timeout=30)
            
            if restart_result.returncode == 0:
                # Проверяем, что сервис запустился
                import time
                time.sleep(2)
                
                status_result = subprocess.run([
                    '/usr/bin/systemctl', 'is-active', 'xray'
                ], capture_output=True, text=True, timeout=10)
                
                if status_result.returncode == 0:
                    text = "✅ **Xray успешно перезапущен**\n\nСервис работает нормально\\."
                else:
                    text = "⚠️ **Xray перезапущен, но не активен**\n\nПроверьте логи для диагностики\\."
            else:
                error_msg = restart_result.stderr.strip() if restart_result.stderr else "Неизвестная ошибка"
                text = f"❌ **Ошибка перезапуска Xray**\n\n`{escape_markdown(error_msg, version=2)}`"
                
        except Exception as e:
            text = f"❌ **Ошибка выполнения команды**\n\n`{escape_markdown(str(e), version=2)}`"
        
        await query.edit_message_text(
            text=text,
            parse_mode='MarkdownV2',
            reply_markup=get_admin_xray_keyboard()
        )
    
    async def reload_xray(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перезагружает конфигурацию Xray"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await query.answer("🔧 Перезагружаю конфигурацию...", show_alert=False)
        
        try:
            # Используем нашу функцию из manage_user_limits
            success = reload_xray_config()
            
            if success:
                text = "✅ **Конфигурация перезагружена**\n\nXray использует обновленную конфигурацию\\."
            else:
                text = "❌ **Ошибка перезагрузки конфигурации**\n\nПроверьте логи для диагностики\\."
                
        except Exception as e:
            text = f"❌ **Ошибка выполнения**\n\n`{escape_markdown(str(e), version=2)}`"
        
        await query.edit_message_text(
            text=text,
            parse_mode='MarkdownV2',
            reply_markup=get_admin_xray_keyboard()
        )
    
    async def show_xray_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает логи Xray"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        try:
            import subprocess
            
            # Получаем последние логи
            logs_result = subprocess.run([
                'journalctl', '-u', 'xray', '--no-pager', '-n', '20', '--reverse'
            ], capture_output=True, text=True, timeout=15)
            
            if logs_result.returncode == 0:
                logs = logs_result.stdout.strip()
                if logs:
                    # Обрезаем логи если они слишком длинные
                    if len(logs) > 3000:
                        logs = logs[-3000:]
                        logs = "...\n" + logs
                    
                    text = f"📋 **Логи Xray \\(последние 20 записей\\)**\n\n```\n{escape_markdown(logs, version=2)}\n```"
                else:
                    text = "📋 **Логи Xray**\n\nЛоги пусты или недоступны\\."
            else:
                error_msg = logs_result.stderr.strip() if logs_result.stderr else "Ошибка получения логов"
                text = f"❌ **Ошибка получения логов**\n\n`{escape_markdown(error_msg, version=2)}`"
                
        except Exception as e:
            text = f"❌ **Ошибка выполнения**\n\n`{escape_markdown(str(e), version=2)}`"
        
        await self.safe_edit_message(query, text, 'MarkdownV2', get_admin_xray_keyboard())
    
    async def cleanup_expired_keys(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очищает просроченные ключи"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await query.answer("🧹 Очищаю просроченные ключи...", show_alert=False)
        
        try:
            # Используем функцию из manage_user_limits
            removed_keys = cleanup_expired_keys()
            
            if removed_keys:
                count = len(removed_keys)
                text = f"✅ **Очистка завершена**\n\nУдалено просроченных ключей: `{count}`\n\n"
                
                # Показываем первые несколько удаленных ключей
                if count <= 5:
                    text += "Удаленные ключи:\n"
                    for key_info in removed_keys:
                        text += f"• {escape_markdown(key_info, version=2)}\n"
                else:
                    text += "Удаленные ключи \\(первые 5\\):\n"
                    for key_info in removed_keys[:5]:
                        text += f"• {escape_markdown(key_info, version=2)}\n"
                    text += f"\\.\\.\\. и еще {count - 5} ключей"
            else:
                text = "✅ **Очистка завершена**\n\nПросроченных ключей не найдено\\."
                
        except Exception as e:
            text = f"❌ **Ошибка очистки**\n\n`{escape_markdown(str(e), version=2)}`"
        
        await query.edit_message_text(
            text=text,
            parse_mode='MarkdownV2',
            reply_markup=get_admin_xray_keyboard()
        )