# Path: database/query_builder.py
# Version: 26.0
# Description: Бэкенд с поддержкой Soft Delete.

from .connection import DBConnection
from .db_config import TABLE_NAME
from datetime import datetime, timedelta

class QueryBuilder:
    
    @staticmethod
    def get_columns():
        try:
            with DBConnection() as conn:
                cursor = conn.execute(f"PRAGMA table_info({TABLE_NAME})")
                return [row["name"] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB Error] Get columns: {e}")
            return []

    @staticmethod
    def fetch_data(offset=0, limit=100, sort_col="timestamp", sort_desc=True, filters=None, show_deleted=False):
        params = []
        where_clauses = []
        
        # --- SOFT DELETE FILTER ---
        if not show_deleted:
            # Показываем только живые записи
            # (is_deleted IS NULL нужно для совместимости, если колонка только создана и там null)
            where_clauses.append("(is_deleted = 0 OR is_deleted IS NULL)")

        if filters:
            mode = filters.get("period", "all")
            now = datetime.now()
            sql_date_converter = "substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2)"

            if mode == "today":
                today_str = now.strftime("%d.%m.%Y")
                where_clauses.append("timestamp LIKE ?")
                params.append(f"{today_str}%")
            elif mode == "yesterday":
                yesterday_str = (now - timedelta(days=1)).strftime("%d.%m.%Y")
                where_clauses.append("timestamp LIKE ?")
                params.append(f"{yesterday_str}%")
            elif mode == "week":
                week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
                where_clauses.append(f"date({sql_date_converter}) >= date(?)")
                params.append(week_ago)

            search = filters.get("search", "").strip()
            if search:
                where_clauses.append("category_path LIKE ?")
                params.append(f"%{search}%")

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        direction = "DESC" if sort_desc else "ASC"
        
        if sort_col not in ["id", "timestamp"]: sort_col = "timestamp"

        query = f"SELECT * FROM {TABLE_NAME} {where_sql} ORDER BY {sort_col} {direction} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with DBConnection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DB Error] Fetch: {e}")
            return []

    @staticmethod
    def get_record(pk):
        try:
            with DBConnection() as conn:
                cursor = conn.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (pk,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[DB Error] Get record {pk}: {e}")
            return None

    @staticmethod
    def add_record(data_dict):
        # (Используется Repository, но оставим для совместимости)
        pass 

    @staticmethod
    def update_record(pk, updates):
        if not updates: return False
        
        # Обновляем время изменения
        updates["updated_at"] = datetime.now().isoformat()
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(pk)
        try:
            with DBConnection() as conn:
                conn.execute(f"UPDATE {TABLE_NAME} SET {set_clause} WHERE id = ?", values)
            return True
        except Exception as e:
            print(f"[DB Error] Update: {e}")
            return False

    @staticmethod
    def delete_records(ids):
        """
        SOFT DELETE: Помечает записи как удаленные.
        """
        if not ids: return False
        placeholders = ",".join("?" * len(ids))
        
        # Обновляем updated_at, чтобы этот факт удаления синхронизировался
        now_iso = datetime.now().isoformat()
        
        # Параметры: [updated_at, id1, id2...]
        params = [now_iso] + list(ids)
        
        query = f"UPDATE {TABLE_NAME} SET is_deleted=1, updated_at=? WHERE id IN ({placeholders})"
        
        try:
            with DBConnection() as conn:
                conn.execute(query, params)
            print(f">>> [DB] Soft Deleted {len(ids)} records")
            return True
        except Exception as e:
            print(f"[DB Error] Soft Delete: {e}")
            return False

    @staticmethod
    def generate_summary(row_dict):
        parts = []
        for k, v in row_dict.items():
            if k.startswith("T_") and v:
                clean_key = k[2:]
                if "_" in clean_key and clean_key.split("_")[-1].isdigit():
                     clean_key = clean_key.rsplit("_", 1)[0]
                parts.append(f"{clean_key.title()}: {v}")
        for k, v in row_dict.items():
            if k.startswith("C_") and v:
                clean_key = k[2:]
                if "_" in clean_key and clean_key.split("_")[-1].isdigit():
                     clean_key = clean_key.rsplit("_", 1)[0]
                parts.append(f"☑ {clean_key.title()}")
        return ", ".join(parts)