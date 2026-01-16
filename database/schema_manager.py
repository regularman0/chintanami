# Path: database/schema_manager.py
# Version: 18.0
# Description: Динамическое управление схемой (ALTER TABLE).

from .connection import DBConnection
from .db_config import TABLE_NAME

class SchemaManager:
    @staticmethod
    def ensure_table_exists():
        """Создает базовую таблицу с обязательными полями."""
        query = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT,
            category_path TEXT,
            range_start TEXT,
            range_end TEXT
        )
        """
        with DBConnection() as conn:
            conn.execute(query)

    @staticmethod
    def get_existing_columns():
        """Возвращает список имен всех колонок в таблице."""
        with DBConnection() as conn:
            cursor = conn.execute(f"PRAGMA table_info({TABLE_NAME})")
            columns = [row["name"] for row in cursor.fetchall()]
        return columns

    @staticmethod
    def sync_columns(data_keys):
        """
        Проверяет, есть ли ключи из data_keys в таблице.
        Если нет — добавляет новые колонки (TEXT).
        """
        SchemaManager.ensure_table_exists()
        existing = set(SchemaManager.get_existing_columns())
        
        new_columns = []
        for key in data_keys:
            # Ключи должны быть безопасными для SQL (только буквы, цифры, _)
            # Мы предполагаем, что Flattening это уже сделал.
            if key.lower() not in [col.lower() for col in existing]:
                new_columns.append(key)
        
        if not new_columns:
            return

        with DBConnection() as conn:
            for col in new_columns:
                print(f">>> [DB Schema] Adding new column: {col}")
                # В SQLite добавить колонку можно только по одной за раз
                # Тип данных TEXT — самый универсальный для JSON-хранилища
                try:
                    conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col} TEXT")
                except Exception as e:
                    print(f"[DB Schema Error] Failed to add {col}: {e}")