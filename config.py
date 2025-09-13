import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Читаем строку с ID и превращаем ее в список чисел
ADMIN_IDS_STR = os.getenv("ADMIN_IDS")
ADMIN_IDS = [int(admin_id) for admin_id in ADMIN_IDS_STR.split(',') if admin_id]

GSHEET_NAME = os.getenv("GSHEET_NAME")

# --- Читаем настройки БД из .env ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Собираем строку подключения (DSN) для PostgreSQL
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"