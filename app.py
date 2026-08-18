import os
import asyncio
import logging

from flask import Flask

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")

if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID не найден")


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


@app.get("/")
def index():
    return "Admin bot is running"


# ============================================================
# TELEGRAM
# ============================================================

dp = Dispatcher()


# ============================================================
# АДМИН-КЛАВИАТУРА
# ============================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Создать бота",
                    callback_data="create_bot"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Мои боты",
                    callback_data="my_bots"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="statistics"
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

    # Только владелец админки
    if user_id != ADMIN_ID:

        await message.answer(
            "Доступ запрещён."
        )

        return

    await message.answer(
        "👑 Панель управления\n\n"
        "Здесь ты сможешь управлять своими "
        "Telegram-ботами.",
        reply_markup=admin_keyboard()
    )


# ============================================================
# КНОПКИ
# ============================================================

@dp.callback_query()
async def callback_handler(
    callback: types.CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Доступ запрещён",
            show_alert=True
        )

        return

    await callback.answer()

    if callback.data == "create_bot":

        await callback.message.answer(
            "➕ Создание бота\n\n"
            "Следующим шагом здесь будет форма, "
            "куда ты вставишь токен нового бота."
        )

    elif callback.data == "my_bots":

        await callback.message.answer(
            "📋 Мои боты\n\n"
            "Пока ботов нет."
        )

    elif callback.data == "statistics":

        await callback.message.answer(
            "📊 Статистика\n\n"
            "Пока статистики нет."
        )


# ============================================================
# WEBHOOK
# ============================================================

async def run_bot():

    bot = Bot(
        token=BOT_TOKEN
    )

    try:

        await dp.start_polling(
            bot
        )

    finally:

        await bot.session.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    logger.info(
        "Starting admin bot..."
    )

    # Запускаем Telegram polling
    asyncio.run(
        run_bot()
    )
