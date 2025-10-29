import cv2
import os
import yaml
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import requests
from requests.auth import HTTPDigestAuth
import time

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

def get_snapshot_from_camera(camera_config):
    """Получаем снимок с камеры через HTTP запрос"""
    if not camera_config:
        print("Неверная конфигурация камеры")
        return None

    # Используем snapshot_url если есть, иначе формируем стандартный
    if 'snapshot_url' in camera_config and camera_config['snapshot_url']:
        url = camera_config['snapshot_url']
    else:
        # Стандартный URL для снимков Hikvision
        url = f"http://{camera_config['camera_ip']}/ISAPI/Streaming/channels/101/picture?snapShotImageType=JPEG"
    
    username = camera_config.get('username', 'admin')
    password = camera_config.get('password', '')
    
    print(f"Подключаемся к камере {camera_config['name']}...")
    print(f"URL: {url}")
    
    try:
        # Создаем сессию с аутентификацией
        session = requests.Session()
        session.auth = HTTPDigestAuth(username, password)
        session.timeout = 10
        
        # Получаем снимок
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            # Конвертируем в изображение OpenCV
            img_array = np.frombuffer(response.content, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                print(f"Успешно получен снимок: {frame.shape[1]}x{frame.shape[0]}")
                return frame
            else:
                print("Ошибка: не удалось декодировать изображение")
        else:
            print(f"Ошибка HTTP: {response.status_code}")
            # Пробуем альтернативный URL
            if response.status_code == 404 or response.status_code == 401:
                print("Пробуем альтернативный URL...")
                alt_url = f"http://{camera_config['camera_ip']}/ISAPI/Streaming/channels/1/picture"
                response = session.get(alt_url, timeout=10)
                if response.status_code == 200:
                    img_array = np.frombuffer(response.content, dtype=np.uint8)
                    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    if frame is not None:
                        print(f"Успешно получен снимок с альтернативного URL: {frame.shape[1]}x{frame.shape[0]}")
                        return frame
                
    except requests.exceptions.Timeout:
        print("Таймаут подключения к камере")
    except requests.exceptions.ConnectionError:
        print("Ошибка соединения с камерой")
    except Exception as e:
        print(f"Ошибка получения снимка: {e}")
    
    return None

def select_roi_from_snapshot(camera_config):
    """Выбираем ROI из снимка камеры используя matplotlib"""
    # Получаем снимок с камеры
    frame = get_snapshot_from_camera(camera_config)
    if frame is None:
        print("Не удалось получить снимок с камеры")
        return None

    # Загружаем существующий ROI
    existing_roi = load_existing_roi(camera_config['camera_ip'])
    
    # Конвертируем BGR в RGB для matplotlib
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Создаем график
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(frame_rgb)
    ax.set_title(f'Выберите ROI для {camera_config["name"]}\n'
                f'Кликните дважды для определения двух противоположных углов\n'
                f'Закройте окно для сохранения')
    
    # Рисуем существующий ROI красным
    if existing_roi:
        rect = Rectangle((existing_roi['x'], existing_roi['y']), 
                        existing_roi['w'], existing_roi['h'],
                        linewidth=2, edgecolor='red', facecolor='none',
                        label='Существующий ROI')
        ax.add_patch(rect)
        ax.legend()
    
    # Включаем интерактивный режим
    plt.ion()
    plt.show()
    
    print("Инструкция:")
    print("1. Кликните ЛЕВОЙ кнопкой мыши в первый угол ROI")
    print("2. Кликните ЛЕВОЙ кнопкой мыши во второй противоположный угол")
    print("3. Закройте окно для сохранения")
    print("4. Нажмите 'q' в окне для отмены")
    
    try:
        # Получаем ROI через matplotlib ginput
        roi_coords = plt.ginput(2, timeout=0, show_clicks=True)
        
        if len(roi_coords) == 2:
            x1, y1 = roi_coords[0]
            x2, y2 = roi_coords[1]
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            
            # Проверяем минимальный размер
            if w > 10 and h > 10:
                selected_roi = {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
                print(f"Выбран новый ROI: {selected_roi}")
                plt.close()
                return selected_roi
            else:
                print("Слишком маленький ROI, минимальный размер 10x10 пикселей")
        
        plt.close()
        
    except Exception as e:
        print(f"Ошибка при выборе ROI: {e}")
        plt.close()
    
    # Если не выбран новый ROI, используем существующий
    if existing_roi:
        use_existing = input("Использовать существующий ROI? (y/n): ").lower().strip()
        if use_existing == 'y':
            print("Используется существующий ROI")
            return existing_roi
    
    print("ROI не выбран")
    return None

def test_camera_connection(camera_config):
    """Тестируем подключение к камере"""
    print(f"Тестируем подключение к {camera_config['name']}...")
    
    frame = get_snapshot_from_camera(camera_config)
    if frame is not None:
        print("✓ Подключение успешно")
        return True
    else:
        print("✗ Ошибка подключения")
        return False

def main():
    """Основная функция"""
    try:
        # Загружаем конфигурацию
        config_path = input("Введите путь к config.yaml (по умолчанию config.yaml): ").strip()
        if not config_path:
            config_path = "config.yaml"
            
        config = load_config(config_path)
        if not config:
            print("Не удалось загрузить конфигурацию")
            return
        
        # Выбираем камеру
        camera = select_camera(config)
        if not camera:
            print("Камера не выбрана")
            return
        
        print(f"\nНастройка ROI для камеры: {camera['name']} ({camera['camera_ip']})")
        
        # Тестируем подключение
        if not test_camera_connection(camera):
            retry = input("Повторить попытку подключения? (y/n): ").lower().strip()
            if retry != 'y':
                return
        
        # Выбираем ROI
        roi = select_roi_from_snapshot(camera)
        
        # Сохраняем результат
        if roi and roi['w'] > 0 and roi['h'] > 0:
            filename = "roi/roi.xml"
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            save_roi_for_ip(camera['camera_ip'], roi, filename)
            print(f"✓ ROI успешно сохранен в {os.path.abspath(filename)}")
            
            # Показываем предпросмотр
            preview = input("Показать предпросмотр с ROI? (y/n): ").lower().strip()
            if preview == 'y':
                frame = get_snapshot_from_camera(camera)
                if frame is not None:
                    # Рисуем ROI на изображении
                    x, y, w, h = roi['x'], roi['y'], roi['w'], roi['h']
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                    cv2.putText(frame, f"ROI: {w}x{h}", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # Показываем изображение
                    cv2.imshow(f"ROI Preview - {camera['name']}", frame)
                    print("Нажмите любую клавишу для закрытия окна...")
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
        else:
            print("Сохранение отменено")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Гарантируем закрытие всех окон
        cv2.destroyAllWindows()
        plt.close('all')

if __name__ == "__main__":
    main()