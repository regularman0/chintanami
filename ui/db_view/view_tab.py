# Path: ui/db_view/view_tab.py
# Version: 22.0
# Description: Сборщик вкладки БД. Добавлены Фильтры.

import tkinter as tk
from .table_panel import TablePanel
from .details_panel import DetailsPanel
from .filter_panel import FilterPanel # <--- NEW

class DbViewTab:
    def __init__(self, notebook, theme):
        self.frame = tk.Frame(notebook, bg=theme["window_bg"])
        self.frame.pack(fill="both", expand=True)
        self.theme = theme
        self._setup_layout()
        
    def _setup_layout(self):
        # 1. Top Frame: Filters + View Settings
        self.top_bar = tk.Frame(self.frame, bg=self.theme["window_bg"])
        self.top_bar.pack(fill="x", padx=5, pady=5)
        
        # --- Filters Panel ---
        # Передаем метод таблицы apply_filters как коллбэк
        # (Сначала создадим заглушку, потом переназначим, т.к. таблица еще не создана)
        self.filters = FilterPanel(self.top_bar, self.theme, self._on_filter_update)
        self.filters.frame.pack(side="left")
        
        # --- Right Side Utils ---
        self.var_raw = tk.BooleanVar(value=False)
        tk.Checkbutton(self.top_bar, text="Raw View", variable=self.var_raw, 
                       bg=self.theme["window_bg"], command=self.toggle_view).pack(side="right")
        tk.Button(self.top_bar, text="⟳", command=self.refresh_all).pack(side="right", padx=5)

        # 2. Main Content
        self.paned = tk.PanedWindow(self.frame, orient="horizontal", bg=self.theme["window_bg"], sashwidth=4)
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.left_pane = tk.Frame(self.paned, bg="white"); self.paned.add(self.left_pane, minsize=400, width=800)
        self.right_pane = tk.Frame(self.paned, bg=self.theme["sidebar_bg"]); self.paned.add(self.right_pane, minsize=350)
        
        # 3. Components
        self.details = DetailsPanel(self.right_pane, self.theme, self.refresh_table_only)
        self.table = TablePanel(self.left_pane, self.theme, self.details.load_record)

    def _on_filter_update(self, filter_data):
        self.table.apply_filters(filter_data)

    def toggle_view(self):
        self.table.set_raw_mode(self.var_raw.get())
        
    def refresh_table_only(self):
        self.table.refresh()

    def refresh_all(self):
        self.table.refresh()