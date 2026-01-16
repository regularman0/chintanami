# Path: core/schema.py
# Version: 19.1
# Description: Пути и форматы. Формат времени изменен (без секунд).

import os
import re

BASE_DIR = os.getcwd()
CONFIG_DIR = os.path.join(BASE_DIR, "config")

FAS_PATH = os.path.join(CONFIG_DIR, "fas.json")
EVENT_DATA_PATH = os.path.join(CONFIG_DIR, "event_data.json")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")

# ИСПРАВЛЕНО: Убраны секунды (%S)
DT_FMT = "%d.%m.%Y %H:%M"
LEGACY_DT_FMT = "%d.%m.%Y %H:%M:%S" # Для совместимости со старыми записями

def normalize_db_name(prefix, index):
    clean_prefix = prefix.rstrip("_")
    return f"{clean_prefix}_{index}"

def migrate_and_clean(event_data):
    if not isinstance(event_data, dict): event_data = {}
    
    if "range" not in event_data: event_data["range"] = {"or_range_val": "", "end_range_val": ""}
    if "duration" in event_data: del event_data["duration"]
    if "checkboxes" not in event_data: event_data["checkboxes"] = []
    if "tags" not in event_data: event_data["tags"] = []
    if "meta" not in event_data: event_data["meta"] = {"version": 3}
    
    # Clean Tags
    clean_t = []
    seen_t = set()
    for item in event_data["tags"]:
        fixed = re.sub(r"_+", "_", item["db_name"])
        item["db_name"] = fixed
        if fixed not in seen_t:
            clean_t.append(item)
            seen_t.add(fixed)
    event_data["tags"] = clean_t

    # Clean Checks
    clean_c = []
    seen_c = set()
    for item in event_data["checkboxes"]:
        fixed = re.sub(r"_+", "_", item["db_name"])
        item["db_name"] = fixed
        if fixed not in seen_c:
            clean_c.append(item)
            seen_c.add(fixed)
    event_data["checkboxes"] = clean_c
    
    return event_data