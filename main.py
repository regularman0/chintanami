# Path: main.py
# Version: 20.0
# Description: Точка входа. Добавлена Валидация, Статус-бар и передача кнопки сохранения во вкладку ввода.

import tkinter as tk
from tkinter import ttk
import json
import os
from datetime import datetime

# --- Импорты из CORE ---
from core import schema
from core.storage import Storage
from core.managers import TagManager, CheckboxManager, RangeManager, PathManager

# --- Импорты БД ---
from database.repository import DataRepository
from database.settings_io import SettingsManager

# --- Импорты из UI ---
from ui.input.input_tab import InputTab
from ui.debug_tab import DebugTab
from ui.editor.editor_tab import EditorTab
from ui.db_tab import DBTab

from ui.db_view.view_tab import DbViewTab

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

fas_config = Storage.load_json(schema.FAS_PATH, {"category": {}, "tag_lists": {}, "checkboxes_list": {}})
for k in ["tag_lists", "checkboxes_list"]:
    if k not in fas_config: fas_config[k] = {}

raw_event_data = Storage.load_json(schema.EVENT_DATA_PATH)
event_data = schema.migrate_and_clean(raw_event_data)
Storage.save_json_atomic(schema.EVENT_DATA_PATH, event_data)

ui_debug = None
ui_input = None

def save_callback():
    Storage.save_json_atomic(schema.EVENT_DATA_PATH, event_data)
    if ui_debug: ui_debug.update_data(event_data)

managers = {
    "tag": TagManager(event_data, save_callback),
    "check": CheckboxManager(event_data, save_callback),
    "range": RangeManager(event_data, save_callback),
    "path": PathManager(event_data, save_callback)
}

# =========================== ЛОГИКА ВАЛИДАЦИИ И ОТПРАВКИ ===========================

def show_status(msg, is_error=False):
    """Показывает сообщение в шапке на 3 секунды"""
    color = THEME["status_err"] if is_error else THEME["status_ok"]
    lbl_status.config(text=msg, fg=color)
    # Автоочистка через 3 сек
    root.after(3000, lambda: lbl_status.config(text="Ready", fg="gray"))

def validate_payload():
    """Проверяет, есть ли смысл сохранять запись"""
    # 1. Проверка Пути
    path = managers['path'].get_path()
    if not path:
        return False, "Категория не выбрана!"
    
    # 2. Проверка Чекбоксов (Флаг действия)
    has_checks = len(event_data.get("checkboxes", [])) > 0
    
    # 3. Проверка Времени (Длительность > 0)
    # Используем метод менеджера, он уже умеет считать разницу
    minutes = managers['range'].get_duration_minutes()
    # Если minutes None (ошибка парсинга) или <= 0, то false
    has_duration = (minutes is not None) and (minutes > 0)
    
    # ИТОГ: Либо действие, либо потраченное время
    if has_checks or has_duration:
        return True, "OK"
    else:
        return False, "Пустая запись! (Нужен чекбокс или время > 0)"

def process_save_action():
    # 1. Валидация
    is_valid, msg = validate_payload()
    
    if not is_valid:
        show_status(f"ОШИБКА: {msg}", is_error=True)
        return

    # 2. Запись в БД
    success = DataRepository.save_event(event_data)
    
    if success:
        show_status(f"УСПЕШНО ЗАПИСАНО (ID последней: ...)", is_error=False)
        
        # 3. Авто-очистка
        do_clear = SettingsManager.get("db", "auto_clear_after_save", False)
        if do_clear:
            clear_event_data_form()
            print(">>> [Auto-Clear] Форма очищена")
    else:
        show_status("ОШИБКА ЗАПИСИ В БД (см. консоль)", is_error=True)

def clear_event_data_form():
    """Очищает данные (кроме пути)"""
    event_data["tags"].clear()
    event_data["checkboxes"].clear()
    
    # Сбрасываем время на "Сейчас" (или потом добавим логику переноса конца)
    # TODO: Сюда добавим логику "Взять конец предыдущей" позже
    now_str = datetime.now().strftime(schema.DT_FMT)
    event_data["range"]["or_range_val"] = now_str
    event_data["range"]["end_range_val"] = now_str
    
    save_callback()
    
    if ui_input:
        ui_input.render_dynamic_content()

# =========================== GUI ===========================
root = tk.Tk()
root.title("System Panel v20.0 (Validation & UX)")
root.geometry("1300x850")
root.configure(bg=THEME["window_bg"])

# --- HEADER (Статус-бар вместо кнопок) ---
header_frame = tk.Frame(root, bg=THEME["header_bg"], height=40)
header_frame.pack(fill="x", side="top")

# Лейбл статуса (по центру или слева)
lbl_status = tk.Label(header_frame, text="System Ready", bg=THEME["header_bg"], fg="gray", font=("Consolas", 12, "bold"))
lbl_status.pack(side="left", padx=20, pady=10)

# --- TABS ---
style = ttk.Style()
style.theme_use('clam')
style.configure("TNotebook.Tab", padding=[15, 5], font=('Arial', 10))
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=5, pady=5)

def on_config_change(new_conf):
    if ui_debug: ui_debug.update_config(new_conf)

# 1. Ввод (Передаем process_save_action как коллбэк)
ui_input = InputTab(
    notebook, 
    THEME, 
    managers, 
    fas_config, 
    event_data, 
    debug_callback=on_config_change,
    save_callback=process_save_action # <--- Новая функция сохранения
)
notebook.add(ui_input.frame, text="  ВВОД ДАННЫХ  ")

# 2. Редактор
ui_editor = EditorTab(notebook, THEME, ui_input, fas_config)
notebook.add(ui_editor.frame, text="  РЕДАКТОР  ")

# 3. Настройки БД
ui_db = DBTab(notebook, THEME)
notebook.add(ui_db.frame, text="  НАСТРОЙКИ БД  ")

# 4. Отладка
ui_debug = DebugTab(notebook, THEME)
notebook.add(ui_debug.frame, text="  ОТЛАДКА  ")

# 5. Просмотр БД
ui_db_view = DbViewTab(notebook, THEME)
notebook.add(ui_db_view.frame, text="  БАЗА ДАННЫХ  ")


# Init
ui_debug.update_data(event_data)
root.mainloop()