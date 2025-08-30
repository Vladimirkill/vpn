from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from config import PAYMENT_WALLET

async def show_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💸 Отправьте оплату на кошелёк:\n{PAYMENT_WALLET}\nПосле этого напишите 'Оплатил'.")

handler = MessageHandler(filters.TEXT & filters.Regex("Оплатить"), show_payment)