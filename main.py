import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'

import argparse
import time
from config_loader import ConfigLoader
from camera_utils.camera_processing import CameraProcessor
from camera_utils.display_manager import DisplayManager

def parse_args():
    parser = argparse.ArgumentParser(description='AprilTag Detection System')
    parser.add_argument('--console', action='store_true', 
                       help='Run in console mode (for Docker)')
    parser.add_argument('--config', default='config.yaml',
                       help='Path to config file (default: config.yaml)')
    return parser.parse_args()

def gui_main(config_path):
    try:
        # Загрузка конфигурации
        config_loader = ConfigLoader(config_path)
        status_configs, camera_configs = config_loader.load()  
        
        # Инициализация процессора
        processor = CameraProcessor(camera_configs, roi_file='roi/roi.xml')
        
        # Запуск heartbeat для всех конфигураций
        processor.modbus_handler.start_heartbeat(status_configs)
        
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
        print(f"Фатальная ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    args = parse_args()
    
    if args.console:
        from cli import console_worker
        console_worker(args.config)
    else:
        gui_main(args.config)