import os
import asyncio
import logging
import random
import threading

from flask import Flask, request

from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

WEBHOOK_PATH = os.getenv(
    "WEBHOOK_PATH",
    "/webhook/ec750989503ad40b54d76ec334e24805"
)

PORT = int(os.getenv("PORT", "10000"))

# Ссылка на бота команды
CURATOR_URL = os.getenv(
    "CURATOR_URL",
    "https://t.me/usdteamrubot?start=6a76eafa1c83616169c692b9"
)

# Через сколько отправлять второе сообщение.
# Сейчас случайно от 5 до 30 минут.
MIN_DELAY = int(os.getenv("MIN_DELAY", "5"))
MAX_DELAY = int(os.getenv("MAX_DELAY", "30"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Environment")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# TELEGRAM
# ============================================================

dp = Dispatcher()


# ============================================================
# КНОПКИ
# ============================================================

def details_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Узнать подробности",
                    callback_data="details"
                )
            ]
        ]
    )


def curator_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Связаться ↗",
                    url=CURATOR_URL
                )
            ]
        ]
    )


# ============================================================
# ТЕКСТЫ
# ============================================================

START_TEXT = """Здравствуйте 🤝

Расскажите немного о себе:

— Где работали раньше и чем занимались?
— Сколько Вам лет?
— Был ли опыт удалённой работы?

И буквально пару слов о себе: какие у Вас сильные стороны, что хорошо получается, как обычно подходите к работе 🙂"""


FORM_ACCEPTED_TEXT = """Спасибо за заполнение анкеты 🤝

Ваша анкета отправлена на рассмотрение.

Ожидайте ответ."""


# ВАЖНО:
# Здесь указывай только реальные и проверяемые условия вакансии.
# Не используй гарантии дохода или неподтверждённые цифры.

VACANCY_TEXT = """К сожалению, на данную вакансию уже утвердили другого кандидата.
Мы можем предложить вам другую позицию в нашей команде:

В нашей команде сейчас открыта новая вакансия.
Работа полностью удалённая, график свободный, обучение предоставляем.

Если вас заинтересовало данное предложение, нажмите кнопку ниже чтобы узнать подробности👇"""


DETAILS_TEXT = """Команда специализируется на криптовалютном арбитраже между биржами.

Опытный отдел аналитиков находит разницу в цене активов между биржами и передаёт информацию наставникам.

Все операции должны выполняться самостоятельно после ознакомления с рисками и условиями соответствующих платформ.

Для работы используются популярные криптовалютные биржи.

Условия обучения и взаимодействия с наставниками необходимо заранее уточнить у команды.

Для связи с менеджером для дальнейшей работы вам необходимо:

1. Перейти в бота команды по кнопке ниже.
2. Нажать «Старт».
3. Получить контакт свободного куратора и написать ему, что вы хотите попасть в команду."""


# ============================================================
# ХРАНЕНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================

# Для текущей версии достаточно памяти процесса.
# Для большой фермы потом лучше вынести это в PostgreSQL.

users = {}

lock = threading.Lock()


# ============================================================
# ОТПРАВКА ОТЛОЖЕННОГО СООБЩЕНИЯ
# ============================================================

def send_delayed_offer(user_id: int, delay_seconds: int):

    logger.info(
        "USER %s: offer scheduled in %s seconds",
        user_id,
        delay_seconds
    )

    def worker():

        logger.info(
            "USER %s: sending delayed offer",
            user_id
        )

        asyncio.run(
            send_offer(user_id)
        )

    timer = threading.Timer(
        delay_seconds,
        worker
    )

    timer.daemon = True
    timer.start()


async def send_offer(user_id: int):

    bot = Bot(token=BOT_TOKEN)

    try:

        await bot.send_message(
            chat_id=user_id,
            text=VACANCY_TEXT,
            reply_markup=details_keyboard()
        )

        logger.info(
            "USER %s: offer sent",
            user_id
        )

    except Exception:

        logger.exception(
            "USER %s: ERROR SENDING OFFER",
            user_id
        )

    finally:

        await bot.session.close()


# ============================================================
# /START
# ============================================================

@dp.message(CommandStart())
async def start_handler(message: types.Message):

    user_id = message.from_user.id

    logger.info(
        "START FROM USER: %s",
        user_id
    )

    with lock:

        users[user_id] = {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "state": "waiting_form",
            "started": True
        }

    await message.answer(
        START_TEXT
    )

    logger.info(
        "START MESSAGE SENT TO: %s",
        user_id
    )


# ============================================================
# НАЖАТИЕ "УЗНАТЬ ПОДРОБНОСТИ"
# ============================================================

@dp.callback_query(lambda c: c.data == "details")
async def details_handler(callback: types.CallbackQuery):

    user_id = callback.from_user.id

    logger.info(
        "USER %s PRESSED DETAILS",
        user_id
    )

    await callback.answer()

    await callback.message.answer(
        DETAILS_TEXT
    )

    await callback.message.answer(
        "Для связи с менеджером нажмите кнопку ниже:",
        reply_markup=curator_keyboard()
    )


