# Script: database/migrator_v2.py
# Description: Добавляет поле is_deleted в существующую БД.

import sqlite3
import os
import sys

# Хак путей
if __name__ == "__main__" and __package__ is None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    sys.path.append(root_dir)
    __package__ = "database"

from .db_config import DB_PATH, TABLE_NAME

def add_is_deleted():
    if not os.path.exists(DB_PATH):
        print("БД не найдена.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        # Проверяем наличие
        cursor = conn.execute(f"PRAGMA table_info({TABLE_NAME})")
        cols = [row[1] for row in cursor.fetchall()]
        
        if "is_deleted" in cols:
            print("Колонка is_deleted уже существует.")
        else:
            print("Добавляем колонку is_deleted...")
            conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN is_deleted INTEGER DEFAULT 0")
            conn.commit()
            print("Успешно.")
            
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_is_deleted()