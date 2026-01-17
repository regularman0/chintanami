# Path: main.py
# Version: 20.2
# Description: Точка входа. Полная версия с Валидацией, UI, БД и Автозапуском.

import tkinter as tk
from tkinter import ttk
import json
import os
from datetime import datetime

# CORE
from core import schema
from core.storage import Storage
from core.managers import TagManager, CheckboxManager, RangeManager, PathManager

# DB & API
from database.repository import DataRepository
from database.settings_io import SettingsManager
from api.launcher import SyncManager

# UI
from ui.input.input_tab import InputTab
from ui.debug_tab import DebugTab
from ui.editor.editor_tab import EditorTab
from ui.db_tab import DBTab

# =========================== ТЕМА ===========================
THEME = {
    "window_bg": "#ecf0f1", "sidebar_bg": "#2c3e50", "header_bg": "#34495e",
    "text_fg": "#2c3e50", "btn_save": "#27ae60", "btn_fg": "white",
    "range_bg": "#d6eaf8", "duration_bg": "#d7bde2", 
    "check_bg": "#f9e79f", "tags_bg": "#a9dfbf", 
    "ghost_warning": "#c0392b", "status_ok": "#2ecc71", "status_err": "#e74c3c",
    "editor_bg": "#2c3e50", "json_fg": "#f1c40f", 
    "json_ok": "#27ae60", "json_err": "#e74c3c", "tree_bg": "#ffffff"
}

# =========================== ДАННЫЕ ===========================
if not os.path.exists(schema.CONFIG_DIR): os.makedirs(schema.CONFIG_DIR)

# Загрузка FAS
fas_config = Storage.load_json(schema.FAS_PATH, {"category": {}, "tag_lists": {}, "checkboxes_list": {}})
for k in ["tag_lists", "checkboxes_list"]:
    if k not in fas_config: fas_config[k] = {}

# Загрузка Event Data
raw_event_data = Storage.load_json(schema.EVENT_DATA_PATH)
event_data = schema.migrate_and_clean(raw_event_data)
Storage.save_json_atomic(schema.EVENT_DATA_PATH, event_data)

ui_debug = None
ui_input = None

def save_callback():
    """Сохранение промежуточного состояния (черновик)"""
    Storage.save_json_atomic(schema.EVENT_DATA_PATH, event_data)
    if ui_debug: ui_debug.update_data(event_data)

managers = {
    "tag": TagManager(event_data, save_callback),
    "check": CheckboxManager(event_data, save_callback),
    "range": RangeManager(event_data, save_callback),
    "path": PathManager(event_data, save_callback)
}

# =========================== ЛОГИКА СОХРАНЕНИЯ ===========================

def show_status(msg, is_error=False):
    color = THEME["status_err"] if is_error else THEME["status_ok"]
    lbl_status.config(text=msg, fg=color)
    root.after(3000, lambda: lbl_status.config(text="System Ready", fg="gray"))

def validate_payload():
    """Проверка перед записью в БД"""
    # 1. Путь
    path = managers['path'].get_path()
    if not path: return False, "Категория не выбрана!"
    
    # 2. Чекбоксы
    has_checks = len(event_data.get("checkboxes", [])) > 0
    
    # 3. Время
    minutes = managers['range'].get_duration_minutes()
    has_duration = (minutes is not None) and (minutes > 0)
    
    if has_checks or has_duration: return True, "OK"
    else: return False, "Пустая запись (нет времени или действий)!"

def process_save_action():
    """Вызывается кнопкой 'Сохранить'"""
    is_valid, msg = validate_payload()
    if not is_valid:
        show_status(f"ОШИБКА: {msg}", is_error=True)
        return

    success = DataRepository.save_event(event_data)
    
    if success:
        show_status("УСПЕШНО ЗАПИСАНО В БД", is_error=False)
        # Проверка настройки авто-очистки
        do_clear = SettingsManager.get("db", "auto_clear_after_save", False)
        if do_clear:
            clear_event_data_form()
    else:
        show_status("ОШИБКА ЗАПИСИ (см. консоль)", is_error=True)

def clear_event_data_form():
    """Очистка формы после записи"""
    event_data["tags"].clear()
    event_data["checkboxes"].clear()
    
    # Сброс времени на "Сейчас"
    now_str = datetime.now().strftime(schema.DT_FMT)
    event_data["range"]["or_range_val"] = now_str
    event_data["range"]["end_range_val"] = now_str
    
    save_callback() # Сохраняем пустой черновик
    if ui_input: ui_input.render_dynamic_content() # Обновляем UI

# =========================== GUI ===========================
root = tk.Tk()
root.title("System Panel v20.2 (Full)")
root.geometry("1300x850")
root.configure(bg=THEME["window_bg"])

# Header
header_frame = tk.Frame(root, bg=THEME["header_bg"], height=50)
header_frame.pack(fill="x", side="top")

tk.Label(header_frame, text="SYSTEM KERNEL", bg=THEME["header_bg"], fg="white", font=("Arial", 14, "bold")).pack(side="left", padx=15)
# Статус бар
lbl_status = tk.Label(header_frame, text="System Ready", bg=THEME["header_bg"], fg="gray", font=("Consolas", 12, "bold"))
lbl_status.pack(side="right", padx=20, pady=12)

# Notebook
style = ttk.Style()
style.theme_use('clam')
style.configure("TNotebook.Tab", padding=[15, 5], font=('Arial', 10))
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=5, pady=5)

def on_config_change(new_conf):
    if ui_debug: ui_debug.update_config(new_conf)

# --- Инициализация вкладок ---

# 1. Ввод
ui_input = InputTab(notebook, THEME, managers, fas_config, event_data, 
                    debug_callback=on_config_change, 
                    save_callback=process_save_action)
notebook.add(ui_input.frame, text="  ВВОД ДАННЫХ  ")

# 2. Редактор
ui_editor = EditorTab(notebook, THEME, ui_input, fas_config)
notebook.add(ui_editor.frame, text="  РЕДАКТОР  ")

# 3. БД
ui_db = DBTab(notebook, THEME)
notebook.add(ui_db.frame, text="  НАСТРОЙКИ БД  ")

# 4. Отладка
ui_debug = DebugTab(notebook, THEME)
notebook.add(ui_debug.frame, text="  ОТЛАДКА  ")

# Initial Data Update
ui_debug.update_data(event_data)

# --- АВТОЗАПУСК СЕРВЕРА ---
# Читаем настройку. Если True — запускаем.
if SettingsManager.get("network", "autostart_server", False):
    url = SyncManager.start_server()
    print(f">>> [AutoStart] Server started at {url}")
    # UI во вкладке БД обновится сам при открытии (там есть проверка is_running)

root.mainloop()