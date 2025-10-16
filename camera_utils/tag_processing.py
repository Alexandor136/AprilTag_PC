# tag_processing
import cv2
from logger_setup import logger

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

def process_frame(frame, detector, min_tag_area=100.0, max_tag_area=10000.0, camera_name="Unknown"):
    """
    Обрабатывает кадр: конвертирует в оттенки серого, детектирует AprilTags,
    выбирает самые крупные теги с ID 1-4 и рисует их на кадре.

    Args:
        frame (numpy.ndarray): Исходный кадр изображения.
        detector (AprilTagDetector): Объект детектора AprilTag.
        min_tag_area (float): Минимальная площадь тега для фильтрации.
        max_tag_area (float): Максимальная площадь тега для фильтрации.
        camera_name (str): Название камеры для логирования.

    Returns:
        tuple: Кадр с отрисованными тегами и словарь с самыми крупными тегами по ID.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tags = detector.detect(gray)
    largest_tags = {}

    detected_tags_info = []  # Для сбора информации о найденных тегах

    for tag in tags:
        tag_id = tag.tag_id
        if tag_id not in [1, 2, 3, 4]:
            continue
        
        area = calculate_tag_area(tag)
        
        # Фильтрация по площади
        if area < min_tag_area or area > max_tag_area:
            logger.debug(f"Камера {camera_name}: Тег ID {tag_id} отфильтрован по площади {area:.1f} (диапазон: {min_tag_area:.1f}-{max_tag_area:.1f})")
            continue
            
        detected_tags_info.append(f"ID {tag_id} (площадь: {area:.1f})")
            
        if (
            tag_id not in largest_tags or
            area > calculate_tag_area(largest_tags[tag_id])
        ):
            largest_tags[tag_id] = tag

    # Логируем информацию о найденных тегах
    if detected_tags_info:
        logger.info(f"Камера {camera_name}: Обнаружены теги - {', '.join(detected_tags_info)}")
    elif tags:  # Если были теги, но все отфильтрованы
        logger.debug(f"Камера {camera_name}: Теги обнаружены, но отфильтрованы по площади")

    for tag in largest_tags.values():
        draw_tag(frame, tag)

    return frame, largest_tags