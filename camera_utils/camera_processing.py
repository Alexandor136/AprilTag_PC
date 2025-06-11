import queue
import threading
import time
import cv2
from pupil_apriltags import Detector
from .tag_processing import process_frame
from .frame_utils import prepare_text_frame
from roi.read_roi import load_roi_for_ip, extract_ip_from_url

class CameraProcessor:
    def __init__(self, camera_urls, frame_rate=10, roi_file='roi/roi.xml'):
        self.camera_urls = camera_urls
        self.frame_rate = frame_rate
        self.roi_file = roi_file
        self.output_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.threads = []
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
        for i, url in enumerate(self.camera_urls):
            thread = threading.Thread(
                target=self._camera_worker,
                args=(url, i),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
    
    def _camera_worker(self, url, cam_index):
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            print(f"Не удалось подключиться к камере {cam_index + 1}")
            return

        ip_address = extract_ip_from_url(url)
        roi = load_roi_for_ip(ip_address, self.roi_file) or {
            'x': 0, 'y': 0, 
            'w': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'h': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        }

        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                continue
                
            try:
                processed = self._process_frame(frame, roi)
                self.output_queue.put((cam_index, processed))
            except Exception as e:
                print(f"Ошибка обработки кадра: {e}")

        cap.release()
    
    def _process_frame(self, frame, roi):
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
            
        return display_frame
    
    def stop_processing(self):
        self.stop_event.set()
        for t in self.threads:
            t.join()
    
    def is_running(self):
        return not self.stop_event.is_set()