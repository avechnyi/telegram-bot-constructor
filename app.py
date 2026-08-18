import os
import asyncio
import logging
import random
from typing import Dict, Any

from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
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

# Простое хранение состояния в памяти.
# Для одного процесса подходит для тестирования.
users: Dict[int, Dict[str, Any]] = {}

# Задачи отложенных сообщений.
scheduled_tasks: Dict[int, asyncio.Task] = {}


# ============================================================
# ТЕКСТЫ
# ============================================================

QUESTIONNAIRE_TEXT = """Здравствуйте 🤝

Расскажите немного о себе:

— Где работали раньше и чем занимались?
— Сколько Вам лет?
— Был ли опыт удалённой работы?

И буквально пару слов о себе: какие у Вас сильные стороны, что хорошо получается, как обычно подходите к работе 🙂"""


REVIEW_TEXT = """Спасибо за заполнение анкеты 🤝

Ваша анкета отправлена на рассмотрение.
Ожидайте ответ."""


OFFER_TEXT = """К сожалению, на данную вакансию уже утвердили другого кандидата.
Мы можем предложить вам другую позицию в нашей команде:

Сейчас открыта новая удалённая позиция.
Работа полностью удалённая, график свободный, обучение предоставляем.

Если вас заинтересовало данное предложение, нажмите кнопку ниже чтобы узнать подробности👇"""


DETAILS_TEXT = """Наша команда занимается работой с цифровыми активами и аналитикой рынка.

Перед началом работы кандидат получает информацию о задачах, условиях, порядке обучения и возможных рисках.

Все условия обсуждаются с ответственным специалистом до начала работы.

Если предложение вам подходит, свяжитесь с менеджером для получения подробной информации."""


CONTACT_TEXT = """Для связи с менеджером для дальнейшей работы вам необходимо:

1. Перейти в бота команды по кнопке ниже.
2. Нажать «Старт».
3. Получить контакт свободного куратора и написать ему, что вы хотите попасть в команду."""


# ============================================================
# КНОПКИ
# ============================================================

def details_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Узнать подробности",
                    callback_data="show_details"
                )
            ]
        ]
    )


def contact_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Связаться ↗",
                    url="https://t.me/usdteamrubot?start=6a76eafa1c83616169c692b9"
                )
            ]
        ]
    )


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

    users[user_id] = {
        "state": "questionnaire",
        "answer": None,
    }

    await message.answer(
        QUESTIONNAIRE_TEXT
    )

    logger.info(
        "QUESTIONNAIRE SENT TO USER: %s",
        user_id
    )


# ============================================================
# КНОПКА "УЗНАТЬ ПОДРОБНОСТИ"
# ============================================================

@dp.callback_query(lambda callback: callback.data == "show_details")
async def details_handler(callback: types.CallbackQuery):

    user_id = callback.from_user.id

    logger.info(
        "DETAILS BUTTON FROM USER: %s",
        user_id
    )

    await callback.answer()

    await callback.message.answer(
        DETAILS_TEXT
    )

    await callback.message.answer(
        CONTACT_TEXT,
        reply_markup=contact_keyboard()
    )


# ============================================================
# ОТЛОЖЕННАЯ ОТПРАВКА
# ============================================================

