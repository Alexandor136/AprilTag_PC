import cv2
from pupil_apriltags import Detector
import numpy as np
import threading
import queue
import time
import reboot_ethernet_interface

def draw_tag(frame, tag):
    """Отображает AprilTag на кадре."""
    corners = tag.corners.astype(int)
    for j in range(4):
        # Рисуем линии между углами тега
        cv2.line(frame, tuple(corners[j]), tuple(corners[(j + 1) % 4]), (0, 255, 0), 2)
    center = (int(tag.center[0]), int(tag.center[1]))
    # Рисуем центр тега
    cv2.circle(frame, center, 5, (0, 0, 255), -1)

def process_frame(frame, detector):
    """Обрабатывает кадр, детектируя AprilTags и возвращая наибольший по площади тег для каждого id."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tags = detector.detect(gray)

    max_area = 0
    largest_tag = None
    largest_tags = {}  # ключ: tag_id, значение: тег с максимальной площадью

    for tag in tags:
        tag_id = tag.tag_id
        if tag_id not in [1, 2, 3, 4]:
            continue

        area = calculate_tag_area(tag)

        if tag_id not in largest_tags or area > calculate_tag_area(largest_tags[tag_id]):
            largest_tags[tag_id] = tag

    return frame, largest_tags

def calculate_tag_area(tag):
    """Вычисляет площадь AprilTag на основании его углов."""
    corners = tag.corners
    x = [p[0] for p in corners]
    y = [p[1] for p in corners]
    return 0.5 * abs(
        (x[0] * y[1] + x[1] * y[2] + x[2] * y[3] + x[3] * y[0]) -
        (y[0] * x[1] + y[1] * x[2] + y[2] * x[3] + y[3] * x[0])
    )

def camera_worker(camera_url, detector, frame_rate, output_queue, stop_event, cam_index):
    """Рабочий поток для захвата и обработки кадров с камеры."""
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Камера {cam_index + 1} недоступна")
        return

    delay = 1.0 / frame_rate
    while not stop_event.is_set():
        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            print(f"Ошибка получения кадра с камеры {cam_index + 1}")
            time.sleep(delay)
            continue

        processed_frame, largest_tags = process_frame(frame, detector)

        if largest_tags:
            text_lines = []
            for tag_id, tag in largest_tags.items():
                draw_tag(processed_frame, tag)
                area = calculate_tag_area(tag)
                info = f"ID: {tag_id} Area: {int(area)} px Margin: {tag.decision_margin:.2f} Hamming: {tag.hamming}"
                text_lines.append(info)

            # Параметры текста
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.6  
            font_color = (255, 255, 255)
            line_type = 2
            
            line_height = 50  # высота строки (пиксели)
            margin = 10  # дополнительный отступ снизу
            text_height = line_height * len(text_lines) + margin

            # Создаем новый кадр с дополнительным местом для текста
            new_frame = np.zeros((frame.shape[0] + text_height, frame.shape[1], 3), dtype=np.uint8)
            new_frame[:frame.shape[0], :, :] = processed_frame

            # Рисуем текст
            for i, line in enumerate(text_lines):
                y = frame.shape[0] + (i + 1) * line_height - 10  # корректируем по базовой линии текста
                cv2.putText(new_frame, line, (10, y), font, font_scale, font_color, line_type)

            output_queue.put((cam_index, new_frame))
        else:
            output_queue.put((cam_index, processed_frame))

        elapsed = time.time() - start_time
        time_to_wait = delay - elapsed
        if time_to_wait > 0:
            time.sleep(time_to_wait)

    cap.release()

def main(camera_urls, frame_rate, display=True):
    """Основная функция, запускающая обработку видеопотоков."""
    detectors = [Detector(families='tag36h11', nthreads=1) for _ in camera_urls]
    output_queue = queue.Queue()
    stop_event = threading.Event()

    # Запускаем потоки для каждой камеры
    threads = []
    for i, (url, detector) in enumerate(zip(camera_urls, detectors)):
        t = threading.Thread(target=camera_worker, args=(url, detector, frame_rate, output_queue, stop_event, i), daemon=True)
        t.start()
        threads.append(t)

    if display:
        for i in range(len(camera_urls)):
            cv2.namedWindow(f'Камера {i + 1}', cv2.WINDOW_NORMAL)
            cv2.resizeWindow(f'Камера {i + 1}', 800, 600)

    try:
        frames = [None] * len(camera_urls)
        while True:
            # Получаем обработанные кадры из очереди
            while not output_queue.empty():
                cam_index, frame = output_queue.get()
                frames[cam_index] = frame

            if display:
                for i, frame in enumerate(frames):
                    if frame is not None:
                        cv2.imshow(f'Камера {i + 1}', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(0.01)  # Пауза для снижения нагрузки на CPU

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()  # Устанавливаем событие остановки для всех потоков
        for t in threads:
            t.join()  # Ждем завершения всех потоков
        cv2.destroyAllWindows()  # Закрываем все окна OpenCV

if __name__ == "__main__":

    reboot_ethernet_interface.reboot_interface('enp2s0')

    CAMERA_URLS = [
        "rtsp://admin:kZx_vN8!@172.16.9.52/stream1",
        "rtsp://admin:kZx_vN8!@172.16.9.53/stream1",
        "rtsp://admin:kZx_vN8!@172.16.9.54/stream1"
    ]

    FRAME_RATE = 10  # Частота кадров
    main(CAMERA_URLS, FRAME_RATE)  # Запускаем основную функцию
# 9.17