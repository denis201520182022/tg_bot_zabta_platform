# main.py

import asyncio
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import user_handlers, admin_handlers
from database.models import async_main as db_init
from webhook.handlers import notify_handler
from logging_config import setup_logging

# Функция, которая будет запускать polling бота
async def start_bot(dp: Dispatcher, bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# Функция, которая будет запускать веб-сервер
async def start_webapp(app: web.Application, host: str, port: int):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    logging.info(f"Веб-сервер запущен на http://{host}:{port}")
    await site.start()
    # Этот await будет "висеть", пока приложение работает
    await asyncio.Event().wait()

async def main():
    
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск бота...")
    

    # Инициализация БД
    await db_init()

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    
    # Создание веб-приложения
    app = web.Application()
    # "Прокидываем" объект бота в веб-приложение, чтобы иметь к нему доступ в хендлере
    app["bot"] = bot
    # Регистрируем наш эндпоинт
    app.router.add_post("/api/notify", notify_handler)

    # Запускаем обе задачи (бот и веб-сервер) одновременно
    await asyncio.gather(
        start_bot(dp, bot),
        start_webapp(app, host="localhost", port=8080)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")