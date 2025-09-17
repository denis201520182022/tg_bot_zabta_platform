# bot_commands.py

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat

from config import ADMIN_IDS

# --- Команды для обычных пользователей ---
user_commands = [
    BotCommand(command="start", description="🔄 Перезапустить / Обновить меню"),
    BotCommand(command="help", description="ℹ️ Справка по работе с ботом")
]

# --- Команды для администраторов (включают все команды пользователей) ---
admin_commands = user_commands + [
    BotCommand(command="admin", description="🔒 Админ-панель"),
    BotCommand(command="list_users", description="👥 Список пользователей"),
    BotCommand(command="assign", description="📎 Назначить данные пользователю"),
    BotCommand(command="get_template", description="📄 Показать текущий шаблон"),
    BotCommand(command="edit_template", description="✏️ Редактировать шаблон"),
    BotCommand(command="export_gsheet", description="📈 Экспорт в Google Sheets")
]

# --- Функция для установки команд ---
async def set_user_commands(bot: Bot, chat_id: int):
    """
    Устанавливает меню команд в зависимости от роли пользователя.
    """
    commands = admin_commands if chat_id in ADMIN_IDS else user_commands
    # Устанавливаем команды для конкретного чата
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeChat(chat_id=chat_id))