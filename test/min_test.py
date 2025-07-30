import cv2
from pupil_apriltags import Detector
from concurrent.futures import ThreadPoolExecutor
import numpy as np


def draw_tag(frame, tag):
    """Обводит найденный AprilTag на кадре."""
    corners = tag.corners.astype(int)
    for i in range(4):
        pt1 = tuple(corners[i])
        pt2 = tuple(corners[(i + 1) % 4])
        cv2.line(frame, pt1, pt2, (0, 255, 0), 2)


def process_stream(rtsp_url):
    at_detector = Detector(
        families="tag36h11",
        nthreads=1,
        quad_decimate=1.0,
        quad_sigma=0.0,
        refine_edges=1,
        decode_sharpening=0.25,
        debug=0,
    )

    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"Ошибка: Не удалось открыть поток {rtsp_url}")
        return

    window_name = f"Stream from {rtsp_url}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # Параметры для текста
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    font_color = (255, 255, 255)
    line_type = 2
    margin = 5

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Ошибка: Не удалось получить кадр из {rtsp_url}")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tags = at_detector.detect(gray)

        max_area = 0
        largest_tag = None

        # Находим тег с максимальной площадью
        for tag in tags:
            corners = tag.corners.astype(int)
            area = cv2.contourArea(corners)
            if area > max_area:
                max_area = area
                largest_tag = tag

        # Если найден самый большой тег, рисуем его и выводим информацию
        if largest_tag is not None:
            draw_tag(frame, largest_tag)
            corners = largest_tag.corners.astype(int)
            area = cv2.contourArea(corners)

            # Создаем текст для отображения
            info_text = f"ID: {largest_tag.tag_id} Area: {int(area)} px"

            # Высота полосы: примерно 25 пикселей на строку текста
            text_height = 30
            h, w = frame.shape[:2]

            # Создаем новое изображение с дополнительной полосой снизу
            new_frame = np.zeros((h + text_height, w, 3), dtype=np.uint8)
            new_frame[:h, :, :] = frame

            # Рисуем текст внизу
            cv2.putText(new_frame, info_text, (10, h + text_height - margin), font, font_scale, font_color, line_type)

            cv2.imshow(window_name, new_frame)
        else:
            # Если тегов нет, просто показываем кадр без доп. полосы
            cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyWindow(window_name)


def main():
    rtsp_urls = [
        "rtsp://admin:kZx_vN8!@192.168.17.86/stream1"
    ]

    with ThreadPoolExecutor(max_workers=len(rtsp_urls)) as executor:
        executor.map(process_stream, rtsp_urls)


if __name__ == "__main__":
    main()
