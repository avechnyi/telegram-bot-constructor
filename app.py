import os
import asyncio
import logging
import random
import threading

from flask import Flask, request

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import CommandStart


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

PORT = int(
    os.getenv("PORT", "10000")
)

WEBHOOK_PATH = os.getenv(
    "WEBHOOK_PATH",
    "/webhook/ec750989503ad40b54d76ec334e24805"
)

CURATOR_URL = os.getenv(
    "CURATOR_URL",
    "https://t.me/usdteamrubot?start=6a76eafa1c83616169c692b9"
)

# Задержка второго сообщения.
# В минутах.
MIN_DELAY = int(
    os.getenv("MIN_DELAY", "5")
)

MAX_DELAY = int(
    os.getenv("MAX_DELAY", "30")
)


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден в Environment"
    )


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
# ПРОСТОЕ ХРАНИЛИЩЕ
# ============================================================

users = {}

users_lock = threading.Lock()


# ============================================================
# КНОПКА "УЗНАТЬ ПОДРОБНОСТИ"
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


# ============================================================
# КНОПКА "СВЯЗАТЬСЯ"
# ============================================================

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
# ПЕРВОЕ СООБЩЕНИЕ
# ============================================================

START_TEXT = """Здравствуйте 🤝

Расскажите немного о себе:

— Где работали раньше и чем занимались?
— Сколько Вам лет?
— Был ли опыт удалённой работы?

И буквально пару слов о себе: какие у Вас сильные стороны, что хорошо получается, как обычно подходите к работе 🙂"""


# ============================================================
# ПОСЛЕ АНКЕТЫ
# ============================================================

FORM_ACCEPTED_TEXT = """Спасибо за заполнение анкеты 🤝

Ваша анкета отправлена на рассмотрение.

Ожидайте ответ."""


# ============================================================
# ОТЛОЖЕННОЕ СООБЩЕНИЕ
# ============================================================

# Здесь можно поставить свой фактический текст вакансии.
#
# Не добавляй сюда гарантии дохода или утверждения,
# которые не соответствуют реальным условиям.

VACANCY_TEXT = """К сожалению, на первоначальную вакансию уже выбран другой кандидат.

Мы можем предложить вам рассмотреть другую позицию в нашей команде.

Работа полностью удалённая, график свободный, обучение и сопровождение предоставляются.

Если предложение актуально для вас, нажмите кнопку ниже, чтобы узнать подробности👇"""


# ============================================================
# ПОДРОБНОСТИ
# ============================================================

DETAILS_TEXT = """Здесь разместите подробное описание вакансии и реальные условия работы.

Укажите:
— чем занимается команда;
— какие задачи предстоит выполнять;
— как проходит обучение;
— какие требования предъявляются;
— как устроено взаимодействие с наставником;
— условия оплаты.

Перед началом работы обязательно ознакомьтесь со всеми рисками и условиями соответствующих сервисов."""


# ============================================================
# ИНСТРУКЦИЯ ДЛЯ КУРАТОРА
# ============================================================

CURATOR_TEXT = """Для связи с менеджером для дальнейшей работы вам необходимо:

1. Перейти в бота команды по кнопке ниже.
2. Нажать «Старт».
3. Получить контакт свободного куратора и написать ему, что вы хотите попасть в команду."""


# ============================================================
# ОТЛОЖЕННАЯ ОТПРАВКА
# ============================================================

def schedule_offer(
    user_id: int,
    delay_seconds: int
):

    logger.info(
        "USER %s: offer scheduled in %s seconds",
        user_id,
        delay_seconds
    )

    timer = threading.Timer(
        delay_seconds,
        delayed_offer_worker,
        args=(user_id,)
    )

    timer.daemon = True

    timer.start()


# ============================================================
# WORKER
# ============================================================

def delayed_offer_worker(
    user_id: int
):

    logger.info(
        "USER %s: delayed offer worker started",
        user_id
    )

    try:

        asyncio.run(
            send_offer(user_id)
        )

    except Exception:

        logger.exception(
            "USER %s: delayed offer error",
            user_id
        )


# ============================================================
# ОТПРАВКА ВТОРОГО СООБЩЕНИЯ
# ============================================================

async def send_offer(
    user_id: int
):

    bot = Bot(
        token=BOT_TOKEN
    )

    try:

        await bot.send_message(
            chat_id=user_id,
            text=VACANCY_TEXT,
            reply_markup=details_keyboard()
        )

        logger.info(
            "USER %s: delayed offer sent",
            user_id
        )

    except Exception:

        logger.exception(
            "USER %s: failed to send offer",
            user_id
        )

    finally:

        await bot.session.close()


# ============================================================
# /START
# ============================================================

@dp.message(CommandStart())
async def start_handler(
    message: types.Message
):

    user_id = message.from_user.id

    logger.info(
        "START FROM USER: %s",
        user_id
    )

    with users_lock:

        users[user_id] = {
            "user_id": user_id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "state": "waiting_form"
        }

    await message.answer(
        START_TEXT
    )

    logger.info(
        "START MESSAGE SENT TO: %s",
        user_id
    )


