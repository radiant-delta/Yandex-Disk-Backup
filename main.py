"""
Резервное копирование папки на сервер Яндекс.Диска
"""

import yadisk
import os
import sys
import datetime
import pyzipper
import psutil

# ========== НАСТРОЙКИ ==========
TOKEN = ""
LOCAL_DIR = r"D:/Целевая папка" # Путь к архивируемой папке
REMOTE_DIR = "app:/"
ARCHIVE_NAME = f"backup_{datetime.date.today().strftime('%Y-%m-%d')}.zip"
PASSWORD = os.environ.get("backup_password", "запасной пароль")
# ===============================

def vpn_check() -> int:
    # Получаем имена всех активных интерфейсов в Windows
    interfaces = psutil.net_if_stats().keys()
    
    # Если AmneziaVPN есть в списке — возвращаем 1, если нет — 0
    if "AmneziaVPN" in interfaces:
        return 1
    return 0

def create_encrypted_backup(source, output, password):
    print("Создание зашифрованного архива...")
    with pyzipper.AESZipFile(output, 'w', 
                             compression=pyzipper.ZIP_DEFLATED, 
                             encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode('utf-8'))
        for root, dirs, files in os.walk(source):
            for file in files:
                full = os.path.join(root, file)
                zf.write(full, os.path.relpath(full, source))
    
    size_mb = os.path.getsize(output) / (1024 * 1024)
    print(f"Готово: {size_mb:.2f} МБ")

if __name__ == "__main__":

    # Проверка VPN
    if vpn_check():
        # в Python 1 приравнивается к True, а 0 к False
        print("Активно VPN соединение. Резервное копирование остановлено", file=sys.stderr)
        sys.exit(1)

    # Архивация с паролем
    create_encrypted_backup(LOCAL_DIR, ARCHIVE_NAME, PASSWORD)
    
    # Загрузка на Яндекс.Диск
    with yadisk.Client(token=TOKEN) as client:
        if client.check_token():
            remote_path = f"{REMOTE_DIR}{ARCHIVE_NAME}"
            print("Загрузка на Яндекс.Диск...")
            client.upload(ARCHIVE_NAME, remote_path, overwrite=True)
            print("Загружено!")
    
    # ========= Очистка =========
    os.remove(ARCHIVE_NAME)
    print("Локальный архив удалён.")
    
    # Ротация – оставляем 2 последних архива
    with yadisk.Client(token=TOKEN) as client:
        backups = list(client.listdir(REMOTE_DIR))
        backups = [f for f in backups if f.name.endswith('.zip')]
        backups.sort(key=lambda f: f.name)  # По имени (дате)
        for old in backups[:-2]:  # Удаляем все кроме последних 2
            client.remove(old.path, permanently=True)
            print(f"Удалён старый бэкап: {old.name}")