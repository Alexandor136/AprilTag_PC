FROM python:3.12.3-slim-bookworm

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости отдельно для кэширования
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Переменные окружения
ENV QT_QPA_PLATFORM=offscreen \
    PYTHONUNBUFFERED=1 \
    OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp"
# Запус программы
CMD ["python", "main.py", "--console"]