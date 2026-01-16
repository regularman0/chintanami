# Path: ui/input/generators/time_gens.py
# Version: 19.2
# Description: Генераторы времени. Реализован Shift/Stretch, удалены секунды, добавлен Diff Label и Copy Last.

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from core import schema
from .base import BaseGenerator

class TimeGenerator(BaseGenerator):
    
    # ================= RANGE MODULE =================
    def draw_range(self, parent, cfg):
        fr = tk.LabelFrame(parent, text="RANGE", bg=self.theme["range_bg"], font=("Arial", 10, "bold"))
        fr.pack(fill="x", padx=10, pady=5)
        
        # --- Row 0: Labels ---
        tk.Label(fr, text="Start:", bg=self.theme["range_bg"]).grid(row=0, column=0, sticky="w")
        tk.Label(fr, text="End:", bg=self.theme["range_bg"]).grid(row=0, column=2, sticky="w")
        
        # --- Row 1: Entries + Clear ---
        # Start
        or_ent = tk.Entry(fr, width=20, font=("Consolas", 10))
        or_ent.grid(row=1, column=0, padx=(5,0))
        btn_clr_s = tk.Button(fr, text="×", fg="red", relief="flat", bg=self.theme["range_bg"], 
                              command=lambda: [or_ent.delete(0, tk.END), self.update_diff()])
        btn_clr_s.grid(row=1, column=1, sticky="w")

        # End
        end_ent = tk.Entry(fr, width=20, font=("Consolas", 10))
        end_ent.grid(row=1, column=2, padx=(5,0))
        btn_clr_e = tk.Button(fr, text="×", fg="red", relief="flat", bg=self.theme["range_bg"], 
                              command=lambda: [end_ent.delete(0, tk.END), self.update_diff()])
        btn_clr_e.grid(row=1, column=3, sticky="w")

        self.register_widget("or_entry", or_ent)
        self.register_widget("end_entry", end_ent)
        
        # Restore values
        s, e = self.mgrs["range"].get_values()
        or_ent.insert(0, s)
        end_ent.insert(0, e)
        
        # Binds (Save + Update Diff)
        def manual(e): 
            self.mgrs["range"].set_values(or_ent.get(), end_ent.get())
            self.update_diff()
            
        or_ent.bind("<KeyRelease>", manual)
        end_ent.bind("<KeyRelease>", manual)

        # --- Row 2: Now Buttons ---
        def set_now(key, w):
            n = datetime.now().strftime(schema.DT_FMT)
            w.delete(0, tk.END); w.insert(0, n)
            if key == "or_range_val": self.mgrs["range"].set_values(start=n)
            else: self.mgrs["range"].set_values(end=n)
            self.update_diff()

        b_now_s = tk.Button(fr, text="Now -> Start", bg="white", command=lambda: set_now("or_range_val", or_ent))
        b_now_s.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        
        b_now_e = tk.Button(fr, text="Now -> End", bg="white", command=lambda: set_now("end_range_val", end_ent))
        b_now_e.grid(row=2, column=2, columnspan=2, sticky="ew", padx=2, pady=2)

        # --- Row 3: Copy Last ---
        def copy_last():
            # 1. Сначала пробуем взять из БД
            val = self.mgrs["range"].copy_last_end_from_db()
            if not val:
                # Fallback: копируем из текущего End
                val = end_ent.get()
                self.mgrs["range"].set_values(start=val)
            
            if val:
                or_ent.delete(0, tk.END); or_ent.insert(0, val)
                self.update_diff()

        b_copy = tk.Button(fr, text="⬇ Copy Last End to Start ⬇", bg="#e8f8f5", command=copy_last)
        b_copy.grid(row=3, column=0, columnspan=4, sticky="ew", padx=2, pady=(2, 8))

        # --- Row 4: Math Controls (Step / Value) ---
        math_frame = tk.Frame(fr, bg=self.theme["range_bg"])
        math_frame.grid(row=4, column=0, columnspan=4)

        step_opts = cfg.get("step_options", [5, 60, 5])
        default_val = cfg.get("defaults", {}).get("value", 15)

        tk.Label(math_frame, text="Step:", bg=self.theme["range_bg"]).pack(side="left")
        sc = ttk.Combobox(math_frame, values=list(range(*step_opts)), width=5, state="readonly")
        sc.pack(side="left", padx=5)
        sc.set(step_opts[0])

        tk.Label(math_frame, text="Value:", bg=self.theme["range_bg"]).pack(side="left")
        rv = ttk.Combobox(math_frame, width=5, state="readonly")
        rv.pack(side="left", padx=5)
        self.register_widget("r_val_combo", rv)

        def upd(e): 
            val = int(sc.get())
            rv["values"] = list(range(val, 61, val))
            if default_val in rv["values"]: rv.set(default_val)
            else: rv.set(val)
        sc.bind("<<ComboboxSelected>>", upd)
        upd(None)

        # --- Row 5: Math Actions (+/-) ---
        # Логика кнопок
        def do_math(target, w, op):
            mins = int(rv.get())
            is_dur_mode = self.tab.duration_mode_var.get()
            
            # Logic:
            # Start: Always Modify (Stretch)
            # End: If Mode=Duration -> Shift (Move interval), Else -> Modify (Stretch)
            
            if target == "end" and is_dur_mode:
                # SHIFT (Сдвиг всего интервала)
                op_arg = "add" if op == "add" else "sub"
                ns, ne = self.mgrs["range"].shift_range(mins, op_arg)
                
                # Обновляем оба поля
                or_ent.delete(0, tk.END); or_ent.insert(0, ns)
                end_ent.delete(0, tk.END); end_ent.insert(0, ne)
            
            else:
                # STRETCH (Изменение одной границы)
                key = "or_range_val" if target == "start" else "end_range_val"
                nt = self.mgrs["range"].modify_time(key, mins, op)
                w.delete(0, tk.END); w.insert(0, nt)

            self.update_diff()

        # Кнопки Start
        btns_s_frame = tk.Frame(fr, bg=self.theme["range_bg"])
        btns_s_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
        tk.Button(btns_s_frame, text="-", width=4, command=lambda: do_math("start", or_ent, "sub")).pack(side="left", fill="x", expand=True)
        tk.Button(btns_s_frame, text="+", width=4, command=lambda: do_math("start", or_ent, "add")).pack(side="left", fill="x", expand=True)
        
        # Кнопки End
        btns_e_frame = tk.Frame(fr, bg=self.theme["range_bg"])
        btns_e_frame.grid(row=5, column=2, columnspan=2, sticky="ew")
        tk.Button(btns_e_frame, text="-", width=4, command=lambda: do_math("end", end_ent, "sub")).pack(side="left", fill="x", expand=True)
        tk.Button(btns_e_frame, text="+", width=4, command=lambda: do_math("end", end_ent, "add")).pack(side="left", fill="x", expand=True)
        
        # Сохраняем ссылки на кнопки Range для блокировки (если нужно будет)
        # Для простоты сохраняем фреймы
        self.register_widget("range_btns_s", btns_s_frame)
        self.register_widget("range_btns_e", btns_e_frame)


    # ================= DURATION MODULE =================
    def draw_duration(self, parent, cfg):
        fr = tk.LabelFrame(parent, text="DURATION", bg=self.theme["duration_bg"], font=("Arial", 10, "bold"))
        fr.pack(fill="x", padx=10, pady=5)
        
        # --- Row 0: Config ---
        top_frame = tk.Frame(fr, bg=self.theme["duration_bg"])
        top_frame.pack(fill="x", pady=2)
        
        s_opts = cfg.get("step_options", [5, 125, 5])
        default_val = cfg.get("defaults", {}).get("value", 30)
        
        tk.Label(top_frame, text="Step:", bg=self.theme["duration_bg"]).pack(side="left")
        sc = ttk.Combobox(top_frame, values=list(range(*s_opts)), width=5, state="readonly")
        sc.pack(side="left", padx=5)
        sc.set(s_opts[0])
        
        tk.Label(top_frame, text="Value:", bg=self.theme["duration_bg"]).pack(side="left")
        vc = ttk.Combobox(top_frame, width=5, state="readonly")
        vc.pack(side="left", padx=5)
        
        self.register_widget("dur_step", sc)
        self.register_widget("dur_val", vc)
        
        def upd(e): 
            val = int(sc.get())
            vc["values"] = list(range(val, 181, val))
            if default_val in vc["values"]: vc.set(default_val)
            else: vc.set(val)
        sc.bind("<<ComboboxSelected>>", upd)
        upd(None)
        
        # --- Row 1: Actions + Info ---
        act_frame = tk.Frame(fr, bg=self.theme["duration_bg"])
        act_frame.pack(fill="x", pady=5)
        
        lbl_fixed = tk.Label(act_frame, text="", fg="gray", bg=self.theme["duration_bg"])
        
        def apply():
            if "or_entry" not in self.tab.widgets: return
            mins = int(vc.get())
            ns, ne = self.mgrs["range"].sync_start_from_end_and_duration(mins)
            
            # Update Range widgets
            self.tab.widgets["or_entry"].delete(0, tk.END); self.tab.widgets["or_entry"].insert(0, ns)
            self.tab.widgets["end_entry"].delete(0, tk.END); self.tab.widgets["end_entry"].insert(0, ne)
            
            # Update Fix Label
            now_time = datetime.now().strftime("%H:%M")
            lbl_fixed.config(text=f"(fix: {now_time})")
            
            self.update_diff()
            
        bn = tk.Button(act_frame, text="Update", command=apply, bg="white")
        bn.pack(side="left", padx=10)
        self.register_widget("dur_btn", bn)
        
        lbl_fixed.pack(side="left")
        
        # --- Diff Label ---
        self.lbl_diff = tk.Label(act_frame, text="Diff: --", font=("Arial", 10, "bold"), bg=self.theme["duration_bg"], fg="#2c3e50")
        self.lbl_diff.pack(side="right", padx=10)
        
        # Initial calc
        self.update_diff()

    def update_diff(self):
        """Пересчитывает разницу между Start и End и обновляет лейбл"""
        # Этот метод вызывается из Range (при вводе) и Duration (при update)
        if hasattr(self, 'lbl_diff') and self.lbl_diff.winfo_exists():
            mins = self.mgrs["range"].get_duration_minutes()
            if mins is not None:
                self.lbl_diff.config(text=f"Diff: {mins} min")
                
                # Опционально: синхронизировать комбобокс Value, если числа совпадают
                # Но пока оставим ручной выбор, чтобы не сбивать настройки шага
            else:
                self.lbl_diff.config(text="Diff: --")