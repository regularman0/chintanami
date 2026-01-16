# Path: ui/input/input_tab.py
# Version: 21.0
# Description: Вкладка ввода. Добавлена валидация "Призрачных данных" (данных не из текущего контекста).

import tkinter as tk
from tkinter import ttk
from core import schema, config_gen
from ui.input.generators import InputModuleRenderer

class InputTab:
    def __init__(self, notebook, theme, managers, fas_config, event_data, debug_callback, save_callback=None):
        self.frame = tk.Frame(notebook, bg=theme["window_bg"])
        self.theme = theme
        self.mgrs = managers
        self.fas_config = fas_config
        self.event_data = event_data
        self.debug_cb = debug_callback
        self.save_cb = save_callback

        self.nav_combos = []
        self.widgets = {} 
        
        self.rendered_checkbox_groups = {}
        self.rendered_tag_groups = {}
        
        self.range_mode_var = tk.BooleanVar(value=True)
        self.duration_mode_var = tk.BooleanVar(value=False)
        
        self.renderer = InputModuleRenderer(self, theme, managers, fas_config)

        self._setup_layout()
        self.init_navigation()

    def _setup_layout(self):
        paned = tk.PanedWindow(self.frame, orient="horizontal", bg=self.theme["window_bg"], sashwidth=4)
        paned.pack(fill="both", expand=True)

        # 1. Sidebar
        self.sidebar, self.sidebar_scroll = self._create_scroll_frame(paned, self.theme["sidebar_bg"])
        paned.add(self.sidebar, minsize=250, width=300)
        
        # Header + Delete Button
        sb_head = tk.Frame(self.sidebar_scroll, bg=self.theme["sidebar_bg"])
        sb_head.pack(pady=(15, 10), fill="x", padx=10)
        
        tk.Label(sb_head, text="КАТЕГОРИИ", bg=self.theme["sidebar_bg"], fg="#bdc3c7", font=("Arial", 10, "bold")).pack(side="left")
        tk.Button(sb_head, text="< Назад", fg="red", bg="white", font=("Arial", 8), 
                  command=self._delete_last_category).pack(side="right")

        # 2. Content
        self.content, self.content_scroll = self._create_scroll_frame(paned, self.theme["window_bg"])
        paned.add(self.content, minsize=400)

        # Mode Selector & Action Bar
        self.mode_frame = tk.Frame(self.content_scroll, bg=self.theme["window_bg"], pady=10)
        self.mode_frame.pack(fill="x", padx=10)
        
        tk.Checkbutton(self.mode_frame, text="Range Mode", variable=self.range_mode_var, command=self.set_range_mode, bg=self.theme["window_bg"]).pack(side="left", padx=20)
        tk.Checkbutton(self.mode_frame, text="Duration Mode", variable=self.duration_mode_var, command=self.set_duration_mode, bg=self.theme["window_bg"]).pack(side="left", padx=20)

        if self.save_cb:
            tk.Button(self.mode_frame, text="✔ СОХРАНИТЬ", bg=self.theme["btn_save"], fg="white", 
                      font=("Arial", 10, "bold"), command=self.save_cb).pack(side="right", padx=10)

    def _create_scroll_frame(self, parent, bg):
        outer = tk.Frame(parent, bg=bg)
        cv = tk.Canvas(outer, bg=bg, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
        fr = tk.Frame(cv, bg=bg)
        fr.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        wid = cv.create_window((0,0), window=fr, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfig(wid, width=e.width))
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        return outer, fr

    # ================= GHOST DATA LOGIC =================
    
    def _get_allowed_prefixes(self):
        """Собирает разрешенные префиксы (DB Name) для текущего конфига"""
        cb_prefixes = set()
        tag_prefixes = set()

        # 1. Чекбоксы
        for item in self.current_ui_config.get("checkboxes_module", []):
            db_name = None
            # Если ссылка (list) - ищем реальное имя в глобальном конфиге
            if item.get("list"):
                ref = item["list"]
                global_def = self.fas_config.get("checkboxes_list", {}).get(ref, {})
                db_name = global_def.get("db_name", ref)
            # Если кастом (db_name)
            elif item.get("db_name"):
                db_name = item["db_name"]
            
            if db_name:
                cb_prefixes.add(db_name + "_") # Префикс включает подчеркивание

        # 2. Теги
        for item in self.current_ui_config.get("tags_module", []):
            db_name = None
            if item.get("list"):
                ref = item["list"]
                # Ищем в глобальном tag_lists
                global_def = self.fas_config.get("tag_lists", {}).get(ref)
                if global_def:
                    db_name = global_def.get("db_name", ref.upper())
                else:
                    # Если нет в глобальном (кастомный тег-лист), считаем сам ключ именем
                    db_name = ref.upper()
            
            if db_name:
                tag_prefixes.add(db_name + "_")

        return cb_prefixes, tag_prefixes

    def _detect_ghosts(self):
        ghosts = []
        cb_pref, tag_pref = self._get_allowed_prefixes()

        # Проверяем записанные чекбоксы
        for cb in self.event_data.get("checkboxes", []):
            name = cb.get("db_name", "")
            if not any(name.startswith(p) for p in cb_pref):
                ghosts.append(f"Checkbox: {name}")

        # Проверяем записанные теги
        for tag in self.event_data.get("tags", []):
            name = tag.get("db_name", "")
            if not any(name.startswith(p) for p in tag_pref):
                ghosts.append(f"Tag: {name}")
                
        return ghosts

    def _clean_ghosts(self):
        cb_pref, tag_pref = self._get_allowed_prefixes()

        # Фильтрация
        self.event_data["checkboxes"] = [
            x for x in self.event_data["checkboxes"] 
            if any(x["db_name"].startswith(p) for p in cb_pref)
        ]
        
        self.event_data["tags"] = [
            x for x in self.event_data["tags"] 
            if any(x["db_name"].startswith(p) for p in tag_pref)
        ]
        
        # Сохраняем чистый файл через любой менеджер
        self.mgrs["path"]._save()
        
        # Перерисовываем (панель ошибки исчезнет)
        self.render_dynamic_content()


    # ================= NAVIGATION =================
    
    def _delete_last_category(self):
        if not self.nav_combos: return
        if len(self.nav_combos) == 1:
            self.nav_combos[0].set("")
        else:
            last = self.nav_combos.pop()
            last.destroy()
        path = [c.get() for c in self.nav_combos if c.get()]
        self.mgrs["path"].set_path(path)
        self.render_dynamic_content()

    def on_nav_select(self, event):
        combo = event.widget
        try: idx = self.nav_combos.index(combo)
        except ValueError: return
        while len(self.nav_combos) > idx + 1:
            self.nav_combos.pop().destroy()

        path = [c.get() for c in self.nav_combos if c.get()]
        self.mgrs["path"].set_path(path)
        
        self.render_dynamic_content()
        
        nxt = config_gen.get_next_children(self.fas_config, path)
        if nxt: self._create_nav_combo(list(nxt.keys()))

    def _create_nav_combo(self, values, selected=None):
        cb = ttk.Combobox(self.sidebar_scroll, values=values, state="readonly")
        cb.pack(fill="x", padx=15, pady=2)
        cb.bind("<<ComboboxSelected>>", self.on_nav_select)
        self.nav_combos.append(cb)
        if selected and selected in values: cb.set(selected)

    def init_navigation(self):
        for w in self.nav_combos: w.destroy()
        self.nav_combos.clear()
        
        raw_path = self.mgrs["path"].get_path()
        valid_path = self._validate_path(raw_path)
        
        # Если путь был невалиден (обрезан), сохраняем исправленный
        if len(valid_path) != len(raw_path):
             self.mgrs["path"].set_path(valid_path)

        root = self.fas_config.get("category", {}).get("main", {}).get("children", {})
        self._create_nav_combo(list(root.keys()), valid_path[0] if valid_path else None)
        
        cursor = root
        for i in range(len(valid_path)):
            step = valid_path[i]
            if step in cursor:
                cursor = cursor[step].get("children", {})
                if not cursor: break
                nxt = valid_path[i+1] if i+1 < len(valid_path) else None
                self._create_nav_combo(list(cursor.keys()), nxt)
            else: break
        
        self.render_dynamic_content()

    def _validate_path(self, path):
        cursor = self.fas_config.get("category", {}).get("main", {}).get("children", {})
        res = []
        for p in path:
            if p in cursor:
                res.append(p)
                cursor = cursor[p].get("children", {})
            else:
                break
        return res

    # ================= RENDER =================
    
    def render_dynamic_content(self):
        # Save range values
        if "or_entry" in self.widgets and self.widgets["or_entry"].winfo_exists():
            self.mgrs["range"].set_values(self.widgets["or_entry"].get(), self.widgets["end_entry"].get())
            
        # Clear content
        for w in self.content_scroll.winfo_children():
            if w != self.mode_frame: w.destroy()
            
        self.rendered_checkbox_groups = {}
        self.rendered_tag_groups = {}
        self.widgets = {} 
        
        # Config
        path = self.mgrs["path"].get_path()
        self.current_ui_config = config_gen.resolve_config(self.fas_config, path)
        self.debug_cb(self.current_ui_config)
        
        # --- GHOST CHECK ---
        ghosts = self._detect_ghosts()
        if ghosts:
            warn_f = tk.Frame(self.content_scroll, bg=self.theme["ghost_warning"], padx=10, pady=5)
            warn_f.pack(fill="x", pady=(0, 10))
            
            msg = f"⚠ Найдено {len(ghosts)} записей не из этой категории!"
            tk.Label(warn_f, text=msg, bg=self.theme["ghost_warning"], fg="white", font=("Arial", 10, "bold")).pack(side="left")
            
            tk.Button(warn_f, text="Очистить мусор", bg="white", fg=self.theme["ghost_warning"], 
                      command=self._clean_ghosts).pack(side="right")
        # -------------------

        # Draw Modules
        active = self.current_ui_config.get("active_modules", [])
        if "range" in active: 
            self.renderer.draw_range(self.content_scroll, self.current_ui_config.get("range_module", {}))
        
        if "duration" in active:
            self.renderer.draw_duration(self.content_scroll, self.current_ui_config.get("duration_module", {}))
            
        if "checkboxes" in active:
            self.renderer.draw_checks(self.content_scroll, self.current_ui_config.get("checkboxes_module", []))
            
        if "tags" in active:
            self.renderer.draw_tags(self.content_scroll, self.current_ui_config.get("tags_module", []))
            
        self.toggle_mode_ui()

    def set_range_mode(self): 
        self.range_mode_var.set(True); self.duration_mode_var.set(False); self.toggle_mode_ui()
    def set_duration_mode(self): 
        self.duration_mode_var.set(True); self.range_mode_var.set(False); self.toggle_mode_ui()

    def toggle_mode_ui(self):
        is_dur = self.duration_mode_var.get()
        if "range_btns" in self.widgets:
            s = "disabled" if is_dur else "normal"
            for b in self.widgets["range_btns"]: b.config(state=s)
        if "dur_step" in self.widgets:
            s = "readonly" if is_dur else "disabled"
            self.widgets["dur_step"].config(state=s)
            self.widgets["dur_val"].config(state=s)
            self.widgets["dur_btn"].config(state="normal" if is_dur else "disabled")