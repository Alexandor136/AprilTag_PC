import os


import time
import sys
from pathlib import Path



from camera_utils.camera_processing import CameraProcessor
from camera_utils.display_manager import DisplayManager


def main():
    camera_urls = [
        "rtsp://admin:kZx_vN8!@10.16.9.52/stream1",
        "rtsp://admin:kZx_vN8!@10.16.9.53/stream1",
        "rtsp://admin:kZx_vN8!@10.16.9.54/stream1"
    ]
    
    processor = CameraProcessor(camera_urls)
    display = DisplayManager(len(camera_urls))
    
    processor.start_processing()
    display.start_display(processor.output_queue)
    
    try:
        while processor.is_running():
            if display.update_display():
                break
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        processor.stop_processing()
        display.stop_display()

if __name__ == "__main__":
    main()
