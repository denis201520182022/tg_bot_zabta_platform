# database/models.py
from sqlalchemy import BigInteger, String, func, Boolean, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.types import DateTime
import datetime
from config import DATABASE_URL

# Заменяем создание движка на новое, для PostgreSQL
engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

# Таблица пользователей (без изменений)
class User(Base):
    __tablename__ = 'users'
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    phone_number: Mapped[str] = mapped_column(String, unique=True)
    registered_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

# НОВАЯ ТАБЛИЦА: Конфигурации для пользователей
class UserConfig(Base):
    __tablename__ = 'user_configs'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Связываем с номером телефона из таблицы users
    user_phone: Mapped[str] = mapped_column(ForeignKey('users.phone_number'))
    bot_id: Mapped[str] = mapped_column(String)
    api_key: Mapped[str] = mapped_column(String)
    trunk_id: Mapped[str] = mapped_column(String)
    last_checked_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)

# НОВАЯ ТАБЛИЦА: Шаблоны уведомлений
class NotificationTemplate(Base):
    __tablename__ = 'notification_templates'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[int] = mapped_column(BigInteger) # telegram_id администратора
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

# Функция для создания таблиц
async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)