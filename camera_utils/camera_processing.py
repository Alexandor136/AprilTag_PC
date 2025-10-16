# camera_processing.py
import time
import queue
import threading
import cv2
from pupil_apriltags import Detector
from dataclasses import dataclass
from .tag_processing import process_frame
from .frame_utils import prepare_text_frame
from network.modbus_handler import ModbusHandler
from roi.read_roi import load_roi_for_ip
from logger_setup import logger


@dataclass
class DetectedTag:
    tag_id: int
    camera_index: int


class CameraProcessor:
    def __init__(self, camera_configs=None, roi_file='roi/roi.xml'):
        """
        Инициализация процессора камер.

        Args:
            camera_configs (list): Список конфигураций камер.
            roi_file (str): Путь к файлу с ROI.
        """
        self.camera_configs = camera_configs or []
        self.roi_file = roi_file
        self.modbus_handler = ModbusHandler()
        self.output_queue = queue.Queue(maxsize=3)  # Ограничиваем размер очереди для пропуска кадров
        self.stop_event = threading.Event()
        self.threads = []
        self.detector_lock = threading.Lock()  # Блокировка для детектора
        self.last_sent_tags = {}

        # Инициализация детектора один раз
        self.detector = Detector(
            families='tag36h11',
            nthreads=4,
            quad_decimate=1.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0
        )

    def start_processing(self):
        """
        Запуск потоков обработки камер и Modbus.
        """
        if not self.camera_configs:
            raise ValueError("Не заданы конфигурации камер!")

        # Запуск Modbus потока
        modbus_thread = threading.Thread(
            target=self._modbus_sender_worker,
            daemon=True
        )
        modbus_thread.start()
        self.threads.append(modbus_thread)

        # Запуск потока для каждой камеры
        for config in self.camera_configs:
            thread = threading.Thread(
                target=self._camera_worker,
                args=(config,),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)

    def _modbus_sender_worker(self):
        """
        Поток для периодической отправки тегов в Modbus.
        """
        while not self.stop_event.is_set():
            try:
                all_tags = []
                for config in self.camera_configs:
                    tags = self.last_sent_tags.get(config.index, [])
                    for tag_id in tags:
                        all_tags.append(DetectedTag(tag_id=tag_id, camera_index=config.index))

                for config in self.camera_configs:
                    if config.modbus:
                        tags_for_camera = [
                            tag for tag in all_tags if tag.camera_index == config.index
                        ]
                        self.modbus_handler.send_tags(
                            tags_for_camera if tags_for_camera else [],
                            config.modbus
                        )

                time.sleep(1)
            except Exception as e:
                logger.warning(f"Ошибка в потоке отправки Modbus: {e}")

    def _camera_worker(self, config):
        """
        Поток захвата и обработки кадров с камеры.

        Добавлена обработка переподключения и пропуск кадров при перегрузке.

        Args:
            config: Конфигурация камеры.
        """
        cap = None

        def open_capture():
            """Открыть VideoCapture с оптимальными параметрами."""
            cap_local = cv2.VideoCapture(config.rtsp, cv2.CAP_FFMPEG)
            if not cap_local.isOpened():
                return None

            # Оптимизация параметров VideoCapture
            cap_local.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Минимальный буфер кадров
            cap_local.set(cv2.CAP_PROP_FPS, 15)        # Ограничение FPS, если возможно
            cap_local.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap_local.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            return cap_local

        while not self.stop_event.is_set():
            if cap is None:
                cap = open_capture()
                if cap is None:
                    logger.warning(f"Не удалось подключиться к {config.name} ({config.camera_ip}), повтор через 5 сек...")
                    time.sleep(5)
                    continue
                else:
                    logger.info(f"Подключение к {config.name} ({config.camera_ip}) успешно")

            roi = load_roi_for_ip(config.camera_ip, self.roi_file) or {
                'x': 0, 'y': 0,
                'w': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'h': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            }

            ret, frame = cap.read()
            if not ret or frame is None:
                logger.warning(f"Потеря кадра с {config.name} ({config.camera_ip}), переподключение...")
                cap.release()
                cap = None
                time.sleep(2)
                continue

            try:
                # Обработка кадра с параметрами площади тега
                processed_frame, detected_tags = self._process_frame(
                    frame, roi, config.min_tag_area, config.max_tag_area, config.name
                )

                # Пробуем положить в очередь без блокировки, пропуская кадры при переполнении
                try:
                    self.output_queue.put_nowait((config.index, processed_frame))
                except queue.Full:
                    # Очередь переполнена - пропускаем кадр
                    pass

                # Сохраняем обнаруженные теги с блокировкой
                with threading.Lock():
                    if detected_tags:
                        self.last_sent_tags[config.index] = list(detected_tags.keys())
                    else:
                        self.last_sent_tags[config.index] = []

            except Exception as e:
                logger.warning(f"Ошибка обработки кадра камеры {config.name}: {e}")

        if cap:
            cap.release()

    def _process_frame(self, frame, roi, min_tag_area=100.0, max_tag_area=10000.0, camera_name="Unknown"):
        """
        Обработка кадра: выделение ROI, детекция AprilTag и отрисовка.

        Args:
            frame (np.ndarray): Исходный кадр.
            roi (dict): Область интереса.
            min_tag_area (float): Минимальная площадь тега.
            max_tag_area (float): Максимальная площадь тега.
            camera_name (str): Название камеры для логирования.

        Returns:
            tuple: (обработанный кадр, словарь обнаруженных тегов)
        """
        display_frame = frame.copy()
        x, y, w, h = roi['x'], roi['y'], roi['w'], roi['h']

        h_img, w_img = frame.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)

        roi_frame = frame[y:y + h, x:x + w]

        with self.detector_lock:
            processed_roi, tags = process_frame(
                roi_frame, self.detector, min_tag_area, max_tag_area, camera_name
            )

        display_frame[y:y + h, x:x + w] = processed_roi
        cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

        if tags:
            text_lines = [f"ID: {tag_id}" for tag_id in tags.keys()]
            display_frame = prepare_text_frame(display_frame, text_lines)

        return display_frame, tags

    def stop_processing(self):
        """
        Остановка потоков.
        """
        self.stop_event.set()
        for t in self.threads:
            if t.is_alive():
                t.join(timeout=1.0)
        self.modbus_handler.stop()

    def is_running(self):
        """
        Проверка состояния работы.

        Returns:
            bool: True если не остановлен.
        """
        return not self.stop_event.is_set()