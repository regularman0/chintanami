import tkinter as tk
from tkinter import ttk
import json

class DebugTab:
    def __init__(self, notebook, theme):
        self.frame = tk.Frame(notebook, bg=theme["window_bg"])
        self.theme = theme
        
        # Используем PanedWindow для разделения экрана по вертикали
        self.paned = tk.PanedWindow(self.frame, orient="vertical", bg=theme["window_bg"], sashwidth=4)
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)

        # --- БЛОК 1: ДАННЫЕ (Event Data) ---
        self.d1_frame = self._create_scrollable_text_block("Файл event_data.json (База)")
        self.paned.add(self.d1_frame, height=400)
        self.text_data = self.d1_frame.text_widget

        # --- БЛОК 2: КОНФИГ (Current Config) ---
        self.d2_frame = self._create_scrollable_text_block("Текущий Config UI (В памяти)")
        self.paned.add(self.d2_frame)
        self.text_config = self.d2_frame.text_widget

    def _create_scrollable_text_block(self, title):
        container = tk.Frame(self.paned, bg="#ecf0f1")
        
        lbl = tk.Label(container, text=title, font=("Arial", 10, "bold"), bg="#ecf0f1")
        lbl.pack(anchor="w")
        
        # Текстовое поле со скроллом
        txt_frame = tk.Frame(container)
        txt_frame.pack(fill="both", expand=True)
        
        scroll = ttk.Scrollbar(txt_frame)
        text = tk.Text(txt_frame, bg="white", font=("Consolas", 9), yscrollcommand=scroll.set)
        scroll.config(command=text.yview)
        
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        
        container.text_widget = text # Сохраняем ссылку
        return container

    def update_data(self, data):
        self.text_data.delete("1.0", tk.END)
        self.text_data.insert("1.0", json.dumps(data, ensure_ascii=False, indent=4))

    def update_config(self, config):
        self.text_config.delete("1.0", tk.END)
        self.text_config.insert("1.0", json.dumps(config, ensure_ascii=False, indent=4))