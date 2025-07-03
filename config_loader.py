import yaml
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ModbusStatusConfig:
    """Конфигурация для Modbus heartbeat."""
    modbus_server_ip: str  # IP сервера Modbus
    register: int          # Регистр для heartbeat
    interval: float = 1.0  # Интервал отправки (сек)

@dataclass
class ModbusConfig:
    """Конфигурация Modbus для отправки тегов."""
    modbus_server_ip: str  # IP сервера Modbus
    register: int          # Регистр для записи тегов

@dataclass
class CameraConfig:
    """Конфигурация камеры."""
    name: str            # Название камеры
    camera_ip: str       # IP адрес камеры
    rtsp: str            # RTSP поток
    index: int           # Уникальный индекс (1-3)
    modbus: ModbusConfig  # Конфигурация Modbus для камеры

class ConfigLoader:
    """Загрузчик конфигурации из YAML файла."""

    def __init__(self, config_path: str):
        """Инициализация загрузчика.
        
        Args:
            config_path: Путь к YAML файлу конфигурации
        """
        self.config_path = config_path

    def load(self) -> tuple[List[ModbusStatusConfig], List[CameraConfig]]:
        """Загрузка и парсинг конфигурации.
        
        Returns:
            Кортеж (список конфигураций heartbeat, список конфигураций камер)
            
        Raises:
            ValueError: При ошибках в структуре конфигурации
        """
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f) or {}

        # Загрузка конфигураций heartbeat
        heartbeat_configs = self._load_heartbeat_configs(config)
        
        # Загрузка конфигураций камер
        camera_configs = self._load_camera_configs(config)
        
        return heartbeat_configs, camera_configs

    def _load_heartbeat_configs(self, config: Dict[str, Any]) -> List[ModbusStatusConfig]:
        """Загрузка конфигураций heartbeat."""
        if 'modbus_status' not in config:
            raise ValueError("Отсутствует секция 'modbus_status' в конфигурации")

        return [
            ModbusStatusConfig(
                modbus_server_ip=str(cfg['modbus_server_ip']),
                register=int(cfg['register']),
                interval=float(cfg.get('interval', 1.0))
            )
            for cfg in config['modbus_status']
        ]

    def _load_camera_configs(self, config: Dict[str, Any]) -> List[CameraConfig]:
        """Загрузка конфигураций камер с валидацией."""
        if 'cameras' not in config:
            raise ValueError("Отсутствует секция 'cameras' в конфигурации")

        camera_configs = []
        for cam in config['cameras']:
            try:
                # Валидация обязательных полей
                required = ['name', 'camera_ip', 'rtsp', 'index', 'modbus']
                if not all(field in cam for field in required):
                    raise ValueError("Отсутствуют обязательные поля в конфигурации камеры")

                camera_configs.append(
                    CameraConfig(
                        name=str(cam['name']),
                        camera_ip=str(cam['camera_ip']),
                        rtsp=str(cam['rtsp']),
                        index=int(cam['index']),
                        modbus=ModbusConfig(
                            modbus_server_ip=str(cam['modbus']['modbus_server_ip']),
                            register=int(cam['modbus']['register'])
                        )
                    )
                )
            except (ValueError, TypeError, KeyError) as e:
                print(f"Ошибка загрузки конфигурации камеры: {e}")
                continue

        if not camera_configs:
            raise ValueError("Не найдено ни одной валидной конфигурации камеры")
            
        return camera_configs