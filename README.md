# AprilTag Detection Project

## Описание
Этот проект предназначен для обнаружения AprilTags с использованием видеопотока из нескольких IP-камер. 
Он включает в себя функции для обработки видео и перезапуска Ethernet-интерфейса.

Добавление камер происходит путём изменения словаря `CAMERA_URLS`. 
Программа написана так, чтобы можно было легко добавлять новые камеры и изменять их количество.
Для этого нужно добавить RTSP-ссылку на камеру.

Функция перезапуска сетевого интерфейса необходима в случаях, когда после аварийного выключения ПК 
не происходит автоматического подключения к камерам.

## Структура проекта

- `camera_utils.py` — функции для работы с видеопотоком камер:
  - Детекция AprilTag на кадрах.
  - Обрезка по ROI.
  - Отрисовка тегов и текста.
  - Поток обработки камеры (`camera_worker`).
  - Отображение кадров с нескольких камер.

- `main.py` — точка входа:
  - Инициализация детекторов и потоков камер.
  - Загрузка ROI из файла.
  - Запуск отображения видео.
  - Перезапуск сетевого интерфейса перед стартом.

- `read_roi.py` — загрузка ROI из XML-файла по IP камеры.

- `setting_roi.py` — утилита для выбора и сохранения ROI с помощью мыши на RTSP-потоке.

- `reboot_ethernet_interface.py` — скрипт для перезапуска сетевого интерфейса Linux.

- `roi.xml` — файл с сохранёнными областями интереса (ROI) для каждой камеры.

- `log.py` — функции логирования.

- `modbus.py` — клиент для отпраки сообщений по modbus TCP registr.

## Использование

1. Для добавления новой камеры:
   - Добавьте RTSP URL в список `CAMERA_URLS` в `main.py`.
   - Определите ROI для камеры с помощью `setting_roi.py` и сохраните в `roi.xml`.

2. Запустите `main.py` для старта детекции и отображения.

3. Для перезапуска сетевого интерфейса (если камеры недоступны после перезагрузки) используется `reboot_ethernet_interface.py`.

## Зависимости

- Python 3
- OpenCV (`opencv-python`)
- AprilTag детектор (`pupil-apriltags`)

Установка:

```bash
pip install opencv-python pupil-apriltags

