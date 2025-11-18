"""
Telegram bot GitHub Pages bilan ishlash uchun

SOZLASH (PowerShell):
$env:TELEGRAM_BOT_TOKEN = "8556257044:AAGZEgPCZWBGv5vCa04sYlr8s_xh1ZwvWs0"
$env:BOT_ADMIN_ID = "8258534176"
$env:WEBAPP_BASE_URL = "https://telegram-app-store.onrender.com"
python bot_simple.py
"""

import logging
import os
import json
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MUHIM: Environment variables dan olish (default qiymatlar ishlatish kerak emas!)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8556257044:AAGZEgPCZWBGv5vCa04sYlr8s_xh1ZwvWs0")
BOT_ADMIN_ID = os.environ.get("BOT_ADMIN_ID", "8258534176")  # BU YERDA XATO BOR EDI!
WEBAPP_BASE_URL = os.environ.get("WEBAPP_BASE_URL", "https://telegram-app-store.onrender.com").rstrip('/')

APPS_FILE = "apps.json"

logger.info(f"Bot Token: {BOT_TOKEN[:20]}...")
logger.info(f"Admin ID: {BOT_ADMIN_ID}")
logger.info(f"WebApp URL: {WEBAPP_BASE_URL}")


def _load_apps():
    try:
        with open(APPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _save_apps(apps):
    with open(APPS_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, ensure_ascii=False, indent=2)


def _is_admin(user_id):
    if not BOT_ADMIN_ID:
        return False
    return str(user_id) == str(BOT_ADMIN_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boshlash buyrug'i - Open Store tugmasi bilan"""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    keyboard = []
    
    # WEBAPP_BASE_URL mavjud bo'lsa, WebApp tugmasini qo'shamiz
    if WEBAPP_BASE_URL:
        try:
            webapp_url = WEBAPP_BASE_URL.rstrip('/') + '/'
            logger.info(f"Creating WebApp button with URL: {webapp_url}")
            
            webapp = WebAppInfo(url=webapp_url)
            btn = InlineKeyboardButton("🛒 Open Store", web_app=webapp)
            keyboard.append([btn])
        except Exception as e:
            logger.error(f"Failed to create WebApp button: {e}")
            # Fallback - oddiy URL tugmasi
            btn = InlineKeyboardButton("🛒 Open Store", url=WEBAPP_BASE_URL)
            keyboard.append([btn])
    else:
        logger.warning("WEBAPP_BASE_URL is not set!")
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    message_text = (
        "👋 Salom! Mini App Store'ga xush kelibsiz!\n\n"
        "🛒 Do'konni ochish uchun pastdagi tugmani bosing\n"
        "📱 Ilovalar ro'yxatini ko'rish: /list\n\n"
    )
    
    if _is_admin(user.id):
        message_text += "🔑 Siz adminsiz! Yangi ilova qo'shish: /addapp"
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup
    )


async def addapp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ilova qo'shish (faqat admin)"""
    user = update.effective_user
    
    if not _is_admin(user.id):
        await update.message.reply_text(
            f"❌ Siz admin emassiz!\n"
            f"Sizning ID: {user.id}\n"
            f"Admin ID: {BOT_ADMIN_ID}"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📱 Yangi ilova qo'shish:\n\n"
        "1️⃣ APK yoki EXE faylni yuboring\n\n"
        "Bekor qilish uchun: /cancel"
    )
    return "WAITING_FILE"


async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fayl qabul qilish"""
    if not update.message.document:
        await update.message.reply_text("Iltimos, fayl yuboring!")
        return "WAITING_FILE"
    
    file_name = update.message.document.file_name
    if not (file_name.lower().endswith('.apk') or file_name.lower().endswith('.exe')):
        await update.message.reply_text("❌ Faqat .apk yoki .exe fayllar!")
        return "WAITING_FILE"
    
    context.user_data['file_id'] = update.message.document.file_id
    context.user_data['file_name'] = file_name
    
    logger.info(f"File received: {file_name} (ID: {update.message.document.file_id})")
    
    await update.message.reply_text("✅ Fayl qabul qilindi!\n\n2️⃣ Endi rasm yuboring:")
    return "WAITING_PHOTO"


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rasm qabul qilish"""
    if not update.message.photo:
        await update.message.reply_text("Iltimos, rasm yuboring!")
        return "WAITING_PHOTO"
    
    photo_id = update.message.photo[-1].file_id
    context.user_data['photo_id'] = photo_id
    
    logger.info(f"Photo received (ID: {photo_id})")
    
    await update.message.reply_text("✅ Rasm qabul qilindi!\n\n3️⃣ Ilova nomini kiriting:")
    return "WAITING_NAME"


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nom qabul qilish"""
    if not update.message or not update.message.text:
        await update.message.reply_text("Iltimos, ilova nomini yozing!")
        return "WAITING_NAME"
    
    context.user_data['title'] = update.message.text.strip()
    await update.message.reply_text("4️⃣ Qisqa tavsif kiriting:")
    return "WAITING_DESC"


async def receive_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tavsif qabul qilish va saqlash"""
    if not update.message or not update.message.text:
        await update.message.reply_text("Iltimos, tavsif yozing!")
        return "WAITING_DESC"
    
    description = update.message.text.strip()
    
    # Ma'lumotlarni apps.json'ga saqlash
    apps = _load_apps()
    new_app = {
        "title": context.user_data['title'],
        "description": description,
        "file_id": context.user_data['file_id'],
        "file_name": context.user_data['file_name'],
        "photo_id": context.user_data['photo_id']
    }
    apps.append(new_app)
    _save_apps(apps)
    
    logger.info(f"App added: {new_app['title']}")
    
    await update.message.reply_text(
        f"✅ Ilova muvaffaqiyatli qo'shildi!\n\n"
        f"📱 Nom: {context.user_data['title']}\n"
        f"📝 Tavsif: {description}\n"
        f"📄 Fayl: {context.user_data['file_name']}"
    )
    
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bekor qilish"""
    await update.message.reply_text("❌ Bekor qilindi")
    context.user_data.clear()
    return ConversationHandler.END


async def list_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ilovalar ro'yxati"""
    apps = _load_apps()
    
    if not apps:
        await update.message.reply_text(
            "Hozircha ilovalar yo'q\n\n"
            "Do'konni ochish uchun: /start"
        )
        return
    
    text = "📱 Ilovalar ro'yxati:\n\n"
    for i, app in enumerate(apps, 1):
        text += f"{i}. {app['title']}\n"
        text += f"   📝 {app['description']}\n"
        text += f"   📄 {app['file_name']}\n\n"
    
    await update.message.reply_text(text)


def main():
    if not BOT_TOKEN or BOT_TOKEN == "REPLACE_WITH_YOUR_TOKEN":
        print("❌ TELEGRAM_BOT_TOKEN o'rnatilmagan!")
        print("PowerShell'da:")
        print('$env:TELEGRAM_BOT_TOKEN = "your_token"')
        return
    
    print("🚀 Bot ishga tushmoqda...")
    print(f"📱 Bot Token: {BOT_TOKEN[:20]}...")
    print(f"👤 Admin ID: {BOT_ADMIN_ID}")
    print(f"🌐 WebApp URL: {WEBAPP_BASE_URL}")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # /start buyrug'i
    app.add_handler(CommandHandler("start", start))
    
    # /list buyrug'i
    app.add_handler(CommandHandler("list", list_apps))
    
    # /addapp conversation
    conv = ConversationHandler(
        entry_points=[CommandHandler("addapp", addapp_cmd)],
        states={
            "WAITING_FILE": [MessageHandler(filters.Document.ALL, receive_file)],
            "WAITING_PHOTO": [MessageHandler(filters.PHOTO, receive_photo)],
            "WAITING_NAME": [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            "WAITING_DESC": [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_desc)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv)
    
    print("✅ Bot ishga tushdi! Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()