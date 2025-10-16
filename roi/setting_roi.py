import cv2
import os
import yaml
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib

def load_config(config_path="config.yaml"):
    """Загружаем конфигурацию из YAML файла"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        return None

def select_camera(config):
    """Выбираем камеру из списка в конфигурации"""
    if not config or 'cameras' not in config:
        print("В конфигурации нет списка камер")
        return None
    
    cameras = [cam for cam in config['cameras'] if not cam.get('disabled', False)]
    
    if not cameras:
        print("Нет доступных камер в конфигурации")
        return None
    
    print("\nДоступные камеры:")
    for i, cam in enumerate(cameras, 1):
        print(f"{i}. {cam['name']} ({cam['camera_ip']})")
    
    while True:
        try:
            choice = int(input("\nВыберите номер камеры (0 для выхода): "))
            if choice == 0:
                return None
            if 1 <= choice <= len(cameras):
                return cameras[choice-1]
            print("Некорректный выбор, попробуйте еще раз")
        except ValueError:
            print("Введите число")

def ip_to_key(ip):
    """Конвертируем IP в ключ для XML"""
    return "ip_" + ip.replace(".", "_")

def save_roi_for_ip(ip, roi, filename):
    """Сохраняем ROI в XML файл с проверкой и перезаписью"""
    filename = str(Path(filename).absolute())
    print(f"Сохраняем ROI для {ip} в файл: {filename}")
    
    data = {ip_to_key(ip): roi}
    
    if os.path.exists(filename):
        try:
            fs_read = cv2.FileStorage(filename, cv2.FILE_STORAGE_READ)
            if fs_read.isOpened():
                current_key = ip_to_key(ip)
                for key in fs_read.root().keys():
                    if key != current_key:
                        node = fs_read.getNode(key)
                        if not node.empty() and node.isMap():
                            x = node.getNode('x').real() if not node.getNode('x').empty() else 0
                            y = node.getNode('y').real() if not node.getNode('y').empty() else 0
                            w = node.getNode('w').real() if not node.getNode('w').empty() else 0
                            h = node.getNode('h').real() if not node.getNode('h').empty() else 0
                            data[key] = {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
        finally:
            fs_read.release()

    try:
        fs_write = cv2.FileStorage(filename, cv2.FILE_STORAGE_WRITE)
        if not fs_write.isOpened():
            raise IOError("Не удалось открыть файл для записи")
            
        for cam_key, r in data.items():
            fs_write.startWriteStruct(cam_key, cv2.FILE_NODE_MAP)
            fs_write.write("x", int(r['x']))
            fs_write.write("y", int(r['y']))
            fs_write.write("w", int(r['w']))
            fs_write.write("h", int(r['h']))
            fs_write.endWriteStruct()
        
        print(f"ROI успешно сохранен для камеры {ip}")
    except Exception as e:
        print(f"Ошибка записи в файл: {e}")
    finally:
        fs_write.release()

def load_existing_roi(ip, filename="roi/roi.xml"):
    """Загружаем существующий ROI из XML файла"""
    if not os.path.exists(filename):
        return None
    
    try:
        fs = cv2.FileStorage(filename, cv2.FILE_STORAGE_READ)
        if not fs.isOpened():
            return None
            
        key = ip_to_key(ip)
        node = fs.getNode(key)
        if node.empty() or not node.isMap():
            return None
            
        x = node.getNode('x').real() if not node.getNode('x').empty() else 0
        y = node.getNode('y').real() if not node.getNode('y').empty() else 0
        w = node.getNode('w').real() if not node.getNode('w').empty() else 0
        h = node.getNode('h').real() if not node.getNode('h').empty() else 0
        
        fs.release()
        
        if w > 0 and h > 0:
            return {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
        else:
            return None
            
    except Exception as e:
        print(f"Ошибка загрузки существующего ROI: {e}")
        return None

def select_roi_from_rtsp(camera_config):
    """Выбираем ROI из RTSP потока используя matplotlib"""
    if not camera_config or 'rtsp' not in camera_config:
        print("Неверная конфигурация камеры")
        return None

    rtsp_url = camera_config['rtsp']
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print(f"Ошибка подключения к RTSP потоку: {rtsp_url}")
        return None

    # Получаем кадр
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Не удалось получить кадр из потока")
        return None

    # Загружаем существующий ROI
    existing_roi = load_existing_roi(camera_config['camera_ip'])
    
    # Конвертируем BGR в RGB для matplotlib
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Создаем график
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(frame_rgb)
    ax.set_title(f'Выберите ROI для {camera_config["name"]}\n'
                f'Кликните и протяните для выбора области\n'
                f'Закройте окно для сохранения')
    
    # Рисуем существующий ROI красным
    if existing_roi:
        rect = Rectangle((existing_roi['x'], existing_roi['y']), 
                        existing_roi['w'], existing_roi['h'],
                        linewidth=2, edgecolor='red', facecolor='none',
                        label='Existing ROI')
        ax.add_patch(rect)
        ax.legend()
    
    # Включаем интерактивный режим
    plt.ion()
    plt.show()
    
    # Используем встроенный выбор ROI matplotlib
    print("Выберите область на изображении...")
    print("Инструкция:")
    print("1. Нажмите 'r' для сброса выделения")
    print("2. Нажмите 'c' для отмены")
    print("3. Закройте окно для сохранения")
    
    # Получаем ROI через matplotlib
    roi_coords = plt.ginput(2, timeout=0, show_clicks=True)
    
    if len(roi_coords) == 2:
        x1, y1 = roi_coords[0]
        x2, y2 = roi_coords[1]
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        
        if w > 10 and h > 10:  # Минимальный размер
            selected_roi = {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
            print(f"Выбран новый ROI: {selected_roi}")
            plt.close()
            return selected_roi
    
    plt.close()
    
    # Если не выбран новый ROI, используем существующий
    if existing_roi:
        print("Используется существующий ROI")
        return existing_roi
    else:
        print("ROI не выбран")
        return None
    
def main():
    """Основная функция"""
    try:
        # Загружаем конфигурацию
        config = load_config()
        if not config:
            print("Не удалось загрузить конфигурацию")
            return
        
        # Выбираем камеру
        camera = select_camera(config)
        if not camera:
            print("Камера не выбрана")
            return
        
        print(f"\nНастройка ROI для камеры: {camera['name']} ({camera['camera_ip']})")
        
        # Выбираем ROI
        roi = select_roi_from_rtsp(camera)
        
        # Сохраняем результат
        if roi and roi['w'] > 0 and roi['h'] > 0:
            filename = "roi/roi.xml"
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            save_roi_for_ip(camera['camera_ip'], roi, filename)
            print(f"ROI успешно сохранен в {os.path.abspath(filename)}")
        else:
            print("Сохранение отменено")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Гарантируем закрытие всех окон OpenCV
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()