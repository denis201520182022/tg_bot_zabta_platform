# database/requests.py

from .models import async_session, User
from sqlalchemy import select
from sqlalchemy.orm import aliased

# Функция для добавления нового пользователя
async def add_user(tg_id: int, phone: str):
    async with async_session() as session:
        # Проверяем, нет ли уже пользователя с таким telegram_id или номером телефона
        user_by_id = await session.get(User, tg_id)
        if user_by_id:
            return "user_exists"
        
        user_by_phone = await session.scalar(select(User).where(User.phone_number == phone))
        if user_by_phone:
            return "phone_exists"

        # Если проверили и все чисто - добавляем
        session.add(User(telegram_id=tg_id, phone_number=phone))
        await session.commit()
        return "ok"

# Функция для получения информации о пользователе по его telegram_id
async def get_user(tg_id: int):
    async with async_session() as session:
        return await session.get(User, tg_id)
    


# database/requests.py

# ... (старый код add_user и get_user) ...

# Добавляем импорт новых моделей
from .models import UserConfig, NotificationTemplate
from sqlalchemy import update

# --- Функции для администратора ---

async def get_all_users():
    """Возвращает список всех зарегистрированных пользователей."""
    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.registered_at.desc()))
        return result.scalars().all()

async def get_user_by_phone(phone: str):
    """Находит пользователя по номеру телефона."""
    async with async_session() as session:
        return await session.scalar(select(User).where(User.phone_number == phone))

async def add_user_config(phone: str, bot_id: str, api_key: str, trunk_id: str):
    """Добавляет связку параметров для пользователя."""
    async with async_session() as session:
        session.add(UserConfig(
            user_phone=phone,
            bot_id=bot_id,
            api_key=api_key,
            trunk_id=trunk_id
        ))
        await session.commit()

# --- Функции для работы с шаблонами ---

async def get_active_template():
    """Возвращает текст активного шаблона."""
    async with async_session() as session:
        template = await session.scalar(select(NotificationTemplate).where(NotificationTemplate.is_active == True))
        return template

async def set_new_template(template_text: str, admin_id: int):
    """Деактивирует старый шаблон и добавляет новый."""
    async with async_session() as session:
        # Деактивируем все активные шаблоны
        await session.execute(
            update(NotificationTemplate)
            .where(NotificationTemplate.is_active == True)
            .values(is_active=False)
        )
        # Добавляем новый активный шаблон
        session.add(NotificationTemplate(
            template_text=template_text,
            updated_by=admin_id,
            is_active=True
        ))
        await session.commit()

async def find_user_by_config(bot_id: str, trunk_id: str, api_key: str):
    """
    Находит пользователя (User) по его конфигурации (UserConfig).
    """
    async with async_session() as session:
        # Выполняем запрос с объединением (JOIN) двух таблиц
        query = (
            select(User)
            .join(UserConfig, User.phone_number == UserConfig.user_phone)
            .where(
                UserConfig.bot_id == bot_id,
                UserConfig.trunk_id == trunk_id,
                UserConfig.api_key == api_key
            )
        )
        result = await session.execute(query)
        # scalar_one_or_none() вернет одного пользователя или None, если не найдено
        return result.scalar_one_or_none()
    



async def get_all_users_with_configs():
    """
    Возвращает объединенный список всех пользователей и их конфигураций.
    """
    async with async_session() as session:
        # Используем LEFT JOIN, чтобы включить даже тех пользователей,
        # у которых еще нет конфигураций
        query = (
            select(
                User.telegram_id,
                User.phone_number,
                UserConfig.bot_id,
                UserConfig.trunk_id,
                UserConfig.api_key
            )
            .outerjoin(UserConfig, User.phone_number == UserConfig.user_phone)
            .order_by(User.registered_at)
        )
        result = await session.execute(query)
        return result.all()