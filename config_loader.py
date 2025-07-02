import yaml
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class HeartbeatConfig:
    modbus_server_ip: str
    register: int
    interval: float = 1.0

@dataclass
class ModbusConfig:
    modbus_server_ip: str
    register: int

@dataclass
class CameraConfig:
    name: str
    camera_ip: str
    rtsp: str
    index: int
    modbus: ModbusConfig  # Используем ModbusConfig вместо CameraModbusConfig

class ConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path

    def load(self) -> tuple[List[HeartbeatConfig], List[CameraConfig]]:
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        heartbeat_configs = self._load_heartbeat_configs(config)
        camera_configs = self._load_camera_configs(config)
        
        return heartbeat_configs, camera_configs

    def _load_heartbeat_configs(self, config: Dict[str, Any]) -> List[HeartbeatConfig]:
        if 'modbus_status' not in config:
            raise ValueError("Отсутствует секция 'modbus_status' в конфигурации")
        
        return [
            HeartbeatConfig(
                modbus_server_ip=str(cfg['modbus_server_ip']),
                register=int(cfg['register']),
                interval=float(cfg.get('interval', 1.0))
            )
            for cfg in config['modbus_status']
        ]

    def _load_camera_configs(self, config: Dict[str, Any]) -> List[CameraConfig]:
        if 'cameras' not in config:
            raise ValueError("Отсутствует секция 'cameras' в конфигурации")
        
        camera_configs = []
        for cam in config['cameras']:
            try:
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
            except (KeyError, TypeError) as e:
                print(f"Ошибка загрузки конфигурации камеры: {e}")
                continue
                
        if not camera_configs:
            raise ValueError("Не найдено валидных конфигураций камер")
            
        return camera_configs