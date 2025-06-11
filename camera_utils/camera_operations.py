import cv2
import time
from camera_utils import tag_processing, frame_utils

def open_camera(camera_url, cam_index):
    """
    Открывает видеопоток камеры.

    Args:
        camera_url (str): URL камеры.
        cam_index (int): Индекс камеры для сообщений.

    Returns:
        cv2.VideoCapture or None: Объект захвата или None при ошибке.
    """
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Камера {cam_index + 1} недоступна")
        return None
    return cap

def camera_worker(camera_url, detector, frame_rate, output_queue,
                  stop_event, cam_index, roi):
    """
    Обрабатывает видеопоток с камеры: захват, обрезка ROI, детекция AprilTag,
    добавление текста и отправка в очередь. Отображается полный кадр с
    выделенным ROI красной рамкой.

    Args:
        camera_url (str): URL камеры.
        detector (Detector): Объект детектора AprilTag.
        frame_rate (float): Частота кадров.
        output_queue (Queue): Очередь для передачи обработанных кадров.
        stop_event (Event): Событие остановки потока.
        cam_index (int): Индекс камеры.
        roi (tuple): Область интереса (x, y, w, h).
    """
    cap = open_camera(camera_url, cam_index)
    if cap is None:
        return

    delay = 1.0 / frame_rate

    while not stop_event.is_set():
        start_time = time.time()
        ret, frame = cap.read()

        if not ret:
            print(f"Ошибка получения кадра с камеры {cam_index + 1}")
            time.sleep(delay)
            continue

        # Копируем полный кадр для отображения
        display_frame = frame.copy()
    
        x = int(roi["x"])
        y = int(roi["y"])
        w = int(roi["w"])
        h = int(roi["h"])
        roi_frame = frame[y:y + h, x:x + w]

        # Обработка ROI
        processed_roi, largest_tags = tag_processing.process_frame(roi_frame, detector)

        # Вставляем обработанный ROI обратно в копию полного кадра
        display_frame[y:y + h, x:x + w] = processed_roi

        # Рисуем красную рамку вокруг ROI
        cv2.rectangle(display_frame, (x, y), (x + w, y + h),
                      color=(0, 0, 255), thickness=2)

        # Добавляем текст с ID тегов, если есть
        if largest_tags:
            text_lines = [f"ID: {tag_id}" for tag_id in largest_tags.keys()]
            display_frame = frame_utils.prepare_text_frame(display_frame, text_lines)

        output_queue.put((cam_index, display_frame))

        elapsed = time.time() - start_time
        time_to_wait = delay - elapsed
        if time_to_wait > 0:
            time.sleep(time_to_wait)

    cap.release()