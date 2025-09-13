# logging_config.py

import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging():
    """
    Настраивает логирование в консоль и в файл с ротацией.
    """
    # Форматтер, который будет определять вид сообщений
    LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
    
    # Получаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # Устанавливаем самый низкий уровень, чтобы ловить все сообщения

    # --- Настройка обработчика для вывода в консоль ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # В консоль выводим только INFO и выше
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # --- Настройка обработчика для записи в файл ---
    # RotatingFileHandler будет создавать новые файлы, когда старый достигнет 5 МБ
    # и будет хранить до 5 старых файлов (backupCount)
    file_handler = RotatingFileHandler('bot.log', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG) # В файл пишем всё, начиная с DEBUG
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # Добавляем оба обработчика к корневому логгеру
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)