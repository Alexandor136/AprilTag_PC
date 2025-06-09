import cv2
import os

def ip_to_key(ip):
    return "ip_" + ip.replace(".", "_").replace(":", "_")

def save_roi_for_ip(ip, roi, filename):
    data = {}
    if os.path.exists(filename):
        fs_read = cv2.FileStorage(filename, cv2.FILE_STORAGE_READ)
        if fs_read.isOpened():
            root = fs_read.root()
            for key in root.keys():
                node = fs_read.getNode(key)
                if not node.empty() and node.isMap():
                    x_node = node.getNode('x')
                    y_node = node.getNode('y')
                    w_node = node.getNode('w')
                    h_node = node.getNode('h')
                    if not x_node.empty() and not y_node.empty() and not w_node.empty() and not h_node.empty():
                        data[key] = {
                            'x': int(x_node.real()),
                            'y': int(y_node.real()),
                            'w': int(w_node.real()),
                            'h': int(h_node.real())
                        }
            fs_read.release()

    data[ip_to_key(ip)] = roi

    fs_write = cv2.FileStorage(filename, cv2.FILE_STORAGE_WRITE)
    for cam_key, r in data.items():
        fs_write.startWriteStruct(cam_key, cv2.FILE_NODE_MAP)
        fs_write.write("x", r['x'])
        fs_write.write("y", r['y'])
        fs_write.write("w", r['w'])
        fs_write.write("h", r['h'])
        fs_write.endWriteStruct()
    fs_write.release()
    print(f"ROI для камеры {ip} сохранён в {filename}")

def select_roi_from_rtsp(ip):
    rtsp_url = f"rtsp://admin:kZx_vN8!@{ip}/stream1"
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print("Ошибка подключения к RTSP потоку")
        return None

    roi = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
    drawing = False
    ix, iy = -1, -1
    rect_frame = None

    def draw_rectangle(event, x, y, flags, param):
        nonlocal drawing, ix, iy, roi, rect_frame
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            rect_frame = frame.copy()
            cv2.rectangle(rect_frame, (ix, iy), (x, y), (0, 255, 0), 2)
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            x0, y0 = min(ix, x), min(iy, y)
            x1, y1 = max(ix, x), max(iy, y)
            roi['x'], roi['y'] = x0, y0
            roi['w'], roi['h'] = x1 - x0, y1 - y0
            rect_frame = frame.copy()
            cv2.rectangle(rect_frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
            print(f"ROI: x={roi['x']}, y={roi['y']}, w={roi['w']}, h={roi['h']}")

    cv2.namedWindow('RTSP Stream')
    cv2.setMouseCallback('RTSP Stream', draw_rectangle)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Не удалось получить кадр")
            break

        if rect_frame is not None:
            display = rect_frame
        else:
            display = frame

        cv2.imshow('RTSP Stream', display)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            break
        elif key == ord('c'):
            cap.release()
            cv2.destroyAllWindows()
            return roi

    cap.release()
    cv2.destroyAllWindows()
    return roi

if __name__ == "__main__":
    ip = "172.16.9.52"
    filename = "roi.xml"
    roi = select_roi_from_rtsp(ip)
    if roi and roi['w'] > 0 and roi['h'] > 0:
        save_roi_for_ip(ip, roi, filename)



