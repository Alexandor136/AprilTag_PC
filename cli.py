import time
import logging
from config_loader import ConfigLoader
from camera_utils.camera_processing import CameraProcessor

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def console_worker(config_path='config.yaml'):
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Загрузка конфигурации
        config_loader = ConfigLoader(config_path)
        status_configs, camera_configs = config_loader.load()  
        
        # Инициализация процессора
        processor = CameraProcessor(camera_configs, roi_file='roi/roi.xml')
        
        # Запуск heartbeat для всех конфигураций
        processor.modbus_handler.start_heartbeat(status_configs)
        
        # Запуск обработки
        processor.start_processing()
        logger.info("Сервис запущен в консольном режиме")
        
        try:
            while processor.is_running():
                # В консольном режиме просто ждем и логируем обнаруженные теги
                time.sleep(1)
                
                # Логируем обнаруженные теги
                for cam_idx, tags in processor.last_sent_tags.items():
                    if tags:
                        logger.info(f"Камера {cam_idx + 1}: Обнаружены теги {tags}")
                    else:
                        logger.debug(f"Камера {cam_idx + 1}: Теги не обнаружены")
                        
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания, останавливаю сервис...")
        finally:
            processor.stop_processing()
            logger.info("Сервис остановлен")
            
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    console_worker()