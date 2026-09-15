# Path: analyzer.py
# Version: 3.0 (Ultimate Dashboard Edition)
# Description: Календарь, Планировщик, Аналитика, Мини-календарь и Темная тема.

import os
import sqlite3
import json
import uuid
import hashlib
import colorsys
import math
from datetime import datetime, date, time, timedelta
import calendar
import tkinter as tk
from tkinter import ttk, messagebox

# =========================== КОНФИГУРАЦИЯ ===========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
os.makedirs(CONFIG_DIR, exist_ok=True)

DB_PATH = os.path.join(CONFIG_DIR, "events_storage.db")
PLANS_PATH = os.path.join(CONFIG_DIR, "planned_events.json")

DT_FMT = "%d.%m.%Y %H:%M"
ISO_FMT = "%Y-%m-%dT%H:%M:%S"

HOUR_HEIGHT = 60
TIME_COL_WIDTH = 60
MIN_EVENT_HEIGHT = 15

WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTH_NAMES = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

# --- ТЕМЫ ОФОРМЛЕНИЯ ---
LIGHT_THEME = {
    "name": "light", "bg_main": "#f8f9fa", "bg_panel": "#ffffff", "bg_canvas": "#ffffff",
    "grid_hour": "#e9ecef", "grid_half": "#f1f3f5", "text_main": "#212529",
    "text_muted": "#6c757d", "accent": "#1a73e8", "accent_light": "#e8f0fe",
    "red_line": "#ea4335", "border": "#dee2e6", "selection": "#bbdefb",
    "plan_alpha": "", "chart_bg": "#f8f9fa"
}

DARK_THEME = {
    "name": "dark", "bg_main": "#121212", "bg_panel": "#1e1e1e", "bg_canvas": "#121212",
    "grid_hour": "#333333", "grid_half": "#222222", "text_main": "#e0e0e0",
    "text_muted": "#888888", "accent": "#8ab4f8", "accent_light": "#3b4043",
    "red_line": "#f28b82", "border": "#3c4043", "selection": "#174ea6",
    "plan_alpha": "", "chart_bg": "#1e1e1e"
}


# =========================== ЯДРО И ДАННЫЕ ===========================

def parse_dt(dt_str):
    if not dt_str: return None
    try: return datetime.strptime(dt_str.strip(), DT_FMT)
    except:
        try: return datetime.strptime(dt_str.strip(), "%d.%m.%Y %H:%M:%S")
        except: return None

def generate_pastel_color(text_seed, is_dark=False):
    """Цвета для категорий. Подстраиваются под темную тему."""
    hash_digest = hashlib.md5((text_seed or "default").encode("utf-8")).hexdigest()
    hue = (int(hash_digest[:4], 16) % 360) / 360.0
    
    if is_dark:
        bg = colorsys.hls_to_rgb(hue, 0.25, 0.4)
        border = colorsys.hls_to_rgb(hue, 0.4, 0.6)
        text = colorsys.hls_to_rgb(hue, 0.8, 0.8)
    else:
        bg = colorsys.hls_to_rgb(hue, 0.88, 0.45)
        border = colorsys.hls_to_rgb(hue, 0.65, 0.60)
        text = colorsys.hls_to_rgb(hue, 0.22, 0.70)

    to_hex = lambda rgb: f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
    return to_hex(bg), to_hex(border), to_hex(text)

class EventObj:
    def __init__(self, e_id, title, start_dt, end_dt, e_type="fact", raw=None):
        self.id = e_id
        self.title = title
        self.start = start_dt
        self.end = end_dt
        self.type = e_type # 'fact' или 'plan'
        self.raw = raw or {}
        
        # Для отрисовки
        self.lane_index = 0
        self.total_lanes = 1

class DataManager:
    def __init__(self):
        self.ensure_db()
        self.ensure_json()

    def ensure_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY, session_id TEXT, timestamp TEXT, updated_at TEXT,
                    is_deleted INTEGER DEFAULT 0, category_path TEXT, range_start TEXT, range_end TEXT
                )
            """)

    def ensure_json(self):
        if not os.path.exists(PLANS_PATH):
            with open(PLANS_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)

    def load_events(self, start_date, end_date, show_facts=True, show_plans=True):
        events = []
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        # 1. Загрузка Фактов (SQLite)
        if show_facts:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute("SELECT * FROM events WHERE (is_deleted = 0 OR is_deleted IS NULL)").fetchall()
                    for r in rows:
                        s = parse_dt(r["range_start"])
                        e = parse_dt(r["range_end"])
                        if s and e and s <= end_dt and e >= start_dt:
                            if e < s: s, e = e, s
                            events.append(EventObj(r["id"], r["category_path"], s, e, "fact", dict(r)))
            except Exception as ex:
                print(f"DB Load Error: {ex}")

        # 2. Загрузка Планов (JSON)
        if show_plans:
            try:
                with open(PLANS_PATH, "r", encoding="utf-8") as f:
                    plans = json.load(f)
                    for p in plans:
                        s = parse_dt(p.get("start"))
                        e = parse_dt(p.get("end"))
                        if s and e and s <= end_dt and e >= start_dt:
                            if e < s: s, e = e, s
                            events.append(EventObj(p["id"], p.get("category"), s, e, "plan", p))
            except Exception as ex:
                print(f"JSON Load Error: {ex}")

        return events

    def add_plan(self, title, start_str, end_str):
        plans = []
        if os.path.exists(PLANS_PATH):
            with open(PLANS_PATH, "r", encoding="utf-8") as f: plans = json.load(f)
        plans.append({"id": str(uuid.uuid4()), "category": title, "start": start_str, "end": end_str})
        with open(PLANS_PATH, "w", encoding="utf-8") as f: json.dump(plans, f, ensure_ascii=False, indent=2)

    def add_fact(self, title, start_str, end_str):
        new_id = str(uuid.uuid4())
        now_ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        now_iso = datetime.now().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO events (id, session_id, timestamp, updated_at, is_deleted, category_path, range_start, range_end)
                VALUES (?, 'ANALYZER', ?, ?, 0, ?, ?, ?)
            """, (new_id, now_ts, now_iso, title, start_str, end_str))

    def turn_plan_to_fact(self, plan_id):
        plans = []
        target = None
        with open(PLANS_PATH, "r", encoding="utf-8") as f: plans = json.load(f)
        
        new_plans = []
        for p in plans:
            if p["id"] == plan_id: target = p
            else: new_plans.append(p)
            
        if target:
            with open(PLANS_PATH, "w", encoding="utf-8") as f: json.dump(new_plans, f, ensure_ascii=False, indent=2)
            self.add_fact(target["category"], target["start"], target["end"])
            return True
        return False


