import logging
import os
import json
from datetime import datetime
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── НАСТРОЙКИ ───────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8759777576:AAEE-E-i1WvMQXkImz392b6QxBatfvxhYpc")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "426493206")

# Реклама услуги по созданию ботов — поменяй на свои контакты
DEVELOPER_CONTACT = "@Alyohin_Vadim"

ANKETA_STORONNIK_PATH = "anketa_storonnik.pdf"
ANKETA_CHLEN_PATH = "anketa_chlen.pdf"
LOGO_PATH = "logo.png"

PARTY_INFO = (
    "🟢 *Политическая партия «НОВЫЕ ЛЮДИ»*\n\n"
    "Зарегистрирована в марте 2020 года. Представлена в Государственной думе РФ.\n\n"
    "Партия выступает за:\n"
    "• сменяемость и обновление власти\n"
    "• сокращение бюрократии\n"
    "• развитие промышленности и малого бизнеса\n"
    "• современную инфраструктуру и рабочие места\n"
    "• свободу слова и собраний\n\n"
    "Подробнее об идеологии, программе и новостях — на официальном сайте:\n"
    "🔗 https://newpeople.ru"
)

# ─── СОСТОЯНИЯ ───────────────────────────────────────────────
(
    ASK_AGE,
    ASK_CITIZENSHIP,
    ASK_TYPE,
    WAIT_PHOTO,
    ASK_NAME,
    ASK_PHONE,
) = range(6)

LEADS_FILE = "applications.json"

def load_apps():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_apps(apps):
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, ensure_ascii=False, indent=2)

apps_db = load_apps()

# ─── КЛАВИАТУРЫ ──────────────────────────────────────────────
YES_NO_KB = ReplyKeyboardMarkup(
    [[KeyboardButton("Да"), KeyboardButton("Нет")]],
    resize_keyboard=True, one_time_keyboard=True
)

TYPE_KB = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🤝 Сторонник партии")],
        [KeyboardButton("📋 Член партии")],
    ],
    resize_keyboard=True, one_time_keyboard=True
)

CONTACT_KB = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 Отправить номер телефона", request_contact=True)]],
    resize_keyboard=True, one_time_keyboard=True
)

# ─── /start ───────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user

    try:
        with open(LOGO_PATH, "rb") as logo:
            await update.message.reply_photo(photo=logo, read_timeout=30, write_timeout=30, connect_timeout=30)
    except Exception as e:
        logger.error(f"Не удалось отправить лого: {e}")

    await update.message.reply_text(
        PARTY_INFO, parse_mode="Markdown", disable_web_page_preview=False
    )

    await update.message.reply_text(
        f"Здравствуйте, {user.first_name}! 👋\n\n"
        "Этот бот поможет вам вступить в партию «Новые люди» в качестве "
        "сторонника или члена партии.\n\n"
        "Сначала несколько уточняющих вопросов.\n\n"
        "Вам уже исполнилось 18 лет?",
        reply_markup=YES_NO_KB
    )
    return ASK_AGE

# ─── Проверка возраста ───────────────────────────────────────
async def ask_citizenship(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer != "да":
        await update.message.reply_text(
            "К сожалению, вступить в партию могут только граждане старше 18 лет.\n\n"
            "Если ошиблись — нажмите /start чтобы начать заново."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Отлично! Теперь уточните — у вас гражданство РФ?",
        reply_markup=YES_NO_KB
    )
    return ASK_CITIZENSHIP

# ─── Проверка гражданства ────────────────────────────────────
async def ask_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer != "да":
        await update.message.reply_text(
            "К сожалению, в партию могут вступить только граждане РФ.\n\n"
            "Если ошиблись — нажмите /start чтобы начать заново."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Прекрасно! Теперь выберите, в каком статусе вы хотите вступить в партию:\n\n"
        "🤝 *Сторонник* — разделяете цели партии, готовы участвовать в мероприятиях\n"
        "📋 *Член партии* — полноправное членство с обязанностями по Уставу",
        parse_mode="Markdown",
        reply_markup=TYPE_KB
    )
    return ASK_TYPE

# ─── Выбор типа анкеты → отправка файла ──────────────────────
async def send_anketa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if "сторонник" in choice.lower():
        context.user_data["type"] = "Сторонник партии"
        file_path = ANKETA_STORONNIK_PATH
    elif "член" in choice.lower():
        context.user_data["type"] = "Член партии"
        file_path = ANKETA_CHLEN_PATH
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите один из вариантов на клавиатуре ниже.",
            reply_markup=TYPE_KB
        )
        return ASK_TYPE

    with open(file_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            caption=(
                "📄 Вот анкета для заполнения.\n\n"
                "*Как заполнить:*\n"
                "1️⃣ Скачайте файл\n"
                "2️⃣ Распечатайте и заполните от руки чёрной или тёмно-синей ручкой "
                "(или заполните на компьютере, если формат позволяет)\n"
                "3️⃣ Сфотографируйте или отсканируйте заполненную анкету — "
                "убедитесь, что всё читается чётко\n"
                "4️⃣ Отправьте фото или файл прямо сюда, в этот чат\n\n"
                "Когда анкета будет готова — пришлите её следующим сообщением 👇"
            ),
            parse_mode="Markdown",
            reply_markup=None
        )
    return WAIT_PHOTO