async def send_delayed_offer(
    bot: Bot,
    user_id: int
):

    try:

        # Случайная задержка.
        # Сейчас от 5 до 10 минут.
        delay = random.randint(
            5 * 60,
            10 * 60
        )

        logger.info(
            "USER %s: offer scheduled in %s seconds",
            user_id,
            delay
        )

        await asyncio.sleep(delay)

        # Проверяем, что пользователь всё ещё существует.
        if user_id not in users:
            return

        await bot.send_message(
            chat_id=user_id,
            text=OFFER_TEXT,
            reply_markup=details_keyboard()
        )

        logger.info(
            "OFFER SENT TO USER: %s",
            user_id
        )

    except asyncio.CancelledError:

        logger.info(
            "SCHEDULE CANCELLED FOR USER: %s",
            user_id
        )

        raise

    except Exception:

        logger.exception(
            "DELAYED OFFER ERROR FOR USER: %s",
            user_id
        )

    finally:

        scheduled_tasks.pop(
            user_id,
            None
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

    user = users.get(user_id)

    # Если пользователь ещё не запускал бота
    if not user:

        await message.answer(
            "Нажмите /start, чтобы начать."
        )

        return

    # Если пользователь заполняет анкету
    if user.get("state") == "questionnaire":

        user["answer"] = text
        user["state"] = "waiting"

        await message.answer(
            REVIEW_TEXT
        )

        # Отменяем старую задачу, если она вдруг существует
        old_task = scheduled_tasks.get(user_id)

        if old_task:

            old_task.cancel()

        # Создаём отдельный Bot для фоновой задачи
        bot = Bot(token=BOT_TOKEN)

        task = asyncio.create_task(
            send_delayed_offer(
                bot,
                user_id
            )
        )

        scheduled_tasks[user_id] = task

        logger.info(
            "USER %s: questionnaire completed",
            user_id
        )

        return

    # Если анкета уже заполнена
    if user.get("state") == "waiting":

        await message.answer(
            "Спасибо, ваша анкета уже находится на рассмотрении."
        )

        return


# ============================================================
# ОБРАБОТКА UPDATE
# ============================================================

async def process_update(
    update_data: dict
):

    bot = Bot(
        token=BOT_TOKEN
    )

    try:

        update_id = update_data.get(
            "update_id"
        )

        logger.info("=" * 60)

        logger.info(
            "PROCESS: update %s",
            update_id
        )

        update = Update.model_validate(
            update_data
        )

        await dp.feed_update(
            bot,
            update
        )

        logger.info(
            "PROCESS: finished update %s",
            update_id
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
        "=" * 60
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
            "WEBHOOK: update %s processed",
            update_id
        )

        return "ok", 200

    except Exception:

        logger.exception(
            "WEBHOOK PROCESS ERROR"
        )

        # Возвращаем 200, чтобы Telegram
        # не создавал бесконечные повторные попытки.
        return "ok", 200


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def health():

    return "Bot is running", 200


# ============================================================
# РУЧНАЯ УСТАНОВКА WEBHOOK
# ============================================================

async def setup_webhook():

    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )

    if not render_url:

        raise RuntimeError(
            "RENDER_EXTERNAL_URL не найден"
        )

    webhook_url = (
        render_url.rstrip("/")
        + WEBHOOK_PATH
    )

    bot = Bot(
        token=BOT_TOKEN
    )

    try:

        logger.info(
            "=" * 60
        )

        logger.info(
            "SETTING WEBHOOK"
        )

        logger.info(
            "WEBHOOK URL: %s",
            webhook_url
        )

        # Устанавливаем webhook
        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=False
        )

        logger.info(
            "WEBHOOK SUCCESSFULLY SET"
        )

        # Получаем информацию о webhook
        info = await bot.get_webhook_info()

        logger.info(
            "TELEGRAM WEBHOOK URL: %s",
            info.url
        )

        logger.info(
            "PENDING UPDATES: %s",
            info.pending_update_count
        )

        logger.info(
            "LAST ERROR DATE: %s",
            info.last_error_date
        )

        logger.info(
            "LAST ERROR MESSAGE: %s",
            info.last_error_message
        )

        logger.info(
            "=" * 60
        )

    finally:

        await bot.session.close()


# ============================================================
# РУЧНОЙ /setup
# ============================================================

@app.route(
    "/setup",
    methods=["GET"]
)
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
# START
# ============================================================

if __name__ == "__main__":

    logger.info(
        "=" * 60
    )

    logger.info(
        "STARTING TELEGRAM BOT"
    )

    logger.info(
        "WEBHOOK PATH: %s",
        WEBHOOK_PATH
    )

    logger.info(
        "PORT: %s",
        PORT
    )

    logger.info(
        "=" * 60
    )

    # Автоматически ставим webhook
    try:

        asyncio.run(
            setup_webhook()
        )

    except Exception:

        logger.exception(
            "STARTUP WEBHOOK SETUP ERROR"
        )

    logger.info(
        "STARTING FLASK"
    )

    app.run(
        host="0.0.0.0",
        port=PORT
    )
