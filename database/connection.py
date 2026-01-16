# Path: database/connection.py
# Version: 18.0
# Description: Управление соединением с SQLite.

import sqlite3
from .db_config import DB_PATH

class DBConnection:
    """
    Контекстный менеджер для безопасного соединения.
    Использование:
    with DBConnection() as conn:
        cursor = conn.cursor()
        ...
    """
    def __enter__(self):
        # check_same_thread=False нужен, если GUI и БД работают в разных потоках (на будущее)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # Позволяет обращаться к колонкам по имени (row["id"]), а не по индексу
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Если была ошибка, откатываем изменения
            self.conn.rollback()
            print(f"[DB Error] Rollback executed due to: {exc_val}")
        else:
            # Если все ок, сохраняем
            self.conn.commit()
        self.conn.close()

def init_db():
    """Создает файл БД, если его нет"""
    with DBConnection() as conn:
        # Пока ничего не делаем, таблицы создаст SchemaManager
        pass