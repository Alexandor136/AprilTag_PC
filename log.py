import sys
import logging
from logging import StreamHandler, Formatter

# Создаем логгер
logger = logging.getLogger('__name__')
logger.setLevel(logging.DEBUG)

# Создаем обработчик для вывода логов уровня INFO
info_handler = StreamHandler(stream=sys.stdout)
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s %(message)s'))

# Создаем обработчик для вывода логов уровня DEBUG
debug_handler = StreamHandler(stream=sys.stderr)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s'))

# Создаем обработчик для вывода логов уровня WARNING и выше
error_handler = StreamHandler(stream=sys.stderr)
error_handler.setLevel(logging.WARNING)
error_handler.setFormatter(Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s'))


# Добавляем обработчики к логгеру
logger.addHandler(info_handler)
logger.addHandler(debug_handler)
logger.addHandler(error_handler)


#logger.debug('Это отладочное сообщение')  # Не будет выведено
#logger.info('Это информационное сообщение')  # Будет выведено в stdout
#logger.warning('Это предупреждение')  # Будет выведено в stderr
#logger.error('Это сообщение об ошибке')  # Будет выведено в stderr
#logger.critical('Это критическое сообщение')  # Будет выведено в stderr