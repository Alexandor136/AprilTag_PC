import asyncio
import threading
import time
from typing import List, Dict
from dataclasses import dataclass
from config_loader import ModbusStatusConfig, ModbusConfig
from network.modbus_client import write_modbus
from logger_setup import logger

@dataclass
class HeartbeatTask:
    """Задача для управления состоянием heartbeat."""
    status: int = 0          # Текущее состояние (0/1)
    interval: float = 1.0    # Интервал отправки
    last_sent: float = 0.0   # Время последней отправки

class ModbusHandler:
    """Обработчик Modbus операций (heartbeat и отправка тегов)."""

    def __init__(self):
        """Инициализация обработчика."""
        self.active = True
        self.heartbeat_tasks: Dict[str, HeartbeatTask] = {}
        self.loop = asyncio.new_event_loop()
        self.lock = threading.Lock()
        self.last_sent_tags = {}
        self._thread = threading.Thread()  # Инициализация пустым потоком
        self._thread.daemon = True

    async def _send_tags_async(self, tags: List, modbus_cfg: ModbusConfig):
        """Асинхронная отправка тегов на Modbus сервер.
        
        Args:
            tags: Список обнаруженных тегов
            modbus_cfg: Конфигурация Modbus для отправки
        """
        try:
            modbus_value = self._encode_tags(tags)
            logger.info(f"Отправка тегов на {modbus_cfg.modbus_server_ip}:{modbus_cfg.register}")
            await write_modbus(
                value=modbus_value,
                address=modbus_cfg.register,
                host=modbus_cfg.modbus_server_ip
            )
        except Exception as e:
            print(f"Ошибка отправки тегов: {str(e)}")

    def send_tags(self, tags: List, modbus_cfg: ModbusConfig):
        """Синхронная обертка для отправки тегов.
        
        Args:
            tags: Список обнаруженных тегов
            modbus_cfg: Конфигурация Modbus для отправки
        """
        asyncio.run_coroutine_threadsafe(
            self._send_tags_async(tags, modbus_cfg),
            self.loop
        )

    async def _send_heartbeats(self, status_configs: List[ModbusStatusConfig]):
        """Управление отправкой heartbeat для всех конфигураций."""
        while self.active:
            try:
                current_time = time.time()
                
                for cfg in status_configs:
                    key = f"{cfg.modbus_server_ip}:{cfg.register}"
                    
                    if key not in self.heartbeat_tasks:
                        self.heartbeat_tasks[key] = HeartbeatTask(interval=cfg.interval)
                    
                    task = self.heartbeat_tasks[key]
                    
                    if current_time - task.last_sent >= task.interval:
                        task.status = 1 - task.status
                        await write_modbus(
                            value=task.status,
                            address=cfg.register,
                            host=cfg.modbus_server_ip
                        )
                        task.last_sent = current_time
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Ошибка heartbeat: {str(e)}")
                await asyncio.sleep(5)

    def _run_event_loop(self):
        """Запуск цикла событий в отдельном потоке."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_heartbeat(self, status_configs: List[ModbusStatusConfig]):
        """Запуск heartbeat для всех конфигураций.
        
        Args:
            status_configs: Список конфигураций heartbeat
        """
        if not hasattr(self, '_thread') or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True
            )
            self._thread.start()
            
            asyncio.run_coroutine_threadsafe(
                self._send_heartbeats(status_configs),
                self.loop
            )

    def _encode_tags(self, tags: List) -> int:
        """Кодирование списка тегов в битовую маску.
        
        Args:
            tags: Список тегов для кодирования
            
        Returns:
            Числовое значение битовой маски
        """
        if not tags:
            return 0
        value = 0
        for tag in tags:
            if 1 <= tag.tag_id <= 32:
                value |= 1 << (tag.tag_id - 1)
        return value

    def stop(self):
        """Остановка всех Modbus операций."""
        self.active = False
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)