# ============================================================
# КНОПКА "УЗНАТЬ ПОДРОБНОСТИ"
# ============================================================

@dp.callback_query(
    F.data == "details"
)
async def details_handler(
    callback: types.CallbackQuery
):

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
        CURATOR_TEXT,
        reply_markup=curator_keyboard()
    )


# ============================================================
# ОБЫЧНЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message()
async def message_handler(
    message: types.Message
):

    user_id = message.from_user.id

    text = (
        message.text
        or message.caption
        or ""
    )

    logger.info(
        "MESSAGE FROM %s: %s",
        user_id,
        text
    )

    # --------------------------------------------------------
    # ПОЛЬЗОВАТЕЛЬ ЗАПОЛНЯЕТ АНКЕТУ
    # --------------------------------------------------------

    with users_lock:

        user = users.get(
            user_id
        )

        if user is None:

            users[user_id] = {
                "user_id": user_id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "state": "waiting_form"
            }

            user = users[user_id]

        current_state = user.get(
            "state"
        )

    # --------------------------------------------------------
    # ПЕРВЫЙ ОТВЕТ
    # --------------------------------------------------------

    if current_state == "waiting_form":

        with users_lock:

            users[user_id]["state"] = (
                "form_completed"
            )

        await message.answer(
            FORM_ACCEPTED_TEXT
        )

        # Случайная задержка
        # от MIN_DELAY до MAX_DELAY минут.

        delay_minutes = random.randint(
            MIN_DELAY,
            MAX_DELAY
        )

        delay_seconds = (
            delay_minutes * 60
        )

        with users_lock:

            users[user_id][
                "offer_delay"
            ] = delay_seconds

        schedule_offer(
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
    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПИШЕТ ПОСЛЕ АНКЕТЫ
    # --------------------------------------------------------

    await message.answer(
        "Спасибо, информация получена. Ожидайте дальнейшей информации."
    )


# ============================================================
# ОБРАБОТКА TELEGRAM UPDATE
# ============================================================

async def process_update(
    update_data: dict
):

    bot = Bot(
        token=BOT_TOKEN
    )

    try:

        logger.info(
            "=" * 50
        )

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
# TELEGRAM WEBHOOK
# ============================================================

@app.route(
    WEBHOOK_PATH,
    methods=["POST"]
)
def telegram_webhook():

    logger.info(
        "=" * 50
    )

    logger.info(
        "WEBHOOK: request received"
    )

    try:

        update_data = request.get_json(
            force=True,
            silent=False
        )

        if not update_data:

            logger.warning(
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

@app.route(
    "/",
    methods=["GET"]
)
def health():

    return (
        "Telegram bot is running",
        200
    )


# ============================================================
# WEBHOOK SETUP
# ============================================================

async def setup_webhook():

    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )

    if not render_url:

        logger.error(
            "RENDER_EXTERNAL_URL not found"
        )

        return False

    webhook_url = (
        render_url.rstrip("/")
        + WEBHOOK_PATH
    )

    bot = Bot(
        token=BOT_TOKEN
    )

    try:

        logger.info(
            "Setting webhook:"
        )

        logger.info(
            "%s",
            webhook_url
        )

        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=False
        )

        info = await bot.get_webhook_info()

        logger.info(
            "Webhook successfully set"
        )

        logger.info(
            "Webhook URL: %s",
            info.url
        )

        logger.info(
            "Pending updates: %s",
            info.pending_update_count
        )

        if info.last_error_message:

            logger.warning(
                "Telegram last error: %s",
                info.last_error_message
            )

        return True

    except Exception:

        logger.exception(
            "WEBHOOK SET ERROR"
        )

        return False

    finally:

        await bot.session.close()


# ============================================================
# РУЧНАЯ УСТАНОВКА WEBHOOK
# ============================================================

@app.route(
    "/setup",
    methods=["GET"]
)
def setup_route():

    try:

        success = asyncio.run(
            setup_webhook()
        )

        if success:

            return (
                "Webhook setup completed. "
                "Check Render logs.",
                200
            )

        return (
            "Webhook setup failed. "
            "Check Render logs.",
            500
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

@app.route(
    "/webhook-info",
    methods=["GET"]
)
def webhook_info():

    async def get_info():

        bot = Bot(
            token=BOT_TOKEN
        )

        try:

            info = await bot.get_webhook_info()

            return {
                "url": info.url,
                "pending_updates": (
                    info.pending_update_count
                ),
                "last_error": (
                    info.last_error_message
                ),
                "last_error_date": (
                    str(info.last_error_date)
                    if info.last_error_date
                    else None
                )
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
# СТАТИСТИКА
# ============================================================

@app.route(
    "/stats",
    methods=["GET"]
)
def stats():

    with users_lock:

        total = len(users)

        completed = sum(
            1
            for user in users.values()
            if user.get("state")
            == "form_completed"
        )

    return {
        "total_users": total,
        "completed_forms": completed
    }, 200


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    logger.info(
        "=" * 50
    )

    logger.info(
        "Starting Telegram bot..."
    )

    logger.info(
        "=" * 50
    )

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

    logger.info(
        "=" * 50
    )

    app.run(
        host="0.0.0.0",
        port=PORT
    )
