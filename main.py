import cv2
import os
from pupil_apriltags import Detector
import threading
import queue
import reboot_ethernet_interface
from read_roi import load_roi_for_ip, extract_ip_from_url
from camera_utils import camera_worker, display_frames


def main(camera_urls, frame_rate, display=True):
    """Основная функция: запускает потоки обработки камер и отображает результат.

    Args:
        camera_urls (list): Список URL камер для подключения.
        frame_rate (float): Частота обработки кадров (кадров в секунду).
        display (bool): Флаг отображения окон с видеопотоком.
    """
    # Инициализация очереди для передачи кадров между потоками
    output_queue = queue.Queue()
    
    # Событие для остановки всех рабочих потоков
    stop_event = threading.Event()
    
    # Файл с настройками областей интереса (ROI)
    roi_file = "roi.xml"

    # Создаем детекторы AprilTag для каждой камеры
    detectors = [Detector(families='tag36h11', nthreads=1) for _ in camera_urls]
    
    # Список для хранения рабочих потоков
    threads = []

    # Запускаем поток обработки для каждой камеры
    for i, (url, detector) in enumerate(zip(camera_urls, detectors)):
        # Извлекаем IP-адрес из URL камеры
        ip = extract_ip_from_url(url)
        
        # Загружаем настройки ROI для данного IP
        roi = load_roi_for_ip(ip, roi_file)
        
        # Создаем и запускаем поток обработки видеопотока
        thread = threading.Thread(
            target=camera_worker,
            args=(url, detector, frame_rate, output_queue, stop_event, i, roi),
            daemon=True  # Поток завершится при завершении main
        )
        thread.start()
        threads.append(thread)

    # Если требуется отображение, запускаем показ кадров
    if display:
        display_frames(len(camera_urls), output_queue, stop_event)

    # Устанавливаем флаг остановки для всех потоков
    stop_event.set()
    
    # Ожидаем завершения всех рабочих потоков
    for t in threads:
        t.join()
    
    # Закрываем все окна OpenCV
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # URL-адреса камер для подключения
    CAMERA_URLS = [
        "rtsp://admin:kZx_vN8!@10.16.9.52/stream1",
        "rtsp://admin:kZx_vN8!@10.16.9.53/stream1",
        "rtsp://admin:kZx_vN8!@10.16.9.54/stream1"
    ]
    
    # Частота обработки кадров (10 кадров в секунду)
    FRAME_RATE = 10
    
    # Запуск основной функции
    main(CAMERA_URLS, FRAME_RATE)