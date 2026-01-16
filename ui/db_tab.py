# Path: ui/db_tab.py
# Version: 19.0
# Description: Вкладка настроек базы данных и приложения.

import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import platform

from database.settings_io import SettingsManager
from database.db_config import DB_PATH

class DBTab:
    def __init__(self, notebook, theme):
        self.frame = tk.Frame(notebook, bg=theme["window_bg"])
        self.theme = theme
        
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        # Контейнер с отступами
        pad_frame = tk.Frame(self.frame, bg=self.theme["window_bg"])
        pad_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Секция 1: Настройки поведения ---
        lbl_behavior = tk.Label(pad_frame, text="ПОВЕДЕНИЕ", font=("Arial", 12, "bold"), 
                                bg=self.theme["window_bg"], fg=self.theme["text_fg"])
        lbl_behavior.pack(anchor="w", pady=(0, 10))

        # Чекбокс автоочистки
        self.var_auto_clear = tk.BooleanVar()
        cb_clear = tk.Checkbutton(pad_frame, text="Очищать форму ввода после успешного сохранения", 
                                  variable=self.var_auto_clear, command=self._on_change_clear,
                                  bg=self.theme["window_bg"], activebackground=self.theme["window_bg"],
                                  font=("Arial", 10))
        cb_clear.pack(anchor="w", padx=10)
        
        tk.Label(pad_frame, text="(Range сбрасывается на текущее время, списки очищаются)", 
                 font=("Arial", 8), fg="gray", bg=self.theme["window_bg"]).pack(anchor="w", padx=30)

        # Разделитель
        ttk.Separator(pad_frame, orient="horizontal").pack(fill="x", pady=20)

        # --- Секция 2: Информация о БД ---
        lbl_db = tk.Label(pad_frame, text="БАЗА ДАННЫХ (SQLite)", font=("Arial", 12, "bold"), 
                          bg=self.theme["window_bg"], fg=self.theme["text_fg"])
        lbl_db.pack(anchor="w", pady=(0, 10))

        # Путь к файлу
        f_path = tk.Frame(pad_frame, bg=self.theme["window_bg"])
        f_path.pack(fill="x", padx=10)
        
        tk.Label(f_path, text="Путь:", font=("Arial", 10, "bold"), bg=self.theme["window_bg"]).pack(side="left")
        self.ent_path = tk.Entry(f_path, width=60, font=("Consolas", 9), fg="gray")
        self.ent_path.insert(0, DB_PATH)
        self.ent_path.config(state="readonly")
        self.ent_path.pack(side="left", padx=10)

        # Кнопки действий
        btn_box = tk.Frame(pad_frame, bg=self.theme["window_bg"])
        btn_box.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_box, text="📂 Открыть папку", command=self._open_folder).pack(side="left")
        
    def _load_values(self):
        """Загрузка текущих настроек из файла"""
        val = SettingsManager.get("db", "auto_clear_after_save", False)
        self.var_auto_clear.set(val)

    def _on_change_clear(self):
        """Сохранение настройки при клике"""
        SettingsManager.set("db", "auto_clear_after_save", self.var_auto_clear.get())

    def _open_folder(self):
        """Открывает папку с базой данных в проводнике"""
        folder = os.path.dirname(DB_PATH)
        try:
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку:\n{e}")