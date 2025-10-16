import os
import cv2

def ip_to_key(ip):
    return "ip_" + ip.replace(".", "_").replace(":", "_")

def load_roi_for_ip(ip, filename):
    key = ip_to_key(ip)
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден")
        return None
    fs = cv2.FileStorage(filename, cv2.FILE_STORAGE_READ)
    if not fs.isOpened():
        print(f"Не удалось открыть {filename}")
        return None
    node = fs.getNode(key)
    if node.empty() or not node.isMap():
        print(f"ROI для камеры {ip} не найден или неверный формат")
        fs.release()
        return None
    roi = {
        'x': int(node.getNode('x').real()),
        'y': int(node.getNode('y').real()),
        'w': int(node.getNode('w').real()),
        'h': int(node.getNode('h').real())
    }
    fs.release()
    return roi

def extract_ip_from_url(url):
    return url.split("@")[-1].split("/")[0]

#print(load_roi_for_ip('10.16.9.52', 'roi/roi.xml'))