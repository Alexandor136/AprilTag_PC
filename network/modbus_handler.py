import asyncio
from typing import List
import threading
from config_loader import ModbusStatusConfig, ModbusConfig
from network.modbus_client import write_modbus

class ModbusHandler:
    def __init__(self):
        self.active = True
        self.heartbeat_task = None
        self.current_status = 0
        self.loop = asyncio.new_event_loop()
        self.lock = threading.Lock()
        self.last_sent_tags = {}

    async def _send_tags_async(self, tags: List, modbus_cfg: ModbusConfig):
        """Асинхронная отправка тегов"""
        try:
            modbus_value = self._encode_tags(tags)
            await write_modbus(
                value=modbus_value,
                address=modbus_cfg.register,
                host=modbus_cfg.modbus_server_ip
            )
            print(f"Отправлены теги в регистр {modbus_cfg.register}: {modbus_value}")
        except Exception as e:
            print(f"Ошибка отправки тегов: {str(e)}")

    def send_tags(self, tags: List, modbus_cfg: ModbusConfig):
        """Синхронная обертка для отправки тегов"""
        asyncio.run_coroutine_threadsafe(
            self._send_tags_async(tags, modbus_cfg),
            self.loop
        )

    async def _send_heartbeat(self, status_config: ModbusStatusConfig):
        """Циклическая отправка статуса 0/1"""
        while self.active:
            try:
                self.current_status = 1 - self.current_status
                await write_modbus(
                    value=self.current_status,
                    address=status_config.register,
                    host=status_config.modbus_server_ip
                )
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Ошибка heartbeat: {str(e)}")
                await asyncio.sleep(5)

    def _run_event_loop(self):
        """Запуск цикла событий в отдельном потоке"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_heartbeat(self, status_config: ModbusStatusConfig):
        """Запуск всех асинхронных задач"""
        if not hasattr(self, '_thread') or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True
            )
            self._thread.start()
            
            # Запускаем heartbeat
            asyncio.run_coroutine_threadsafe(
                self._send_heartbeat(status_config),
                self.loop
            )

    def _encode_tags(self, tags: List) -> int:
        """Кодирование тегов в битовую маску"""
        if not tags:
            return 0
        value = 0
        for tag in tags:
            if 1 <= tag.tag_id <= 32:
                value |= 1 << (tag.tag_id - 1)
        return value

    def stop(self):
        """Остановка всех задач"""
        self.active = False
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)