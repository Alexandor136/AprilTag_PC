from dataclasses import dataclass
from typing import List, Tuple
import yaml

@dataclass
class ModbusStatusConfig:
    register: int
    modbus_server_ip: str

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

    def load(self) -> Tuple[ModbusStatusConfig, List[CameraConfig]]:
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        self._validate(config)
        
        status_config = ModbusStatusConfig(
            register=config['modbus_status']['register'],
            modbus_server_ip=config['modbus_status']['modbus_server_ip']
        )
        
        cameras = []
        for cam in config['cameras']:
            cameras.append(CameraConfig(
                name=cam['name'],
                camera_ip=cam['camera_ip'],
                rtsp=cam['rtsp'],
                index=cam['index'] - 1,
                modbus=ModbusConfig(
                    register=cam['modbus']['register'],
                    modbus_server_ip=cam['modbus']['modbus_server_ip']
                )
            ))
            
        return status_config, cameras

    def _validate(self, config: dict):
        if 'modbus_status' not in config:
            raise ValueError("Отсутствует секция modbus_status в конфиге")
            
        if not isinstance(config['modbus_status']['register'], int):
            raise ValueError("modbus_status.register должен быть целым числом")
            
        #if len(config['cameras']) != 3:
            #raise ValueError("Конфиг должен содержать ровно 3 камеры")
        
        indices = set()
        for cam in config['cameras']:
            if not 1 <= cam['index'] <= 3:
                raise ValueError("Индексы камер должны быть от 1 до 3")
            if cam['index'] in indices:
                raise ValueError(f"Дублируется индекс камеры: {cam['index']}")
            indices.add(cam['index'])