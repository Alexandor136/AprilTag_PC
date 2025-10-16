# display_manager.py (исправленная версия)
import cv2
import threading
import queue

class DisplayManager:
    def __init__(self, camera_count):
        self.camera_count = camera_count
        self.stop_event = threading.Event()
        self.frames = [None] * camera_count
        self.locks = [threading.Lock() for _ in range(camera_count)]
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
                try:
                    idx, frame = output_queue.get(timeout=0.1)
                    with self.locks[idx]:
                        self.frames[idx] = frame.copy()
                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"Display worker error: {e}")
        except Exception as e:
            print(f"Display worker fatal error: {e}")
            self.stop_event.set()

    def update_display(self):
        """Этот метод должен вызываться из основного потока"""
        self._init_windows()
        quit_pressed = False
        
        for i in range(self.camera_count):
            with self.locks[i]:
                frame = self.frames[i]
            
            if frame is not None:
                cv2.imshow(f'Camera {i+1}', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            quit_pressed = True
        elif key == 27:  # ESC
            quit_pressed = True
            
        return quit_pressed

    def stop_display(self):
        self.stop_event.set()
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        if self.windows_initialized:
            cv2.destroyAllWindows()