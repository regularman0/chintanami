# Path: database/repository.py
# Version: 19.1
# Description: Добавлен метод получения последней записи (get_last_event_end).

import uuid
from datetime import datetime
from .connection import DBConnection
from .schema_manager import SchemaManager
from .db_config import TABLE_NAME

SESSION_ID = str(uuid.uuid4())[:8].upper()

class DataRepository:
    
    @staticmethod
    def _flatten_data(event_data):
        flat = {}
        flat["range_start"] = event_data.get("range", {}).get("or_range_val", "")
        flat["range_end"] = event_data.get("range", {}).get("end_range_val", "")
        flat["category_path"] = event_data.get("category_path", "")

        for tag in event_data.get("tags", []):
            key = f"T_{tag['db_name'].upper()}"
            flat[key] = tag["value"]

        for cb in event_data.get("checkboxes", []):
            key = f"C_{cb['db_name'].upper()}"
            flat[key] = cb["change_time"]
            
        return flat

    @staticmethod
    def save_event(event_data):
        flat_data = DataRepository._flatten_data(event_data)
        flat_data["session_id"] = SESSION_ID
        flat_data["timestamp"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S") # В БД пишем с секундами (тех. поле)
        
        SchemaManager.sync_columns(flat_data.keys())
        
        columns = ", ".join(flat_data.keys())
        placeholders = ", ".join(["?"] * len(flat_data))
        values = list(flat_data.values())
        
        query = f"INSERT INTO {TABLE_NAME} ({columns}) VALUES ({placeholders})"
        
        try:
            with DBConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                row_id = cursor.lastrowid
                print(f">>> [DB Success] Saved Row ID: {row_id}")
                return True
        except Exception as e:
            print(f">>> [DB Error] Save failed: {e}")
            return False

    @staticmethod
    def get_last_event_end():
        """
        Возвращает значение range_end из последней записанной строки.
        Нужно для кнопки 'Copy End -> Start'.
        """
        query = f"SELECT range_end FROM {TABLE_NAME} ORDER BY id DESC LIMIT 1"
        try:
            # Проверяем, существует ли таблица
            SchemaManager.ensure_table_exists()
            
            with DBConnection() as conn:
                cursor = conn.execute(query)
                row = cursor.fetchone()
                if row and row["range_end"]:
                    return row["range_end"]
                return None
        except Exception as e:
            print(f"[DB Read Error] {e}")
            return None