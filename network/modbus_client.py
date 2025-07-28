from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from logger_setup import logger


def check_response(response):
    """Только проверка без логирования"""
    if isinstance(response, ModbusIOException):
        raise ModbusException(f"Ошибка ввода-вывода: {response}")  # Без logger.warning
    if hasattr(response, 'isError') and response.isError():
        raise ModbusException(f"Устройство вернуло ошибку: {response}")  # Без logger.warning

async def write_modbus(
    value: int,
    address: int,
    host: str,
    port: int = 502,
    slave_id: int = 1,
) -> None:
    """
    Записывает значение в Modbus-регистр по TCP.

    Параметры:
        value: значение для записи (целое число)
        address: адрес Modbus-регистра
        host: IP-адрес устройства
        port: порт Modbus-TCP (по умолчанию 502)
        slave_id: ID устройства Modbus (по умолчанию 1)
    """
    #print(f"Подключение к {host}:{port}...")
    logger.debug(f"Подключение к {host}:{port}...")

    try:
        async with AsyncModbusTcpClient(
            host=host,
            port=port,
            framer="socket",  # протокол Modbus-TCP
        ) as client:
            if not client.connected:
                raise ConnectionError(logger.warning("Не удалось подключиться к устройству"))
                
            #print(f"Запись {value} в регистр {address} (slave={slave_id})...")
            logger.debug(f"Запись {value} в регистр {address} (slave={slave_id})...")

            response = await client.write_register(
                address=address,
                value=value,
                slave=slave_id,
            )
            check_response(response)
            #print("Успешно!")
            logger.info(f"Выполнена запись значения: {value} в регистр {address} (slave={slave_id})")


    except ModbusException as e:
        # Исключение будет перехвачено выше с автоматическим логированием
        raise
    except Exception as e:
        #print(f"Критическая ошибка: {e}")
        logger.warning(f"Критическая ошибка: {e}")

