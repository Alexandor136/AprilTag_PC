#!/bin/bash

# Установка TigerVNC (для новых сессий)
sudo apt update
sudo apt install -y tigervnc-standalone-server tigervnc-xorg-extension

# Настройка пароля VNC
echo "Задайте пароль для VNC:"
vncpasswd

# Создание systemd-сервиса для TigerVNC
sudo tee /etc/systemd/system/vncserver@.service > /dev/null <<EOF
[Unit]
Description=TigerVNC server
After=network.target

[Service]
User=$USER
WorkingDirectory=/home/$USER
ExecStart=/usr/bin/vncserver -geometry 1920x1080 -depth 24 -localhost no :%i
ExecStop=/usr/bin/vncserver -kill :%i
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Включение TigerVNC
sudo systemctl daemon-reload
sudo systemctl enable vncserver@1
sudo systemctl start vncserver@1

# Установка x11vnc (для текущей сессии)
sudo apt install -y x11vnc

# Настройка пароля x11vnc
echo "Задайте пароль для x11vnc:"
x11vnc -storepasswd

# Создание systemd-сервиса для x11vnc
sudo tee /etc/systemd/system/x11vnc.service > /dev/null <<EOF
[Unit]
Description=x11vnc remote desktop server
After=display-manager.service

[Service]
ExecStart=/usr/bin/x11vnc -display :0 -auth guess -forever -shared -rfbauth /home/$USER/.vnc/passwd
User=$USER
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Включение x11vnc
sudo systemctl daemon-reload
sudo systemctl enable x11vnc
sudo systemctl start x11vnc

# Открытие портов в брандмауэре
sudo ufw allow 5901/tcp  # TigerVNC
sudo ufw allow 5900/tcp  # x11vnc
sudo ufw reload

echo "Настройка завершена!"
echo "TigerVNC (новые сессии) доступен на порту 5901"
echo "x11vnc (текущая сессия) доступен на порту 5900"