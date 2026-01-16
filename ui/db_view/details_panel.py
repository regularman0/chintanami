# Path: ui/db_view/details_panel.py
# Version: 21.1
# Description: Панель редактирования конкретной записи.

import tkinter as tk
from tkinter import ttk, messagebox
from database.query_builder import QueryBuilder

class DetailsPanel:
    def __init__(self, parent, theme, on_change_callback):
        self.frame = tk.Frame(parent, bg=theme["sidebar_bg"])
        # ДОБАВЛЕНО: Теперь фрейм редактора будет виден
        self.frame.pack(fill="both", expand=True)
        
        self.theme = theme
        self.on_change = on_change_callback
        
        self.current_id = None
        self.entries = {}
        
        self._setup_ui()

    def _setup_ui(self):
        # Заголовок
        self.lbl_header = tk.Label(self.frame, text="РЕДАКТИРОВАНИЕ", 
                                   font=("Arial", 10, "bold"), 
                                   bg=self.theme["sidebar_bg"], fg="white")
        self.lbl_header.pack(pady=10, fill="x")

        # Область скролла для полей (их может быть много)
        self.canvas = tk.Canvas(self.frame, bg=self.theme["sidebar_bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=self.theme["sidebar_bg"])
        
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.cw = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.cw, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Нижняя панель кнопок (фиксированная)
        self.btn_frame = tk.Frame(self.frame, bg=self.theme["sidebar_bg"])
        self.btn_frame.pack(side="bottom", fill="x", pady=10, padx=5)
        
        tk.Button(self.btn_frame, text="Удалить", bg="#c0392b", fg="white", 
                  command=self.delete_record).pack(side="left")
        
        tk.Button(self.btn_frame, text="Сохранить", bg=self.theme["btn_save"], fg="white", 
                  command=self.save_changes).pack(side="right")

    def load_record(self, pk):
        """Загружает запись и строит форму"""
        self.current_id = pk
        self.entries = {}
        
        # Очистка
        for w in self.scroll_frame.winfo_children(): w.destroy()
        
        data = QueryBuilder.get_record(pk)
        if not data:
            tk.Label(self.scroll_frame, text="Запись не найдена", bg=self.theme["sidebar_bg"], fg="red").pack()
            return

        self.lbl_header.config(text=f"ID: {pk}")

        # Группируем поля для красоты
        # 1. Системные
        self._add_section_header("System")
        self._add_field("timestamp", data.get("timestamp"), readonly=True)
        self._add_field("session_id", data.get("session_id"), readonly=True)
        
        # 2. Основные
        self._add_section_header("General")
        self._add_field("category_path", data.get("category_path"))
        self._add_field("range_start", data.get("range_start"))
        self._add_field("range_end", data.get("range_end"))
        
        # 3. Динамические (Теги и Чекбоксы)
        self._add_section_header("Data")
        # Сортируем ключи, чтобы T_ и C_ шли по порядку
        for key in sorted(data.keys()):
            if key in ["id", "timestamp", "session_id", "category_path", "range_start", "range_end"]:
                continue
            # Показываем только если есть значение (разреженность), или можно показать все
            # Лучше показывать только заполненные + кнопку "Добавить поле" (в будущем)
            if data[key]:
                self._add_field(key, data[key])

    def _add_section_header(self, text):
        tk.Label(self.scroll_frame, text=f"--- {text} ---", fg="#95a5a6", bg=self.theme["sidebar_bg"]).pack(pady=(10, 2), anchor="w", padx=5)

    def _add_field(self, key, value, readonly=False):
        row = tk.Frame(self.scroll_frame, bg=self.theme["sidebar_bg"])
        row.pack(fill="x", pady=2, padx=5)
        
        # Красивое имя (убираем префиксы визуально)
        display_key = key
        if key.startswith("T_"): display_key = f"Tag: {key[2:]}"
        elif key.startswith("C_"): display_key = f"Check: {key[2:]}"
        
        tk.Label(row, text=display_key, fg="white", bg=self.theme["sidebar_bg"], width=15, anchor="w").pack(side="left")
        
        ent = tk.Entry(row, bg="#34495e", fg="white", insertbackground="white", relief="flat")
        if value is not None:
            ent.insert(0, str(value))
        
        if readonly:
            ent.config(state="readonly", fg="gray")
        else:
            # Сохраняем ссылку только на редактируемые поля
            self.entries[key] = ent
            
        ent.pack(side="right", fill="x", expand=True)

    def save_changes(self):
        if not self.current_id: return
        
        updates = {}
        for key, ent in self.entries.items():
            updates[key] = ent.get()
            
        success = QueryBuilder.update_record(self.current_id, updates)
        if success:
            # Обновляем таблицу (Сводка могла измениться)
            self.on_change()
            # Показываем визуальное подтверждение (мигание заголовка)
            original_bg = self.lbl_header.cget("bg")
            self.lbl_header.config(bg=self.theme["btn_save"])
            self.frame.after(500, lambda: self.lbl_header.config(bg=original_bg))
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить изменения")

    def delete_record(self):
        if not self.current_id: return
        if messagebox.askyesno("Удаление", f"Удалить запись ID {self.current_id}?"):
            success = QueryBuilder.delete_records([self.current_id])
            if success:
                self.on_change() # Обновить таблицу
                # Очистить панель
                for w in self.scroll_frame.winfo_children(): w.destroy()
                self.lbl_header.config(text="Удалено")
                self.current_id = None