import cv2
import os
import sys
from pathlib import Path

def ip_to_key(ip):
    """Конвертируем IP в ключ для XML"""
    return "ip_" + ip.replace(".", "_")

def save_roi_for_ip(ip, roi, filename):
    """Сохраняем ROI в XML файл с проверкой и перезаписью"""
    # Получаем абсолютный путь к файлу
    filename = str(Path(filename).absolute())
    print(f"Сохраняем ROI для {ip} в файл: {filename}")
    
    # Создаем новую структуру данных
    data = {ip_to_key(ip): roi}
    
    # Если файл существует, читаем старые данные (кроме текущей камеры)
    if os.path.exists(filename):
        try:
            fs_read = cv2.FileStorage(filename, cv2.FILE_STORAGE_READ)
            if fs_read.isOpened():
                current_key = ip_to_key(ip)
                for key in fs_read.root().keys():
                    if key != current_key:  # Пропускаем данные для текущей камеры
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

    # Записываем новые данные
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

def select_roi_from_rtsp(ip):
    """Выбираем ROI из RTSP потока"""
    rtsp_url = f"rtsp://admin:kZx_vN8!@{ip}/stream1"
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print(f"Ошибка подключения к RTSP потоку: {rtsp_url}")
        return None

    roi = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
    drawing = False
    ix, iy = -1, -1
    rect_frame = None

    def draw_rectangle(event, x, y, flags, param):
        nonlocal drawing, ix, iy, roi, rect_frame
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            rect_frame = frame.copy()
            cv2.rectangle(rect_frame, (ix, iy), (x, y), (0, 255, 0), 2)
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            x0, y0 = min(ix, x), min(iy, y)
            x1, y1 = max(ix, x), max(iy, y)
            roi.update({'x': x0, 'y': y0, 'w': x1-x0, 'h': y1-y0})
            rect_frame = frame.copy()
            cv2.rectangle(rect_frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
            print(f"Выбран ROI: {roi}")

    cv2.namedWindow(f'RTSP Stream - {ip}')
    cv2.setMouseCallback(f'RTSP Stream - {ip}', draw_rectangle)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Не удалось получить кадр")
            continue

        display = rect_frame if rect_frame is not None else frame
        cv2.imshow(f'RTSP Stream - {ip}', display)
        
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
    # Настройки
    ip = "10.16.9.54"  # IP камеры по умолчанию
    filename = "roi/roi.xml"  # Файл для сохранения ROI
    
    # Выбираем ROI
    print(f"Настройка ROI для камеры {ip}")

    
    roi = select_roi_from_rtsp(ip)
    
    # Сохраняем результат
    if roi and roi['w'] > 0 and roi['h'] > 0:
        save_roi_for_ip(ip, roi, filename)
        print(f"ROI успешно сохранен в {os.path.abspath(filename)}")
    else:
        print("Сохранение отменено")

if __name__ == "__main__":
    main()