# ─── Приём фото/файла анкеты ─────────────────────────────────
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data["anketa_file_id"] = file_id
        context.user_data["anketa_kind"] = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        context.user_data["anketa_file_id"] = file_id
        context.user_data["anketa_kind"] = "document"
    else:
        await update.message.reply_text(
            "Пожалуйста, пришлите фото или файл заполненной анкеты."
        )
        return WAIT_PHOTO

    await update.message.reply_text(
        "✅ Анкета получена!\n\n"
        "Теперь укажите, пожалуйста, ваше ФИО полностью (как в паспорте):"
    )
    return ASK_NAME

# ─── ФИО ──────────────────────────────────────────────────────
async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fio"] = update.message.text.strip()
    await update.message.reply_text(
        "Спасибо! И последнее — оставьте номер телефона для связи:",
        reply_markup=CONTACT_KB
    )
    return ASK_PHONE

# ─── Телефон → финал ─────────────────────────────────────────
async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    user = update.effective_user
    context.user_data["phone"] = phone
    context.user_data["username"] = f"@{user.username}" if user.username else "нет username"
    context.user_data["created_at"] = datetime.now().isoformat()

    apps_db[str(user.id)] = {
        k: v for k, v in context.user_data.items() if k != "anketa_file_id"
    }
    save_apps(apps_db)

    # Сообщение заявителю
    await update.message.reply_text(
        "🎉 *Спасибо! Ваша заявка принята.*\n\n"
        "Мы передали анкету и ваши контакты ответственному сотруднику партии. "
        "С вами свяжутся в ближайшее время для подтверждения.\n\n"
        "Хорошего дня!",
        parse_mode="Markdown",
        reply_markup=None
    )

    # Небольшая реклама бот-разработки в конце — отдельным сообщением с кнопкой
    ad_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Узнать про создание бота", url=f"https://t.me/{DEVELOPER_CONTACT.lstrip('@')}")]
    ])
    await update.message.reply_text(
        "P.S. Этот бот сделан на заказ 🤖\n"
        "Если хотите такого же помощника для своего проекта или бизнеса — "
        "пишите разработчику.",
        reply_markup=ad_kb
    )

    # Уведомление администратору + анкета
    machine = context.user_data.get("type", "—")
    fio = context.user_data.get("fio", "—")

    admin_text = (
        f"🔔 Новая заявка на вступление!\n\n"
        f"Тип: {machine}\n"
        f"ФИО: {fio}\n"
        f"Телефон: {phone}\n"
        f"Telegram: {context.user_data['username']}\n"
        f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)

        file_id = context.user_data.get("anketa_file_id")
        kind = context.user_data.get("anketa_kind")
        if file_id:
            if kind == "photo":
                await context.bot.send_photo(
                    chat_id=ADMIN_CHAT_ID, photo=file_id,
                    caption=f"Анкета от {fio} ({phone})"
                )
            else:
                await context.bot.send_document(
                    chat_id=ADMIN_CHAT_ID, document=file_id,
                    caption=f"Анкета от {fio} ({phone})"
                )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление администратору: {e}")

    return ConversationHandler.END

# ─── /cancel ──────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Заявка отменена. Если захотите начать заново — напишите /start",
        reply_markup=None
    )
    return ConversationHandler.END

# ─── /applications — список для администратора ───────────────
async def show_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        return
    if not apps_db:
        await update.message.reply_text("Заявок пока нет.")
        return

    text = "📋 *Последние заявки:*\n\n"
    for uid, app in list(apps_db.items())[-10:]:
        text += (
            f"• {app.get('fio', '—')} — {app.get('type', '—')}\n"
            f"  📞 {app.get('phone', '—')}  {app.get('username', '')}\n\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── ЗАПУСК ───────────────────────────────────────────────────
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_AGE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_citizenship)],
            ASK_CITIZENSHIP:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_type)],
            ASK_TYPE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, send_anketa)],
            WAIT_PHOTO:     [MessageHandler((filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, receive_photo)],
            ASK_NAME:       [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE:      [
                MessageHandler(filters.CONTACT, finish),
                MessageHandler(filters.TEXT & ~filters.COMMAND, finish),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("applications", show_apps))

    logger.info("Бот «Новые люди» запущен ✅")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
