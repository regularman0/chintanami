# Path: ui/input/generators/list_gens.py
# Version: 18.1
# Description: Генераторы списков (Input Tab). Исправлен Lookup чекбоксов и расположение кнопок.

import tkinter as tk
from tkinter import ttk
from core import schema
from .base import BaseGenerator

class ListGenerator(BaseGenerator):

    # ================= CHECKBOXES =================
    def draw_checks(self, parent, mod_list):
        fr = tk.LabelFrame(parent, text="CHECKBOXES", bg=self.theme["check_bg"], font=("Arial", 10, "bold"))
        fr.pack(fill="x", padx=10, pady=5)
        
        for cb_s in mod_list:
            self._render_cb_group(fr, cb_s)

    def _render_cb_group(self, parent, node_schema):
        # node_schema = {"list": "done", "number": 1...} ИЛИ {"db_name": "...", ...}
        
        # 1. Пытаемся понять, это ссылка (list) или кастом (db_name)
        # В новой миграции мы договорились использовать "list" для ссылок, 
        # но старый код мог оставить "db_name" как ключ.
        
        # Ключ поиска в глобальном списке
        ref_key = node_schema.get("list") or node_schema.get("db_name")
        
        # Ищем в глобальном конфиге
        global_def = self.fas_config.get("checkboxes_list", {}).get(ref_key)

        if global_def:
            # ЭТО ГЛОБАЛЬНЫЙ ЧЕКБОКС
            real_db_name = global_def.get("db_name", ref_key)
            real_label = global_def.get("label_name", ref_key)
            # Используем ref_key как уникальный идентификатор группы в UI
            group_id = ref_key 
        else:
            # ЭТО КАСТОМНЫЙ ЧЕКБОКС (определен прямо в узле)
            real_db_name = node_schema.get("db_name", "UNKNOWN")
            real_label = node_schema.get("label_name", "Unknown")
            group_id = real_db_name

        # Конфиг для логики
        full_cb_config = {
            "db_name": real_db_name,
            "label_name": real_label,
            "number": node_schema.get("number", 1),
            "add": node_schema.get("add", False)
        }
        
        # Формируем префикс (DONE -> DONE_)
        prefix = real_db_name
        if not prefix.endswith("_"): prefix += "_"
        
        # Визуал
        sub = tk.Frame(parent, bg=self.theme["check_bg"])
        sub.pack(fill="x", pady=2)
        
        items_frame = tk.Frame(sub, bg=self.theme["check_bg"])
        items_frame.pack(fill="x", side="top")
        
        self.tab.rendered_checkbox_groups[group_id] = {
            "items_frame": items_frame,
            "schema": full_cb_config, 
            "prefix": prefix, 
            "items": []
        }
        
        # Рендерим элементы
        cnt = max(full_cb_config["number"], self.mgrs["check"].get_max_index(prefix))
        for i in range(1, cnt+1):
            self._add_cb_widget(group_id, i)
            
        # Кнопки (Строго внизу)
        if full_cb_config["add"]:
            btn_box = tk.Frame(sub, bg=self.theme["check_bg"])
            btn_box.pack(fill="x", pady=2, side="bottom")
            tk.Button(btn_box, text="+", width=2, command=lambda k=group_id: self._add_cb_widget(k)).pack(side="left")
            tk.Button(btn_box, text="-", width=2, command=lambda k=group_id: self._rem_cb_widget(k)).pack(side="left")

    def _add_cb_widget(self, key, idx=None):
        g = self.tab.rendered_checkbox_groups[key]
        if idx is None: idx = len(g["items"]) + 1
        
        fn = schema.normalize_db_name(g["prefix"], idx)
        ent = self.mgrs["check"].get_entry(fn)
        chk = ent is not None
        ts = ent["change_time"] if chk else ""
        
        row = tk.Frame(g["items_frame"], bg=self.theme["check_bg"])
        row.pack(anchor="w")
        
        var = tk.BooleanVar(value=chk)
        l = tk.Label(row, text=f"({ts})", bg=self.theme["check_bg"], fg="gray", font=("Arial", 8))
        
        def tog():
            nt = self.mgrs["check"].toggle(fn, var.get())
            l.config(text=f"({nt})" if nt else "")
            
        text_label = f"{g['schema']['label_name']} ({fn})"
        cb_widget = tk.Checkbutton(row, text=text_label, variable=var, 
                                   command=tog, bg=self.theme["check_bg"])
        cb_widget.pack(side="left")
        l.pack(side="left")
        
        g["items"].append({
            "frame": row, 
            "var": var, 
            "db_name": fn, 
            "index": idx, 
            "label": cb_widget, 
            "label_base": g['schema']['label_name'], 
            "time_label": l
        })

    def _rem_cb_widget(self, key):
        g = self.tab.rendered_checkbox_groups[key]
        if len(g["items"]) > 1:
            item = g["items"].pop()
            item["frame"].destroy()
            
            snap = []
            for i in g["items"]:
                snap.append({
                    "is_checked": i["var"].get(),
                    "db_name": i["db_name"],
                    "index": i["index"],
                    "label": i["label"],      # Передаем виджет
                    "label_base": i["label_base"]
                })
            
            new_data_list = self.mgrs["check"].rebuild_numbering(g["prefix"], snap)
            
            # Обновляем замыкания для оставшихся
            for widget_dict, new_data in zip(g["items"], new_data_list):
                widget_dict["db_name"] = new_data["db_name"]
                widget_dict["index"] = new_data["index"]
                
                cur_fn = new_data["db_name"]
                cur_var = widget_dict["var"]
                cur_lbl = widget_dict["time_label"]
                
                def new_tog(f=cur_fn, v=cur_var, l=cur_lbl):
                    nt = self.mgrs["check"].toggle(f, v.get())
                    l.config(text=f"({nt})" if nt else "")
                
                widget_dict["label"].config(command=new_tog)

    # ================= TAGS =================
    def draw_tags(self, parent, mod_list):
        fr = tk.LabelFrame(parent, text="TAGS", bg=self.theme["tags_bg"], font=("Arial", 10, "bold"))
        fr.pack(fill="x", padx=10, pady=5)
        
        for t_s in mod_list:
            self._render_tag_group(fr, t_s)

    def _render_tag_group(self, parent, schema_item):
        ln = schema_item["list"]
        cfg = self.fas_config["tag_lists"].get(ln, {
            "label_name": schema_item.get("label_name", ln), 
            "db_name": schema_item.get("db_name", ln.upper()), 
            "value": {}
        })
        prefix = cfg["db_name"]
        if not prefix.endswith("_"): prefix += "_"
        
        sub = tk.Frame(parent, bg=self.theme["tags_bg"])
        sub.pack(fill="x", pady=2)
        tk.Label(sub, text=cfg["label_name"], bg=self.theme["tags_bg"], font=("Arial", 9, "bold")).pack(anchor="w")
        
        items_frame = tk.Frame(sub, bg=self.theme["tags_bg"])
        items_frame.pack(fill="x", side="top")
        
        self.tab.rendered_tag_groups[ln] = {
            "items_frame": items_frame, 
            "cfg": cfg, "prefix": prefix, "items": []
        }
        
        cnt = max(schema_item.get("number", 1), self.mgrs["tag"].get_max_index(prefix))
        for i in range(1, cnt+1):
            self._add_tag_widget(ln, i)
        
        if schema_item.get("add", False):
            btn_box = tk.Frame(sub, bg=self.theme["tags_bg"])
            btn_box.pack(fill="x", pady=2, side="bottom")
            tk.Button(btn_box, text="+", width=2, command=lambda: self._add_tag_widget(ln)).pack(side="left")
            tk.Button(btn_box, text="-", width=2, command=lambda: self._rem_tag_widget(ln)).pack(side="left")

    def _add_tag_widget(self, l_name, idx=None):
        g = self.tab.rendered_tag_groups[l_name]
        cfg = g["cfg"]
        if idx is None: idx = len(g["items"]) + 1
        
        fn = schema.normalize_db_name(g["prefix"], idx)
        ent = self.mgrs["tag"].get_entries(g["prefix"])
        val = next((x["value"] for x in ent if x["db_name"] == fn), None)
        
        box = tk.Frame(g["items_frame"], bg=self.theme["tags_bg"])
        box.pack(anchor="w", pady=1)
        
        lbl = tk.Label(box, text=f"{cfg['label_name']} ({fn}):", bg=self.theme["tags_bg"])
        lbl.pack(side="left")
        
        val_cfg = cfg.get("value", {})
        item_data = {"frame": box, "db_name": fn, "index": idx, "label": lbl, "label_base": cfg['label_name']}
        
        # --- SIMPLE LIST ---
        if "list_range" in val_cfg:
            lr = val_cfg["list_range"]
            vals = list(range(lr[0], lr[1], lr[2]))
            cb = ttk.Combobox(box, values=vals, width=8, state="readonly")
            cb.pack(side="left")
            if val: cb.set(val)
            
            cb.bind("<<ComboboxSelected>>", lambda e: self.mgrs["tag"].update_value(fn, cb.get()))
            tk.Button(box, text="X", width=2, command=lambda: [cb.set(""), self.mgrs["tag"].update_value(fn, "")]).pack(side="left", padx=5)
            
            item_data["type"] = "simple"
            item_data["combo"] = cb
            
        # --- TREE LOGIC ---
        elif "type" in val_cfg and val_cfg["type"] == "tree":
            chain_frame = tk.Frame(box, bg=self.theme["tags_bg"])
            chain_frame.pack(side="left")
            chain = []
            
            def build(node_dict):
                c = ttk.Combobox(chain_frame, values=list(node_dict.keys()), width=12, state="readonly")
                c.pack(side="left", padx=2)
                chain.append(c)
                
                def on_sel(e):
                    ix = chain.index(c)
                    while len(chain) > ix + 1:
                        chain.pop().destroy()
                    
                    nxt = node_dict.get(c.get(), {}).get("children", {})
                    if nxt: build(nxt)
                    
                    path = "/".join([x.get() for x in chain if x.get()])
                    self.mgrs["tag"].update_value(fn, path)
                
                c.bind("<<ComboboxSelected>>", on_sel)
                return c

            root_node = self.fas_config.get("category", {}).get("main", {}).get("children", {})
            if val:
                cursor = root_node
                try:
                    for part in val.split("/"):
                        c = build(cursor); c.set(part); cursor = cursor[part].get("children", {})
                except: pass
            else:
                build(root_node)
            
            item_data["type"] = "tree"
            item_data["chain"] = chain
            
        else:
            cb = ttk.Combobox(box, width=15); cb.pack(side="left")
            if val: cb.set(val)
            item_data["type"] = "simple"; item_data["combo"] = cb

        g["items"].append(item_data)

    def _rem_tag_widget(self, l_name):
        g = self.tab.rendered_tag_groups[l_name]
        if len(g["items"]) > 1:
            item = g["items"].pop()
            item["frame"].destroy()
            
            snap = []
            for i in g["items"]:
                val = ""
                if i.get("type") == "tree":
                    val = "/".join([c.get() for c in i["chain"] if c.get()])
                elif "combo" in i:
                    val = i["combo"].get()
                snap.append({
                    "current_value": val,
                    "db_name": i["db_name"],
                    "index": i["index"],
                    "label_base": i["label_base"],
                    "label": i["label"]
                })
            
            self.mgrs["tag"].rebuild_numbering(g["prefix"], snap)