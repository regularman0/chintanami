# Path: database/connection.py
# Version: 2.5 (With Auto-Backup)
# Description: Подключение к БД с автоматическим созданием бэкапа.

import sqlite3
import os
import shutil
from datetime import datetime
from .db_config import DB_PATH

class DBConnection:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        # Авто-бэкап раз в день при первом запуске
        self._check_backup()
        
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

    def _check_backup(self):
        """Создает копию базы в папке /backups, если её там еще нет за сегодня"""
        if not os.path.exists(DB_PATH): return
        
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        today = datetime.now().strftime("%Y_%m_%d")
        backup_file = os.path.join(backup_dir, f"db_backup_{today}.bak")
        
        if not os.path.exists(backup_file):
            try:
                shutil.copy2(DB_PATH, backup_file)
                # Удаляем старые бэкапы (оставляем только последние 7)
                all_backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir)])
                if len(all_backups) > 7:
                    os.remove(all_backups[0])
            except Exception as e:
                print(f"Backup failed: {e}")