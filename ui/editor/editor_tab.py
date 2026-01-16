# Path: ui/editor/editor_tab.py
# Version: 17.0
# Description: Вкладка редактора. Поддержка сохранения полного конфига для MAIN.

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import copy
from core import config_gen, schema
from core.storage import Storage
from ui.editor.renders import ModuleRenderer

class EditorTab:
    def __init__(self, notebook, theme, input_tab_ref, fas_config):
        self.frame = tk.Frame(notebook, bg=theme["window_bg"])
        self.theme = theme
        self.app = input_tab_ref
        self.fas_data = fas_config
        
        self.current_path = []
        self.module_frames = {}
        self.state_vars = {}
        self.current_delta = {} 
        
        self.renderer = ModuleRenderer(self, theme, fas_config)
        self._setup_layout()
        self.rebuild_tree()

    def _setup_layout(self):
        paned = tk.PanedWindow(self.frame, orient="horizontal", bg=self.theme["window_bg"], sashwidth=4)
        paned.pack(fill="both", expand=True)

        # LEFT
        left = tk.Frame(paned, bg=self.theme["window_bg"]); paned.add(left, minsize=300, width=350)
        tk.Label(left, text="ИЕРАРХИЯ", font=("Arial", 10, "bold"), bg=self.theme["window_bg"]).pack(pady=5)
        
        btn_box = tk.Frame(left, bg=self.theme["window_bg"]); btn_box.pack(fill="x", padx=5)
        tk.Button(btn_box, text="+ Узел", command=self.add_child_node, bg="white").pack(side="left", fill="x", expand=True)
        tk.Button(btn_box, text="- Удалить", command=self.delete_node, bg="white", fg="#c0392b").pack(side="left", fill="x", expand=True)
        tk.Button(btn_box, text="Expand All", command=self.expand_all_nodes, bg="white").pack(side="right", fill="x", expand=True)
        
        self.tree = ttk.Treeview(left); scr = ttk.Scrollbar(left, command=self.tree.yview); self.tree.configure(yscrollcommand=scr.set)
        scr.pack(side="right", fill="y"); self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # RIGHT
        right = tk.Frame(paned, bg=self.theme["editor_bg"]); paned.add(right, minsize=500)
        cv = tk.Canvas(right, bg=self.theme["editor_bg"], highlightthickness=0)
        sb = ttk.Scrollbar(right, command=cv.yview)
        self.scroll_frame = tk.Frame(cv, bg=self.theme["editor_bg"])
        self.scroll_frame.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cw = cv.create_window((0,0), window=self.scroll_frame, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfig(cw, width=e.width))
        cv.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)
        
        self.lbl_path = tk.Label(self.scroll_frame, text="Select Node", bg=self.theme["editor_bg"], fg="white", font=("Consolas", 11))
        self.lbl_path.pack(pady=10, fill="x")
        
        self.modules_container = tk.Frame(self.scroll_frame, bg=self.theme["editor_bg"]); self.modules_container.pack(fill="x", padx=10)
        self.am_frame = tk.LabelFrame(self.modules_container, text="Active Modules", bg=self.theme["editor_bg"], fg="white", padx=5, pady=5); self.am_frame.pack(fill="x", pady=5)
        
        pb = tk.Frame(self.scroll_frame, bg=self.theme["editor_bg"]); pb.pack(fill="x", padx=10, pady=10)
        tk.Label(pb, text="Effective (View):", bg=self.theme["editor_bg"], fg="#bdc3c7").grid(row=0, column=0, sticky="w")
        tk.Label(pb, text="Delta (Save):", bg=self.theme["editor_bg"], fg="#27ae60").grid(row=0, column=1, sticky="w")
        self.txt_eff = tk.Text(pb, height=8, width=40, bg="#34495e", fg="white", font=("Consolas", 8)); self.txt_eff.grid(row=1, column=0, padx=5)
        self.txt_diff = tk.Text(pb, height=8, width=40, bg="#2c3e50", fg="#f1c40f", font=("Consolas", 8)); self.txt_diff.grid(row=1, column=1, padx=5)
        
        tk.Button(self.scroll_frame, text="SAVE CHANGES", bg=self.theme["btn_save"], fg="white", font=("Arial", 12, "bold"), command=self.save_current_node).pack(pady=20)

    # --- Tree ---
    def rebuild_tree(self):
        self.tree.delete(*self.tree.get_children())
        rid = self.tree.insert("", "end", text="main", open=True, values=("main",))
        self._build_rec(rid, self.fas_data["category"]["main"].get("children", {}))
    def _build_rec(self, pid, children):
        for k, v in children.items():
            nid = self.tree.insert(pid, "end", text=k, open=False)
            if "children" in v: self._build_rec(nid, v["children"])
    def expand_all_nodes(self):
        def ex(i):
            self.tree.item(i, open=True)
            for c in self.tree.get_children(i): ex(c)
        for r in self.tree.get_children(): ex(r)
    def on_tree_select(self, e):
        sel = self.tree.selection()
        if not sel: return
        path = []
        c = sel[0]
        while c:
            path.insert(0, self.tree.item(c, "text"))
            c = self.tree.parent(c)
        self.current_path = path[1:] if path[0] == "main" else path
        self.lbl_path.config(text=f"Node: main / {'/'.join(self.current_path)}")
        self.render_editor()

    # --- Render ---
    def render_editor(self):
        for w in self.am_frame.winfo_children(): w.destroy()
        for m in ["range", "duration", "checkboxes", "tags"]:
            if m in self.module_frames: self.module_frames[m].destroy()
        self.module_frames = {}
        self.state_vars = {}
        
        inh = config_gen.resolve_config(self.fas_data, self.current_path)
        active = inh.get("active_modules", [])
        
        MODULE_ORDER = ["range", "duration", "checkboxes", "tags"]
        for mod in MODULE_ORDER:
            var = tk.BooleanVar(value=(mod in active))
            self.state_vars[mod] = var
            tk.Checkbutton(self.am_frame, text=mod.title(), variable=var, 
                           command=self.refresh_frames_visibility,
                           bg=self.theme["editor_bg"], fg="white", selectcolor="#2c3e50").pack(side="left", padx=10)
            
            bk = f"{'check' if mod=='checkboxes' else mod}_bg"
            if mod=="tags": bk="tags_bg"
            fr = tk.LabelFrame(self.modules_container, text=mod.title(), bg=self.theme[bk], padx=5, pady=5)
            self.module_frames[mod] = fr
            
            if mod=="range": self.renderer.render_range(fr, inh.get("range_module", {}))
            elif mod=="duration": self.renderer.render_duration(fr, inh.get("duration_module", {}))
            elif mod=="checkboxes": self.renderer.render_checkboxes(fr, inh.get("checkboxes_module", []))
            elif mod=="tags": self.renderer.render_tags(fr, inh.get("tags_module", []))
        
        self.refresh_frames_visibility()

    def refresh_frames_visibility(self):
        for f in self.module_frames.values(): f.pack_forget()
        MODULE_ORDER = ["range", "duration", "checkboxes", "tags"]
        for mod in MODULE_ORDER:
            if self.state_vars[mod].get(): self.module_frames[mod].pack(fill="x", pady=5)
        self.update_preview()

    def update_preview(self):
        ui_conf = {"active_modules": [m for m, v in self.state_vars.items() if v.get()]}
        
        if self.state_vars.get("range") and self.state_vars["range"].get():
            v = self.module_frames["range"].vars
            try: s = [int(x) for x in v["step"].get().split(",")]
            except: s = [5,60,5]
            try: d = int(v["def"].get())
            except: d = 15
            ui_conf["range_module"] = {"step_options": s, "defaults": {"value": d}}
            
        if self.state_vars.get("duration") and self.state_vars["duration"].get():
            v = self.module_frames["duration"].vars
            try: s = [int(x) for x in v["step"].get().split(",")]
            except: s = [5,125,5]
            try: d = int(v["def"].get())
            except: d = 30
            ui_conf["duration_module"] = {"step_options": s, "defaults": {"value": d}}
            
        if self.state_vars.get("checkboxes") and self.state_vars["checkboxes"].get():
            ui_conf["checkboxes_module"] = self.renderer.get_data(self.module_frames["checkboxes"], "checkboxes")
        if self.state_vars.get("tags") and self.state_vars["tags"].get():
            ui_conf["tags_module"] = self.renderer.get_data(self.module_frames["tags"], "tags")
        
        self.txt_eff.delete("1.0", tk.END); self.txt_eff.insert("1.0", json.dumps(ui_conf, ensure_ascii=False, indent=4))
        
        # --- LOGIC FOR MAIN VS CHILD ---
        if not self.current_path:
            # Main: Full Save
            self.current_delta = copy.deepcopy(ui_conf)
        else:
            # Child: Delta Save
            parent = config_gen.resolve_config(self.fas_data, self.current_path[:-1])
            self.current_delta = self._calc_delta(parent, ui_conf)
            
        self.txt_diff.delete("1.0", tk.END); self.txt_diff.insert("1.0", json.dumps(self.current_delta, ensure_ascii=False, indent=4))

    def _calc_delta(self, parent, curr):
        if not parent: return copy.deepcopy(curr)
        out = {}
        for k, v in curr.items():
            pv = parent.get(k)
            # If values differ or parent doesn't have it -> save to delta
            if isinstance(v, dict) and isinstance(pv, dict):
                d = self._calc_delta(pv, v)
                if d: out[k] = d
            elif v != pv:
                out[k] = copy.deepcopy(v)
        return out

    def save_current_node(self):
        cur = self.fas_data["category"]["main"]
        for p in self.current_path: cur = cur["children"][p]
        cur["supported_types"] = self.current_delta
        Storage.save_json_atomic(schema.FAS_PATH, self.fas_data)
        messagebox.showinfo("OK", "Saved"); self.app.init_navigation()

    def add_child_node(self):
        if not self.tree.selection(): return
        nm = simpledialog.askstring("New", "Name:")
        if not nm: return
        cur = self.fas_data["category"]["main"]
        for p in self.current_path: cur = cur["children"][p]
        if "children" not in cur: cur["children"] = {}
        cur["children"][nm] = {"supported_types": {}, "children": {}}
        Storage.save_json_atomic(schema.FAS_PATH, self.fas_data); self.rebuild_tree()

    def delete_node(self):
        if not self.current_path: return
        if messagebox.askyesno("Del", "Delete?"):
            p = self.current_path[:-1]; cur = self.fas_data["category"]["main"]
            for step in p: cur = cur["children"][step]
            del cur["children"][self.current_path[-1]]
            Storage.save_json_atomic(schema.FAS_PATH, self.fas_data); self.rebuild_tree()