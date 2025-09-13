# handlers/admin_handlers.py

import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import html
from datetime import datetime

from config import ADMIN_IDS
from database.requests import (get_all_users, get_user_by_phone,
                               add_user_config, get_active_template, set_new_template)
from bot_commands import set_user_commands
from g_sheets import export_to_google_sheet

# Создаем именованный логгер для этого файла
logger = logging.getLogger(__name__)

# --- Вспомогательная функция для экранирования (остается без изменений) ---
def escape_md_v2(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(f'\\{char}' if char in escape_chars else char for char in text)

# --- Фильтр для проверки на админа (остается без изменений) ---
class IsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id in ADMIN_IDS

# --- Классы состояний (FSM) (остаются без изменений) ---
class AssignData(StatesGroup):
    waiting_for_phone = State()
    waiting_for_bot_id = State()
    waiting_for_api_key = State()
    waiting_for_trunk_id = State()

class EditTemplate(StatesGroup):
    waiting_for_template = State()

# --- Роутер и его фильтрация (остается без изменений) ---
router = Router()
router.message.filter(IsAdmin())

# --- ОБНОВЛЕННАЯ КЛАВИАТУРА ДЛЯ АДМИН-МЕНЮ ---
def admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="👥 Список пользователей")
    builder.button(text="📎 Назначить данные")
    builder.button(text="📄 Показать шаблон")
    builder.button(text="✏️ Редактировать шаблон")
    builder.button(text="📢 Тестовая рассылка")
    builder.button(text="📈 Экспорт в Google Sheets") # <--- ДОБАВЬТЕ КНОПКУ
    builder.adjust(2, 2, 2) # Новое расположение кнопок
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите действие:")

# --- Обработчики команд ---

@router.message(Command("admin"))
async def cmd_admin(message: types.Message, bot: Bot):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} вошел в админ-панель.")
    await set_user_commands(bot, admin_id)
    await message.answer("Вы вошли в панель администратора.", reply_markup=admin_keyboard())

# Универсальный обработчик для отмены
@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cmd_cancel(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    current_state = await state.get_state()
    if current_state is None:
        logger.debug(f"Администратор {admin_id} попытался отменить действие, не находясь в состоянии.")
        await message.answer("Нет активной операции для отмены.", reply_markup=admin_keyboard())
        return
    
    logger.info(f"Администратор {admin_id} отменил действие в состоянии {current_state}.")
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=admin_keyboard())

# Команда /list_users
@router.message(Command("list_users"))
@router.message(F.text == "👥 Список пользователей")
async def cmd_list_users(message: types.Message):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} запросил список пользователей.")
    users = await get_all_users()
    if not users:
        await message.answer("Зарегистрированных пользователей пока нет.")
        return
    user_list_parts = ["<b>Список зарегистрированных пользователей:</b>\n"]
    for user in users:
        line = f"📞 <code>{user.phone_number}</code> (ID: <code>{user.telegram_id}</code>)\n"
        user_list_parts.append(line)
    await message.answer("".join(user_list_parts), parse_mode="HTML")

# --- Тестовая рассылка ---
@router.message(Command("test_broadcast"))
@router.message(F.text == "📢 Тестовая рассылка")
async def cmd_test_broadcast(message: types.Message, bot: Bot):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} инициировал тестовую рассылку.")

    template = await get_active_template()

    if not template:
        logger.warning(f"Администратор {admin_id} пытался запустить тест без активного шаблона.")
        await message.answer("❌ Не найден активный шаблон. Сначала установите его с помощью команды '✏️ Редактировать шаблон'.")
        return

    # Создаем тестовые данные для подстановки
    test_data = {
        "datetime": datetime.now().strftime('%d.%m.%Y %H:%M'),
        "audioLink": "https://example.com/test_record.mp3",
        "transcription": "Это тестовая транскрипция звонка. Клиент выразил заинтересованность.",
        "var_is_actual": "Тест",
        "var_result": "Результат: Тестовый звонок успешно завершен."
    }

    try:
        # Формируем сообщение по шаблону
        message_text = template.template_text.format(**test_data)
        
        # Отправляем сообщение самому себе (администратору)
        await bot.send_message(
            chat_id=admin_id,
            text=message_text,
            parse_mode="HTML"
        )
        
        await message.answer("✅ В таком виде пользователи будут получать уведомленния.")
        logger.info(f"Тестовое уведомление успешно отправлено администратору {admin_id}.")

    except KeyError as e:
        # Эта проверка сработает, если админ в шаблоне допустил опечатку в имени переменной
        logger.error(f"Ошибка в шаблоне при тестовой рассылке для админа {admin_id}. Не найдена переменная: {e}")
        await message.answer(f"❌ <b>Ошибка в шаблоне!</b>\n\nНе найдена переменная: <code>{e}</code>.\nПожалуйста, исправьте шаблон и попробуйте снова.", parse_mode="HTML")

