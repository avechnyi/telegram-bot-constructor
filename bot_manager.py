import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database import (
    get_bots,
    add_user,
    add_event,
)


logger = logging.getLogger(__name__)


# ============================================================
# РАБОЧИЕ БОТЫ
# ============================================================

running_bots = {}


# ============================================================
# ТЕКСТЫ ШАБЛОНА
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


VACANCY_TEXT = """К сожалению, на первоначальную вакансию уже выбран другой кандидат.

Мы можем предложить вам рассмотреть другую позицию в нашей команде.

Работа полностью удалённая, график свободный, обучение предоставляются.

Если предложение вам интересно, нажмите кнопку ниже, чтобы узнать подробности👇"""


DETAILS_TEXT = """Здесь размещается подробное описание вакансии.

Укажите реальные условия работы, задачи, требования, порядок обучения и условия оплаты.

Перед началом работы пользователь должен получить полную информацию об условиях и рисках."""


CURATOR_TEXT = """Для связи с менеджером для дальнейшей работы вам необходимо:

1. Перейти в бота команды по кнопке ниже.
2. Нажать «Старт».
3. Получить контакт свободного куратора и написать ему, что вы хотите попасть в команду."""


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


def curator_keyboard(url):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Связаться ↗",
                    url=url
                )
            ]
        ]
    )


# ============================================================
# ЗАПУСК ОДНОГО БОТА
# ============================================================

async def run_single_bot(
    bot_record
):

    bot_id = bot_record["id"]
    token = bot_record["token"]

    logger.info(
        "Starting worker bot %s",
        bot_id
    )

    bot = Bot(
        token=token
    )

    dp = Dispatcher()

    # --------------------------------------------------------
    # СТАРТ
    # --------------------------------------------------------

    @dp.message(CommandStart())
    async def start_handler(
        message: types.Message
    ):

        user_id = message.from_user.id

        logger.info(
            "BOT %s: START FROM %s",
            bot_id,
            user_id
        )

        add_user(
            bot_id=bot_id,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )

        add_event(
            bot_id=bot_id,
            telegram_id=user_id,
            event="start"
        )

        await message.answer(
            START_TEXT
        )

    # --------------------------------------------------------
    # КНОПКА ПОДРОБНОСТЕЙ
    # --------------------------------------------------------

    @dp.callback_query(
        lambda callback: callback.data == "details"
    )
    async def details_handler(
        callback: types.CallbackQuery
    ):

        user_id = callback.from_user.id

        logger.info(
            "BOT %s: DETAILS FROM %s",
            bot_id,
            user_id
        )

        add_event(
            bot_id=bot_id,
            telegram_id=user_id,
            event="details"
        )

        await callback.answer()

        await callback.message.answer(
            DETAILS_TEXT
        )

        # Здесь пока используем URL из переменной окружения.
        # Позже сделаем индивидуальную ссылку в настройках
        # каждого бота.

        curator_url = (
            bot_record.get("curator_url")
            or "https://t.me/"
        )

        await callback.message.answer(
            CURATOR_TEXT,
            reply_markup=curator_keyboard(
                curator_url
            )
        )

    # --------------------------------------------------------
    # ОБЫЧНЫЕ СООБЩЕНИЯ
    # --------------------------------------------------------

    @dp.message()
    async def message_handler(
        message: types.Message
    ):

        user_id = message.from_user.id

        logger.info(
            "BOT %s: MESSAGE FROM %s",
            bot_id,
            user_id
        )

        add_user(
            bot_id=bot_id,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )

        await message.answer(
            FORM_ACCEPTED_TEXT
        )

    try:

        await dp.start_polling(
            bot
        )

    except asyncio.CancelledError:

        logger.info(
            "BOT %s: polling cancelled",
            bot_id
        )

        raise

    except Exception:

        logger.exception(
            "BOT %s: polling error",
            bot_id
        )

    finally:

        await bot.session.close()


# ============================================================
# ЗАПУСК ВСЕХ БОТОВ
# ============================================================

async def start_all_bots():

    bot_records = get_bots()

    if not bot_records:

        logger.info(
            "No worker bots found"
        )

        return

    tasks = []

    for bot_record in bot_records:

        if not bot_record["enabled"]:
            continue

        task = asyncio.create_task(
            run_single_bot(
                bot_record
            )
        )

        running_bots[
            bot_record["id"]
        ] = task

        tasks.append(
            task
        )

    if tasks:

        await asyncio.gather(
            *tasks
        )
