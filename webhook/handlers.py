# webhook/handlers.py

import logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot
import html

from database.requests import find_user_by_config, get_active_template

# Создаем именованный логгер для этого файла
logger = logging.getLogger(__name__)

async def notify_handler(request: web.Request):
    bot: Bot = request.app['bot']

    try:
        data = await request.json()
        # Используем DEBUG для полного тела запроса, т.к. оно может быть большим
        logger.debug(f"Получены данные от платформы: {data}")

        required_keys = ["bot_id", "trunk_id", "api_key", "datetime", "recording_url", "transcription", "relevance", "call_result"]
        # Проверяем, все ли ключи на месте
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            # Логируем, каких именно ключей не хватает
            logger.warning(f"Некорректные данные. Отсутствуют обязательные поля: {', '.join(missing_keys)}")
            return web.json_response({"status": "error", "message": f"Missing required fields: {', '.join(missing_keys)}"}, status=400)

        # Логируем начало обработки конкретного запроса
        bot_id = data['bot_id']
        logger.info(f"Начало обработки уведомления для bot_id: {bot_id}")

        user = await find_user_by_config(bot_id, data['trunk_id'], data['api_key'])

        if not user:
            logger.warning(f"Конфигурация не найдена для bot_id={bot_id}, trunk_id={data['trunk_id']}")
            return web.json_response({"status": "error", "message": "User config not found"}, status=404)

        template = await get_active_template()
        if not template:
            logger.error("В базе данных нет активного шаблона для отправки! Невозможно отправить уведомление.")
            return web.json_response({"status": "error", "message": "Active template not found"}, status=500)

        # --- Подготовка переменных ---
        
        # 1. Форматируем дату
        formatted_datetime_str = data['datetime']
        try:
            dt_object = datetime.fromisoformat(data['datetime'])
            formatted_datetime_str = dt_object.strftime('%d.%m.%Y %H:%M')
        except ValueError:
            logger.warning(f"Не удалось распарсить дату: {data['datetime']}. Будет использован исходный формат.")

        # 2. Экранируем пользовательские данные для безопасной вставки в HTML
        escaped_transcription = html.escape(data['transcription'])
        escaped_call_result = html.escape(data['call_result'])
        escaped_relevance = html.escape(data['relevance'])
        
        # --- Формирование текста сообщения ---
        message_text = template.template_text.format(
            datetime=formatted_datetime_str,
            audioLink=data['recording_url'],
            transcription=escaped_transcription,
            var_is_actual=escaped_relevance,
            var_result=escaped_call_result
        )

        # Отправляем сообщение пользователю
        await bot.send_message(user.telegram_id, message_text, parse_mode="HTML")
        
        logger.info(f"Уведомление для bot_id={bot_id} успешно отправлено пользователю telegram_id={user.telegram_id}")
        return web.json_response({"status": "success"}, status=200)

    except Exception as e:
        # Используем exception, чтобы автоматически записать traceback ошибки
        logger.exception("Произошла критическая ошибка при обработке запроса от платформы:")
        return web.json_response({"status": "error", "message": "Internal server error"}, status=500)