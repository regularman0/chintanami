# Path: database/schema_manager.py
# Version: 26.0
# Description: Схема БД. Добавлена колонка is_deleted для синхронизации.

from .connection import DBConnection
from .db_config import TABLE_NAME

class SchemaManager:
    @staticmethod
    def ensure_table_exists():
        """Создает таблицу с поддержкой синхронизации (UUID + is_deleted)."""
        query = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            updated_at TEXT,
            is_deleted INTEGER DEFAULT 0,
            category_path TEXT,
            range_start TEXT,
            range_end TEXT
        )
        """
        with DBConnection() as conn:
            conn.execute(query)

    @staticmethod
    def get_existing_columns():
        with DBConnection() as conn:
            cursor = conn.execute(f"PRAGMA table_info({TABLE_NAME})")
            columns = [row["name"] for row in cursor.fetchall()]
        return columns

    @staticmethod
    def sync_columns(data_keys):
        """Добавляет недостающие динамические колонки."""
        SchemaManager.ensure_table_exists()
        
        # Гарантируем, что is_deleted существует (для миграции старых баз на лету)
        existing = set(SchemaManager.get_existing_columns())
        if "is_deleted" not in existing:
             with DBConnection() as conn:
                try:
                    conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN is_deleted INTEGER DEFAULT 0")
                    print(">>> [Schema] Added 'is_deleted' column")
                except Exception as e:
                    print(f"[Schema Error] {e}")
            
             # Обновляем список существующих после добавления
             existing.add("is_deleted")

        new_columns = []
        for key in data_keys:
            if key.lower() not in [col.lower() for col in existing]:
                new_columns.append(key)
        
        if not new_columns:
            return

        with DBConnection() as conn:
            for col in new_columns:
                try:
                    conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col} TEXT")
                except Exception as e:
                    print(f"[DB Schema Error] Failed to add {col}: {e}")