import cv2
import threading
import time
import queue

class DisplayManager:
    def __init__(self, camera_count):
        self.camera_count = camera_count
        self.stop_event = threading.Event()
        self.frames = [None] * camera_count
        self.windows_initialized = False

    def _init_windows(self):
        if not self.windows_initialized:
            for i in range(self.camera_count):
                cv2.namedWindow(f'Camera {i+1}', cv2.WINDOW_NORMAL)
                cv2.resizeWindow(f'Camera {i+1}', 800, 600)
            self.windows_initialized = True

    def start_display(self, output_queue):
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._display_worker,
            args=(output_queue,),
            daemon=True
        )
        self.thread.start()

    def _display_worker(self, output_queue):
        try:
            while not self.stop_event.is_set():
                # Обновляем кадры
                try:
                    while True:
                        idx, frame = output_queue.get_nowait()
                        self.frames[idx] = frame
                except queue.Empty:
                    pass
                
                # Инициализация окон в основном потоке (вызывается извне)
                # Отображение кадров должно быть в основном потоке
                # Поэтому мы просто собираем кадры здесь, а отображение будет в update_display
                
                time.sleep(0.01)
        except Exception as e:
            print(f"Display error: {e}")
            self.stop_event.set()

    def update_display(self):
        """Этот метод должен вызываться из основного потока"""
        self._init_windows()
        for i, frame in enumerate(self.frames):
            if frame is not None:
                cv2.imshow(f'Camera {i+1}', frame)
        return cv2.waitKey(1) & 0xFF == ord('q')

    def stop_display(self):
        self.stop_event.set()
        if hasattr(self, 'thread'):
            self.thread.join()
        if self.windows_initialized:
            cv2.destroyAllWindows()