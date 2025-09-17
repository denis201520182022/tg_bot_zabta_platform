# scheduler.py
import logging
import datetime
from aiogram import Bot
from aiogram.types import BufferedInputFile

from database.requests import get_all_active_configs, update_config_check_time, get_active_template
from platform_api import get_new_calls

logger = logging.getLogger(__name__)

async def check_new_calls_and_notify(bot: Bot):
    logger.info("Планировщик: Начало проверки новых звонков...")
    
    # Получаем все конфигурации из БД
    configs = await get_all_active_configs()
    template_obj = await get_active_template()

    if not template_obj:
        logger.warning("Планировщик: Нет активного шаблона, проверка отменена.")
        return

    template_text = template_obj.template_text

    for config in configs:
        telegram_id, api_key, bot_id, last_checked_at = config
        
        # Если это первая проверка, берем звонки за последний час
        if last_checked_at is None:
            last_checked_at = datetime.datetime.now() - datetime.timedelta(days=1)
        
        current_check_time = datetime.datetime.now()
        
        # Получаем новые звонки с платформы
        new_calls = await get_new_calls(api_key, bot_id, last_checked_at)
        
        if not new_calls:
            # Обновляем время, даже если звонков нет, чтобы не проверять одно и то же
            await update_config_check_time(api_key, bot_id, current_check_time)
            continue

        # Отправляем уведомления по каждому новому звонку
        for call_data in new_calls:
            try:
                # Используем ПРАВИЛЬНЫЕ имена переменных
                message_text = template_text.format(
                call_time=call_data['call_time'],
                audio_link=call_data['audio_link'],
                summarizing_pretty=call_data['summarizing_pretty']
                )
    
                transcription_file = BufferedInputFile(
                file=call_data['transcription_text'].encode('utf-8'),
                filename=call_data['transcription_filename']
                )

                await bot.send_document(
                    chat_id=telegram_id,
                    document=transcription_file,
                    caption=message_text,
                    parse_mode="HTML"
                )
                logger.info(f"Отправлено уведомление пользователю {telegram_id} по звонку.")
            except KeyError as e:
                # Эта ошибка сработает, если в шаблоне опечатка
                logger.error(f"Ошибка форматирования шаблона для пользователя {telegram_id}. Отсутствует ключ: {e}")
            except Exception as e:
                logger.exception(f"Не удалось отправить уведомление пользователю {telegram_id}:")
        
        # Обновляем время последней проверки
        await update_config_check_time(api_key, bot_id, current_check_time)
        
    logger.info("Планировщик: Проверка новых звонков завершена.")