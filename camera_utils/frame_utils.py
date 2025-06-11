import cv2
import numpy as np

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