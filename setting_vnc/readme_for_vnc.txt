# Настройка VNC-сервера

Этот скрипт автоматически устанавливает и настраивает два типа VNC-серверов:
1. **TigerVNC** – создает новые сессии (порт `5901`, `5902`, ...).
2. **x11vnc** – подключается к текущей графической сессии (порт `5900`).

## Как использовать
1. Дайте права на выполнение:
   ```bash
   chmod +x vnc.sh
   ./vnc.sh

ответы  111111 n 111111 y


Команда	Описание
sudo apt install tigervnc-standalone-server	Установка TigerVNC
vncpasswd	Настройка пароля для TigerVNC
sudo systemctl enable vncserver@1	Автозапуск TigerVNC для :1 (порт 5901)
sudo apt install x11vnc	Установка x11vnc
x11vnc -storepasswd	Настройка пароля для x11vnc
sudo systemctl enable x11vnc	Автозапуск x11vnc
sudo ufw allow 5901/tcp	Открытие порта для TigerVNC
sudo ufw allow 5900/tcp	Открытие порта для x11vnc   