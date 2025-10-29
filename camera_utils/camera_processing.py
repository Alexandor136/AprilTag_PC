import time
import threading
import queue
import cv2
from pupil_apriltags import Detector
from dataclasses import dataclass

from .tag_processing import process_frame
from .frame_utils import prepare_text_frame
from .snapshot_client import SnapshotClient  # Новый импорт
from network.modbus_handler import ModbusHandler
from roi.read_roi import load_roi_for_ip
from logger_setup import logger

@dataclass
class DetectedTag:
    tag_id: int
    camera_index: int

class CameraProcessor:
    def __init__(self, camera_configs=None, roi_file='roi/roi.xml'):
        self.camera_configs = camera_configs or []
        self.roi_file = roi_file
        self.modbus_handler = ModbusHandler()
        self.output_queue = queue.Queue(maxsize=2)  # Еще меньше буфер
        self.stop_event = threading.Event()
        self.threads = []
        self.detector_lock = threading.Lock()
        self.last_sent_tags = {}
        
        # Клиенты для снимков
        self.snapshot_clients = {}

        # Инициализация детектора
        self.detector = Detector(
            families='tag36h11',
            nthreads=2,  # Меньше потоков для стабильности
            quad_decimate=1.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0
        )

    def start_processing(self):
        """Запуск потоков обработки камер и Modbus."""
        if not self.camera_configs:
            raise ValueError("Не заданы конфигурации камер!")

        logger.info(f"Запуск обработки {len(self.camera_configs)} камер через снимки (4 FPS)")

        # Инициализация клиентов снимков
        for config in self.camera_configs:
            client = SnapshotClient(config)
            self.snapshot_clients[config.index] = client
            client.start()

        # Запуск Modbus потока
        modbus_thread = threading.Thread(
            target=self._modbus_sender_worker,
            daemon=True
        )
        modbus_thread.start()
        self.threads.append(modbus_thread)

        # Запуск потока обработки для каждой камеры
        for config in self.camera_configs:
            thread = threading.Thread(
                target=self._processing_worker,
                args=(config,),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)

    def _modbus_sender_worker(self):
        """Поток для периодической отправки тегов в Modbus."""
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

                time.sleep(1)  # Отправка каждую секунду
                
            except Exception as e:
                logger.warning(f"Ошибка в потоке отправки Modbus: {e}")
                time.sleep(5)

    def _processing_worker(self, config):
        """Поток обработки снимков с камеры с синхронизацией."""
        client = self.snapshot_clients[config.index]
        last_processed_frame_id = 0
        
        while not self.stop_event.is_set():
            try:
                # Ждем новый кадр (синхронизация с получением)
                if client.wait_for_new_frame(timeout=1.0):
                    client.clear_new_frame_event()
                    
                    # Получаем свежий кадр
                    frame = client.get_frame()
                    
                    if frame is None:
                        continue

                    # Загружаем ROI
                    roi = load_roi_for_ip(config.camera_ip, self.roi_file) or {
                        'x': 0, 'y': 0,
                        'w': frame.shape[1],
                        'h': frame.shape[0]
                    }

                    # Обрабатываем кадр
                    processed_frame, detected_tags = self._process_frame(
                        frame, roi, config.min_tag_area, config.max_tag_area, config.name
                    )

                    # Отправляем в очередь отображения
                    try:
                        self.output_queue.put_nowait((config.index, processed_frame))
                    except queue.Full:
                        pass  # Пропускаем кадр если очередь полна

                    # Сохраняем обнаруженные теги
                    with threading.Lock():
                        if detected_tags:
                            self.last_sent_tags[config.index] = list(detected_tags.keys())
                        else:
                            self.last_sent_tags[config.index] = []
                            
                else:
                    # Таймаут ожидания нового кадра
                    time.sleep(0.01)

            except Exception as e:
                logger.warning(f"Ошибка обработки кадра {config.name}: {e}")
                time.sleep(0.1)

    def _process_frame(self, frame, roi, min_tag_area, max_tag_area, camera_name):
        """Обработка кадра: ROI, детекция AprilTag и отрисовка."""
        display_frame = frame.copy()
        x, y, w, h = roi['x'], roi['y'], roi['w'], roi['h']

        # Проверка границ
        h_img, w_img = frame.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)

        if w <= 0 or h <= 0:
            return display_frame, {}

        roi_frame = frame[y:y + h, x:x + w]

        # Детекция тегов
        with self.detector_lock:
            processed_roi, tags = process_frame(
                roi_frame, self.detector, min_tag_area, max_tag_area, camera_name
            )

        display_frame[y:y + h, x:x + w] = processed_roi
        cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Добавление информации о тегах
        if tags:
            text_lines = [f"ID: {tag_id}" for tag_id in tags.keys()]
            display_frame = prepare_text_frame(display_frame, text_lines)

        return display_frame, tags

    def stop_processing(self):
        """Остановка всех потоков."""
        self.stop_event.set()
        
        # Останавливаем клиенты снимков
        for client in self.snapshot_clients.values():
            client.stop()
        
        # Ожидаем завершения потоков
        for t in self.threads:
            if t.is_alive():
                t.join(timeout=1.0)
                
        self.modbus_handler.stop()
        logger.info("Все потоки обработки остановлены")

    def is_running(self):
        return not self.stop_event.is_set()
    
    def get_client_stats(self, camera_index):
        """Получение статистики клиента."""
        client = self.snapshot_clients.get(camera_index)
        return client.get_stats() if client else None