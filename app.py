import os
import asyncio
import logging

from flask import Flask

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database import (
    init_database,
    add_bot,
    get_bots,
    get_bot,
    bot_statistics,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", "10000"))

if not ADMIN_BOT_TOKEN:
    raise RuntimeError(
        "ADMIN_BOT_TOKEN не найден в Environment"
    )

if not ADMIN_ID:
    raise RuntimeError(
        "ADMIN_ID не найден в Environment"
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


@app.get("/")
def index():
    return "Bot constructor is running", 200


# ============================================================
# TELEGRAM
# ============================================================

dp = Dispatcher()


# ============================================================
# СОСТОЯНИЕ АДМИНА
# ============================================================

admin_state = {}


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def main_keyboard():

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
# ПРОВЕРКА АДМИНА
# ============================================================

def is_admin(user_id: int):

    return user_id == ADMIN_ID


# ============================================================
# /START
# ============================================================

@dp.message(CommandStart())
async def start_handler(
    message: types.Message
):

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "Доступ запрещён."
        )

        return

    admin_state.pop(
        message.from_user.id,
        None
    )

    await message.answer(
        "👑 Конструктор ботов\n\n"
        "Выбери действие:",
        reply_markup=main_keyboard()
    )


# ============================================================
# КНОПКА «СОЗДАТЬ БОТА»
# ============================================================

@dp.callback_query(
    lambda c: c.data == "create_bot"
)
async def create_bot_start(
    callback: types.CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Доступ запрещён",
            show_alert=True
        )

        return

    await callback.answer()

    admin_state[
        callback.from_user.id
    ] = {
        "step": "name"
    }

    await callback.message.answer(
        "➕ Создание нового бота\n\n"
        "Шаг 1 из 3.\n\n"
        "Отправь название бота."
    )


# ============================================================
# МОИ БОТЫ
# ============================================================

@dp.callback_query(
    lambda c: c.data == "my_bots"
)
async def my_bots(
    callback: types.CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Доступ запрещён",
            show_alert=True
        )

        return

    await callback.answer()

    bots = get_bots()

    if not bots:

        await callback.message.answer(
            "📋 Ботов пока нет.\n\n"
            "Нажми «➕ Создать бота»."
        )

        return

    text = "📋 Твои боты:\n\n"

    buttons = []

    for bot in bots:

        status = (
            "🟢"
            if bot["enabled"]
            else "🔴"
        )

        username = (
            bot["username"]
            or "без username"
        )

        text += (
            f"{status} {bot['name']}\n"
            f"   @{username.lstrip('@')}\n\n"
        )

        buttons.append([
            InlineKeyboardButton(
                text=f"⚙️ {bot['name']}",
                callback_data=f"bot:{bot['id']}"
            )
        ])

    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )


# ============================================================
# СТАТИСТИКА
# ============================================================

@dp.callback_query(
    lambda c: c.data == "statistics"
)
async def statistics(
    callback: types.CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Доступ запрещён",
            show_alert=True
        )

        return

    await callback.answer()

    bots = get_bots()

    if not bots:

        await callback.message.answer(
            "📊 Пока нет ботов для статистики."
        )

        return

    text = "📊 Статистика\n\n"

    for bot in bots:

        stats = bot_statistics(
            bot["id"]
        )

        text += (
            f"🤖 {bot['name']}\n"
            f"👥 Пользователей: {stats['users']}\n"
            f"▶️ Стартов: {stats['starts']}\n"
            f"ℹ️ Подробности: {stats['details']}\n"
            f"🔗 Куратор: {stats['curator']}\n\n"
        )

    await callback.message.answer(
        text
    )


# ============================================================
# ОТКРЫТИЕ КОНКРЕТНОГО БОТА
# ============================================================

@dp.callback_query(
    lambda c: c.data.startswith("bot:")
)
async def bot_details(
    callback: types.CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Доступ запрещён",
            show_alert=True
        )

        return

    await callback.answer()

    bot_id = int(
        callback.data.split(":")[1]
    )

    bot = get_bot(
        bot_id
    )

    if not bot:

        await callback.message.answer(
            "Бот не найден."
        )

        return

    stats = bot_statistics(
        bot_id
    )

    status = (
        "🟢 Работает"
        if bot["enabled"]
        else "🔴 Выключен"
    )

    text = (
        f"🤖 {bot['name']}\n\n"
        f"Username: @{(bot['username'] or '').lstrip('@')}\n"
        f"Статус: {status}\n\n"
        f"👥 Пользователей: {stats['users']}\n"
        f"▶️ Стартов: {stats['starts']}\n"
        f"ℹ️ Подробности: {stats['details']}\n"
        f"🔗 Куратор: {stats['curator']}"
    )

    await callback.message.answer(
        text
    )


# ============================================================
# ПОЛУЧЕНИЕ ТЕКСТОВ ОТ АДМИНА
# ============================================================

@dp.message()
async def admin_messages(
    message: types.Message
):

    user_id = message.from_user.id

    if not is_admin(user_id):

        return

    state = admin_state.get(
        user_id
    )

    if not state:

        await message.answer(
            "Используй /start.",
            reply_markup=main_keyboard()
        )

        return

    step = state.get(
        "step"
    )

    # --------------------------------------------------------
    # НАЗВАНИЕ
    # --------------------------------------------------------

    if step == "name":

        state["name"] = (
            message.text or ""
        ).strip()

        state["step"] = "username"

        await message.answer(
            "Шаг 2 из 3.\n\n"
            "Отправь username нового бота.\n\n"
            "Например:\n"
            "@my_new_bot"
        )

        return

    # --------------------------------------------------------
    # USERNAME
    # --------------------------------------------------------

    if step == "username":

        state["username"] = (
            message.text or ""
        ).strip()

        state["step"] = "token"

        await message.answer(
            "Шаг 3 из 3.\n\n"
            "Отправь BOT TOKEN нового бота.\n\n"
            "Токен не публикуй в чатах или GitHub."
        )

        return

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    if step == "token":

        token = (
            message.text or ""
        ).strip()

        name = state["name"]
        username = state["username"]

        try:

            # Проверяем токен через Telegram
            test_bot = Bot(
                token=token
            )

            info = await test_bot.get_me()

            await test_bot.session.close()

        except Exception:

            await message.answer(
                "❌ Токен не прошёл проверку.\n\n"
                "Проверь BOT TOKEN и отправь его ещё раз."
            )

            return

        try:

            bot_id = add_bot(
                name=name,
                username=username,
                token=token
            )

        except Exception:

            logger.exception(
                "BOT SAVE ERROR"
            )

            await message.answer(
                "❌ Не удалось сохранить бота."
            )

            return

        admin_state.pop(
            user_id,
            None
        )

        await message.answer(
            "✅ Бот добавлен!\n\n"
            f"Название: {name}\n"
            f"Username: @{username.lstrip('@')}\n"
            f"Telegram: @{info.username}\n\n"
            "Теперь он появился в списке ботов.",
            reply_markup=main_keyboard()
        )

        logger.info(
            "NEW BOT CREATED: %s (%s)",
            bot_id,
            username
        )


# ============================================================
# ЗАПУСК
# ============================================================

async def run_bot():

    bot = Bot(
        token=ADMIN_BOT_TOKEN
    )

    try:

        logger.info(
            "Admin bot started"
        )

        await dp.start_polling(
            bot
        )

    finally:

        await bot.session.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info(
        "Initializing database..."
    )

    init_database()

    logger.info(
        "Starting admin bot..."
    )

    asyncio.run(
        run_bot()
    )