# =========================== КОМПОНЕНТЫ ===========================

class QuickAddDialog(tk.Toplevel):
    """Google-style Pop-up для быстрого создания события."""
    def __init__(self, parent, x, y, start_dt, end_dt, on_save):
        super().__init__(parent)
        self.overrideredirect(True) # Без рамок ОС
        self.geometry(f"300x220+{x}+{y}")
        self.configure(bg="#ffffff", highlightthickness=1, highlightbackground="#ccc")
        self.on_save = on_save
        self.start_dt = start_dt
        self.end_dt = end_dt

        # Фокус и закрытие по клику вне окна
        self.focus_force()
        self.bind("<FocusOut>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())

        pad = {"padx": 15, "pady": 5}
        
        # Header
        tk.Label(self, text="Новое событие", font=("Segoe UI", 12, "bold"), bg="#ffffff").pack(anchor="w", **pad, pady=(15,5))
        
        # Название / Категория
        self.ent_title = ttk.Entry(self, font=("Segoe UI", 10))
        self.ent_title.pack(fill="x", **pad)
        self.ent_title.insert(0, "Новая задача")
        self.ent_title.focus()

        # Время
        time_str = f"{start_dt.strftime('%d.%m %H:%M')}  —  {end_dt.strftime('%H:%M')}"
        tk.Label(self, text=time_str, font=("Segoe UI", 9), fg="#666", bg="#ffffff").pack(anchor="w", **pad)

        # Тип (План / Факт)
        self.var_type = tk.StringVar(value="plan")
        f_radio = tk.Frame(self, bg="#ffffff")
        f_radio.pack(fill="x", **pad)
        tk.Radiobutton(f_radio, text="В План", variable=self.var_type, value="plan", bg="#ffffff").pack(side="left")
        tk.Radiobutton(f_radio, text="В Факт (Логгер)", variable=self.var_type, value="fact", bg="#ffffff").pack(side="left")

        # Кнопки
        f_btn = tk.Frame(self, bg="#ffffff")
        f_btn.pack(fill="x", side="bottom", pady=15, padx=15)
        tk.Button(f_btn, text="Сохранить", bg="#1a73e8", fg="white", relief="flat", command=self.save).pack(side="right", padx=(10,0))
        tk.Button(f_btn, text="Отмена", bg="#f1f3f4", relief="flat", command=self.destroy).pack(side="right")

    def save(self):
        title = self.ent_title.get().strip() or "Без названия"
        e_type = self.var_type.get()
        self.on_save(title, self.start_dt.strftime(DT_FMT), self.end_dt.strftime(DT_FMT), e_type)
        self.destroy()

class MiniCalendar(tk.Canvas):
    """Интерактивный мини-календарь с поддержкой drag-to-select."""
    def __init__(self, parent, theme, on_range_select):
        super().__init__(parent, bg=theme["bg_panel"], highlightthickness=0, height=220)
        self.theme = theme
        self.on_range_select = on_range_select
        
        self.current_date = date.today()
        self.view_year = self.current_date.year
        self.view_month = self.current_date.month
        
        self.sel_start = None
        self.sel_end = None
        
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        
        self.draw()

    def update_theme(self, theme):
        self.theme = theme
        self.config(bg=theme["bg_panel"])
        self.draw()

    def change_month(self, delta):
        m = self.view_month + delta
        y = self.view_year
        if m > 12: m = 1; y += 1
        elif m < 1: m = 12; y -= 1
        self.view_month = m
        self.view_year = y
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width() or 220, 220
        cw = w / 7
        rh = 25
        
        # Header (Месяц Год + стрелки)
        title = f"{MONTH_NAMES[self.view_month]} {self.view_year}"
        self.create_text(w/2, 15, text=title, fill=self.theme["text_main"], font=("Segoe UI", 10, "bold"))
        
        # Невидимые кнопки-стрелки (через координаты клика)
        self.create_text(20, 15, text="<", fill=self.theme["text_muted"], font=("Segoe UI", 12, "bold"), tags="btn_prev")
        self.create_text(w-20, 15, text=">", fill=self.theme["text_muted"], font=("Segoe UI", 12, "bold"), tags="btn_next")

        # Дни недели
        for i, d in enumerate(WEEKDAY_NAMES):
            self.create_text(i*cw + cw/2, 40, text=d, fill=self.theme["text_muted"], font=("Segoe UI", 8))

        # Сетка дней
        cal = calendar.Calendar(firstweekday=0)
        days = list(cal.itermonthdates(self.view_year, self.view_month))
        
        self.day_boxes = [] # Сохраняем геометрию для кликов
        
        for row in range(6):
            for col in range(7):
                idx = row * 7 + col
                if idx >= len(days): break
                d = days[idx]
                
                x1, y1 = col * cw, 55 + row * rh
                x2, y2 = x1 + cw, y1 + rh
                cx, cy = (x1+x2)/2, (y1+y2)/2
                
                is_cur_month = (d.month == self.view_month)
                is_today = (d == self.current_date)
                
                # Подсветка выделения
                is_selected = False
                if self.sel_start and self.sel_end:
                    s, e = min(self.sel_start, self.sel_end), max(self.sel_start, self.sel_end)
                    if s <= d <= e: is_selected = True

                if is_selected:
                    self.create_rectangle(x1, y1+2, x2, y2-2, fill=self.theme["selection"], outline="")
                
                # Кружок для Сегодня
                if is_today:
                    r = 10
                    self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=self.theme["accent"], outline="")
                    t_color = "#ffffff"
                else:
                    t_color = self.theme["text_main"] if is_cur_month else self.theme["text_muted"]

                self.create_text(cx, cy, text=str(d.day), fill=t_color, font=("Segoe UI", 9, "bold" if is_today else "normal"))
                self.day_boxes.append((x1, y1, x2, y2, d))

    def _get_day_at(self, x, y):
        # Проверка стрелок
        if y < 30:
            if x < 40: return "prev"
            if x > self.winfo_width() - 40: return "next"
        # Проверка сетки
        for x1, y1, x2, y2, d in self.day_boxes:
            if x1 <= x <= x2 and y1 <= y <= y2: return d
        return None

    def on_press(self, e):
        res = self._get_day_at(e.x, e.y)
        if res == "prev": self.change_month(-1)
        elif res == "next": self.change_month(1)
        elif isinstance(res, date):
            self.sel_start = res
            self.sel_end = res
            self.draw()

    def on_drag(self, e):
        if not self.sel_start: return
        res = self._get_day_at(e.x, e.y)
        if isinstance(res, date) and res != self.sel_end:
            self.sel_end = res
            self.draw()

    def on_release(self, e):
        if self.sel_start and self.sel_end:
            s, e = min(self.sel_start, self.sel_end), max(self.sel_start, self.sel_end)
            self.on_range_select(s, e)


