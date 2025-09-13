# g_sheets.py
import gspread
import pandas as pd
import logging

from config import GSHEET_NAME
from database.requests import get_all_users_with_configs # Эту функцию мы создадим дальше

logger = logging.getLogger(__name__)

# --- Функция маскировки номера ---
def mask_phone_number(phone: str) -> str:
    """Маскирует средние 3 цифры номера. +79123456789 -> '+7912***6789"""
    if phone and len(phone) == 12 and phone.startswith('+7'):
        # Добавляем апостроф в начало, чтобы GSheets считали это текстом
        return f"'{phone[:5]}***{phone[8:]}"
    return phone # Возвращаем как есть, если формат не стандартный

# --- Основная функция экспорта ---
async def export_to_google_sheet() -> tuple[bool, str]:
    """
    Экспортирует данные в Google Таблицу.
    Возвращает кортеж (успех: bool, сообщение/ссылка: str).
    """
    try:
        logger.info("Начало экспорта в Google Sheets.")
        
        # Авторизация по JSON-ключу
        gc = gspread.service_account(filename='google_credentials.json')
        # Открытие таблицы по имени
        spreadsheet = gc.open(GSHEET_NAME)
        # Выбор первого листа
        worksheet = spreadsheet.sheet1
        
        logger.debug("Успешно подключились к Google Sheet.")

        # Получаем данные из БД
        users_data = await get_all_users_with_configs()

        if not users_data:
            logger.warning("Нет данных для экспорта.")
            return True, "Нет данных для экспорта."

        # Формируем данные для записи с помощью pandas
        export_data = []
        for user in users_data:
            export_data.append({
                "Telegram ID": user.telegram_id,
                "Номер телефона": mask_phone_number(user.phone_number),
                "Bot ID": user.bot_id,
                "Trunk ID": user.trunk_id,
                "Api key": user.api_key
            })
        
        df = pd.DataFrame(export_data)

        # Очищаем лист и записываем новые данные
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option='USER_ENTERED')
        
        logger.info(f"Экспорт успешно завершен. Записано {len(df)} строк.")
        return True, spreadsheet.url

    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Таблица с именем '{GSHEET_NAME}' не найдена. Проверьте .env и права доступа.")
        return False, f"Ошибка: Таблица с именем '{GSHEET_NAME}' не найдена."
    except Exception as e:
        logger.exception("Произошла критическая ошибка при экспорте в Google Sheets:")
        return False, f"Произошла непредвиденная ошибка: {e}"