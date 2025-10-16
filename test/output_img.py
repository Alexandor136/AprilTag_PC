import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QVBoxLayout, QHBoxLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

class CameraWidget(QLabel):
    def __init__(self, url, caption, parent=None):
        super().__init__(parent)
        self.url = url
        self.caption = caption
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setStyleSheet("""
            background-color: #222;
            color: #FFF;
            font: 14px Arial;
            border: 1px solid #444;
        """)
        
        # Создаем подпись
        self.cap_label = QLabel(caption, self)
        self.cap_label.setAlignment(Qt.AlignCenter)
        self.cap_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 150);
            color: white;
            padding: 4px;
        """)
        self.cap_label.setGeometry(0, self.height() - 30, self.width(), 30)
        
    def resizeEvent(self, event):
        # Обновляем положение подписи при изменении размера
        self.cap_label.setGeometry(0, self.height() - 30, self.width(), 30)
        super().resizeEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IP Camera Viewer")
        self.setGeometry(100, 100, 1200, 400)
        
        # Центральный виджет и основной слой
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # URL камер
        self.camera_urls = [
            "rtsp://admin:kZx_vN8!@172.16.9.54/stream2",
            "rtsp://admin:kZx_vN8!@172.16.9.53/stream2",
            "rtsp://admin:kZx_vN8!@172.16.9.52/stream2"
        ]
        
        # Создаем виджеты камер
        self.camera_widgets = []
        for i, url in enumerate(self.camera_urls):
            widget = CameraWidget(url, f"Camera {i+1}")
            main_layout.addWidget(widget)
            self.camera_widgets.append(widget)
        
        # Инициализация видеозахватов
        self.captures = [cv2.VideoCapture(url) for url in self.camera_urls]
        
        # Проверка подключения к камерам
        for i, cap in enumerate(self.captures):
            if not cap.isOpened():
                print(f"Ошибка подключения к камере {i+1}")
        
        # Таймер для обновления кадров
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(10)  # FPS

    def update_frames(self):
        for i, (camera_widget, cap) in enumerate(zip(self.camera_widgets, self.captures)):
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # Конвертация в RGB (OpenCV использует BGR)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Получаем текущий размер виджета
                    widget_width = camera_widget.width()
                    widget_height = camera_widget.height()
                    
                    # Вычисляем целевой размер с соотношением 16:9, который вписывается в виджет
                    target_aspect_ratio = 16 / 9
                    
                    # Рассчитываем размеры для отображения с сохранением соотношения
                    if widget_width / widget_height > target_aspect_ratio:
                        # Широкий виджет: ограничиваем по высоте
                        display_height = widget_height
                        display_width = int(display_height * target_aspect_ratio)
                    else:
                        # Высокий виджет: ограничиваем по ширине
                        display_width = widget_width
                        display_height = int(display_width / target_aspect_ratio)
                    
                    # Масштабируем кадр до display_width x display_height
                    resized_frame = cv2.resize(frame, (display_width, display_height))
                    
                    # Создаем черное изображение размером с виджет
                    black_background = np.zeros((widget_height, widget_width, 3), dtype=np.uint8)
                    
                    # Вычисляем координаты для вставки масштабированного изображения по центру
                    x_offset = (widget_width - display_width) // 2
                    y_offset = (widget_height - display_height) // 2
                    
                    # Помещаем масштабированный кадр на черный фон
                    black_background[y_offset:y_offset+display_height, x_offset:x_offset+display_width] = resized_frame
                    
                    # Конвертируем в QImage
                    h, w, c = black_background.shape
                    qimage = QImage(black_background.data, w, h, w * c, QImage.Format_RGB888)
                    
                    # Отображаем
                    camera_widget.setPixmap(QPixmap.fromImage(qimage))
        # Запланировать следующий вызов
        QTimer.singleShot(30, self.update_frames)


    def show_error(self, widget, message):
        # Отображаем сообщение об ошибке
        widget.setText(message)
        widget.setStyleSheet("""
            background-color: #300;
            color: #FFF;
            font: bold 16px Arial;
            border: 2px solid #F00;
        """)

    def closeEvent(self, event):
        # Освобождение ресурсов при закрытии
        for capture in self.captures:
            if capture.isOpened():
                capture.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Стиль для всего приложения
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
