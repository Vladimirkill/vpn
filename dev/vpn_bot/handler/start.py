from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Добро пожаловать в VPN-бот!", reply_markup=ReplyKeyboardRemove())

handler = CommandHandler("start", start)