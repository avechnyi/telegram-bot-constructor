import os
import asyncio
import logging

from flask import Flask, request

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Update


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

PORT = int(os.getenv("PORT", "10000"))

WEBHOOK_PATH = os.getenv(
    "WEBHOOK_PATH",
    "/telegram/webhook"
)


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден в Environment Variables"
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
# START
# ============================================================

@dp.message(CommandStart())
async def start_handler(message: types.Message):

    user_id = message.from_user.id

    logger.info(
        "START FROM USER: %s",
        user_id
    )

    await message.answer(
        "Привет 👋\n\n"
        "Чтобы начать, напиши немного о себе."
    )

    logger.info(
        "START SENT TO USER: %s",
        user_id
    )


# ============================================================
# Обычные сообщения
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

    if text:

        await message.answer(
            "Получила сообщение 👌\n\n"
            "Расскажи немного о себе и своём опыте."
        )


# ============================================================
# PROCESS UPDATE
# ============================================================

async def process_update(update_data: dict):

    bot = Bot(
        token=BOT_TOKEN
    )

    try:

        logger.info(
            "PROCESS UPDATE: %s",
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
            "UPDATE FINISHED: %s",
            update_data.get("update_id")
        )

    except Exception:

        logger.exception(
            "UPDATE PROCESS ERROR"
        )

        raise

    finally:

        await bot.session.close()


# ============================================================
# WEBHOOK
# ============================================================

@app.route(
    WEBHOOK_PATH,
    methods=["POST"]
)
def telegram_webhook():

    logger.info(
        "=========================================="
    )

    logger.info(
        "WEBHOOK REQUEST RECEIVED"
    )

    try:

        update_data = request.get_json(
            force=True
        )

        if not update_data:

            logger.warning(
                "EMPTY TELEGRAM UPDATE"
            )

            return "ok", 200

        logger.info(
            "UPDATE ID: %s",
            update_data.get("update_id")
        )

        asyncio.run(
            process_update(
                update_data
            )
        )

        logger.info(
            "WEBHOOK FINISHED"
        )

        return "ok", 200

    except Exception:

        logger.exception(
            "WEBHOOK ERROR"
        )

        return "ok", 200


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/")
def health():

    return (
        "Telegram bot is running",
        200
    )


# ============================================================
# SETUP WEBHOOK
# ============================================================

@app.route("/setup")
def setup():

    async def setup_async():

        bot = Bot(
            token=BOT_TOKEN
        )

        try:

            # Получаем внешний адрес Render
            render_url = os.getenv(
                "RENDER_EXTERNAL_URL"
            )

            if not render_url:

                render_url = request.url_root.rstrip("/")

            webhook_url = (
                render_url.rstrip("/")
                + WEBHOOK_PATH
            )

            logger.info(
                "SETTING WEBHOOK:"
            )

            logger.info(
                "%s",
                webhook_url
            )

            await bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )

            info = await bot.get_webhook_info()

            logger.info(
                "WEBHOOK URL: %s",
                info.url
            )

            logger.info(
                "PENDING: %s",
                info.pending_update_count
            )

            return (
                "<h2>Webhook successfully set ✅</h2>"
                f"<p>{info.url}</p>"
            )

        except Exception as e:

            logger.exception(
                "WEBHOOK SET ERROR"
            )

            return (
                "<h2>Webhook error ❌</h2>"
                f"<pre>{e}</pre>"
            )

        finally:

            await bot.session.close()

    return asyncio.run(
        setup_async()
    )


# ============================================================
# WEBHOOK INFO
# ============================================================

@app.route("/info")
def webhook_info():

    async def get_info():

        bot = Bot(
            token=BOT_TOKEN
        )

        try:

            info = await bot.get_webhook_info()

            return (
                "<h2>Webhook info</h2>"
                f"<p><b>URL:</b> {info.url}</p>"
                f"<p><b>Pending:</b> "
                f"{info.pending_update_count}</p>"
                f"<p><b>Last error:</b> "
                f"{info.last_error_message}</p>"
            )

        except Exception as e:

            return (
                "<pre>"
                f"{e}"
                "</pre>"
            )

        finally:

            await bot.session.close()

    return asyncio.run(
        get_info()
    )


# ============================================================
# DELETE WEBHOOK
# ============================================================

@app.route("/delete-webhook")
def delete_webhook():

    async def delete_async():

        bot = Bot(
            token=BOT_TOKEN
        )

        try:

            await bot.delete_webhook(
                drop_pending_updates=True
            )

            return (
                "<h2>Webhook deleted ✅</h2>"
            )

        except Exception as e:

            return (
                "<pre>"
                f"{e}"
                "</pre>"
            )

        finally:

            await bot.session.close()

    return asyncio.run(
        delete_async()
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    logger.info(
        "=========================================="
    )

    logger.info(
        "STARTING TELEGRAM BOT"
    )

    logger.info(
        "PORT: %s",
        PORT
    )

    logger.info(
        "WEBHOOK PATH: %s",
        WEBHOOK_PATH
    )

    logger.info(
        "=========================================="
    )

    app.run(
        host="0.0.0.0",
        port=PORT
    )
