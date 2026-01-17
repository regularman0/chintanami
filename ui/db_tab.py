# Path: ui/db_tab.py
# Version: 20.1
# Description: Вкладка настроек. Добавлен чекбокс Автозапуска.

import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import platform

from database.settings_io import SettingsManager
from database.db_config import DB_PATH
from api.launcher import SyncManager

class DBTab:
    def __init__(self, notebook, theme):
        self.frame = tk.Frame(notebook, bg=theme["window_bg"])
        self.theme = theme
        self.is_server_running = False
        
        self._setup_ui()
        self._load_values()
        
        # Проверяем, не запущен ли сервер уже (из main.py)
        self._check_server_status()

    def _setup_ui(self):
        pad_frame = tk.Frame(self.frame, bg=self.theme["window_bg"])
        pad_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- СЕКЦИЯ 1: СИНХРОНИЗАЦИЯ ---
        lbl_sync = tk.Label(pad_frame, text="СИНХРОНИЗАЦИЯ (Android)", font=("Arial", 12, "bold"), 
                            bg=self.theme["window_bg"], fg=self.theme["text_fg"])
        lbl_sync.pack(anchor="w", pady=(0, 10))

        # Чекбокс Автозапуска
        self.var_autostart = tk.BooleanVar()
        cb_auto = tk.Checkbutton(pad_frame, text="Запускать сервер автоматически при входе", 
                                 variable=self.var_autostart, command=self._on_change_autostart,
                                 bg=self.theme["window_bg"], activebackground=self.theme["window_bg"])
        cb_auto.pack(anchor="w", padx=10)

        sync_box = tk.Frame(pad_frame, bg="#d5f5e3", bd=1, relief="solid")
        sync_box.pack(fill="x", pady=10)
        
        self.btn_server = tk.Button(sync_box, text="▶ Запустить Сервер", 
                                    bg=self.theme["btn_save"], fg="white", font=("Arial", 10, "bold"),
                                    command=self._toggle_server)
        self.btn_server.pack(side="left", padx=10, pady=10)

        self.lbl_ip = tk.Label(sync_box, text="Сервер выключен", bg="#d5f5e3", font=("Consolas", 11))
        self.lbl_ip.pack(side="left", padx=10)

        ttk.Separator(pad_frame, orient="horizontal").pack(fill="x", pady=20)

        # --- СЕКЦИЯ 2: ПОВЕДЕНИЕ ---
        lbl_behavior = tk.Label(pad_frame, text="ПОВЕДЕНИЕ", font=("Arial", 12, "bold"), 
                                bg=self.theme["window_bg"], fg=self.theme["text_fg"])
        lbl_behavior.pack(anchor="w", pady=(0, 10))

        self.var_auto_clear = tk.BooleanVar()
        cb_clear = tk.Checkbutton(pad_frame, text="Очищать форму ввода после успешного сохранения", 
                                  variable=self.var_auto_clear, command=self._on_change_clear,
                                  bg=self.theme["window_bg"], activebackground=self.theme["window_bg"])
        cb_clear.pack(anchor="w", padx=10)
        
        ttk.Separator(pad_frame, orient="horizontal").pack(fill="x", pady=20)

        # --- СЕКЦИЯ 3: ИНФО О БД ---
        lbl_db = tk.Label(pad_frame, text="БАЗА ДАННЫХ", font=("Arial", 12, "bold"), 
                          bg=self.theme["window_bg"], fg=self.theme["text_fg"])
        lbl_db.pack(anchor="w", pady=(0, 10))

        f_path = tk.Frame(pad_frame, bg=self.theme["window_bg"])
        f_path.pack(fill="x", padx=10)
        tk.Label(f_path, text="Путь:", font=("Arial", 10, "bold"), bg=self.theme["window_bg"]).pack(side="left")
        self.ent_path = tk.Entry(f_path, width=60, font=("Consolas", 9), fg="gray")
        self.ent_path.insert(0, DB_PATH)
        self.ent_path.config(state="readonly")
        self.ent_path.pack(side="left", padx=10)

        btn_box = tk.Frame(pad_frame, bg=self.theme["window_bg"])
        btn_box.pack(fill="x", padx=10, pady=10)
        tk.Button(btn_box, text="📂 Открыть папку", command=self._open_folder).pack(side="left")

    def _check_server_status(self):
        """Обновляет UI если сервер был запущен извне (автозапуск)"""
        if SyncManager.is_running():
            url = SyncManager._last_url or f"http://{SyncManager.get_local_ip()}:8000"
            self.lbl_ip.config(text=f"Работает: {url}", fg="green")
            self.btn_server.config(text="⏹ Остановить Сервер", bg="#c0392b")
            self.is_server_running = True

    def _toggle_server(self):
        if not self.is_server_running:
            url = SyncManager.start_server()
            self.lbl_ip.config(text=f"Работает: {url}", fg="green")
            self.btn_server.config(text="⏹ Остановить Сервер", bg="#c0392b")
            self.is_server_running = True
        else:
            SyncManager.stop_server()
            self.lbl_ip.config(text="Остановлен", fg="black")
            self.btn_server.config(text="▶ Запустить Сервер", bg=self.theme["btn_save"])
            self.is_server_running = False

    def _load_values(self):
        self.var_auto_clear.set(SettingsManager.get("db", "auto_clear_after_save", False))
        self.var_autostart.set(SettingsManager.get("network", "autostart_server", False))

    def _on_change_clear(self):
        SettingsManager.set("db", "auto_clear_after_save", self.var_auto_clear.get())
        
    def _on_change_autostart(self):
        SettingsManager.set("network", "autostart_server", self.var_autostart.get())

    def _open_folder(self):
        folder = os.path.dirname(DB_PATH)
        try:
            if platform.system() == "Windows": os.startfile(folder)
            elif platform.system() == "Darwin": subprocess.Popen(["open", folder])
            else: subprocess.Popen(["xdg-open", folder])
        except: pass