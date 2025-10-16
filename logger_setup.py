# logger_setup.py
import sys
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from logging import StreamHandler, Formatter
from datetime import datetime, timedelta
import glob
import re

LOG_DIR = "logs"
LOG_FORMAT = '[%(asctime)s: %(levelname)s] %(message)s'
LOG_RETENTION_DAYS = 3
LOGGER_NAME = 'my_app_logger'

def cleanup_old_logs():
    """Удаляет логи старше LOG_RETENTION_DAYS дней"""
    if not os.path.exists(LOG_DIR):
        return
        
    cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    
    # Шаблоны для поиска всех лог-файлов (основные и ротированные)
    log_patterns = [
        os.path.join(LOG_DIR, "app_*.log"),
        os.path.join(LOG_DIR, "app_*.log.*")  # Для ротированных файлов
    ]
    
    for pattern in log_patterns:
        for log_file in glob.glob(pattern):
            try:
                # Извлекаем дату из имени файла
                filename = os.path.basename(log_file)
                
                # Основной файл: app_2024-10-16.log
                if filename.startswith("app_") and filename.endswith(".log") and not re.search(r'\.log\.\d+$', filename):
                    date_str = filename.replace("app_", "").replace(".log", "")
                # Ротированный файл: app_2024-10-16.log.2024-10-16
                elif re.match(r'app_\d{4}-\d{2}-\d{2}\.log\.\d{4}-\d{2}-\d{2}$', filename):
                    date_str = filename.split('.')[-1]  # Берем дату из суффикса
                else:
                    continue
                
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff_date:
                    os.remove(log_file)
                    print(f"Удален старый лог-файл: {log_file}")
                    
            except (ValueError, IndexError):
                # Пропускаем файлы с некорректным форматом имени
                continue

def setup_logger():
    """Настройка логгера с ротацией по дням"""
    logger = logging.getLogger(LOGGER_NAME)
    
    if logger.handlers:
        return logger
    
    logger.handlers = []
    logger.propagate = False  # Важно: отключаем распространение
    os.makedirs(LOG_DIR, exist_ok=True)
    cleanup_old_logs()

    logger.setLevel(logging.DEBUG)
    formatter = Formatter(fmt=LOG_FORMAT)

    # Обработчики (только один для каждого назначения)
    handlers = [
        (TimedRotatingFileHandler(
            filename=os.path.join(LOG_DIR, "app.log"),  # Постоянное имя файла
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,  # Храним только нужное количество бэкапов
            encoding='utf-8'
        ), logging.INFO),  # Только INFO+ в файл
        
        (StreamHandler(sys.stdout), logging.DEBUG)  # DEBUG+ в консоль
    ]

    for handler, level in handlers:
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# Глобальный логгер
logger = setup_logger()