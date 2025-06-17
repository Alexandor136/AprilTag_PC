import time
import queue
import threading
import cv2
import asyncio
from pupil_apriltags import Detector
from dataclasses import dataclass
from .tag_processing import process_frame
from .frame_utils import prepare_text_frame
from network.modbus_handler import ModbusHandler
from roi.read_roi import load_roi_for_ip


@dataclass
class DetectedTag:
    tag_id: int
    camera_index: int


class CameraProcessor:
    def __init__(self, camera_configs=None, roi_file='roi/roi.xml'):
        self.camera_configs = camera_configs or []
        self.roi_file = roi_file
        self.modbus_handler = ModbusHandler()
        self.output_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.threads = []
        self.detector = Detector(
            families='tag36h11',
            nthreads=3,
            quad_decimate=1.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0
        )
        self.last_sent_tags = {}  # Для хранения последних отправленных тегов по камерам
    
    def start_processing(self):
        if not self.camera_configs:
            raise ValueError("Не заданы конфигурации камер!")
        
        # Запускаем поток для периодической отправки тегов в Modbus
        modbus_thread = threading.Thread(
            target=self._modbus_sender_worker,
            daemon=True
        )
        modbus_thread.start()
        self.threads.append(modbus_thread)
        
        for config in self.camera_configs:
            thread = threading.Thread(
                target=self._camera_worker,
                args=(config,),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
    
    def _modbus_sender_worker(self):
        """Поток для периодической отправки тегов в Modbus"""
        while not self.stop_event.is_set():
            try:
                # Собираем все обнаруженные теги
                all_tags = []
                for config in self.camera_configs:
                    if config.index in self.last_sent_tags:
                        for tag_id in self.last_sent_tags[config.index]:
                            all_tags.append(DetectedTag(tag_id=tag_id, camera_index=config.index))
                
                # Группируем теги по камерам и отправляем
                for config in self.camera_configs:
                    if config.modbus:  # Проверяем только наличие modbus конфигурации
                        tags_for_camera = [
                            tag for tag in all_tags 
                            if tag.camera_index == config.index
                        ]
                        
                        # Всегда отправляем данные, даже если тегов нет (отправляем 0)
                        asyncio.run(
                            self.modbus_handler.send_tags(
                                tags_for_camera if tags_for_camera else [],
                                config.modbus
                            )
                        )

                time.sleep(1)
            except Exception as e:
                print(f"Ошибка в потоке отправки Modbus: {str(e)}")
    
    def _camera_worker(self, config):
        """Поток обработки для одной камеры"""
        cap = cv2.VideoCapture(config.rtsp)
        if not cap.isOpened():
            print(f"Не удалось подключиться к {config.name} ({config.camera_ip})")
            return

        roi = load_roi_for_ip(config.camera_ip, self.roi_file) or {
            'x': 0, 'y': 0, 
            'w': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'h': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        }

        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                continue
                
            try:
                processed_frame, detected_tags = self._process_frame(frame, roi, config)
                self.output_queue.put((config.index, processed_frame))
                
                # Сохраняем обнаруженные теги для этой камеры
                if detected_tags:
                    self.last_sent_tags[config.index] = list(detected_tags.keys())
                else:
                    self.last_sent_tags[config.index] = []
                    
            except Exception as e:
                print(f"Ошибка в камере {config.name}: {str(e)}")

        cap.release()
    
    def _process_frame(self, frame, roi, config=None):
        display_frame = frame.copy()
        x, y, w, h = roi['x'], roi['y'], roi['w'], roi['h']
        
        # Проверка границ
        h_img, w_img = frame.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)
        
        roi_frame = frame[y:y+h, x:x+w]
        processed_roi, tags = process_frame(roi_frame, self.detector)
        
        display_frame[y:y+h, x:x+w] = processed_roi
        cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
        
        if tags:
            text_lines = [f"ID: {tag_id}" for tag_id in tags.keys()]
            display_frame = prepare_text_frame(display_frame, text_lines)
            
        return display_frame, tags
    
    def stop_processing(self):
        """Корректная остановка всех потоков"""
        self.stop_event.set()
        for t in self.threads:
            t.join()
        self.modbus_handler.stop()
    
    def is_running(self):
        """Проверка статуса работы"""
        return not self.stop_event.is_set()