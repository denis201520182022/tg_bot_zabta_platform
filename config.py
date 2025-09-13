import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Читаем строку с ID и превращаем ее в список чисел
ADMIN_IDS_STR = os.getenv("ADMIN_IDS")
ADMIN_IDS = [int(admin_id) for admin_id in ADMIN_IDS_STR.split(',') if admin_id]

GSHEET_NAME = os.getenv("GSHEET_NAME")