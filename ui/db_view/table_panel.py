# Path: ui/db_view/table_panel.py
# Version: 22.0
# Description: Таблица с поддержкой сортировки и внешних фильтров.

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from database.query_builder import QueryBuilder
from core import schema

PAGE_SIZE = 100

class TablePanel:
    def __init__(self, parent, theme, on_select_callback):
        self.frame = tk.Frame(parent, bg=theme["window_bg"])
        self.frame.pack(fill="both", expand=True) # Важно: Pack
        self.theme = theme
        self.on_select = on_select_callback
        
        self.current_offset = 0
        self.is_raw_mode = False
        
        # Параметры сортировки и фильтрации
        self.sort_col = "id"
        self.sort_desc = True
        self.active_filters = {}
        
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        self.tree_container = tk.Frame(self.frame)
        self.tree_container.pack(fill="both", expand=True)

        self.vsb = ttk.Scrollbar(self.tree_container, orient="vertical")
        self.hsb = ttk.Scrollbar(self.tree_container, orient="horizontal")

        self.tree = ttk.Treeview(self.tree_container, selectmode="browse",
                                 yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        self.vsb.config(command=self.tree.yview); self.vsb.pack(side="right", fill="y")
        self.hsb.config(command=self.tree.xview); self.hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

        # Pagination
        self.pag_frame = tk.Frame(self.frame, bg=self.theme["window_bg"], pady=5)
        self.pag_frame.pack(fill="x", side="bottom")
        tk.Button(self.pag_frame, text="<<", command=self.prev_page).pack(side="left", padx=5)
        self.lbl_page = tk.Label(self.pag_frame, text="1", bg=self.theme["window_bg"])
        self.lbl_page.pack(side="left", padx=5)
        tk.Button(self.pag_frame, text=">>", command=self.next_page).pack(side="left", padx=5)

    def apply_filters(self, filters):
        """Вызывается из FilterPanel"""
        self.active_filters = filters
        self.current_offset = 0 # Сброс на 1 страницу
        self.refresh()

    def sort_by(self, col):
        """Обработчик клика по заголовку"""
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc # Инверсия
        else:
            self.sort_col = col
            self.sort_desc = True # По умолчанию новые DESC
            
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        
        # Настройка колонок
        if self.is_raw_mode: self._setup_columns_raw()
        else: self._setup_columns_summary()

        # Запрос с фильтрами
        rows = QueryBuilder.fetch_data(
            offset=self.current_offset, 
            limit=PAGE_SIZE,
            sort_col=self.sort_col,
            sort_desc=self.sort_desc,
            filters=self.active_filters
        )
        
        for row in rows:
            values = self._process_row(row)
            self.tree.insert("", "end", iid=row["id"], values=values)
            
        self.lbl_page.config(text=f"Стр. {(self.current_offset // PAGE_SIZE) + 1}")

    def _setup_columns_summary(self):
        # Определение колонок и их заголовков
        cols_map = {
            "ID": "id",
            "Date": "timestamp",
            "Duration": "range_start", # Технически сортируем по началу
            "Category": "category_path",
            "Summary": None # Не сортируется в SQL (сложно)
        }
        
        self.tree.config(columns=list(cols_map.keys()), show="headings")
        
        for col_name, db_field in cols_map.items():
            # Добавляем стрелочку, если это текущая колонка сортировки
            arrow = ""
            if db_field == self.sort_col:
                arrow = " ▼" if self.sort_desc else " ▲"
            
            # Назначаем команду клика
            # lambda c=db_field: ... нужен для замыкания значения
            if db_field:
                self.tree.heading(col_name, text=col_name + arrow, command=lambda c=db_field: self.sort_by(c))
            else:
                self.tree.heading(col_name, text=col_name) # Без сортировки

            # Ширина
            width = 50 if col_name == "ID" else (120 if col_name == "Date" else (300 if col_name=="Summary" else 150))
            self.tree.column(col_name, width=width)

    def _setup_columns_raw(self):
        db_cols = QueryBuilder.get_columns()
        self.tree.config(columns=db_cols, show="headings")
        for c in db_cols:
            arrow = ""
            if c == self.sort_col: arrow = " ▼" if self.sort_desc else " ▲"
            self.tree.heading(c, text=c + arrow, command=lambda x=c: self.sort_by(x))
            self.tree.column(c, width=100)

    def _process_row(self, row):
        if self.is_raw_mode:
            return [row[c] for c in QueryBuilder.get_columns()]
        
        # Summary Formatting
        ts = row.get("timestamp", "")
        # Remove seconds visually
        if len(ts) > 16: ts = ts[:16]
        
        s_str = row.get("range_start", "")
        e_str = row.get("range_end", "")
        dur_str = "-"
        if s_str and e_str:
            try:
                # Пытаемся распарсить новый формат
                s = datetime.strptime(s_str, schema.DT_FMT)
                e = datetime.strptime(e_str, schema.DT_FMT)
                diff = (e - s).total_seconds() / 60
                dur_str = f"{int(diff)} min"
            except: pass

        return (row["id"], ts, dur_str, row.get("category_path", ""), QueryBuilder.generate_summary(row))

    def set_raw_mode(self, val):
        self.is_raw_mode = val
        self.refresh()
    
    def _on_row_select(self, e):
        s = self.tree.selection()
        if s and self.on_select: self.on_select(s[0])
    
    def next_page(self): self.current_offset += PAGE_SIZE; self.refresh()
    def prev_page(self): 
        if self.current_offset >= PAGE_SIZE: self.current_offset -= PAGE_SIZE; self.refresh()