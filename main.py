# main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from handlers import user_handlers, admin_handlers
from database.models import async_main as db_init
from logging_config import setup_logging
from scheduler import check_new_calls_and_notify

async def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск бота...")

    await db_init()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    
    # --- Настройка и запуск планировщика ---
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        check_new_calls_and_notify,
        trigger='interval',
        #seconds=100,
        minutes=3,
        kwargs={'bot': bot}
    )
    scheduler.start()
    
    logger.info("Планировщик запущен и настроен.")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")