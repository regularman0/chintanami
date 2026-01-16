# Path: database/db_config.py
# Version: 18.0
# Description: Конфигурация путей к БД.

import os

BASE_DIR = os.getcwd()
CONFIG_DIR = os.path.join(BASE_DIR, "config")

# Имя файла базы данных
DB_NAME = "events_storage.db"
DB_PATH = os.path.join(CONFIG_DIR, DB_NAME)

# Таблица для событий
TABLE_NAME = "events"