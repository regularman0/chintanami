# Path: ui/editor/renders.py
# Version: 19.0
# Description: Рендер редактора. Исправлено: Глобальные чекбоксы теперь сохраняются в поле 'list', кастомные в 'db_name'.

import tkinter as tk
from tkinter import ttk

class ModuleRenderer:
    def __init__(self, editor_ref, theme, fas_data):
        self.editor = editor_ref
        self.theme = theme
        self.fas_data = fas_data

    # ================= RANGE =================
    def render_range(self, frame, conf):
        frame.vars = {}
        tk.Label(frame, text="Steps (s,s,s):", bg=self.theme["range_bg"]).pack(side="left")
        sv = tk.Entry(frame, width=12); sv.pack(side="left", padx=5)
        sv.insert(0, ",".join(map(str, conf.get("step_options", [5, 60, 5]))))
        frame.vars["step"] = sv
        
        tk.Label(frame, text="Default:", bg=self.theme["range_bg"]).pack(side="left")
        dv = tk.Entry(frame, width=6); dv.pack(side="left", padx=5)
        dv.insert(0, str(conf.get("defaults", {}).get("value", 15)))
        frame.vars["def"] = dv
        
        for e in [sv, dv]: e.bind("<KeyRelease>", lambda e: self.editor.update_preview())

    # ================= DURATION =================
    def render_duration(self, frame, conf):
        frame.vars = {}
        tk.Label(frame, text="Steps (s,s,s):", bg=self.theme["duration_bg"]).pack(side="left")
        sv = tk.Entry(frame, width=12); sv.pack(side="left", padx=5)
        sv.insert(0, ",".join(map(str, conf.get("step_options", [5, 125, 5]))))
        frame.vars["step"] = sv
        
        tk.Label(frame, text="Default:", bg=self.theme["duration_bg"]).pack(side="left")
        dv = tk.Entry(frame, width=6); dv.pack(side="left", padx=5)
        dv.insert(0, str(conf.get("defaults", {}).get("value", 30)))
        frame.vars["def"] = dv
        
        sv.bind("<KeyRelease>", lambda e: self.editor.update_preview())
        dv.bind("<KeyRelease>", lambda e: self.editor.update_preview())

    # ================= LISTS (Entry Point) =================
    def render_checkboxes(self, frame, conf_list):
        self._render_list_module(frame, conf_list, "checkboxes")

    def render_tags(self, frame, conf_list):
        self._render_list_module(frame, conf_list, "tags")

    def _render_list_module(self, frame, conf_list, list_type):
        frame.rows = []
        bg_color = self.theme["check_bg"] if list_type == "checkboxes" else self.theme["tags_bg"]
        
        # Кнопки
        btn_box = tk.Frame(frame, bg=bg_color)
        btn_box.pack(anchor="w", fill="x", pady=2)
        btn_txt = "+ Checkbox" if list_type == "checkboxes" else "+ Tag"
        
        tk.Button(btn_box, text=btn_txt, command=lambda: self._add_row(frame, list_type, None, bg_color)).pack(side="left")
        tk.Button(btn_box, text="Delete Last", fg="red", command=lambda: self._rem_last_row(frame)).pack(side="left", padx=5)

        for item in conf_list:
            # Определение Custom или Global
            is_c = False
            
            # Для обоих типов: если нет ключа 'list' или он не найден в глобальном словаре -> это Custom
            # (Для старых записей проверяем db_name, но приоритет у list)
            ref_key = item.get("list")
            
            if list_type == "checkboxes":
                # Если list не задан, проверяем db_name (legacy)
                if not ref_key: ref_key = item.get("db_name")
                
                if ref_key and ref_key in self.fas_data.get("checkboxes_list", {}):
                    is_c = False # Это ссылка
                else:
                    is_c = True  # Это кастом
            else:
                # Tags
                if ref_key and ref_key in self.fas_data.get("tag_lists", {}):
                    is_c = False
                else:
                    is_c = True
            
            item["__custom__"] = is_c
            self._add_row(frame, list_type, item, bg_color)

    def _rem_last_row(self, frame):
        if frame.rows:
            last = frame.rows.pop()
            last["row_widget"].destroy()
            self.editor.update_preview()

    def _add_row(self, frame, list_type, data=None, bg="white"):
        if data is None: 
            # Дефолтные данные
            data = {"number": 1, "add": False, "__custom__": False}
            # Пустые поля, чтобы не было KeyError при get()
            if list_type == "checkboxes": data.update({"label_name": "", "db_name": "", "list": ""})
            else: data.update({"list": "", "label_name": "", "db_name": ""})
        
        row = tk.Frame(frame, bg=bg); row.pack(fill="x", pady=2)
        v_custom = tk.BooleanVar(value=data.get("__custom__", False))
        inp_frame = tk.Frame(row, bg=bg); inp_frame.pack(side="left", fill="x", expand=True)
        
        widgets = {}

        def redraw(*args):
            # 1. Спасение данных из текущих виджетов (чтобы не терять при переключении карандаша)
            saved_vals = {}
            # Пытаемся сохранить универсальный 'key_val', который может быть и в db_val, и в list_val
            if "db_val" in widgets: 
                try: saved_vals["key"] = widgets["db_val"].get()
                except: pass
            if "list_val" in widgets: 
                try: saved_vals["key"] = widgets["list_val"].get()
                except: pass
            if "lbl_val" in widgets: 
                try: saved_vals["label"] = widgets["lbl_val"].get()
                except: pass
            
            # 2. Очистка
            for w in inp_frame.winfo_children(): w.destroy()
            widgets.clear()
            
            is_c = v_custom.get()
            
            # Определяем текущее значение ключа (из сохраненного или из data)
            # Приоритет: Saved UI -> Data List -> Data DB Name
            current_key_val = saved_vals.get("key") or data.get("list") or data.get("db_name", "")
            current_lbl_val = saved_vals.get("label") or data.get("label_name", "")

            # 3. Отрисовка
            if list_type == "checkboxes":
                if not is_c:
                    # --- GLOBAL CHECKBOX (list) ---
                    keys = list(self.fas_data.get("checkboxes_list", {}).keys())
                    tk.Label(inp_frame, text="Ref Key:", bg=bg).pack(side="left")
                    cb = ttk.Combobox(inp_frame, values=keys, width=14, state="readonly")
                    cb.pack(side="left", padx=2)
                    cb.set(current_key_val)
                    widgets["db_val"] = cb # Используем то же имя переменной для унификации get_data
                    
                    lbl_p = tk.Label(inp_frame, text="", fg="gray", bg=bg); lbl_p.pack(side="left")
                    
                    def sel(e):
                        k = widgets["db_val"].get()
                        if k in self.fas_data.get("checkboxes_list", {}):
                            lbl_p.config(text=self.fas_data["checkboxes_list"][k]["label_name"])
                        self.editor.update_preview()
                    
                    widgets["db_val"].bind("<<ComboboxSelected>>", sel)
                    # Init label
                    if current_key_val in self.fas_data.get("checkboxes_list", {}):
                         lbl_p.config(text=self.fas_data["checkboxes_list"][current_key_val]["label_name"])
                else:
                    # --- CUSTOM CHECKBOX ---
                    tk.Label(inp_frame, text="DB:", bg=bg).pack(side="left")
                    w_db = tk.Entry(inp_frame, width=10); w_db.pack(side="left")
                    w_db.insert(0, current_key_val)
                    widgets["db_val"] = w_db
                    
                    tk.Label(inp_frame, text="Lbl:", bg=bg).pack(side="left")
                    w_lb = tk.Entry(inp_frame, width=12); w_lb.pack(side="left")
                    w_lb.insert(0, current_lbl_val)
                    widgets["lbl_val"] = w_lb
                    
                    w_db.bind("<KeyRelease>", lambda e: self.editor.update_preview())
                    w_lb.bind("<KeyRelease>", lambda e: self.editor.update_preview())
            else:
                # --- TAGS ---
                if not is_c:
                    # GLOBAL TAG
                    keys = list(self.fas_data.get("tag_lists", {}).keys())
                    tk.Label(inp_frame, text="List:", bg=bg).pack(side="left")
                    cb = ttk.Combobox(inp_frame, values=keys, width=14, state="readonly")
                    cb.pack(side="left", padx=2)
                    cb.set(current_key_val)
                    widgets["list_val"] = cb
                    cb.bind("<<ComboboxSelected>>", lambda e: self.editor.update_preview())
                else:
                    # CUSTOM TAG
                    tk.Label(inp_frame, text="Key:", bg=bg).pack(side="left")
                    el = tk.Entry(inp_frame, width=10); el.pack(side="left")
                    el.insert(0, current_key_val)
                    widgets["list_val"] = el
                    
                    tk.Label(inp_frame, text="Lbl:", bg=bg).pack(side="left")
                    elb = tk.Entry(inp_frame, width=10); elb.pack(side="left")
                    elb.insert(0, current_lbl_val)
                    widgets["lbl_val"] = elb

                    el.bind("<KeyRelease>", lambda e: self.editor.update_preview())
                    elb.bind("<KeyRelease>", lambda e: self.editor.update_preview())

            # --- COMMON ---
            tk.Label(inp_frame, text="#:", bg=bg).pack(side="left", padx=(5,0))
            en = tk.Entry(inp_frame, width=3); en.pack(side="left", padx=2)
            en.insert(0, str(data.get("number", 1)))
            widgets["num"] = en
            en.bind("<KeyRelease>", lambda e: self.editor.update_preview())
            
            va = tk.BooleanVar(value=data.get("add", False))
            tk.Checkbutton(inp_frame, text="Add", variable=va, bg=bg, padx=5, pady=5, 
                           command=self.editor.update_preview).pack(side="left", padx=5)
            widgets["add"] = va

        redraw()
        
        tk.Checkbutton(row, text="✏", variable=v_custom, command=lambda: [redraw(), self.editor.update_preview()], bg=bg).pack(side="left")
        tk.Button(row, text="X", fg="red", command=lambda: [row.destroy(), frame.rows.remove(row_obj), self.editor.update_preview()]).pack(side="right")
        
        row_obj = {"widgets": widgets, "v_custom": v_custom, "row_widget": row}
        frame.rows.append(row_obj)

    def get_data(self, frame, list_type):
        """
        Сбор данных.
        ИСПРАВЛЕНО: Для глобальных чекбоксов используем ключ 'list'.
        """
        res = []
        if not hasattr(frame, 'rows'): return res
        
        for r in frame.rows:
            w = r["widgets"]
            is_cust = r["v_custom"].get()
            
            try: num_val = int(w["num"].get())
            except: num_val = 1
                
            item = {"number": num_val, "add": w["add"].get()}
            
            if list_type == "checkboxes":
                # 'db_val' хранит значение ключа (из комбобокса или энтри)
                val = w["db_val"].get()
                
                if not is_cust:
                    # Global -> list
                    item["list"] = val
                else:
                    # Custom -> db_name + label_name
                    item["db_name"] = val
                    item["label_name"] = w["lbl_val"].get()
            else:
                # Tags -> всегда list (но для кастомных это работает как ID)
                val = w["list_val"].get()
                item["list"] = val
                if is_cust:
                    # Для кастомных тегов сохраняем доп поля, чтобы потом восстановить
                    item["db_name"] = val # дублируем для надежности
                    item["label_name"] = w["lbl_val"].get()
            
            # Валидация (ключ должен быть заполнен)
            key_check = item.get("list") or item.get("db_name")
            if key_check:
                res.append(item)
                
        return res