# =========================== ГРАФИКА И СЕТКА ===========================

def resolve_collisions(events):
    """Алгоритм раскладки пересекающихся событий по дорожкам (Lanes)."""
    if not events: return
    sorted_evs = sorted(events, key=lambda e: (e.start, -(e.end - e.start)))
    clusters, curr_cluster, max_end = [], [], None

    for ev in sorted_evs:
        if not curr_cluster:
            curr_cluster.append(ev)
            max_end = ev.end
        else:
            if ev.start < max_end:
                curr_cluster.append(ev)
                if ev.end > max_end: max_end = ev.end
            else:
                clusters.append(curr_cluster)
                curr_cluster = [ev]
                max_end = ev.end
    if curr_cluster: clusters.append(curr_cluster)

    for cluster in clusters:
        lanes = []
        for ev in cluster:
            placed = False
            for i, l_end in enumerate(lanes):
                if ev.start >= l_end:
                    lanes[i] = ev.end
                    ev.lane_index = i
                    placed = True
                    break
            if not placed:
                lanes.append(ev.end)
                ev.lane_index = len(lanes) - 1
        for ev in cluster:
            ev.total_lanes = len(lanes)

class AnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализатор & Планировщик (Командный Центр)")
        self.root.geometry("1400x900")
        
        self.data_mgr = DataManager()
        self.is_dark = False
        self.theme = LIGHT_THEME
        
        # Настройки отображения
        self.view_mode = "week" # day, custom, week, month, year
        self.show_facts = tk.BooleanVar(value=True)
        self.show_plans = tk.BooleanVar(value=True)
        
        today = date.today()
        self.range_start = today - timedelta(days=today.weekday())
        self.range_end = self.range_start + timedelta(days=6)
        
        # Drag & Quick Add state
        self.drag_start_min = None
        self.drag_end_min = None
        self.drag_day_idx = None
        self.drag_rect = None
        self.drag_text = None
        self.active_dialog = None
        self.just_dismissed = False

        self.init_ui()
        self.refresh_data()

    def apply_theme(self):
        self.theme = DARK_THEME if self.is_dark else LIGHT_THEME
        self.root.config(bg=self.theme["bg_main"])
        
        # Универсальная перекраска базовых фреймов
        def colorize(w):
            if isinstance(w, (tk.Frame, tk.LabelFrame, tk.PanedWindow)):
                try: w.config(bg=self.theme["bg_panel"])
                except Exception: pass
            if isinstance(w, (tk.Label, tk.Checkbutton)): 
                try:
                    w.config(bg=self.theme["bg_panel"], fg=self.theme["text_main"])
                    if isinstance(w, tk.Checkbutton): w.config(selectcolor=self.theme["bg_main"])
                except Exception: pass
            for child in w.winfo_children(): colorize(child)
            
        colorize(self.root)
        self.control_bar.config(bg=self.theme["bg_panel"])
        self.sidebar.config(bg=self.theme["bg_panel"])
        self.canvas.config(bg=self.theme["bg_canvas"])
        self.header_canvas.config(bg=self.theme["bg_panel"])
        self.mini_cal.update_theme(self.theme)

        # Синхронизация инспектора с выбранной темой
        if hasattr(self, "lbl_inspector"):
            self.lbl_inspector.config(bg=self.theme["bg_panel"], fg=self.theme["text_muted"])
        self.txt_inspector.config(
            bg=self.theme["bg_canvas"],
            fg=self.theme["text_main"],
            insertbackground=self.theme["text_main"],
            selectbackground=self.theme["selection"],
            inactiveselectbackground=self.theme["bg_canvas"],
            highlightbackground=self.theme["border"],
            highlightcolor=self.theme["accent"]
        )
        
        self.refresh_data() # Перерисовка холста

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.btn_theme.config(text="☀" if self.is_dark else "🌙")
        self.apply_theme()

    def init_ui(self):
        # --- Тулбар (Верх) ---
        self.control_bar = tk.Frame(self.root, height=50)
        self.control_bar.pack(side="top", fill="x")
        
        f_nav = tk.Frame(self.control_bar)
        f_nav.pack(side="left", padx=10, pady=10)
        tk.Button(f_nav, text="Сегодня", command=self.go_today).pack(side="left", padx=5)
        
        self.lbl_period = tk.Label(self.control_bar, text="Период", font=("Segoe UI", 14, "bold"))
        self.lbl_period.pack(side="left", padx=20, pady=10)
        
        # Слои
        f_layers = tk.Frame(self.control_bar)
        f_layers.pack(side="left", padx=20)
        tk.Checkbutton(f_layers, text="Факт (Логгер)", variable=self.show_facts, command=self.refresh_data, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Checkbutton(f_layers, text="План (Планировщик)", variable=self.show_plans, command=self.refresh_data, fg="#666").pack(side="left", padx=10)
        
        # Режимы и Тема
        f_right = tk.Frame(self.control_bar)
        f_right.pack(side="right", padx=10, pady=10)
        
        self.cb_view = ttk.Combobox(f_right, values=["День", "Неделя", "Месяц", "Год (Аналитика)"], state="readonly", width=15)
        self.cb_view.set("Неделя")
        self.cb_view.bind("<<ComboboxSelected>>", self.on_view_change)
        self.cb_view.pack(side="left", padx=10)
        
        self.btn_theme = tk.Button(f_right, text="🌙", command=self.toggle_theme, relief="flat", font=("Segoe UI", 12))
        self.btn_theme.pack(side="left", padx=5)

        # --- Основная зона (PanedWindow) ---
        self.paned = tk.PanedWindow(self.root, orient="horizontal", bd=0, sashwidth=4)
        self.paned.pack(fill="both", expand=True)
        
        # Sidebar
        self.sidebar = tk.Frame(self.paned, width=250)
        self.paned.add(self.sidebar, minsize=220)
        
        self.mini_cal = MiniCalendar(self.sidebar, self.theme, self.on_mini_cal_select)
        self.mini_cal.pack(fill="x", padx=10, pady=10)
        self.mini_cal.bind("<Configure>", lambda e: self.mini_cal.draw())

        # Инспектор в сайдбаре
        self.lbl_inspector = tk.Label(self.sidebar, text="ИНСПЕКТОР", font=("Segoe UI", 10, "bold"))
        self.lbl_inspector.pack(anchor="w", padx=15, pady=(20,0))
        self.txt_inspector = tk.Text(
            self.sidebar, height=15, font=("Segoe UI", 9), wrap="word", bd=1,
            highlightthickness=1, state="disabled", cursor="arrow"
        )
        self.txt_inspector.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Workspace (Календарь)
        self.workspace = tk.Frame(self.paned)
        self.paned.add(self.workspace, minsize=500)
        
        self.header_canvas = tk.Canvas(self.workspace, height=40, highlightthickness=0)
        self.header_canvas.pack(fill="x")
        
        f_grid = tk.Frame(self.workspace)
        f_grid.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(f_grid, highlightthickness=0, scrollregion=(0,0,1000, 24*HOUR_HEIGHT))
        self.vsb = ttk.Scrollbar(f_grid, orient="vertical", command=self.canvas.yview)
        self.canvas.config(yscrollcommand=self.vsb.set)
        
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Бинды мыши для календаря
        self.canvas.bind("<Configure>", lambda e: self.draw_grid())
        self.header_canvas.bind("<Configure>", lambda e: self.draw_headers())
        
        self.canvas.bind("<ButtonPress-1>", self.on_grid_press)
        self.canvas.bind("<B1-Motion>", self.on_grid_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_grid_release)
        self.canvas.bind("<Button-3>", self.on_right_click) # Правый клик
        
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.root.bind("<ButtonPress-1>", self.on_root_click, add="+")
        
        self.apply_theme()
        
        # Scroll to 08:00
        self.root.after(200, lambda: self.canvas.yview_moveto(7.5 / 24.0))

    # =========================== НАВИГАЦИЯ ===========================
    def go_today(self):
        t = date.today()
        if self.view_mode == "day": self.range_start = self.range_end = t
        elif self.view_mode == "month":
            self.range_start = date(t.year, t.month, 1)
            self.range_end = date(t.year, t.month, calendar.monthrange(t.year, t.month)[1])
        else:
            self.range_start = t - timedelta(days=t.weekday())
            self.range_end = self.range_start + timedelta(days=6)
        
        self.mini_cal.view_month = t.month
        self.mini_cal.view_year = t.year
        self.mini_cal.sel_start = self.range_start
        self.mini_cal.sel_end = self.range_end
        self.mini_cal.draw()
        self.refresh_data()

    def on_mini_cal_select(self, s_date, e_date):
        self.range_start = s_date
        self.range_end = e_date
        days = (e_date - s_date).days + 1
        
        if days == 1: self.view_mode = "day"; self.cb_view.set("День")
        elif days == 7 and s_date.weekday() == 0: self.view_mode = "week"; self.cb_view.set("Неделя")
        else: self.view_mode = "custom"; self.cb_view.set("Выделение")
        
        self.refresh_data()

    def on_view_change(self, e):
        v = self.cb_view.get()
        t = date.today()
        if v == "День": self.view_mode = "day"; self.range_start = self.range_end = t
        elif v == "Неделя": self.view_mode = "week"; self.range_start = t - timedelta(days=t.weekday()); self.range_end = self.range_start + timedelta(days=6)
        elif v == "Месяц": self.view_mode = "month"; self.range_start = date(t.year, t.month, 1); self.range_end = date(t.year, t.month, calendar.monthrange(t.year, t.month)[1])
        elif "Год" in v: self.view_mode = "year"; self.range_start = date(t.year, 1, 1); self.range_end = date(t.year, 12, 31)
        
        self.refresh_data()

    def refresh_data(self):
        # Обновление заголовка
        m1, y1 = MONTH_NAMES[self.range_start.month], self.range_start.year
        m2, y2 = MONTH_NAMES[self.range_end.month], self.range_end.year
        if self.range_start == self.range_end: title = f"{self.range_start.day} {m1} {y1}"
        elif m1 == m2 and y1 == y2: title = f"{self.range_start.day} — {self.range_end.day} {m1} {y1}"
        else: title = f"{self.range_start.day} {m1} — {self.range_end.day} {m2} {y2}"
        self.lbl_period.config(text=title)
        
        # Получение данных
        if self.view_mode != "year":
            self.events = self.data_mgr.load_events(self.range_start, self.range_end, self.show_facts.get(), self.show_plans.get())
        else:
            self.events = self.data_mgr.load_events(self.range_start, self.range_end, show_facts=True, show_plans=False) # Год только по фактам
            
        self.draw_headers()
        self.draw_grid()

    # =========================== ОТРИСОВКА (ДЕНЬ/НЕДЕЛЯ) ===========================
    def draw_headers(self):
        self.header_canvas.delete("all")
        if self.view_mode in ["month", "year"]: return # У месяца и года свои заголовки
        
        w = self.header_canvas.winfo_width()
        days_count = (self.range_end - self.range_start).days + 1
        if days_count <= 0: days_count = 1
        col_w = max(100, (w - TIME_COL_WIDTH) / days_count)
        
        self.header_canvas.create_rectangle(0,0,TIME_COL_WIDTH,40, fill=self.theme["bg_panel"], outline="")
        
        for i in range(days_count):
            d = self.range_start + timedelta(days=i)
            x1 = TIME_COL_WIDTH + i * col_w
            cx = x1 + col_w/2
            
            is_today = (d == date.today())
            color = self.theme["accent"] if is_today else self.theme["text_muted"]
            
            if is_today:
                self.header_canvas.create_oval(cx-14, 20-14, cx+14, 20+14, fill=self.theme["accent"], outline="")
                t_color = "#ffffff"
            else: t_color = self.theme["text_main"]
                
            self.header_canvas.create_text(cx, 10, text=WEEKDAY_NAMES[d.weekday()], fill=color, font=("Segoe UI", 8))
            self.header_canvas.create_text(cx, 22, text=str(d.day), fill=t_color, font=("Segoe UI", 11, "bold"))
            self.header_canvas.create_line(x1+col_w, 0, x1+col_w, 40, fill=self.theme["border"])
            
        self.header_canvas.create_line(0, 39, w, 39, fill=self.theme["border"])

    def draw_grid(self):
        self.canvas.delete("all")
        self.events_ui_map = {} # id -> event
        
        if self.view_mode == "year":
            self.draw_heatmap()
            return
        elif self.view_mode == "month":
            self.draw_month()
            return

        # Режимы: День, Неделя, Кастом
        w = self.canvas.winfo_width()
        days_count = (self.range_end - self.range_start).days + 1
        if days_count <= 0: days_count = 1
        col_w = max(100, (w - TIME_COL_WIDTH) / days_count)
        
        self.canvas.config(scrollregion=(0,0, w, 24*HOUR_HEIGHT))
        
        # Рисуем линии часов
        for h in range(25):
            y = h * HOUR_HEIGHT
            self.canvas.create_line(0, y, w, y, fill=self.theme["grid_hour"])
            if h < 24:
                self.canvas.create_text(TIME_COL_WIDTH-5, y+2, text=f"{h:02d}:00", anchor="ne", fill=self.theme["text_muted"], font=("Segoe UI", 8))
                self.canvas.create_line(TIME_COL_WIDTH, y+HOUR_HEIGHT/2, w, y+HOUR_HEIGHT/2, fill=self.theme["grid_half"], dash=(2,4))
                
        # Колонки дней
        for i in range(days_count + 1):
            x = TIME_COL_WIDTH + i * col_w
            self.canvas.create_line(x, 0, x, 24*HOUR_HEIGHT, fill=self.theme["border"])
            
            if i < days_count and (self.range_start + timedelta(days=i)) == date.today():
                self.canvas.create_rectangle(x, 0, x+col_w, 24*HOUR_HEIGHT, fill=self.theme["accent_light"], outline="", stipple="gray12")

        # Разрезаем события по дням и резолвим коллизии
        daily_events = {i: [] for i in range(days_count)}
        
        for ev in self.events:
            curr = ev.start
            while curr.date() <= ev.end.date():
                d_idx = (curr.date() - self.range_start).days
                if 0 <= d_idx < days_count:
                    # Сегментация
                    s_min = curr.hour*60 + curr.minute if curr.date() == ev.start.date() else 0
                    e_min = ev.end.hour*60 + ev.end.minute if curr.date() == ev.end.date() else 1440
                    
                    if e_min > s_min:
                        seg = EventObj(ev.id, ev.title, ev.start, ev.end, ev.type, ev.raw)
                        seg.s_min, seg.e_min = s_min, e_min
                        daily_events[d_idx].append(seg)
                
                next_d = datetime.combine(curr.date() + timedelta(days=1), time.min)
                curr = next_d

        # Отрисовка плашек
        for d_idx, segs in daily_events.items():
            resolve_collisions(segs)
            
            for seg in segs:
                lane_w = (col_w - 4) / seg.total_lanes
                x1 = TIME_COL_WIDTH + d_idx*col_w + 2 + seg.lane_index * lane_w
                x2 = x1 + lane_w - 2
                
                y1 = (seg.s_min / 60) * HOUR_HEIGHT
                y2 = (seg.e_min / 60) * HOUR_HEIGHT
                if y2 - y1 < MIN_EVENT_HEIGHT: y2 = y1 + MIN_EVENT_HEIGHT
                
                root_cat = seg.title.split("/")[0] if "/" in seg.title else seg.title
                bg_col, brd_col, txt_col = generate_pastel_color(root_cat, self.is_dark)
                
                # Стиль Плана vs Факта
                if seg.type == "plan":
                    rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=self.theme["bg_main"], outline=brd_col, width=2, dash=(4,2))
                    # Легкая штриховка или прозрачность (stipple)
                    self.canvas.create_rectangle(x1+2, y1+2, x2-2, y2-2, fill=bg_col, outline="", stipple="gray25")
                    display_title = f"[ПЛАН] {seg.title.split('/')[-1]}"
                else:
                    rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_col, outline=brd_col, width=1)
                    display_title = seg.title.split('/')[-1]

                txt = self.canvas.create_text(x1+4, y1+4, text=display_title, anchor="nw", fill=txt_col, font=("Segoe UI", 8, "bold"), width=lane_w-8)
                
                self.events_ui_map[rect] = seg
                self.events_ui_map[txt] = seg

        # Красная нить (Current Time)
        now = datetime.now()
        if self.range_start <= now.date() <= self.range_end:
            d_idx = (now.date() - self.range_start).days
            y = (now.hour + now.minute/60) * HOUR_HEIGHT
            x1 = TIME_COL_WIDTH + d_idx * col_w
            self.canvas.create_line(x1, y, x1+col_w, y, fill=self.theme["red_line"], width=2)
            self.canvas.create_oval(x1-4, y-4, x1+4, y+4, fill=self.theme["red_line"], outline="")


    def draw_month(self):
        """Простая сетка месяца."""
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.config(scrollregion=(0,0,w,h))
        
        cal = calendar.Calendar(firstweekday=0)
        days = list(cal.itermonthdates(self.range_start.year, self.range_start.month))
        
        cw = w / 7
        rh = h / 6
        
        for row in range(6):
            for col in range(7):
                idx = row*7 + col
                if idx >= len(days): break
                d = days[idx]
                
                x1, y1 = col*cw, row*rh
                x2, y2 = x1+cw, y1+rh
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=self.theme["bg_main"], outline=self.theme["border"])
                t_col = self.theme["text_main"] if d.month == self.range_start.month else self.theme["text_muted"]
                self.canvas.create_text(x1+5, y1+5, text=str(d.day), anchor="nw", fill=t_col, font=("Segoe UI", 10, "bold"))
                
                # Собираем события дня
                day_evs = [e for e in self.events if e.start.date() <= d <= e.end.date()]
                ey = y1 + 25
                for i, ev in enumerate(day_evs[:4]): # Макс 4 события
                    bg, brd, txt = generate_pastel_color(ev.title.split("/")[0], self.is_dark)
                    if ev.type == "plan": bg = self.theme["bg_panel"]
                    self.canvas.create_rectangle(x1+2, ey, x2-2, ey+15, fill=bg, outline=brd)
                    self.canvas.create_text(x1+4, ey+7, text=ev.title.split('/')[-1], anchor="w", fill=txt, font=("Segoe UI", 7))
                    ey += 17
                if len(day_evs) > 4:
                    self.canvas.create_text(x1+5, ey+5, text=f"+ еще {len(day_evs)-4}", anchor="w", fill=self.theme["accent"], font=("Segoe UI", 8))

    def draw_heatmap(self):
        """Статистика, Donut Chart и Heatmap активности за год."""
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.config(scrollregion=(0,0,w, max(h, 600)))
        
        # Подсчет активности
        activity = {}
        category_time = {}
        total_fact_mins = 0
        total_plan_mins = 0
        
        for ev in self.events:
            mins = (ev.end - ev.start).total_seconds() / 60
            if ev.type == "fact":
                d = ev.start.date()
                activity[d] = activity.get(d, 0) + mins
                total_fact_mins += mins
                
                root_cat = ev.title.split("/")[0] if "/" in ev.title else ev.title
                category_time[root_cat] = category_time.get(root_cat, 0) + mins
            else:
                total_plan_mins += mins
            
        max_mins = max(activity.values()) if activity else 1

        self.canvas.create_text(w/2, 30, text=f"Аналитика и Активность за {self.range_start.year} год", fill=self.theme["text_main"], font=("Segoe UI", 16, "bold"))
        
        # --- БЛОК 1: СТАТИСТИКА И DONUT CHART ---
        stat_x = w/2 - 250
        stat_y = 80
        self.canvas.create_text(stat_x, stat_y, text="ОБЩАЯ СВОДКА", fill=self.theme["text_muted"], font=("Segoe UI", 10, "bold"), anchor="w")
        self.canvas.create_text(stat_x, stat_y + 25, text=f"Всего затрекано: {int(total_fact_mins//60)} ч {int(total_fact_mins%60)} мин", fill=self.theme["text_main"], font=("Segoe UI", 12), anchor="w")
        self.canvas.create_text(stat_x, stat_y + 50, text=f"Запланировано: {int(total_plan_mins//60)} ч {int(total_plan_mins%60)} мин", fill=self.theme["text_main"], font=("Segoe UI", 12), anchor="w")

        self.canvas.create_text(stat_x, stat_y + 90, text="ТОП КАТЕГОРИИ:", fill=self.theme["text_muted"], font=("Segoe UI", 10, "bold"), anchor="w")
        sorted_cats = sorted(category_time.items(), key=lambda x: x[1], reverse=True)
        cy = stat_y + 115
        for cat, cmins in sorted_cats[:4]:
            bg, _, _ = generate_pastel_color(cat, self.is_dark)
            self.canvas.create_oval(stat_x, cy-4, stat_x+8, cy+4, fill=bg, outline="")
            self.canvas.create_text(stat_x + 15, cy, text=f"{cat}: {int(cmins//60)}ч {int(cmins%60)}м", fill=self.theme["text_main"], font=("Segoe UI", 10), anchor="w")
            cy += 20

        # Круговая диаграмма (Donut Chart)
        chart_x = w/2 + 150
        chart_y = 130
        r = 70
        if total_fact_mins > 0:
            start_ang = 90
            for cat, cmins in sorted_cats:
                extent = -(cmins / total_fact_mins) * 360
                bg, _, _ = generate_pastel_color(cat, self.is_dark)
                self.canvas.create_arc(chart_x-r, chart_y-r, chart_x+r, chart_y+r, start=start_ang, extent=extent, fill=bg, outline=self.theme["bg_main"], width=2)
                start_ang += extent
            # Центр бублика
            self.canvas.create_oval(chart_x-r+30, chart_y-r+30, chart_x+r-30, chart_y+r-30, fill=self.theme["bg_canvas"], outline="")
        else:
            self.canvas.create_oval(chart_x-r, chart_y-r, chart_x+r, chart_y+r, fill=self.theme["grid_hour"], outline="")
            self.canvas.create_oval(chart_x-r+30, chart_y-r+30, chart_x+r-30, chart_y+r-30, fill=self.theme["bg_canvas"], outline="")
            self.canvas.create_text(chart_x, chart_y, text="Нет данных", fill=self.theme["text_muted"], font=("Segoe UI", 9))

        # --- БЛОК 2: HEATMAP ---
        self.canvas.create_text(w/2, 260, text="ТЕПЛОВАЯ КАРТА (Heatmap)", fill=self.theme["text_muted"], font=("Segoe UI", 10, "bold"))
        
        cell_size = 15
        gap = 3
        start_x = (w - (53 * (cell_size + gap))) / 2
        start_y = 290
        
        cur_d = self.range_start
        while cur_d <= self.range_end:
            week = cur_d.isocalendar()[1]
            day = cur_d.weekday()
            
            x = start_x + week * (cell_size + gap)
            y = start_y + day * (cell_size + gap)
            
            mins = activity.get(cur_d, 0)
            if mins == 0: color = self.theme["grid_hour"]
            else:
                intensity = min(1.0, mins / max_mins)
                # От светло-зеленого к темно-зеленому
                r_c = int(235 - intensity * 200)
                g_c = int(245 - intensity * 100)
                b_c = int(235 - intensity * 200)
                if self.is_dark: r_c,g_c,b_c = int(intensity*50), int(intensity*200 + 50), int(intensity*50)
                color = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
                
            self.canvas.create_rectangle(x, y, x+cell_size, y+cell_size, fill=color, outline=self.theme["border"])
            cur_d += timedelta(days=1)

    # =========================== ИНТЕРАКТИВ И POP-UP ===========================

    def on_root_click(self, e):
        """Закрывает карточку при клике вне всплывающего окна."""
        if self.active_dialog and self.active_dialog.winfo_exists():
            try:
                x, y = e.x_root, e.y_root
                dx = self.active_dialog.winfo_rootx()
                dy = self.active_dialog.winfo_rooty()
                dw = self.active_dialog.winfo_width()
                dh = self.active_dialog.winfo_height()
                if not (dx <= x <= dx + dw and dy <= y <= dy + dh):
                    self.cancel_draft()
            except Exception:
                pass

    def cancel_draft(self):
        """Сбрасывает выделенную область и закрывает всплывающее окно карточки."""
        if self.active_dialog:
            try:
                dlg = self.active_dialog
                self.active_dialog = None
                dlg.destroy()
            except Exception:
                pass

        if getattr(self, "drag_rect", None):
            self.canvas.delete(self.drag_rect)
            self.drag_rect = None
        if getattr(self, "drag_text", None):
            self.canvas.delete(self.drag_text)
            self.drag_text = None

        self.drag_start_min = None
        self.drag_end_min = None
        self.drag_day_idx = None

    def on_grid_press(self, e):
        had_active = (self.active_dialog is not None or self.drag_rect is not None)
        self.cancel_draft()

        # Если плашка уже была открыта — этот клик только сбрасывает её, не открывая новую
        if had_active:
            self.just_dismissed = True
            return

        self.just_dismissed = False
        if self.view_mode not in ["day", "week", "custom"]: return
        
        # Проверка клика по существующему событию
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        for item in reversed(items):
            if item in self.events_ui_map:
                self.show_inspector(self.events_ui_map[item])
                return

        # Начало выделения временного диапазона
        days_count = (self.range_end - self.range_start).days + 1
        col_w = max(100, (self.canvas.winfo_width() - TIME_COL_WIDTH) / days_count)
        
        if cx >= TIME_COL_WIDTH:
            self.drag_day_idx = int((cx - TIME_COL_WIDTH) // col_w)
            if 0 <= self.drag_day_idx < days_count:
                raw_min = int((cy / HOUR_HEIGHT) * 60)
                self.drag_start_min = (raw_min // 15) * 15 # Шаг привязки 15 минут
                self.drag_end_min = self.drag_start_min + 30 # Базовый интервал на случай одиночного клика
                self.drag_x1 = TIME_COL_WIDTH + self.drag_day_idx * col_w
                self.drag_col_w = col_w

    def on_grid_drag(self, e):
        if getattr(self, "just_dismissed", False): return
        if self.drag_start_min is None or self.view_mode not in ["day", "week", "custom"]: return
        cy = self.canvas.canvasy(e.y)
        cur_min = int((cy / HOUR_HEIGHT) * 60)
        cur_min = max(0, min(1440, (cur_min // 15) * 15))
        
        s_min = min(self.drag_start_min, cur_min)
        e_min = max(self.drag_start_min, cur_min)
        if s_min == e_min: e_min += 15
        
        self.drag_end_min = e_min
        y1 = (s_min / 60) * HOUR_HEIGHT
        y2 = (e_min / 60) * HOUR_HEIGHT

        # Отрисовка интерактивной плашки выделения
        if self.drag_rect: self.canvas.delete(self.drag_rect)
        if self.drag_text: self.canvas.delete(self.drag_text)

        self.drag_rect = self.canvas.create_rectangle(
            self.drag_x1 + 2, y1, self.drag_x1 + self.drag_col_w - 2, y2,
            fill=self.theme["selection"], outline=self.theme["accent"], width=2, dash=(3, 2)
        )
        time_label = f"({s_min//60:02d}:{s_min%60:02d} — {e_min//60:02d}:{e_min%60:02d})"
        self.drag_text = self.canvas.create_text(
            self.drag_x1 + 6, y1 + 4, text=time_label, anchor="nw",
            fill=self.theme["text_main"], font=("Segoe UI", 8, "bold")
        )

    def on_grid_release(self, e):
        if getattr(self, "just_dismissed", False):
            self.just_dismissed = False
            return

        if self.view_mode not in ["day", "week", "custom"]: return
        if self.drag_start_min is None or self.drag_day_idx is None: return

        s_min = min(self.drag_start_min, self.drag_end_min)
        e_min = max(self.drag_start_min, self.drag_end_min)
        if s_min == e_min: e_min += 30 # При одиночном клике выделяем 30-минутный слот

        y1 = (s_min / 60) * HOUR_HEIGHT
        y2 = (e_min / 60) * HOUR_HEIGHT

        # Фиксируем плашку на сетке под всплывающим окном
        if self.drag_rect: self.canvas.delete(self.drag_rect)
        if self.drag_text: self.canvas.delete(self.drag_text)

        self.drag_rect = self.canvas.create_rectangle(
            self.drag_x1 + 2, y1, self.drag_x1 + self.drag_col_w - 2, y2,
            fill=self.theme["selection"], outline=self.theme["accent"], width=2
        )
        time_label = f"Новое ({s_min//60:02d}:{s_min%60:02d} — {e_min//60:02d}:{e_min%60:02d})"
        self.drag_text = self.canvas.create_text(
            self.drag_x1 + 6, y1 + 4, text=time_label, anchor="nw",
            fill=self.theme["text_main"], font=("Segoe UI", 8, "bold")
        )

        target_date = self.range_start + timedelta(days=self.drag_day_idx)
        start_dt = datetime.combine(target_date, time(s_min // 60, s_min % 60))
        if e_min >= 1440:
            end_dt = datetime.combine(target_date + timedelta(days=1), time.min)
        else:
            end_dt = datetime.combine(target_date, time(e_min // 60, e_min % 60))

        # Позиционируем окно рядом с выделенной областью
        rx, ry = self.root.winfo_pointerxy()
        self.active_dialog = QuickAddDialog(
            self.root, rx, ry, start_dt, end_dt,
            on_save=self.on_quick_save,
            on_cancel=self.cancel_draft,
            theme=self.theme
        )

    def on_quick_save(self, title, start_str, end_str, e_type):
        if e_type == "plan":
            self.data_mgr.add_plan(title, start_str, end_str)
        else:
            self.data_mgr.add_fact(title, start_str, end_str)
        self.cancel_draft()
        self.refresh_data()

    def on_right_click(self, e):
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        for item in reversed(items):
            if item in self.events_ui_map:
                ev = self.events_ui_map[item]
                if ev.type == "plan":
                    menu = tk.Menu(self.root, tearoff=0)
                    menu.add_command(label="✅ Выполнить (Перенести в Факт)", command=lambda: self.turn_plan_to_fact(ev.id))
                    menu.tk_popup(e.x_root, e.y_root)
                return

    def turn_plan_to_fact(self, plan_id):
        if self.data_mgr.turn_plan_to_fact(plan_id):
            self.refresh_data()
            messagebox.showinfo("Успех", "План перенесен в боевую базу!")

    def show_inspector(self, ev):
        self.txt_inspector.config(state="normal")
        self.txt_inspector.delete("1.0", tk.END)
        
        dur = int((ev.end - ev.start).total_seconds() / 60)
        
        info = f"Тип: {'ПЛАН' if ev.type=='plan' else 'ФАКТ'}\n"
        info += f"Категория:\n{ev.title}\n\n"
        info += f"Начало: {ev.start.strftime('%d.%m %H:%M')}\n"
        info += f"Конец:  {ev.end.strftime('%d.%m %H:%M')}\n"
        info += f"Длительность: {dur//60}ч {dur%60}м\n\n"
        
        if ev.type == "fact":
            tags, checks = [], []
            for k, v in ev.raw.items():
                if k.startswith("T_") and v: tags.append(f"{k[2:]}: {v}")
                elif k.startswith("C_") and v: checks.append(f"☑ {k[2:]}")
            
            if tags: info += "Теги:\n" + "\n".join(tags) + "\n\n"
            if checks: info += "Чекбоксы:\n" + "\n".join(checks)
            
        self.txt_inspector.insert("1.0", info)
        self.txt_inspector.config(state="disabled")

# =========================== ЗАПУСК ===========================
if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names(): style.theme_use("clam")
    app = AnalyzerApp(root)
    root.mainloop()