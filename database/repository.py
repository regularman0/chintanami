# Path: database/repository.py
# Version: 26.0
# Description: Логика синхронизации (Pull/Push Changes).

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
        
        new_id = str(uuid.uuid4())
        now_iso = datetime.now().isoformat()
        
        flat_data["id"] = new_id
        flat_data["session_id"] = SESSION_ID
        flat_data["timestamp"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        flat_data["updated_at"] = now_iso
        flat_data["is_deleted"] = 0 # Новая запись жива
        
        SchemaManager.sync_columns(flat_data.keys())
        
        columns = ", ".join(flat_data.keys())
        placeholders = ", ".join(["?"] * len(flat_data))
        values = list(flat_data.values())
        
        query = f"INSERT INTO {TABLE_NAME} ({columns}) VALUES ({placeholders})"
        
        try:
            with DBConnection() as conn:
                conn.execute(query, values)
                print(f">>> [DB] Saved UUID: {new_id}")
                return True
        except Exception as e:
            print(f">>> [DB Error] Save failed: {e}")
            return False

    @staticmethod
    def get_last_event_end():
        # Берем только НЕ удаленные
        query = f"SELECT range_end FROM {TABLE_NAME} WHERE is_deleted = 0 ORDER BY timestamp DESC LIMIT 1"
        try:
            SchemaManager.ensure_table_exists()
            with DBConnection() as conn:
                cursor = conn.execute(query)
                row = cursor.fetchone()
                if row and row["range_end"]:
                    return row["range_end"]
                return None
        except: return None

    # --- МЕТОДЫ СИНХРОНИЗАЦИИ ---

    @staticmethod
    def get_changes_since(last_sync_iso=None):
        """
        Возвращает все записи (и удаленные тоже), измененные ПОСЛЕ указанного времени.
        Если last_sync_iso is None -> отдает всю базу.
        """
        try:
            params = []
            where = ""
            if last_sync_iso:
                where = "WHERE updated_at > ?"
                params.append(last_sync_iso)
            
            query = f"SELECT * FROM {TABLE_NAME} {where}"
            
            with DBConnection() as conn:
                cursor = conn.execute(query, params)
                # Возвращаем список словарей
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Sync Error] Get Changes: {e}")
            return []

    @staticmethod
    def apply_sync_batch(records):
        """
        Принимает список записей (словарей) и обновляет локальную БД.
        Использует INSERT OR REPLACE (Upsert).
        """
        if not records: return 0
        
        # 1. Собираем все возможные ключи из батча, чтобы обновить схему
        all_keys = set()
        for r in records:
            all_keys.update(r.keys())
            
        # Убеждаемся, что колонки существуют
        SchemaManager.sync_columns(all_keys)
        
        count = 0
        with DBConnection() as conn:
            for rec in records:
                cols = ", ".join(rec.keys())
                placeholders = ", ".join(["?"] * len(rec))
                vals = list(rec.values())
                
                # SQLite Upsert
                query = f"INSERT OR REPLACE INTO {TABLE_NAME} ({cols}) VALUES ({placeholders})"
                try:
                    conn.execute(query, vals)
                    count += 1
                except Exception as e:
                    print(f"[Sync Error] Failed to upsert record {rec.get('id')}: {e}")
        
        return count