# ============================================================
# ОБЫЧНЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message()
async def message_handler(message: types.Message):

    user_id = message.from_user.id
    text = message.text or ""

    logger.info(
        "MESSAGE FROM %s: %s",
        user_id,
        text
    )

    with lock:

        user = users.get(user_id)

        if not user:
            users[user_id] = {
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "state": "waiting_form"
            }
            user = users[user_id]

    # --------------------------------------------------------
    # ПЕРВЫЙ ОТВЕТ ПОЛЬЗОВАТЕЛЯ
    # --------------------------------------------------------

    if user.get("state") == "waiting_form":

        with lock:
            users[user_id]["state"] = "form_completed"

        await message.answer(
            FORM_ACCEPTED_TEXT
        )

        # 5-30 минут
        delay_minutes = random.randint(
            MIN_DELAY,
            MAX_DELAY
        )

        delay_seconds = delay_minutes * 60

        with lock:
            users[user_id]["offer_delay"] = delay_seconds

        send_delayed_offer(
            user_id,
            delay_seconds
        )

        logger.info(
            "USER %s: offer scheduled after %s minutes",
            user_id,
            delay_minutes
        )

        return

    # --------------------------------------------------------
    # ЕСЛИ ЧЕЛОВЕК ПИШЕТ ПОСЛЕ АНКЕТЫ
    # --------------------------------------------------------

    await message.answer(
        "Спасибо, информация получена. Ожидайте дальнейшую информацию."
    )


# ============================================================
# ОБРАБОТКА UPDATE
# ============================================================

async def process_update(update_data: dict):

    bot = Bot(token=BOT_TOKEN)

    try:

        logger.info("=" * 50)

        logger.info(
            "PROCESS: update %s",
            update_data.get("update_id")
        )

        update = Update.model_validate(
            update_data
        )

        await dp.feed_update(
            bot,
            update
        )

        logger.info(
            "PROCESS: update finished %s",
            update_data.get("update_id")
        )

    except Exception:

        logger.exception(
            "PROCESS UPDATE ERROR"
        )

        raise

    finally:

        await bot.session.close()


# ============================================================
# WEBHOOK
# ============================================================

@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():

    logger.info("=" * 50)
    logger.info("WEBHOOK: request received")

    try:

        update_data = request.get_json(
            force=True,
            silent=False
        )

        if not update_data:

            logger.error(
                "WEBHOOK: empty update"
            )

            return "ok", 200

        update_id = update_data.get(
            "update_id"
        )

        logger.info(
            "WEBHOOK: update %s",
            update_id
        )

        asyncio.run(
            process_update(
                update_data
            )
        )

        logger.info(
            "WEBHOOK: processing finished"
        )

        return "ok", 200

    except Exception as e:

        logger.exception(
            "WEBHOOK PROCESS ERROR: %r",
            e
        )

        return "ok", 200


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/", methods=["GET"])
def health():

    return "Bot is running", 200


# ============================================================
# MANUAL WEBHOOK SETUP
# ============================================================

async def setup_webhook():

    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )

    if not render_url:

        logger.warning(
            "RENDER_EXTERNAL_URL не найден"
        )

        return

    webhook_url = (
        render_url.rstrip("/")
        + WEBHOOK_PATH
    )

    bot = Bot(token=BOT_TOKEN)

    try:

        logger.info(
            "Setting webhook: %s",
            webhook_url
        )

        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=False
        )

        logger.info(
            "Webhook successfully set"
        )

        info = await bot.get_webhook_info()

        logger.info(
            "Telegram webhook URL: %s",
            info.url
        )

        logger.info(
            "Pending updates: %s",
            info.pending_update_count
        )

    except Exception:

        logger.exception(
            "WEBHOOK SET ERROR"
        )

    finally:

        await bot.session.close()


# ============================================================
# /setup
# ============================================================

@app.route("/setup", methods=["GET"])
def setup_route():

    try:

        asyncio.run(
            setup_webhook()
        )

        return (
            "Webhook setup completed. "
            "Check Render logs.",
            200
        )

    except Exception as e:

        logger.exception(
            "MANUAL WEBHOOK SETUP ERROR"
        )

        return (
            f"Webhook error: {e}",
            500
        )


# ============================================================
# ПРОВЕРКА WEBHOOK
# ============================================================

@app.route("/webhook-info", methods=["GET"])
def webhook_info():

    async def get_info():

        bot = Bot(token=BOT_TOKEN)

        try:

            info = await bot.get_webhook_info()

            return {
                "url": info.url,
                "pending_updates": info.pending_update_count,
                "last_error": info.last_error_message,
                "last_error_date": info.last_error_date
            }

        finally:

            await bot.session.close()

    try:

        result = asyncio.run(
            get_info()
        )

        return result, 200

    except Exception as e:

        logger.exception(
            "WEBHOOK INFO ERROR"
        )

        return {
            "error": str(e)
        }, 500


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    logger.info("=" * 50)
    logger.info("Starting Telegram bot...")
    logger.info("=" * 50)

    try:

        asyncio.run(
            setup_webhook()
        )

    except Exception:

        logger.exception(
            "STARTUP WEBHOOK ERROR"
        )

    logger.info(
        "Telegram application started"
    )

    logger.info(
        "Webhook path: %s",
        WEBHOOK_PATH
    )

    logger.info(
        "Port: %s",
        PORT
    )

    logger.info("=" * 50)

    app.run(
        host="0.0.0.0",
        port=PORT
    )
