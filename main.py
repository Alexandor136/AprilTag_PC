import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'

import time
from config_loader import ConfigLoader
from camera_utils.camera_processing import CameraProcessor
from camera_utils.display_manager import DisplayManager

def main():
    try:
        # Загрузка конфигурации
        config_loader = ConfigLoader("config.yaml")
        camera_configs = config_loader.load()
        
        # Инициализация процессора
        processor = CameraProcessor(camera_configs, roi_file='roi/roi.xml')  # Указываем путь к ROI
        display = DisplayManager(len(camera_configs))
        
        # Запуск обработки
        processor.start_processing()
        display.start_display(processor.output_queue)
        
        try:
            while processor.is_running():
                if display.update_display():
                    break
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\nОстановка по запросу пользователя...")
        finally:
            processor.stop_processing()
            display.stop_display()
            
    except Exception as e:
        print(f"Фатальная ошибка: {str(e)}")

if __name__ == "__main__":
    main()