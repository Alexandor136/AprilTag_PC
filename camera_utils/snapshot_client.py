import cv2
import time
import threading
import numpy as np
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import base64
from logger_setup import logger

class SnapshotClient:
    """Клиент для получения снимков с камеры с синхронизацией."""
    
    def __init__(self, config):
        self.config = config
        self.url = config.snapshot_url
        self.username = config.username
        self.password = config.password
        self.interval = config.interval
        self.timeout = config.timeout
        
        self.last_frame = None
        self.last_frame_time = 0
        self.frame_count = 0
        self.error_count = 0
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.new_frame_event = threading.Event()  # Событие для новых кадров
        
        # Статистика
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0
        }
        
    def start(self):
        """Запуск получения снимков."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self.thread.start()
        logger.info(f"Snapshot клиент запущен для {self.config.name} (интервал: {self.interval}с)")
        
    def stop(self):
        """Остановка получения снимков."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
        logger.info(f"Snapshot клиент остановлен для {self.config.name}")
        
    def _fetch_loop(self):
        """Основной цикл получения снимков."""
        next_time = time.time()
        
        while self.running:
            try:
                start_time = time.time()
                self.stats['total_requests'] += 1
                
                # Получаем снимок
                frame = self._fetch_snapshot()
                
                if frame is not None:
                    with self.lock:
                        self.last_frame = frame
                        self.last_frame_time = time.time()
                        self.frame_count += 1
                    self.stats['successful_requests'] += 1
                    self.error_count = 0
                    self.new_frame_event.set()  # Сигнализируем о новом кадре
                else:
                    self.error_count += 1
                    self.stats['failed_requests'] += 1
                    if self.error_count % 10 == 0:
                        logger.warning(f"{self.config.name}: {self.error_count} ошибок подряд")
                
                # Обновляем статистику
                response_time = time.time() - start_time
                self.stats['avg_response_time'] = (
                    self.stats['avg_response_time'] * 0.9 + response_time * 0.1
                )
                
                # Точное соблюдение интервала
                next_time += self.interval
                sleep_time = next_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    next_time = time.time()
                    logger.debug(f"{self.config.name}: отставание {abs(sleep_time):.3f}с")
                    
            except Exception as e:
                logger.error(f"Критическая ошибка в Snapshot клиенте {self.config.name}: {e}")
                time.sleep(1)
    
    def _fetch_snapshot(self):
        """Получение одного снимка с камеры."""
        try:
            # Создаем запрос с базовой аутентификацией
            request = Request(self.url)
            
            # Добавляем Basic Auth заголовок
            if self.username and self.password:
                credentials = base64.b64encode(
                    f"{self.username}:{self.password}".encode()
                ).decode()
                request.add_header("Authorization", f"Basic {credentials}")
            
            # Добавляем User-Agent
            request.add_header("User-Agent", "AprilTag-Detector/2.0")
            
            # Выполняем запрос
            response = urlopen(request, timeout=self.timeout)
            
            if response.status == 200:
                # Читаем данные
                img_data = response.read()
                
                # Конвертируем в numpy array
                img_array = np.frombuffer(img_data, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    return frame
                else:
                    logger.debug(f"{self.config.name}: ошибка декодирования изображения")
            else:
                logger.debug(f"{self.config.name}: HTTP {response.status}")
                
        except HTTPError as e:
            if e.code == 401:
                logger.debug(f"{self.config.name}: ошибка аутентификации")
            else:
                logger.debug(f"{self.config.name}: HTTP ошибка {e.code}")
        except URLError as e:
            logger.debug(f"{self.config.name}: ошибка URL {e.reason}")
        except Exception as e:
            logger.debug(f"{self.config.name}: ошибка запроса: {e}")
            
        return None
    
    def get_frame(self):
        """Получение последнего кадра."""
        with self.lock:
            if self.last_frame is not None:
                return self.last_frame.copy()
        return None
    
    def wait_for_new_frame(self, timeout=None):
        """Ожидание нового кадра."""
        return self.new_frame_event.wait(timeout)
    
    def clear_new_frame_event(self):
        """Сброс события нового кадра."""
        self.new_frame_event.clear()
    
    def is_connected(self):
        """Проверка подключения."""
        with self.lock:
            return self.last_frame is not None and (time.time() - self.last_frame_time) < 5.0
    
    def get_stats(self):
        """Получение статистики."""
        return self.stats.copy()