# Path: core/managers.py
# Version: 19.1
# Description: Логика времени обновлена (умный парсер, сдвиг, работа с БД).

from datetime import datetime, timedelta
from core import schema
from database.repository import DataRepository # Для чтения истории

DT_FMT = schema.DT_FMT

class BaseManager:
    def __init__(self, event_data, save_callback):
        self.data = event_data
        self._save = save_callback

class PathManager(BaseManager):
    def set_path(self, path_list):
        self.data["category_path"] = "/".join(path_list)
        self._save()
    def get_path(self):
        val = self.data.get("category_path", "")
        return val.split("/") if val else []

class CheckboxManager(BaseManager):
    def get_entry(self, db_name):
        for x in self.data["checkboxes"]:
            if x["db_name"] == db_name: return x
        return None
    def get_max_index(self, prefix):
        max_idx = 0; clean = prefix.rstrip("_")
        for x in self.data["checkboxes"]:
            if x["db_name"].startswith(clean):
                parts = x["db_name"].split("_")
                if parts and parts[-1].isdigit():
                    v = int(parts[-1])
                    if v > max_idx: max_idx = v
        return max_idx
    def toggle(self, db_name, is_checked):
        self.data["checkboxes"] = [x for x in self.data["checkboxes"] if x["db_name"] != db_name]
        ts = ""
        if is_checked:
            # Чекбоксы пишут время в формате схемы (теперь без секунд)
            ts = datetime.now().strftime(DT_FMT)
            self.data["checkboxes"].append({"db_name": db_name, "change_time": ts})
        self._save()
        return ts
    def rebuild_numbering(self, prefix, ui_items):
        ui_items.sort(key=lambda w: w["index"])
        states = []
        for w in ui_items:
            old = self.get_entry(w["db_name"])
            states.append({"checked": w["is_checked"], "time": old["change_time"] if old else ""})
        
        clean = prefix.rstrip("_")
        self.data["checkboxes"] = [x for x in self.data["checkboxes"] if not x["db_name"].startswith(clean)]
        
        new_ui = []
        for i, item in enumerate(ui_items, 1):
            st = states[i-1]
            nn = schema.normalize_db_name(prefix, i)
            item["index"] = i; item["db_name"] = nn
            item["label"]["text"] = f"{item['label_base']} ({nn})"
            if st["checked"]:
                self.data["checkboxes"].append({"db_name": nn, "change_time": st["time"]})
            new_ui.append(item)
        self._save()
        return new_ui

class TagManager(BaseManager):
    def get_entries(self, prefix):
        clean = prefix.rstrip("_")
        return [x for x in self.data["tags"] if x["db_name"].startswith(clean)]
    def get_max_index(self, prefix):
        max_idx = 0; clean = prefix.rstrip("_")
        for x in self.data["tags"]:
            if x["db_name"].startswith(clean):
                parts = x["db_name"].split("_")
                if parts and parts[-1].isdigit():
                    v = int(parts[-1])
                    if v > max_idx: max_idx = v
        return max_idx
    def update_value(self, db_name, value):
        self.data["tags"] = [x for x in self.data["tags"] if x["db_name"] != db_name]
        if value: self.data["tags"].append({"db_name": db_name, "value": value})
        self._save()
    def rebuild_numbering(self, prefix, ui_items):
        ui_items.sort(key=lambda w: w["index"])
        clean = prefix.rstrip("_")
        self.data["tags"] = [x for x in self.data["tags"] if not x["db_name"].startswith(clean)]
        new_ui = []
        for i, item in enumerate(ui_items, 1):
            nn = schema.normalize_db_name(prefix, i)
            item["index"] = i; item["db_name"] = nn
            item["label"]["text"] = f"{item['label_base']} ({nn})"
            if item.get("current_value"):
                self.data["tags"].append({"db_name": nn, "value": item["current_value"]})
            new_ui.append(item)
        self._save()
        return new_ui

class RangeManager(BaseManager):
    def get_values(self):
        return (self.data["range"].get("or_range_val", ""), self.data["range"].get("end_range_val", ""))
    
    def set_values(self, start=None, end=None):
        if start is not None: self.data["range"]["or_range_val"] = start
        if end is not None: self.data["range"]["end_range_val"] = end
        self._save()

    def parse_dt(self, dt_str):
        """
        Умный парсер. Пытается прочитать новый формат (без сек).
        Если не выходит - старый (с сек).
        """
        if not dt_str: return None
        dt_str = dt_str.strip()
        try:
            return datetime.strptime(dt_str, DT_FMT) # New format
        except ValueError:
            try:
                # Fallback to legacy
                return datetime.strptime(dt_str, schema.LEGACY_DT_FMT)
            except ValueError:
                return None

    def modify_time(self, key, mins, op="add"):
        cur = self.data["range"].get(key, "")
        dt = self.parse_dt(cur)
        if dt is None: dt = datetime.now()
        
        delta = timedelta(minutes=mins)
        ndt = dt + delta if op == "add" else dt - delta
        
        ns = ndt.strftime(DT_FMT)
        self.data["range"][key] = ns; self._save()
        return ns

    def shift_range(self, mins, op="add"):
        """
        Сдвигает ВЕСЬ диапазон (и старт, и конец) на mins.
        """
        s_str, e_str = self.get_values()
        s_dt = self.parse_dt(s_str) or datetime.now()
        e_dt = self.parse_dt(e_str) or datetime.now()
        
        delta = timedelta(minutes=mins)
        if op == "sub": delta = -delta
        
        new_s = (s_dt + delta).strftime(DT_FMT)
        new_e = (e_dt + delta).strftime(DT_FMT)
        
        self.set_values(new_s, new_e)
        return new_s, new_e

    def sync_start_from_end_and_duration(self, mins):
        es = self.data["range"].get("end_range_val", "")
        end = self.parse_dt(es)
        if not end:
            end = datetime.now()
            self.data["range"]["end_range_val"] = end.strftime(DT_FMT)
            
        start = end - timedelta(minutes=mins)
        ss = start.strftime(DT_FMT)
        self.data["range"]["or_range_val"] = ss; self._save()
        return ss, end.strftime(DT_FMT)

    def copy_last_end_from_db(self):
        """
        Берет последнюю дату из БД.
        Возвращает строку времени или None.
        """
        last_end = DataRepository.get_last_event_end()
        if last_end:
            # Парсим и переформатируем в новый формат (обрезаем секунды, если были)
            dt = self.parse_dt(last_end)
            if dt:
                new_str = dt.strftime(DT_FMT)
                # Устанавливаем в Start
                self.data["range"]["or_range_val"] = new_str
                self._save()
                return new_str
        return None

    def get_duration_minutes(self):
        """Возвращает разницу (End - Start) в минутах или None"""
        s_str, e_str = self.get_values()
        s = self.parse_dt(s_str)
        e = self.parse_dt(e_str)
        if s and e:
            diff = (e - s).total_seconds()
            return int(diff / 60)
        return None