# Path: analyzer.py
# Version: 1.0
# Description: Модуль визуализации истории активности «Анализатор» (Календарная недельная сетка).

import os
import sqlite3
import hashlib
import colorsys
from datetime import datetime, date, time, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

# =========================== КОНФИГУРАЦИЯ И ПУТИ ===========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_DB_PATHS = [
    os.path.join(BASE_DIR, "config", "events_storage.db"),
    os.path.join(BASE_DIR, "events_storage.db"),
    os.path.join(os.getcwd(), "config", "events_storage.db"),
    os.path.join(os.getcwd(), "events_storage.db"),
]

TABLE_NAME = "events"
DT_FMT = "%d.%m.%Y %H:%M"
LEGACY_DT_FMT = "%d.%m.%Y %H:%M:%S"

HOUR_HEIGHT = 56           # Высота 1 часа в пикселях
TIME_COL_WIDTH = 62        # Ширина шкалы времени слева
MIN_EVENT_HEIGHT = 20      # Минимальная высота плашки (для 5-15 минутных событий)

WEEKDAY_NAMES_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTH_NAMES_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

# Палитра интерфейса
THEME = {
    "bg_main": "#f8f9fa",
    "bg_header": "#ffffff",
    "bg_canvas": "#ffffff",
    "grid_hour": "#e9ecef",
    "grid_half": "#f1f3f5",
    "text_dark": "#212529",
    "text_muted": "#6c757d",
    "today_accent": "#1a73e8",
    "today_badge_bg": "#e8f0fe",
    "red_line": "#ea4335",
    "selection": "#bbdefb",
    "inspector_bg": "#ffffff",
    "border": "#dee2e6"
}


# =========================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===========================

def find_database_path():
    """Находит актуальный файл SQLite базы данных."""
    for p in POSSIBLE_DB_PATHS:
        if os.path.exists(p):
            return p
    # Если база не найдена, вернем путь по умолчанию в config/
    default_path = POSSIBLE_DB_PATHS[0]
    os.makedirs(os.path.dirname(default_path), exist_ok=True)
    return default_path

def parse_datetime(dt_str):
    """Надежный парсер дат (поддерживает формат с секундами и без)."""
    if not dt_str or not isinstance(dt_str, str):
        return None
    dt_str = dt_str.strip()
    try:
        return datetime.strptime(dt_str, DT_FMT)
    except ValueError:
        try:
            return datetime.strptime(dt_str, LEGACY_DT_FMT)
        except ValueError:
            return None

def generate_pastel_color(text_seed):
    """
    Генерирует стабильный мягкий пастельный оттенок фона,
    акцентную рамку и контрастный текст на основе хеша строки.
    """
    if not text_seed:
        text_seed = "default"
    
    # MD5 хеш для детерминированного оттенка
    hash_digest = hashlib.md5(text_seed.encode("utf-8")).hexdigest()
    hue = (int(hash_digest[:4], 16) % 360) / 360.0
    saturation = 0.45
    lightness = 0.88

    # Фоновый пастельный цвет
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    bg_hex = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    # Контрастная рамка (чуть темнее и насыщеннее)
    rb, gb, bb = colorsys.hls_to_rgb(hue, 0.65, 0.60)
    border_hex = f"#{int(rb*255):02x}{int(gb*255):02x}{int(bb*255):02x}"

    # Цвет текста (глубокий темный оттенок той же гаммы)
    rt, gt, bt = colorsys.hls_to_rgb(hue, 0.22, 0.70)
    text_hex = f"#{int(rt*255):02x}{int(gt*255):02x}{int(bt*255):02x}"

    return bg_hex, border_hex, text_hex


# =========================== МОДЕЛЬ ДАННЫХ И БД ===========================

class EventSegment:
    """Визуальный сегмент события, привязанный к конкретному дню (от 00:00 до 24:00)."""
    def __init__(self, raw_record, seg_date, start_minute, end_minute, is_split=False):
        self.raw = raw_record
        self.id = raw_record.get("id", "")
        self.category_path = raw_record.get("category_path", "Без категории")
        self.date = seg_date
        self.start_minute = max(0, min(1440, start_minute))
        self.end_minute = max(0, min(1440, end_minute))
        self.duration_minutes = max(1, self.end_minute - self.start_minute)
        self.is_split = is_split

        # Дорожка для коллизий (рассчитывается компоновщиком)
        self.lane_index = 0
        self.total_lanes = 1

        # Canvas item IDs
        self.rect_id = None
        self.text_id = None
        self.time_id = None


