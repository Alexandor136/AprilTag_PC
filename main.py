# main.py
import cv2
import os
from pupil_apriltags import Detector
import threading
import queue
import reboot_ethernet_interface
from read_roi import load_roi_for_ip, extract_ip_from_url
from camera_utils import camera_worker, display_frames

def init_camera_threads(camera_urls, frame_rate, output_queue, stop_event, roi_file):
    """
    Инициализирует потоки обработки камер.

    Args:
        camera_urls (list): Список URL камер.
        frame_rate (float): Частота кадров.
        output_queue (Queue): Очередь для передачи кадров.
        stop_event (Event): Событие остановки.
        roi_file (str): Путь к файлу ROI.

    Returns:
        list: Список запущенных потоков.
    """
    threads = []
    detectors = [Detector(families='tag36h11', nthreads=1) for _ in camera_urls]

    for i, (url, detector) in enumerate(zip(camera_urls, detectors)):
        ip = extract_ip_from_url(url)
        roi = load_roi_for_ip(ip, roi_file)
        thread = threading.Thread(
            target=camera_worker,
            args=(url, detector, frame_rate, output_queue, stop_event, i, roi),
            daemon=True
        )
        thread.start()
        threads.append(thread)

    return threads

def main(camera_urls, frame_rate, display=True):
    """
    Основная функция: запускает потоки обработки камер и отображает результат.

    Args:
        camera_urls (list): Список URL камер.
        frame_rate (float): Частота кадров.
        display (bool): Флаг отображения окон.
    """
    output_queue = queue.Queue()
    stop_event = threading.Event()
    roi_file = "roi.xml"

    threads = init_camera_threads(
        camera_urls, frame_rate, output_queue, stop_event, roi_file
    )

    if display:
        display_frames(len(camera_urls), output_queue, stop_event)

    stop_event.set()
    for t in threads:
        t.join()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    #reboot_ethernet_interface.reboot_interface('enp2s0')
    CAMERA_URLS = [
        "rtsp://admin:kZx_vN8!@10.16.9.52/stream1",
        "rtsp://admin:kZx_vN8!@10.16.9.53/stream1",
        "rtsp://admin:kZx_vN8!@10.16.9.54/stream1"
    ]
    FRAME_RATE = 10
    main(CAMERA_URLS, FRAME_RATE)
