from dataclasses import dataclass
from typing import List
import yaml

@dataclass
class ModbusConfig:
    register: int
    modbus_server_ip: str

@dataclass
class CameraConfig:
    name: str
    camera_ip: str
    rtsp: str
    index: int
    modbus: ModbusConfig

class ConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path

    def load(self) -> List[CameraConfig]:
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        self._validate(config)
        return self._parse_config(config)

    def _validate(self, config: dict):
        """Проверка корректности конфигурации"""
        if len(config['cameras']) != 3:
            raise ValueError("Конфиг должен содержать ровно 3 камеры")
        
        indices = set()
        for cam in config['cameras']:
            if not 1 <= cam['index'] <= 3:
                raise ValueError("Индексы камер должны быть от 1 до 3")
            if cam['index'] in indices:
                raise ValueError(f"Дублируется индекс камеры: {cam['index']}")
            indices.add(cam['index'])

    def _parse_config(self, config: dict) -> List[CameraConfig]:
        """Создает объекты конфигурации камер"""
        cameras = []
        for cam in config['cameras']:
            cameras.append(CameraConfig(
                name=cam['name'],
                camera_ip=cam['camera_ip'],
                rtsp=cam['rtsp'],
                index=cam['index'] - 1,  # Конвертируем в 0-based индекс
                modbus=ModbusConfig(
                    register=cam['modbus']['register'],
                    modbus_server_ip=cam['modbus']['modbus_server_ip']
                )
            ))
        return cameras