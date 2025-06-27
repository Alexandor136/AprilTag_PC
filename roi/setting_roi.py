import cv2
import os
import yaml
from pathlib import Path

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

def select_roi_from_rtsp(camera_config):
    """Выбираем ROI из RTSP потока с масштабированием"""
    if not camera_config or 'rtsp' not in camera_config:
        print("Неверная конфигурация камеры")
        return None

    rtsp_url = camera_config['rtsp']
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print(f"Ошибка подключения к RTSP потоку: {rtsp_url}")
        return None

    # Получаем разрешение кадра
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Рассчитываем коэффициент масштабирования (макс 90% экрана)
    screen_width = 1920  # Можно заменить на автоматическое определение
    screen_height = 1080
    scale = min(screen_width / width, screen_height / height) * 0.9

    roi = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
    drawing = False
    ix, iy = -1, -1
    rect_frame = None
    original_frame = None

    def draw_rectangle(event, x, y, flags, param):
        nonlocal drawing, ix, iy, roi, rect_frame, original_frame
        orig_x = int(x / scale)
        orig_y = int(y / scale)
        
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = orig_x, orig_y
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            if original_frame is not None:
                rect_frame = original_frame.copy()
                cv2.rectangle(rect_frame, (ix, iy), (orig_x, orig_y), (0, 255, 0), 2)
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            x0, y0 = min(ix, orig_x), min(iy, orig_y)
            x1, y1 = max(ix, orig_x), max(iy, orig_y)
            roi.update({'x': x0, 'y': y0, 'w': x1-x0, 'h': y1-y0})
            if original_frame is not None:
                rect_frame = original_frame.copy()
                cv2.rectangle(rect_frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
            print(f"Выбран ROI: {roi}")

    window_name = f'RTSP Stream - {camera_config["name"]} ({camera_config["camera_ip"]})'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, draw_rectangle)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Не удалось получить кадр")
            continue

        original_frame = frame.copy()
        display_frame = cv2.resize(frame, None, fx=scale, fy=scale)
        
        if rect_frame is not None:
            display = cv2.resize(rect_frame, None, fx=scale, fy=scale)
        else:
            display = display_frame
        
        cv2.imshow(window_name, display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC - выход
            roi = None
            break
        elif key == ord('s'):  # S - сохранить
            if roi['w'] > 0 and roi['h'] > 0:
                break
            print("Выберите область перед сохранением!")
        elif key == ord('q'):  # Q - отмена
            roi = None
            break

    cap.release()
    cv2.destroyAllWindows()
    return roi

def main():
    """Основная функция"""
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
        save_roi_for_ip(camera['camera_ip'], roi, filename)
        print(f"ROI успешно сохранен в {os.path.abspath(filename)}")
    else:
        print("Сохранение отменено")

if __name__ == "__main__":
    main()