import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel,
                             QVBoxLayout, QHBoxLayout, QWidget, QScrollArea)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from pupil_apriltags import Detector


class CameraWidget(QLabel):
    """Виджет для отображения видеопотока с камеры."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 360)
        self.setText("Инициализация камеры...")


class InfoWidget(QLabel):
    """Виджет для отображения информации о найденных AprilTags."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setMinimumWidth(300)
        self.setWordWrap(True)
        self.setText("Информация о AprilTag:\n")

    def update_info(self, info):
        """Обновление информации о AprilTag."""
        self.setText(f"Информация о AprilTag:\n{info}")


class CameraInfoWidget(QWidget):
    """Виджет для отображения информации о камере и видеопотока."""
    
    def __init__(self, camera_url, parent=None):
        super().__init__(parent)

        self.info_widget = InfoWidget()
        self.camera_label = QLabel(f"Камера: {camera_url}")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_widget = CameraWidget()

        # Вертикальный лэйаут с названием и изображением
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.camera_label)
        right_layout.addWidget(self.camera_widget)

        # Горизонтальный лэйаут: слева camera_widget, справа info_widget
        main_layout = QHBoxLayout(self)
        main_layout.addLayout(right_layout)  # Сначала добавляем right_layout с изображением
        main_layout.addWidget(self.info_widget, alignment=Qt.AlignVCenter)  # Затем info_widget справа по центру

        # Настройка растяжения
        main_layout.setStretch(0, 3)  # Изображение с названием шире
        main_layout.setStretch(1, 1)  # info_widget уже


class MainWindow(QMainWindow):
    """Главное окно приложения для системы видеонаблюдения с AprilTags."""
    
    def __init__(self, camera_urls):
        super().__init__()
        self.camera_urls = camera_urls
        self.captures = []  # Список для хранения объектов захвата видео
        self.detectors = []  # Список для хранения детекторов AprilTags
        self.camera_info_widgets = []  # Список для хранения виджетов информации о камерах

        self.init_ui()  # Инициализация пользовательского интерфейса
        self.init_cameras()  # Инициализация камер
        self.init_detectors()  # Инициализация детекторов

        self.timer = QTimer(self)  # Таймер для обновления кадров
        self.timer.timeout.connect(self.update_frames)  # Подключение метода обновления кадров
        self.timer.start(30)  # Запуск таймера (~30 FPS)

    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        self.setWindowTitle("Система видеонаблюдения с обнаружением AprilTags")
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        container = QWidget()
        self.layout = QVBoxLayout(container)

        # Для каждой камеры создаём виджет с картинкой и информацией
        for url in self.camera_urls:
            cam_info_widget = CameraInfoWidget(url)
            self.camera_info_widgets.append(cam_info_widget)
            self.layout.addWidget(cam_info_widget)

        self.scroll_area.setWidget(container)
        self.setCentralWidget(self.scroll_area)
        self.resize(1100, 800)

    def init_cameras(self):
        """Инициализация камер и проверка их доступности."""
        for url in self.camera_urls:
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.captures.append(cap)  # Сохраняем объект захвата
            else:
                print(f"Ошибка подключения к камере: {url}")
                self.captures.append(None)  # Добавляем None, если камера недоступна

    def init_detectors(self):
        """Инициализация детекторов AprilTags."""
        for _ in self.camera_urls:
            detector = Detector(
                families='tag36h11',
                nthreads=2,
                quad_decimate=1.0,
                quad_sigma=0.0,
                refine_edges=1,
                decode_sharpening=0.25,
                debug=0
            )
            self.detectors.append(detector)  # Сохраняем объект детектора

    def update_frames(self):
        """Обновление кадров из камер и обработка AprilTags."""
        for cap, detector, cam_info_widget in zip(self.captures, self.detectors, self.camera_info_widgets):
            camera_widget = cam_info_widget.camera_widget
            info_widget = cam_info_widget.info_widget

            if cap and cap.isOpened():
                ret, frame = cap.read()  # Чтение кадра из камеры
                if ret:
                    processed_frame, tag_info = self.process_frame(frame, detector)

                    h, w, ch = processed_frame.shape
                    bytes_per_line = ch * w
                    qimage = QImage(processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

                    pixmap = QPixmap.fromImage(qimage)
                    pixmap = pixmap.scaled(
                        640, 360,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )

                    camera_widget.setPixmap(pixmap)
                    info_widget.update_info(tag_info)
                else:
                    camera_widget.setText("Ошибка получения кадра")
                    info_widget.update_info("Нет данных о AprilTag")
            else:
                camera_widget.setText("Камера недоступна")
                info_widget.update_info("Камера недоступна")

    def process_frame(self, frame, detector):
        """Обработка кадра для поиска AprilTags."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Преобразование в RGB
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Преобразование в оттенки серого
        tags = detector.detect(gray)  # Обнаружение AprilTags

        max_area = 0
        largest_tag = None
        tag_info = "Нет обнаруженных AprilTags"

        for tag in tags:
            area = self.calculate_tag_area(tag)  # Вычисление площади тега
            if area > max_area:
                max_area = area
                largest_tag = tag  # Запоминаем самый большой тег

        if largest_tag:
            corners = [(int(pt[0]), int(pt[1])) for pt in largest_tag.corners]
            for j in range(4):
                cv2.line(frame_rgb, corners[j], corners[(j + 1) % 4], (0, 255, 0), 2)  # Рисуем рамку тега
            center = (int(largest_tag.center[0]), int(largest_tag.center[1]))
            cv2.circle(frame_rgb, center, 5, (0, 0, 255), -1)  # Рисуем центр тега

            tag_info = f"ID: {largest_tag.tag_id}\nПлощадь: {max_area:.1f}\nЦентр: ({center[0]}, {center[1]})"

        return frame_rgb, tag_info

    def calculate_tag_area(self, tag):
        """Вычисление площади AprilTag."""
        corners = tag.corners
        x = [p[0] for p in corners]
        y = [p[1] for p in corners]
        return 0.5 * abs(
            (x[0] * y[1] + x[1] * y[2] + x[2] * y[3] + x[3] * y[0]) -
            (y[0] * x[1] + y[1] * x[2] + y[2] * x[3] + y[3] * x[0])
        )

    def closeEvent(self, event):
        """Обработка события закрытия окна."""
        for cap in self.captures:
            if cap:
                cap.release()  # Освобождение ресурсов камеры
        event.accept()


if __name__ == "__main__":
    # Список URL-адресов камер
    CAMERA_URLS = [
        "rtsp://admin:kZx_vN8!@172.16.9.54/stream1",
        "rtsp://admin:kZx_vN8!@172.16.9.53/stream1",
        "rtsp://admin:kZx_vN8!@172.16.9.52/stream1"
    ]

    app = QApplication(sys.argv)  # Создание приложения
    window = MainWindow(CAMERA_URLS)  # Создание главного окна
    window.show()  # Отображение окна
    sys.exit(app.exec_())  # Запуск цикла обработки событий
