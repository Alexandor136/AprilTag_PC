from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from logger_setup import logger


def check_response(response):
    """Только проверка без логирования"""
    if isinstance(response, ModbusIOException):
        raise ModbusException(f"Ошибка ввода-вывода: {response}")
    if hasattr(response, 'isError') and response.isError():
        raise ModbusException(f"Устройство вернуло ошибку: {response}")

async def write_modbus(
    value: int,
    address: int,
    host: str,
    port: int = 502,
) -> None:
    """
    Записывает значение в Modbus-регистр по TCP.

    Параметры:
        value: значение для записи (целое число)
        address: адрес Modbus-регистра
        host: IP-адрес устройства
        port: порт Modbus-TCP (по умолчанию 502)
    """
    logger.debug(f"Подключение к {host}:{port}...")

    try:
        async with AsyncModbusTcpClient(
            host=host,
            port=port,
            framer="socket",
        ) as client:
            if not client.connected:
                raise ConnectionError("Не удалось подключиться к устройству")
                
            logger.debug(f"Запись {value} в регистр {address}...")

            # Простая запись без unit/slave параметра
            response = await client.write_register(
                address=address,
                value=value,
            )
            check_response(response)
            logger.info(f"Выполнена запись значения: {value} в регистр {address}")

    except ModbusException as e:
        logger.warning(f"Ошибка Modbus: {e}")
        raise
    except Exception as e:
        logger.warning(f"Критическая ошибка: {e}")
        raise