# Процесс назначения данных (/assign)
@router.message(Command("assign"))
@router.message(F.text == "📎 Назначить данные")
async def cmd_assign(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} начал процесс назначения данных.")
    await message.answer(
        "Введите номер телефона пользователя, которому нужно назначить данные (в формате +7...).\n"
        "Для отмены введите /cancel.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AssignData.waiting_for_phone)

@router.message(AssignData.waiting_for_phone)
async def process_assign_phone(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    phone = message.text
    user = await get_user_by_phone(phone)
    if not user:
        logger.warning(f"Администратор {admin_id} ввел несуществующий номер '{phone}' при назначении данных.")
        await message.answer("Пользователь с таким номером телефона не найден. Попробуйте еще раз.")
        return
    
    logger.info(f"Администратор {admin_id} ввел номер {phone} для назначения данных (шаг 1/4).")
    await state.update_data(phone=phone)
    await message.answer("Пользователь найден. Теперь введите `bot_id`:")
    await state.set_state(AssignData.waiting_for_bot_id)

@router.message(AssignData.waiting_for_bot_id)
async def process_assign_bot_id(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} ввел bot_id (шаг 2/4).")
    await state.update_data(bot_id=message.text)
    await message.answer("Отлично. Теперь введите `api_key`:")
    await state.set_state(AssignData.waiting_for_api_key)

@router.message(AssignData.waiting_for_api_key)
async def process_assign_api_key(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} ввел api_key (шаг 3/4).")
    await state.update_data(api_key=message.text)
    await message.answer("Принято. Последний шаг - введите `trunk_id`:")
    await state.set_state(AssignData.waiting_for_trunk_id)

@router.message(AssignData.waiting_for_trunk_id)
async def process_assign_trunk_id(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    await state.update_data(trunk_id=message.text)
    data = await state.get_data()
    
    logger.info(f"Администратор {admin_id} успешно назначил конфигурацию "
                f"bot_id={data['bot_id']}, trunk_id={data['trunk_id']} "
                f"пользователю с номером {data['phone']}.")

    await add_user_config(
        phone=data['phone'],
        bot_id=data['bot_id'],
        api_key=data['api_key'],
        trunk_id=data['trunk_id']
    )
    await message.answer(
        f"Данные успешно назначены пользователю {data['phone']}.",
        reply_markup=admin_keyboard()
    )
    await state.clear()

# --- Процесс управления шаблонами ---

DEFAULT_TEMPLATE = """Дата и время звонка: {datetime}
Запись разговора: {audioLink}
Актуальность: {var_is_actual}
Результат звонка: {var_result}
Транскрибация: {transcription}"""

@router.message(Command("get_template"))
@router.message(F.text == "📄 Показать шаблон")
async def cmd_get_template(message: types.Message):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} запросил текущий шаблон.")
    template = await get_active_template()
    if template:
        text = f"<b>Текущий активный шаблон:</b>\n\n<pre>{html.escape(template.template_text)}</pre>"
        await message.answer(text, parse_mode="HTML")
    else:
        logger.info("Активный шаблон не найден, устанавливается шаблон по умолчанию.")
        await set_new_template(DEFAULT_TEMPLATE, message.from_user.id)
        text = f"Шаблон не был установлен. <b>Установлен шаблон по умолчанию:</b>\n\n<pre>{html.escape(DEFAULT_TEMPLATE)}</pre>"
        await message.answer(text, parse_mode="HTML")

@router.message(Command("edit_template"))
@router.message(F.text == "✏️ Редактировать шаблон")
async def cmd_edit_template(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} начал процесс редактирования шаблона.")
    text = (
        "<b>Отправьте мне новый текст шаблона.</b>\n\n"
        "Поддерживаемые переменные:\n"
        "<code>{datetime}</code>, <code>{audioLink}</code>, <code>{transcription}</code>, "
        "<code>{var_is_actual}</code>, <code>{var_result}</code>\n\n"
        "<i>Для отмены введите /cancel.</i>"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(EditTemplate.waiting_for_template)

@router.message(EditTemplate.waiting_for_template)
async def process_edit_template(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    logger.debug(f"Администратор {admin_id} отправил новый шаблон: {message.text}")
    await set_new_template(message.text, admin_id)
    logger.info(f"Администратор {admin_id} успешно обновил шаблон.")
    await message.answer("Шаблон успешно обновлен!", reply_markup=admin_keyboard())
    await state.clear()



# --- НОВЫЙ ОБРАБОТЧИК ЭКСПОРТА ---
@router.message(Command("export_gsheet"))
@router.message(F.text == "📈 Экспорт в Google Sheets")
async def cmd_export_gsheet(message: types.Message):
    admin_id = message.from_user.id
    logger.info(f"Администратор {admin_id} инициировал экспорт в Google Sheets.")
    
    # Отправляем уведомление о начале процесса
    processing_message = await message.answer("⏳ Начинаю экспорт данных... Это может занять некоторое время.")

    success, result = await export_to_google_sheet()

    if success:
        if result.startswith('http'):
            await processing_message.edit_text(f"✅ Экспорт успешно завершен!\n\nТаблица доступна по ссылке: {result}", disable_web_page_preview=True)
        else: # Если данных не было
            await processing_message.edit_text(f"✅ {result}")
    else:
        await processing_message.edit_text(f"❌ <b>Ошибка при экспорте!</b>\n\nПричина: <code>{result}</code>", parse_mode="HTML")