class CalendarRepository:
    """Чтение и обработка событий из SQLite базы данных."""
    def __init__(self, db_path):
        self.db_path = db_path

    def load_events(self, start_date, end_date, filter_root_cat=None, search_query=None):
        """
        Загружает события, пересекающиеся с интервалом [start_date, end_date],
        и разбивает события через полночь на сегменты.
        """
        if not os.path.exists(self.db_path):
            return [], []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Проверяем наличие таблицы
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
        if not cursor.fetchone():
            conn.close()
            return [], []

        query = f"SELECT * FROM {TABLE_NAME} WHERE (is_deleted = 0 OR is_deleted IS NULL)"
        cursor.execute(query)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        all_root_categories = set()
        segments = []

        range_start_dt = datetime.combine(start_date, time.min)
        range_end_dt = datetime.combine(end_date, time.max)

        search_lower = (search_query or "").strip().lower()

        for row in rows:
            cat_path = row.get("category_path") or "Не указано"
            root_cat = cat_path.split("/")[0].strip() if "/" in cat_path else cat_path.strip()
            if root_cat:
                all_root_categories.add(root_cat)

            # Фильтрация по категории верхнего уровня
            if filter_root_cat and filter_root_cat != "Все категории":
                if root_cat != filter_root_cat:
                    continue

            # Текстовый поиск
            if search_lower:
                summary = " ".join(str(v) for v in row.values() if v).lower()
                if search_lower not in summary:
                    continue

            s_dt = parse_datetime(row.get("range_start"))
            e_dt = parse_datetime(row.get("range_end"))

            if not s_dt or not e_dt:
                continue

            # Коррекция, если время окончания меньше времени начала
            if e_dt < s_dt:
                s_dt, e_dt = e_dt, s_dt
            elif e_dt == s_dt:
                e_dt = s_dt + timedelta(minutes=15)

            # Проверяем пересечение с текущей просматриваемой неделей
            if e_dt < range_start_dt or s_dt > range_end_dt:
                continue

            # Разбиение на суточные сегменты (если пересекает полночь)
            curr_cur = s_dt
            while curr_cur.date() <= e_dt.date():
                seg_d = curr_cur.date()
                if start_date <= seg_d <= end_date:
                    is_start_day = (seg_d == s_dt.date())
                    is_end_day = (seg_d == e_dt.date())

                    if is_start_day:
                        s_min = curr_cur.hour * 60 + curr_cur.minute
                    else:
                        s_min = 0

                    if is_end_day:
                        e_min = e_dt.hour * 60 + e_dt.minute
                    else:
                        e_min = 1440  # 24:00

                    if e_min > s_min:
                        is_split = not (is_start_day and is_end_day)
                        seg = EventSegment(row, seg_d, s_min, e_min, is_split=is_split)
                        segments.append(seg)

                # Переход к следующему дню
                next_day_dt = datetime.combine(seg_d + timedelta(days=1), time.min)
                curr_cur = next_day_dt
                if curr_cur > e_dt:
                    break

        return segments, sorted(list(all_root_categories))


# =========================== АЛГОРИТМ КОЛЛИЗИЙ ===========================

