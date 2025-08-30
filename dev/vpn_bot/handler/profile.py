from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from telegram.helpers import escape
from db.models import ensure_user, session, VpnKey
from utils.generator import generate_vpn_link

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    
    # Формируем имя пользователя для VPN ссылки
    username = update.effective_user.username or update.effective_user.first_name or str(update.effective_user.id)

    # Проверяем наличие VPN-ключа у пользователя
    vpn_key = session.query(VpnKey).filter_by(user_id=user.id).first()

    if vpn_key and vpn_key.vpn_link.startswith("vless://"):
        vpn_link = vpn_key.vpn_link
    else:
        vpn_link, client_uuid = generate_vpn_link(username)

        # Сохраняем новый ключ только если он валидный
        if vpn_link.startswith("vless://") and client_uuid:
            if vpn_key:
                vpn_key.vpn_link = vpn_link  # обновим старую запись
                vpn_key.uuid = client_uuid    # сохраняем UUID
            else:
                vpn_key = VpnKey(user_id=user.id, vpn_link=vpn_link, uuid=client_uuid)
                session.add(vpn_key)
            session.commit()

    # Отправляем ответ пользователю
    if vpn_link.startswith("vless://"):
        # Экранируем HTML символы для безопасной передачи
        escaped_link = escape(vpn_link)
        message = f"🔐 Ваш VPN ключ:\n<code>{escaped_link}</code>"
        await update.message.reply_text(message, parse_mode="HTML")
    else:
        await update.message.reply_text(f"🔐 Ваш VPN ключ:\n❌ {vpn_link}")

# Обработчик команды "Профиль"
handler = MessageHandler(filters.TEXT & filters.Regex("Профиль"), show_profile)