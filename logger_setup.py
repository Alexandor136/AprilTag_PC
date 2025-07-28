# logger_setup.py
import sys
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from logging import StreamHandler, Formatter
from datetime import datetime, timedelta
import glob

LOG_DIR = "logs"
LOG_FORMAT = '[%(asctime)s: %(levelname)s] %(message)s'
LOG_RETENTION_DAYS = 3
LOGGER_NAME = 'my_app_logger'

def cleanup_old_logs():
    """Удаляет логи старше LOG_RETENTION_DAYS дней"""
    if not os.path.exists(LOG_DIR):
        return
        
    cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    
    for log_file in glob.glob(os.path.join(LOG_DIR, "*.log")):
        file_date_str = os.path.basename(log_file).replace("app_", "").replace(".log", "")
        try:
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
            if file_date < cutoff_date:
                os.remove(log_file)
                print(f"Удален старый лог-файл: {log_file}")
        except ValueError:
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
            filename=os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y-%m-%d')}.log"),
            when="midnight",
            backupCount=LOG_RETENTION_DAYS,
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