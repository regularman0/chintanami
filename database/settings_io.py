# Path: database/settings_io.py
# Version: 18.0
# Description: Управление настройками приложения (чтение/запись).

import json
import os
from core import schema

class SettingsManager:
    _cache = None

    @staticmethod
    def load():
        if SettingsManager._cache:
            return SettingsManager._cache
            
        if not os.path.exists(schema.SETTINGS_PATH):
            return {}
            
        try:
            with open(schema.SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                SettingsManager._cache = data
                return data
        except:
            return {}

    @staticmethod
    def get(section, key, default=None):
        data = SettingsManager.load()
        return data.get(section, {}).get(key, default)

    @staticmethod
    def set(section, key, value):
        data = SettingsManager.load()
        if section not in data:
            data[section] = {}
        data[section][key] = value
        
        # Сохраняем
        with open(schema.SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        SettingsManager._cache = data