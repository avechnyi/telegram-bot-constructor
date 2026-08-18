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

from bot_manager import (
    run_single_bot,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

ADMIN_BOT_TOKEN = os.getenv(
    "ADMIN_BOT_TOKEN"
)

ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "0"
    )
)

PORT = int(
    os.getenv(
        "PORT",
        "10000"
    )
)


if not ADMIN_BOT_TOKEN:
    raise RuntimeError(
        "ADMIN_BOT_TOKEN не найден"
    )


if not ADMIN_ID:
    raise RuntimeError(
        "ADMIN_ID не найден"
    )


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(
    __name__
)


# ============================================================
# DATABASE
# ============================================================

init_database()


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__
)


@app.get("/")
def index():

    return (
        "Bot constructor is running",
        200
    )


# ============================================================
# TELEGRAM ADMIN BOT
# ============================================================

dp = Dispatcher()


# ============================================================
# СОСТОЯНИЕ АДМИНА
# ============================================================

admin_state = {}


# ============================================================
# ЗАДАЧИ РАБОЧИХ БОТОВ
# ============================================================

worker_tasks = {}


# ============================================================
# ПРОВЕРКА АДМИНА
# ============================================================

def is_admin(
    user_id: int
):

    return (
        user_id == ADMIN_ID
    )


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
# /START
# ============================================================

@dp.message(
    CommandStart()
)
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
        "👑 КОНСТРУКТОР БОТОВ\n\n"
        "Выбери действие:",
        reply_markup=main_keyboard()
    )


# ============================================================
# СОЗДАНИЕ БОТА
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
        "➕ СОЗДАНИЕ БОТА\n\n"
        "Шаг 1 из 3.\n\n"
        "Отправь название нового бота."
    )


# ============================================================
# МОИ БОТЫ
# ============================================================

@dp.callback_query(
    lambda c: c.data == "my_bots"
)
async def my_bots_handler(
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

    text = (
        "📋 МОИ БОТЫ\n\n"
    )

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
            f"@{username.lstrip('@')}\n\n"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"⚙️ {bot['name']}",
                    callback_data=(
                        f"bot:{bot['id']}"
                    )
                )
            ]
        )

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
async def statistics_handler(
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
            "📊 Ботов пока нет."
        )

        return

    text = (
        "📊 СТАТИСТИКА\n\n"
    )

    for bot in bots:

        stats = bot_statistics(
            bot["id"]
        )

        text += (
            f"🤖 {bot['name']}\n"
            f"👥 Пользователей: "
            f"{stats['users']}\n"
            f"▶️ Стартов: "
            f"{stats['starts']}\n"
            f"ℹ️ Подробности: "
            f"{stats['details']}\n"
            f"🔗 Переходов: "
            f"{stats['curator']}\n\n"
        )

    await callback.message.answer(
        text
    )


# ============================================================
# КОНКРЕТНЫЙ БОТ
# ============================================================

@dp.callback_query(
    lambda c: c.data.startswith("bot:")
)
async def bot_details_handler(
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

    username = (
        bot["username"]
        or "не указан"
    )

    text = (
        f"🤖 {bot['name']}\n\n"
        f"Username: @{username.lstrip('@')}\n"
        f"Статус: {status}\n\n"
        f"👥 Пользователей: "
        f"{stats['users']}\n"
        f"▶️ Стартов: "
        f"{stats['starts']}\n"
        f"ℹ️ Подробности: "
        f"{stats['details']}\n"
        f"🔗 Переходов: "
        f"{stats['curator']}"
    )

    await callback.message.answer(
        text
    )


# ============================================================
# ПОЛУЧЕНИЕ ДАННЫХ ПРИ СОЗДАНИИ
# ============================================================

@dp.message()
async def admin_message_handler(
    message: types.Message
):

    user_id = (
        message.from_user.id
    )

    if not is_admin(
        user_id
    ):

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

    # ========================================================
    # НАЗВАНИЕ
    # ========================================================

    if step == "name":

        name = (
            message.text or ""
        ).strip()

        if not name:

            await message.answer(
                "Название не может быть пустым."
            )

            return

        state["name"] = name
        state["step"] = "username"

        await message.answer(
            "Шаг 2 из 3.\n\n"
            "Отправь username бота.\n\n"
            "Например:\n"
            "@my_new_bot"
        )

        return

    # ========================================================
    # USERNAME
    # ========================================================

    if step == "username":

        username = (
            message.text or ""
        ).strip()

        if username.startswith("@"):

            username = username[1:]

        if not username:

            await message.answer(
                "Username не может быть пустым."
            )

            return

        state["username"] = username
        state["step"] = "token"

        await message.answer(
            "Шаг 3 из 3.\n\n"
            "Отправь BOT TOKEN нового бота.\n\n"
            "Токен нужен для подключения бота "
            "к конструктору."
        )

        return

    # ========================================================
    # TOKEN
    # ========================================================

    if step == "token":

        token = (
            message.text or ""
        ).strip()

        if not token:

            await message.answer(
                "Токен не может быть пустым."
            )

            return

        test_bot = None

        try:

            test_bot = Bot(
                token=token
            )

            info = await test_bot.get_me()

        except Exception:

            logger.exception(
                "TOKEN VALIDATION ERROR"
            )

            await message.answer(
                "❌ Токен не прошёл проверку.\n\n"
                "Проверь его в BotFather "
                "и отправь ещё раз."
            )

            return

        finally:

            if test_bot:

                await test_bot.session.close()

        try:

            bot_id = add_bot(
                name=state["name"],
                username=state["username"],
                token=token
            )

        except Exception:

            logger.exception(
                "DATABASE BOT CREATE ERROR"
            )

            await message.answer(
                "❌ Не удалось сохранить бота.\n\n"
                "Возможно, этот токен уже добавлен."
            )

            return

        # ----------------------------------------------------
        # СОЗДАЁМ ЗАДАЧУ РАБОЧЕГО БОТА
        # ----------------------------------------------------

        bot_record = get_bot(
            bot_id
        )

        task = asyncio.create_task(
            run_single_bot(
                bot_record
            )
        )

        worker_tasks[
            bot_id
        ] = task

        admin_state.pop(
            user_id,
            None
        )

        await message.answer(
            "✅ БОТ СОЗДАН\n\n"
            f"Название: {state['name']}\n"
            f"Username: @{state['username']}\n"
            f"Telegram: @{info.username}\n\n"
            "🟢 Бот добавлен в конструктор.\n\n"
            "Теперь он использует общий шаблон.",
            reply_markup=main_keyboard()
        )

        logger.info(
            "BOT CREATED: id=%s username=%s",
            bot_id,
            state["username"]
        )

        return


# ============================================================
# ЗАПУСК АДМИНКИ
# ============================================================

async def run_admin():

    bot = Bot(
        token=ADMIN_BOT_TOKEN
    )

    try:

        logger.info(
            "ADMIN BOT STARTED"
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
        "Starting constructor..."
    )

    asyncio.run(
        run_admin()
    )
