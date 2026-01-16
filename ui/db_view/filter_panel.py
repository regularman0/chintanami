# Path: ui/db_view/filter_panel.py
# Version: 22.0
# Description: Панель фильтрации.

import tkinter as tk
from tkinter import ttk

class FilterPanel:
    def __init__(self, parent, theme, on_filter_change):
        self.frame = tk.Frame(parent, bg=theme["window_bg"], pady=5)
        self.theme = theme
        self.on_change = on_filter_change # Коллбэк для обновления таблицы
        
        self._setup_ui()
        
    def _setup_ui(self):
        # 1. Период
        tk.Label(self.frame, text="Период:", bg=self.theme["window_bg"]).pack(side="left", padx=5)
        
        self.combo_period = ttk.Combobox(self.frame, state="readonly", width=15)
        self.combo_period["values"] = ["Все время", "Сегодня", "Вчера", "Последние 7 дней"]
        self.combo_period.current(0) # Выбрать "Все время"
        self.combo_period.pack(side="left", padx=5)
        
        self.combo_period.bind("<<ComboboxSelected>>", self._on_input)
        
        # 2. Поиск по категории
        tk.Label(self.frame, text="Поиск (Категория):", bg=self.theme["window_bg"]).pack(side="left", padx=(15, 5))
        
        self.ent_search = tk.Entry(self.frame, width=25)
        self.ent_search.pack(side="left", padx=5)
        self.ent_search.bind("<KeyRelease>", self._on_input) # Живой поиск
        
        # Кнопка сброса
        tk.Button(self.frame, text="Сброс", command=self.reset).pack(side="left", padx=10)

    def _on_input(self, event=None):
        """Собирает фильтры и дергает таблицу"""
        self.on_change(self.get_filters())

    def get_filters(self):
        # Превращаем текст комбобокса в код для БД
        map_period = {
            "Все время": "all",
            "Сегодня": "today",
            "Вчера": "yesterday",
            "Последние 7 дней": "week"
        }
        
        return {
            "period": map_period.get(self.combo_period.get(), "all"),
            "search": self.ent_search.get()
        }

    def reset(self):
        self.combo_period.current(0)
        self.ent_search.delete(0, tk.END)
        self._on_input()