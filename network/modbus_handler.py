import asyncio
from typing import List
from config_loader import ModbusConfig
from network.modbus_client import write_modbus

class ModbusHandler:
    def __init__(self):
        self.active = True

    async def send_tags(self, tags: List, modbus_cfg: ModbusConfig):
        """Асинхронная отправка тегов в Modbus"""
        if not self.active:
            return

        try:
            modbus_value = self._encode_tags(tags)
            await write_modbus(
                value=modbus_value,
                address=modbus_cfg.register,
                host=modbus_cfg.modbus_server_ip
            )
            print(f"Отправлено в Modbus (регистр {modbus_cfg.register}): {modbus_value}")
        except Exception as e:
            print(f"Ошибка Modbus: {str(e)}")

    def _encode_tags(self, tags: List) -> int:
        """Кодирование тегов в битовую маску"""
        value = 0
        for tag in tags:
            if 1 <= tag.tag_id <= 4:
                value |= 1 << (tag.tag_id - 1)
        return value

    def stop(self):
        """Остановка обработчика"""
        self.active = False