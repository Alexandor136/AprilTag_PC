# AprilTag Detection Project

## Описание
Система для обнаружения AprilTags с нескольких IP-камер с поддержкой Modbus TCP и настройкой областей интереса (ROI)

## 🌟 Особенности

- Реальное обнаружение AprilTags с нескольких RTSP-камер
- Настройка индивидуальных ROI для каждой камеры
- Интеграция с Modbus TCP для передачи данных
- Два режима работы: GUI и консольный
- Автоматическое логирование с ротацией файлов
- Гибкая конфигурация через YAML

## Структура проекта

april_tag/
├── camera_utils/          # Модули обработки видео
│   ├── camera_operations.py
│   ├── camera_processing.py
│   └── display_manager.py
├── network/               # Сетевые функции
│   ├── modbus_client.py
│   └── modbus_handler.py
├── roi/                   # Настройка ROI
│   ├── read_roi.py
│   ├── setting_roi.py
│   └── roi.xml
├── config.yaml            # Основные настройки
├── docker-compose.yml     # Docker конфигурация
├── main.py                # GUI приложение
└── cli.py                 # Консольная версия

## Использование

1. Для добавления новой камеры:
   - Добавьте RTSP URL в список `CAMERA_URLS` в `main.py`.
   - Определите ROI для камеры с помощью `setting_roi.py` и сохраните в `roi.xml`.

2. Запустите `main.py` для старта детекции и отображения.

3. Для перезапуска сетевого интерфейса (если камеры недоступны после перезагрузки) используется `reboot_ethernet_interface.py`.

## 📝 Логирование

Пример лога:
[2024-02-20 14:30:45] INFO Камера 1: Обнаружен тег ID=42
[2024-02-20 14:30:46] DEBUG Modbus: запись 42 в регистр 1001

## Установка зависимостей
pip install -r requirements.txt

🐳 Docker
bash
#Сборка образа
docker-compose build

#Запуск
docker-compose up -d

#Остановка
docker-compose down
