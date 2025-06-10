import subprocess
import time
import logging

logging.basicConfig(
                    level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s'
)

def reboot_interface(interface):
    try:
        subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'down'], check=True)
        time.sleep(4)
        subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'up'], check=True)
        logging.info(f'Интерфейс {interface} успешно перезапущен')

    except subprocess.CalledProcessError as e:
        logging.info(f'Ошибка при перезапуске интерфейса {interface}: {e}')
