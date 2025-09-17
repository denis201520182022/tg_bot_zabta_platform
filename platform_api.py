
# platform_api.py
import aiohttp
import datetime
import json
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://api.client.za-bota.com/v1/calls"
LIMIT = 50

# --- ЗАГОЛОВКИ, КОТОРЫЕ ИМИТИРУЮТ БРАУЗЕР/REQUESTS ---
# Это часто помогает обойти простые защиты на серверах
IMITATION_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
}

async def get_new_calls(api_key: str, bot_id: str, last_check_time: datetime.datetime) -> list:
    start_date_str = last_check_time.isoformat()
    current_date_str = datetime.datetime.now().isoformat()
    
    params = {
        "limit": LIMIT,
        "page": 1,
        "sortBy": "updated_at",
        "filter_date": "updated_at",
        "date_time_start": start_date_str,
        "date_time_end": current_date_str,
        "filter": bot_id,
        "filterOn": '["bot_id"]',
        "api_key": api_key
    }
    
    try:
        logger.info(f"Отправка запроса для bot_id={bot_id}")
        logger.debug(json.dumps(params, indent=2))

        # Создаем сессию с нашими специальными заголовками
        async with aiohttp.ClientSession(headers=IMITATION_HEADERS) as session:
            async with session.get(BASE_URL, params=params, timeout=120) as response:
                
                # --- ИЗМЕНЕНА ЛОГИКА ЧТЕНИЯ ОТВЕТА ---
                # Теперь мы явно указываем, что хотим получить JSON, игнорируя Content-Type
                # content_type=None отключает проверку mimetype, решая проблему с text/html
                response_data = await response.json(content_type=None)

                # Проверяем статус-код ПОСЛЕ попытки чтения
                response.raise_for_status()

                if response_data and response_data.get("status") == "success" and "data" in response_data.get("data", {}):
                    calls_list = response_data["data"]["data"]
                    logger.info(f"Для bot_id={bot_id} получено {len(calls_list)} звонков.")
                    
                    processed_calls = []
                    for call in calls_list:
                        # ... (вся логика парсинга без изменений) ...
                        call_id = call.get('id', 'N/A')
                        call_time = call.get('created_at', 'N/A')
                        storage = call.get('storage')
                        call_uuid = call.get('uuid')
                        
                        variables_data = call.get('variables')
                        if not variables_data: continue
                        variables = json.loads(variables_data) if isinstance(variables_data, str) else variables_data
                        
                        audio_file = variables.get('all_audio_record')
                        
                        if storage and call_uuid and audio_file:
                            audio_link = f"https://client.za-bota.com/calls/storage/{storage}/{call_uuid}/{audio_file}"
                        else:
                            audio_link = "Ссылка недоступна"

                        summarizing_data = variables.get('summarizing', {})
                        if isinstance(summarizing_data, str) and summarizing_data:
                           try:
                               summarizing_obj = json.loads(summarizing_data)
                           except json.JSONDecodeError:
                               summarizing_obj = {"raw_text": summarizing_data}
                        else:
                            summarizing_obj = summarizing_data if summarizing_data else {}
                        summarizing_pretty = json.dumps(summarizing_obj, indent=2, ensure_ascii=False)
                        
                        dialog = variables.get('dialog', [])
                        transcription_text = f"Транскрибация звонка ID: {call_id}\nДата: {call_time}\n\n"
                        for msg in dialog:
                            if "user" in msg:
                                transcription_text += f"Клиент: {msg['user']}\n\n"
                            elif "assistant" in msg and ((msg['assistant'].get('state') == 'active') or (msg['assistant'].get('state') == 'last')):
                                transcription_text += f"Ассистент: {msg['assistant'].get('message', '')}\n\n"

                        processed_calls.append({
                            "call_time": call_time,
                            "audio_link": audio_link,
                            "summarizing_pretty": summarizing_pretty,
                            "transcription_text": transcription_text,
                            "transcription_filename": f"transcription_{call_id}.txt"
                        })
                    return processed_calls
                else:
                    logger.warning(f"Запрос для bot_id={bot_id} успешен, но не содержит данных о звонках. Ответ: {response_data}")
        
    except aiohttp.ClientResponseError as e:
        logger.error(f"Ошибка HTTP от API для bot_id={bot_id}. Статус: {e.status}. Сообщение: {e.message}")
    except aiohttp.ClientError as e:
        logger.error(f"Сетевая ошибка при запросе к API для bot_id={bot_id}: {e}")
    except json.JSONDecodeError:
        logger.error(f"Не удалось прочитать JSON из ответа сервера для bot_id={bot_id}.")
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка при обработке звонков для bot_id={bot_id}:")
    
    return []