def resolve_day_collisions(day_segments):
    """
    Кластерный жадный алгоритм раскладки пересекающихся событий по дорожкам (Lanes).
    Аналог алгоритма Google Calendar.
    """
    if not day_segments:
        return

    # Сортируем: сначала по началу, затем по длительности (более длинные первыми)
    sorted_segs = sorted(day_segments, key=lambda s: (s.start_minute, -(s.end_minute - s.start_minute)))

    # 1. Группируем в кластеры пересечений
    clusters = []
    current_cluster = []
    cluster_max_end = -1

    for seg in sorted_segs:
        if not current_cluster:
            current_cluster.append(seg)
            cluster_max_end = seg.end_minute
        else:
            if seg.start_minute < cluster_max_end:
                current_cluster.append(seg)
                if seg.end_minute > cluster_max_end:
                    cluster_max_end = seg.end_minute
            else:
                clusters.append(current_cluster)
                current_cluster = [seg]
                cluster_max_end = seg.end_minute

    if current_cluster:
        clusters.append(current_cluster)

    # 2. В каждом кластере распределяем дорожки (lanes)
    for cluster in clusters:
        lanes_end_times = []  # время окончания последнего события в каждой дорожке
        for seg in cluster:
            placed = False
            for l_idx, l_end in enumerate(lanes_end_times):
                if seg.start_minute >= l_end:
                    lanes_end_times[l_idx] = seg.end_minute
                    seg.lane_index = l_idx
                    placed = True
                    break
            if not placed:
                lanes_end_times.append(seg.end_minute)
                seg.lane_index = len(lanes_end_times) - 1

        total_lanes = len(lanes_end_times)
        for seg in cluster:
            seg.total_lanes = total_lanes


# =========================== ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ===========================

class AnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Модуль «Анализатор» — Календарный Таймлайн")
        self.root.geometry("1280x850")
        self.root.minsize(980, 600)
        self.root.configure(bg=THEME["bg_main"])

        self.db_path = find_database_path()
        self.repo = CalendarRepository(self.db_path)

        # Текущая дата и навигационный якорь (понедельник недели)
        today = date.today()
        self.current_week_monday = today - timedelta(days=today.weekday())

        self.selected_event = None
        self.segments_by_canvas_id = {}
        self.category_list = ["Все категории"]
        self.filter_category = "Все категории"

        # Параметры drag-to-select
        self.drag_active = False
        self.drag_day_idx = None
        self.drag_start_min = None
        self.drag_rect_id = None

        self._init_ui()
        self.refresh_data()

        # Автопрокрутка к 08:00 после построения окна
        self.root.after(150, self._scroll_to_morning)

    # ----------------------------------------------------------------------
    # ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ----------------------------------------------------------------------
    def _init_ui(self):
        # 1. Верхняя панель управления (Control Bar)
        self.control_bar = tk.Frame(self.root, bg=THEME["bg_header"], height=56, bd=0, relief="flat")
        self.control_bar.pack(side="top", fill="x")
        self._build_control_bar()

        # Разделительная линия
        tk.Frame(self.root, bg=THEME["border"], height=1).pack(side="top", fill="x")

        # 2. Нижняя панель (Инспектор событий)
        self.inspector_panel = tk.Frame(self.root, bg=THEME["inspector_bg"], height=130, bd=0)
        self.inspector_panel.pack(side="bottom", fill="x")
        self._build_inspector()

        tk.Frame(self.root, bg=THEME["border"], height=1).pack(side="bottom", fill="x")

        # 3. Фиксированный заголовок дней недели (Day Header)
        self.header_frame = tk.Frame(self.root, bg=THEME["bg_header"], height=52)
        self.header_frame.pack(side="top", fill="x")
        self.header_canvas = tk.Canvas(self.header_frame, bg=THEME["bg_header"], height=52, highlightthickness=0)
        self.header_canvas.pack(fill="both", expand=True)

        # 4. Основная зона календаря (Canvas + Scrollbar)
        self.grid_container = tk.Frame(self.root, bg=THEME["bg_canvas"])
        self.grid_container.pack(side="top", fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.grid_container,
            bg=THEME["bg_canvas"],
            highlightthickness=0,
            scrollregion=(0, 0, 1000, 24 * HOUR_HEIGHT)
        )
        self.v_scrollbar = ttk.Scrollbar(self.grid_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.v_scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Привязка событий окна и мыши
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.header_canvas.bind("<Configure>", lambda e: self._draw_day_headers())

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_hover)

        # Скролл колесиком мыши
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows/macOS
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))  # Linux
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def _build_control_bar(self):
        # Навигация: << Сегодня >>
        nav_box = tk.Frame(self.control_bar, bg=THEME["bg_header"])
        nav_box.pack(side="left", padx=(15, 10), pady=10)

        btn_style = {"bg": "#f1f3f4", "fg": THEME["text_dark"], "relief": "flat", "bd": 0, "padx": 10, "pady": 4, "font": ("Segoe UI", 9)}

        tk.Button(nav_box, text="<<", command=self.prev_week, **btn_style).pack(side="left", padx=2)
        tk.Button(nav_box, text="Сегодня", command=self.go_today, bg="#e8f0fe", fg=THEME["today_accent"],
                  relief="flat", bd=0, padx=12, pady=4, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
        tk.Button(nav_box, text=">>", command=self.next_week, **btn_style).pack(side="left", padx=2)

        # Текст периода (например: "14 — 20 сентября 2026 г.")
        self.lbl_period = tk.Label(self.control_bar, text="", bg=THEME["bg_header"],
                                   fg=THEME["text_dark"], font=("Segoe UI", 13, "bold"))
        self.lbl_period.pack(side="left", padx=15)

        # Правый блок: Фильтры и селектор масштаба
        right_box = tk.Frame(self.control_bar, bg=THEME["bg_header"])
        right_box.pack(side="right", padx=15, pady=10)

        # Категория
        tk.Label(right_box, text="Категория:", bg=THEME["bg_header"], fg=THEME["text_muted"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        self.combo_category = ttk.Combobox(right_box, values=self.category_list, state="readonly", width=18)
        self.combo_category.set("Все категории")
        self.combo_category.bind("<<ComboboxSelected>>", self._on_filter_change)
        self.combo_category.pack(side="left", padx=(0, 15))

        # Поиск
        tk.Label(right_box, text="Поиск:", bg=THEME["bg_header"], fg=THEME["text_muted"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        self.entry_search = ttk.Entry(right_box, width=16)
        self.entry_search.pack(side="left", padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", lambda e: self._on_filter_change())

        # Селектор масштаба (задел)
        scale_badge = tk.Label(right_box, text="Неделя", bg="#e8f0fe", fg=THEME["today_accent"],
                               font=("Segoe UI", 9, "bold"), padx=10, pady=3)
        scale_badge.pack(side="left", padx=5)

        # Кнопка перезагрузки из БД
        tk.Button(right_box, text="⟳", command=self.refresh_data, bg="#f1f3f4", fg=THEME["text_dark"],
                  relief="flat", padx=8, pady=2, font=("Segoe UI", 10, "bold")).pack(side="left", padx=4)

    def _build_inspector(self):
        """Нижняя панель с деталями выбранного события."""
        self.inspector_panel.columnconfigure(0, weight=1)
        self.inspector_panel.rowconfigure(0, weight=1)

        container = tk.Frame(self.inspector_panel, bg=THEME["inspector_bg"], padx=15, pady=8)
        container.pack(fill="both", expand=True)

        # Заголовок секции инспектора
        top_row = tk.Frame(container, bg=THEME["inspector_bg"])
        top_row.pack(fill="x", side="top")

        self.insp_lbl_title = tk.Label(top_row, text="Инспектор события (кликните на плашку в календаре)",
                                       bg=THEME["inspector_bg"], fg=THEME["text_muted"], font=("Segoe UI", 10, "bold"))
        self.insp_lbl_title.pack(side="left")

        self.insp_lbl_time = tk.Label(top_row, text="", bg=THEME["inspector_bg"],
                                      fg=THEME["today_accent"], font=("Segoe UI", 10, "bold"))
        self.insp_lbl_time.pack(side="right")

        # Детали (Теги, чекбоксы, путь)
        self.insp_content = tk.Text(container, bg=THEME["inspector_bg"], fg=THEME["text_dark"],
                                    height=3, bd=0, relief="flat", font=("Segoe UI", 9), wrap="word")
        self.insp_content.pack(fill="both", expand=True, side="top", pady=(4, 0))
        self.insp_content.insert("1.0", "Данные отсутствуют.")
        self.insp_content.config(state="disabled")

    # ----------------------------------------------------------------------
    # НАВИГАЦИЯ ПО ВРЕМЕНИ
    # ----------------------------------------------------------------------
    def prev_week(self):
        self.current_week_monday -= timedelta(days=7)
        self.refresh_data()

    def next_week(self):
        self.current_week_monday += timedelta(days=7)
        self.refresh_data()

    def go_today(self):
        today = date.today()
        self.current_week_monday = today - timedelta(days=today.weekday())
        self.refresh_data()
        self._scroll_to_morning()

    def _scroll_to_morning(self):
        # Прокручиваем холст примерно к 08:00
        total_h = 24 * HOUR_HEIGHT
        target_y = 7.5 * HOUR_HEIGHT
        fraction = target_y / total_h
        self.canvas.yview_moveto(fraction)

    def _on_mousewheel(self, event):
        # Поддержка колеса мыши в Windows
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ----------------------------------------------------------------------
    # ПЕРЕРАСЧЕТ ГЕОМЕТРИИ И ОТРИСОВКА
    # ----------------------------------------------------------------------
    def _on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=(0, 0, event.width, 24 * HOUR_HEIGHT))
        self._redraw_all()

    def _get_column_geometry(self):
        """Возвращает ширину одной колонки дня и координаты X для каждого из 7 дней."""
        canvas_width = max(self.canvas.winfo_width(), 800)
        available_width = canvas_width - TIME_COL_WIDTH
        day_col_width = max(100, available_width / 7.0)
        return day_col_width

    def _on_filter_change(self, event=None):
        self.filter_category = self.combo_category.get()
        self.refresh_data()

    def refresh_data(self):
        """Загрузка данных за текущую неделю и полная перерисовка."""
        sunday = self.current_week_monday + timedelta(days=6)

        # Обновляем текст периода
        m1_name = MONTH_NAMES_RU[self.current_week_monday.month]
        m2_name = MONTH_NAMES_RU[sunday.month]
        year1 = self.current_week_monday.year
        year2 = sunday.year

        if year1 == year2:
            if self.current_week_monday.month == sunday.month:
                period_str = f"{self.current_week_monday.day} — {sunday.day} {m1_name} {year1} г."
            else:
                period_str = f"{self.current_week_monday.day} {m1_name} — {sunday.day} {m2_name} {year1} г."
        else:
            period_str = f"{self.current_week_monday.day} {m1_name} {year1} — {sunday.day} {m2_name} {year2} г."

        self.lbl_period.config(text=period_str)

        # Чтение из БД
        search_q = self.entry_search.get() if hasattr(self, "entry_search") else None
        segments, root_cats = self.repo.load_events(
            self.current_week_monday, sunday,
            filter_root_cat=self.filter_category,
            search_query=search_q
        )
        self.segments = segments

        # Обновление списка категорий
        new_cats = ["Все категории"] + root_cats
        if set(new_cats) != set(self.category_list):
            self.category_list = new_cats
            self.combo_category.config(values=self.category_list)

        # Расчет коллизий для каждого дня отдельно
        for day_offset in range(7):
            d = self.current_week_monday + timedelta(days=day_offset)
            day_segs = [s for s in self.segments if s.date == d]
            resolve_day_collisions(day_segs)

        self._redraw_all()

    def _redraw_all(self):
        self._draw_day_headers()
        self._draw_grid_and_events()

    # ----------------------------------------------------------------------
    # ШАПКА ДНЕЙ НЕДЕЛИ (Day Header)
    # ----------------------------------------------------------------------
    def _draw_day_headers(self):
        self.header_canvas.delete("all")
        day_col_width = self._get_column_geometry()
        today = date.today()

        # Серый левый квадрат над шкалой времени
        self.header_canvas.create_rectangle(0, 0, TIME_COL_WIDTH, 52, fill=THEME["bg_header"], outline="")
        self.header_canvas.create_line(TIME_COL_WIDTH, 0, TIME_COL_WIDTH, 52, fill=THEME["border"])

        for i in range(7):
            cur_date = self.current_week_monday + timedelta(days=i)
            x1 = TIME_COL_WIDTH + i * day_col_width
            x2 = x1 + day_col_width
            cx = (x1 + x2) / 2.0

            is_today = (cur_date == today)

            # Вертикальная линия разделителя
            self.header_canvas.create_line(x2, 0, x2, 52, fill=THEME["border"])

            # День недели (Пн, Вт...)
            day_name = WEEKDAY_NAMES_RU[i]
            day_color = THEME["today_accent"] if is_today else THEME["text_muted"]
            self.header_canvas.create_text(cx, 16, text=day_name, fill=day_color,
                                          font=("Segoe UI", 9, "bold" if is_today else "normal"))

            # Число месяца
            day_num_str = str(cur_date.day)
            if is_today:
                # Рисуем стильный бейдж-кружок вокруг сегодняшнего числа
                badge_r = 13
                by = 35
                self.header_canvas.create_oval(cx - badge_r, by - badge_r, cx + badge_r, by + badge_r,
                                              fill=THEME["today_accent"], outline="")
                self.header_canvas.create_text(cx, by, text=day_num_str, fill="#ffffff",
                                              font=("Segoe UI", 10, "bold"))
            else:
                self.header_canvas.create_text(cx, 35, text=day_num_str, fill=THEME["text_dark"],
                                              font=("Segoe UI", 10, "bold"))

        # Нижняя разделительная черта шапки
        self.header_canvas.create_line(0, 51, 3000, 51, fill=THEME["border"])

    # ----------------------------------------------------------------------
    # ОСНОВНАЯ СЕТКА И СОБЫТИЯ (Canvas)
    # ----------------------------------------------------------------------
    def _draw_grid_and_events(self):
        self.canvas.delete("all")
        self.segments_by_canvas_id.clear()

        day_col_width = self._get_column_geometry()
        total_canvas_width = TIME_COL_WIDTH + 7 * day_col_width
        today = date.today()

        # 1. Горизонтальные линии часов и метки времени
        for hour in range(25):
            y = hour * HOUR_HEIGHT

            # Линия целого часа
            self.canvas.create_line(0, y, total_canvas_width, y, fill=THEME["grid_hour"], width=1)

            # Метка часа слева (например, 09:00)
            if hour < 24:
                time_str = f"{hour:02d}:00"
                self.canvas.create_text(
                    TIME_COL_WIDTH - 10, y + 2,
                    text=time_str, anchor="ne",
                    fill=THEME["text_muted"],
                    font=("Segoe UI", 8)
                )

                # Пунктирная линия полудня (30 минут)
                y_half = y + (HOUR_HEIGHT / 2.0)
                self.canvas.create_line(
                    TIME_COL_WIDTH, y_half, total_canvas_width, y_half,
                    fill=THEME["grid_half"], dash=(2, 3), width=1
                )

        # 2. Вертикальные линии дней недели
        for i in range(8):
            x = TIME_COL_WIDTH + i * day_col_width
            self.canvas.create_line(x, 0, x, 24 * HOUR_HEIGHT, fill=THEME["border"], width=1)

            # Легкая подсветка фона для сегодняшнего дня
            if i < 7:
                col_date = self.current_week_monday + timedelta(days=i)
                if col_date == today:
                    self.canvas.create_rectangle(
                        x + 1, 0, x + day_col_width - 1, 24 * HOUR_HEIGHT,
                        fill=THEME["today_badge_bg"], outline="", stipple="gray12"
                    )

        # 3. Отрисовка плашек событий
        for seg in self.segments:
            day_idx = (seg.date - self.current_week_monday).days
            if not (0 <= day_idx <= 6):
                continue

            day_x1 = TIME_COL_WIDTH + day_idx * day_col_width
            day_w = day_col_width

            # Рассчитываем координаты с учетом дорожек (коллизий)
            lane_w = (day_w - 6) / float(seg.total_lanes)
            seg_x1 = day_x1 + 3 + (seg.lane_index * lane_w)
            seg_x2 = seg_x1 + lane_w - 3

            y1 = (seg.start_minute / 60.0) * HOUR_HEIGHT
            y2 = (seg.end_minute / 60.0) * HOUR_HEIGHT

            # Минимальная высота плашки
            if (y2 - y1) < MIN_EVENT_HEIGHT:
                y2 = y1 + MIN_EVENT_HEIGHT

            # Цвета категории
            root_cat = seg.category_path.split("/")[0].strip()
            bg_color, border_color, text_color = generate_pastel_color(root_cat)

            # Если событие сейчас выбрано — выделяем толстой рамкой
            is_selected = (self.selected_event and self.selected_event.get("id") == seg.id)
            outline_color = "#1a73e8" if is_selected else border_color
            line_w = 2 if is_selected else 1

            # Прямоугольник плашки
            rect_id = self.canvas.create_rectangle(
                seg_x1, y1, seg_x2, y2,
                fill=bg_color, outline=outline_color, width=line_w
            )

            # Текст: название категории
            display_title = seg.category_path.split("/")[-1] if "/" in seg.category_path else seg.category_path
            if seg.is_split:
                display_title += " (сегмент)"

            # Клиппинг текста по ширине дорожки
            max_char_len = max(4, int(lane_w / 7.5))
            if len(display_title) > max_char_len:
                display_title = display_title[:max_char_len - 1] + "…"

            text_id = self.canvas.create_text(
                seg_x1 + 5, y1 + 3,
                anchor="nw",
                text=display_title,
                fill=text_color,
                font=("Segoe UI", 9, "bold")
            )

            # Время (если высота плашки позволяет)
            time_id = None
            if (y2 - y1) >= 32 and lane_w > 50:
                s_h, s_m = divmod(seg.start_minute, 60)
                e_h, e_m = divmod(seg.end_minute, 60)
                time_range_txt = f"{s_h:02d}:{s_m:02d} - {e_h:02d}:{e_m:02d}"
                time_id = self.canvas.create_text(
                    seg_x1 + 5, y1 + 17,
                    anchor="nw",
                    text=time_range_txt,
                    fill=text_color,
                    font=("Segoe UI", 8)
                )

            # Сохраняем связку графических элементов с объектом сегмента
            seg.rect_id = rect_id
            self.segments_by_canvas_id[rect_id] = seg
            self.segments_by_canvas_id[text_id] = seg
            if time_id:
                self.segments_by_canvas_id[time_id] = seg

        # 4. Красная нить (маркер текущей минуты)
        if self.current_week_monday <= today <= (self.current_week_monday + timedelta(days=6)):
            now = datetime.now()
            today_idx = today.weekday()
            cur_min = now.hour * 60 + now.minute
            cur_y = (cur_min / 60.0) * HOUR_HEIGHT

            line_x1 = TIME_COL_WIDTH + today_idx * day_col_width
            line_x2 = line_x1 + day_col_width

            # Точка на начале линии
            r = 4
            self.canvas.create_oval(line_x1 - r, cur_y - r, line_x1 + r, cur_y + r,
                                    fill=THEME["red_line"], outline="")
            self.canvas.create_line(line_x1, cur_y, line_x2, cur_y,
                                    fill=THEME["red_line"], width=2)

    # ----------------------------------------------------------------------
    # ИНТЕРАКТИВНОСТЬ: КЛИКИ, ВЫБОР И ИНСПЕКТОР
    # ----------------------------------------------------------------------
    def _on_canvas_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # 1. Проверяем клик по событию
        clicked_items = self.canvas.find_overlapping(canvas_x - 1, canvas_y - 1, canvas_x + 1, canvas_y + 1)
        found_seg = None
        for item_id in reversed(clicked_items):
            if item_id in self.segments_by_canvas_id:
                found_seg = self.segments_by_canvas_id[item_id]
                break

        if found_seg:
            self._select_event(found_seg.raw)
            return

        # 2. Если клик на пустом месте — сброс выбора и старт drag-to-select
        self._deselect_event()

        day_col_width = self._get_column_geometry()
        if canvas_x >= TIME_COL_WIDTH:
            day_idx = int((canvas_x - TIME_COL_WIDTH) // day_col_width)
            if 0 <= day_idx <= 6:
                self.drag_active = True
                self.drag_day_idx = day_idx
                clicked_minute = int((canvas_y / float(HOUR_HEIGHT)) * 60)
                # Округляем к ближайшим 15 минутам
                self.drag_start_min = (clicked_minute // 15) * 15

    def _on_canvas_drag(self, event):
        if not self.drag_active:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        day_col_width = self._get_column_geometry()

        cur_minute = max(0, min(1440, int((canvas_y / float(HOUR_HEIGHT)) * 60)))
        cur_minute = (cur_minute // 15) * 15

        min_s = min(self.drag_start_min, cur_minute)
        min_e = max(self.drag_start_min, cur_minute)
        if min_e == min_s:
            min_e += 15

        x1 = TIME_COL_WIDTH + self.drag_day_idx * day_col_width + 2
        x2 = x1 + day_col_width - 4
        y1 = (min_s / 60.0) * HOUR_HEIGHT
        y2 = (min_e / 60.0) * HOUR_HEIGHT

        if self.drag_rect_id:
            self.canvas.delete(self.drag_rect_id)

        self.drag_rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=THEME["selection"], outline="#1976d2", width=1, dash=(3, 2)
        )

        # Выводим текущий выбранный интервал в инспектор
        sel_date = self.current_week_monday + timedelta(days=self.drag_day_idx)
        s_h, s_m = divmod(min_s, 60)
        e_h, e_m = divmod(min_e, 60)
        dur = min_e - min_s
        self.insp_lbl_title.config(text=f"[Планирование]: {sel_date.strftime('%d.%m.%Y')} ({WEEKDAY_NAMES_RU[self.drag_day_idx]})")
        self.insp_lbl_time.config(text=f"{s_h:02d}:{s_m:02d} - {e_h:02d}:{e_m:02d} ({dur} мин)")

    def _on_canvas_release(self, event):
        if self.drag_active:
            self.drag_active = False
            # Задел на будущее: здесь можно открывать всплывающее меню "Создать событие"

    def _on_canvas_hover(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        items = self.canvas.find_overlapping(canvas_x - 1, canvas_y - 1, canvas_x + 1, canvas_y + 1)

        is_over_event = any(i in self.segments_by_canvas_id for i in items)
        self.canvas.config(cursor="hand2" if is_over_event else "")

    def _select_event(self, raw_record):
        self.selected_event = raw_record
        if self.drag_rect_id:
            self.canvas.delete(self.drag_rect_id)
            self.drag_rect_id = None

        self._redraw_all()
        self._update_inspector_details(raw_record)

    def _deselect_event(self):
        self.selected_event = None
        self._redraw_all()
        self.insp_lbl_title.config(text="Инспектор события (кликните на плашку в календаре)")
        self.insp_lbl_time.config(text="")
        self.insp_content.config(state="normal")
        self.insp_content.delete("1.0", tk.END)
        self.insp_content.insert("1.0", "Данные отсутствуют.")
        self.insp_content.config(state="disabled")

    def _update_inspector_details(self, row):
        """Форматирует детальные данные события для вывода в инспектор."""
        cat_path = row.get("category_path") or "Не указано"
        r_start = row.get("range_start") or "?"
        r_end = row.get("range_end") or "?"

        # Расчет длительности
        s_dt = parse_datetime(r_start)
        e_dt = parse_datetime(r_end)
        dur_str = ""
        if s_dt and e_dt:
            diff_m = int((e_dt - s_dt).total_seconds() / 60)
            dur_str = f" • Длительность: {diff_m // 60} ч {diff_m % 60} мин ({diff_m} мин)"

        self.insp_lbl_title.config(text=f"Категория: {cat_path}")
        self.insp_lbl_time.config(text=f"{r_start}  —  {r_end}{dur_str}")

        # Собираем теги и чекбоксы
        tags_list = []
        checks_list = []
        for k, v in row.items():
            if k.startswith("T_") and v:
                clean_k = k[2:].replace("_", " ").title()
                tags_list.append(f"{clean_k}: {v}")
            elif k.startswith("C_") and v:
                clean_k = k[2:].replace("_", " ").title()
                checks_list.append(f"☑ {clean_k} ({v})")

        lines = []
        if tags_list:
            lines.append("🏷 ТЕГИ:  " + "  |  ".join(tags_list))
        if checks_list:
            lines.append("✓ ЧЕКБОКСЫ:  " + "  |  ".join(checks_list))

        lines.append(f"UUID: {row.get('id', '-')}  |  Сессия: {row.get('session_id', '-')}  |  Создано: {row.get('timestamp', '-')}")

        full_text = "\n".join(lines)

        self.insp_content.config(state="normal")
        self.insp_content.delete("1.0", tk.END)
        self.insp_content.insert("1.0", full_text)
        self.insp_content.config(state="disabled")


# =========================== ТОЧКА ВХОДА ===========================

if __name__ == "__main__":
    app_root = tk.Tk()
    # Изящное использование стилей ttk
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")

    app = AnalyzerApp(app_root)
    app_root.mainloop()