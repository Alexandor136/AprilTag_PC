# camera_utils.py
import cv2
import numpy as np
import time
import log

def draw_tag(frame, tag):
    """
    Рисует контур и центр AprilTag на кадре.

    Args:
        frame (numpy.ndarray): Кадр изображения.
        tag (AprilTag): Объект тега с координатами и центром.
    """
    corners = tag.corners.astype(int)
    for j in range(4):
        cv2.line(
            frame,
            tuple(corners[j]),
            tuple(corners[(j + 1) % 4]),
            (0, 255, 0),
            2
        )
    center = (int(tag.center[0]), int(tag.center[1]))
    cv2.circle(frame, center, 5, (0, 0, 255), -1)


def calculate_tag_area(tag):
    """
    Вычисляет площадь четырехугольника, образованного углами тега.

    Args:
        tag (AprilTag): Объект тега с координатами углов.

    Returns:
        float: Площадь тега.
    """
    corners = tag.corners
    x = [p[0] for p in corners]
    y = [p[1] for p in corners]
    return 0.5 * abs(
        (x[0] * y[1] + x[1] * y[2] + x[2] * y[3] + x[3] * y[0]) -
        (y[0] * x[1] + y[1] * x[2] + y[2] * x[3] + y[3] * x[0])
    )


def process_frame(frame, detector):
    """
    Обрабатывает кадр: конвертирует в оттенки серого, детектирует AprilTags,
    выбирает самые крупные теги с ID 1-4 и рисует их на кадре.

    Args:
        frame (numpy.ndarray): Исходный кадр изображения.
        detector (AprilTagDetector): Объект детектора AprilTag.

    Returns:
        tuple: Кадр с отрисованными тегами и словарь с самыми крупными тегами по ID.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tags = detector.detect(gray)
    largest_tags = {}

    for tag in tags:
        tag_id = tag.tag_id
        if tag_id not in [1, 2, 3, 4]:
            continue
        area = calculate_tag_area(tag)
        if (
            tag_id not in largest_tags or
            area > calculate_tag_area(largest_tags[tag_id])
        ):
            largest_tags[tag_id] = tag

    for tag in largest_tags.values():
        draw_tag(frame, tag)

    return frame, largest_tags


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


def crop_frame(frame, roi):
    """
    Обрезает кадр по ROI.

    Args:
        frame (np.ndarray): Исходный кадр.
        roi (dict): Словарь с ключами 'x', 'y', 'w', 'h'.

    Returns:
        np.ndarray: Обрезанный кадр.
    """
    if roi:
        x, y, w, h = roi['x'], roi['y'], roi['w'], roi['h']
        return frame[y:y + h, x:x + w]
    return frame


def prepare_text_frame(frame, text_lines):
    """
    Добавляет текст под изображением.

    Args:
        frame (np.ndarray): Кадр изображения.
        text_lines (list[str]): Список строк текста.

    Returns:
        np.ndarray: Кадр с добавленным текстом снизу.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.6
    font_color = (255, 255, 255)
    line_type = 2
    line_height = 50
    margin = 10
    text_height = line_height * len(text_lines) + margin

    new_frame = np.zeros((frame.shape[0] + text_height, frame.shape[1], 3), dtype=np.uint8)
    new_frame[:frame.shape[0], :, :] = frame

    for i, line in enumerate(text_lines):
        y = frame.shape[0] + (i + 1) * line_height - 10
        cv2.putText(new_frame, line, (10, y), font, font_scale, font_color, line_type)

    return new_frame


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
        processed_roi, largest_tags = process_frame(roi_frame, detector)

        # Вставляем обработанный ROI обратно в копию полного кадра
        display_frame[y:y + h, x:x + w] = processed_roi

        # Рисуем красную рамку вокруг ROI
        cv2.rectangle(display_frame, (x, y), (x + w, y + h),
                      color=(0, 0, 255), thickness=2)

        # Добавляем текст с ID тегов, если есть
        if largest_tags:
            text_lines = [f"ID: {tag_id}" for tag_id in largest_tags.keys()]
            display_frame = prepare_text_frame(display_frame, text_lines)

        output_queue.put((cam_index, display_frame))

        elapsed = time.time() - start_time
        time_to_wait = delay - elapsed
        if time_to_wait > 0:
            time.sleep(time_to_wait)

    cap.release()


def display_frames(camera_count, output_queue, stop_event):
    """
    Отображает кадры с камер в окнах.

    Args:
        camera_count (int): Количество камер.
        output_queue (Queue): Очередь с кадрами.
        stop_event (Event): Событие остановки.
    """
    frames = [None] * camera_count

    for i in range(camera_count):
        cv2.namedWindow(f'Камера {i + 1}', cv2.WINDOW_NORMAL)
        cv2.resizeWindow(f'Камера {i + 1}', 800, 600)

    try:
        while not stop_event.is_set():
            while not output_queue.empty():
                cam_index, frame = output_queue.get()
                frames[cam_index] = frame

            for i, frame in enumerate(frames):
                if frame is not None:
                    cv2.imshow(f'Камера {i + 1}', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_event.set()
                break

            time.sleep(0.01)
    except KeyboardInterrupt:
        stop_event.set()