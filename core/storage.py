# Path: core/storage.py
# Version: 14.0
# Description: Низкоуровневое чтение/запись JSON с защитой.

import json
import os
import shutil
import tempfile

class Storage:
    @staticmethod
    def load_json(filepath, default_value=None):
        if default_value is None: default_value = {}
        if not os.path.exists(filepath): return default_value
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Storage] Error loading {filepath}: {e}")
            return default_value

    @staticmethod
    def save_json_atomic(filepath, data):
        dir_name = os.path.dirname(os.path.abspath(filepath)) or "."
        if not os.path.exists(dir_name): os.makedirs(dir_name)
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tmp:
                json.dump(data, tmp, ensure_ascii=False, indent=4)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_name = tmp.name
            shutil.move(tmp_name, filepath)
        except OSError as e:
            print(f"[Storage] Error saving {filepath}: {e}")