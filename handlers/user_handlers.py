# handlers/user_handlers.py

import logging
import re
from aiogram import Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
import phonenumbers

from database.requests import add_user, get_user
from bot_commands import set_user_commands
from config import ADMIN_IDS
from handlers.admin_handlers import admin_keyboard

# Создаем именованный логгер для этого файла
logger = logging.getLogger(__name__)

router = Router()

class Registration(StatesGroup):
    waiting_for_phone_number = State()

# --- Обработчик команды /help с красивым оформлением ---
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    # Проверяем, является ли пользователь администратором
    if user_id in ADMIN_IDS:
        logger.info(f"Администратор {user_id} запросил справку.")
        admin_help_text = (
            "<b>⚙️ Справка для Администратора</b>\n\n"
            "Вы вошли в режим администратора. Вам доступны следующие функции для управления ботом:\n\n"
            "<b>Управление пользователями:</b>\n"
            "  <code>👥 Список пользователей</code>\n"
            "  <i>Показывает полный список зарегистрированных пользователей, их номера телефонов и Telegram ID.</i>\n\n"
            "  <code>📎 Назначить данные</code>\n"
            "  <i>Запускает пошаговый процесс привязки конфигурации (bot_id, api_key, trunk_id) к номеру телефона пользователя. Эта связка определяет, какие уведомления будет получать клиент.</i>\n\n"
            "<b>Управление шаблонами:</b>\n"
            "  <code>📄 Показать шаблон</code>\n"
            "  <i>Показывает текущий активный шаблон, по которому формируются все уведомления.</i>\n\n"
            "  <code>✏️ Редактировать шаблон</code>\n"
            "  <i>Позволяет установить новый шаблон. Поддерживаются HTML-теги для форматирования и переменные.</i>\n\n"
            "<b>Основные команды:</b>\n"
            "  /start или /admin - <i>Показать главное меню и клавиатуру.</i>\n"
            "  /help - <i>Показать эту справку.</i>"
        )
        await message.answer(admin_help_text, parse_mode="HTML")
    else:
        logger.info(f"Пользователь {user_id} запросил справку.")
        user_help_text = (
            "<b>ℹ️ Справка по работе с ботом</b>\n\n"
            "Привет! Я бот для отправки уведомлений о результатах работы вашего голосового робота.\n\n"
            "<b>Как начать получать уведомления?</b>\n"
            "1. Используйте команду /start.\n"
            "2. Отправьте боту ваш номер телефона в формате <code>+7XXXXXXXXXX</code>.\n"
            "3. После успешной регистрации, администратор должен будет привязать к вашему номеру конфигурацию голосового бота.\n\n"
            "Как только всё будет настроено, вы начнёте автоматически получать отчеты о звонках.\n\n"
            "<b>Доступные команды:</b>\n"
            "  /start - <i>Начать работу или перезапустить бота.</i>\n"
            "  /help - <i>Показать эту справку.</i>"
        )
        await message.answer(user_help_text, parse_mode="HTML")


# --- Обработчик команды /start (без изменений) ---
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    await set_user_commands(bot, user_id)
    await state.clear()

    if user_id in ADMIN_IDS:
        logger.info(f"Администратор {user_id} запустил бота.")
        await message.answer(
            "Добро пожаловать, Администратор!\n"
            "Используйте клавиатуру ниже или меню команд для управления ботом.",
            reply_markup=admin_keyboard()
        )
        return

    logger.info(f"Пользователь {user_id} запустил бота.")
    user = await get_user(user_id)
    if user:
        logger.info(f"Пользователь {user_id} уже зарегистрирован с номером {user.phone_number}.")
        await message.answer(f"Вы уже зарегистрированы с номером {user.phone_number}.")
        return

    logger.info(f"Пользователь {user_id} начинает процесс регистрации.")
    await message.answer(
        "Добрый день. Укажите Ваш номер телефона в формате +7XXXXXXXXXX, "
        "чтобы получать уведомления о работе Вашего бота."
    )
    await state.set_state(Registration.waiting_for_phone_number)


# --- Обработчик получения номера (без изменений) ---
@router.message(Registration.waiting_for_phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone_number = message.text
    logger.info(f"Пользователь {user_id} ввел номер телефона: '{phone_number}'")

    try:
        cleaned_phone = re.sub(r'[^\d+]', '', phone_number)
        parsed_phone = phonenumbers.parse(cleaned_phone, "RU")
        if not phonenumbers.is_valid_number(parsed_phone) or parsed_phone.country_code != 7:
            raise ValueError("Некорректный российский номер")
            
        normalized_phone = phonenumbers.format_number(
            parsed_phone, phonenumbers.PhoneNumberFormat.E164
        )
        
        logger.debug(f"Номер {phone_number} для пользователя {user_id} нормализован в {normalized_phone}")
        result = await add_user(user_id, normalized_phone)

        if result == "ok":
            logger.info(f"Пользователь {user_id} успешно зарегистрирован с номером {normalized_phone}.")
            await message.answer(
                f"Вы успешно зарегистрированы с номером {normalized_phone}.\n"
                "Ожидайте уведомлений о звонках."
            )
            await state.clear()
        elif result == "user_exists":
            logger.warning(f"Пользователь {user_id} уже был зарегистрирован. (Обнаружено на этапе ввода номера)")
            await message.answer("Вы уже были зарегистрированы.")
            await state.clear()
        elif result == "phone_exists":
            logger.warning(f"Пользователь {user_id} попытался зарегистрировать уже используемый номер {normalized_phone}.")
            await message.answer("Этот номер телефона уже используется другим пользователем.")
        
    except Exception as e:
        logger.warning(f"Пользователь {user_id} ввел некорректный номер '{phone_number}'. Ошибка: {e}")
        await message.answer(
            "Номер телефона введен некорректно. "
            "Пожалуйста, попробуйте еще раз. Пример: +79123456789"
        )