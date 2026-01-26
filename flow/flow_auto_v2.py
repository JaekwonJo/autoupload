import json
import os
import time
import random
import threading
import math
import traceback 
from pathlib import Path
from datetime import datetime
import ctypes
import importlib 

# [CRITICAL] 윈도우/리눅스(WSL) 호환성 체크
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

# [비전 봇 핵심 모듈]
import pyautogui
import pyperclip

# [NEW] 인간 행동 엔진 탑재
try:
    import flow.human_behavior_v2 as hb
    importlib.reload(hb) 
    from flow.human_behavior_v2 import HumanActor
except ImportError:
    from flow.human_behavior_v2 import HumanActor

# --- 윈도우 절전 방지 ---
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

APP_NAME = "Flow Veo Vision Bot (Ultimate V2)"
CONFIG_FILE = "flow_config.json"
DEFAULT_CONFIG = {
    "prompts_file": "flow_prompts.txt",
    "prompts_separator": "|||",
    "interval_seconds": 180,
    "input_area": None,
    "submit_area": None,
    "afk_area": None,
    "afk_mode": False,
    "prompt_slots": [],
    "active_prompt_slot": 0,
    "sound_enabled": True,
    "relay_mode": False,
    "relay_count": 1
}

# [TOOLTIP] 친절한 설명서 풍선 기능
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        label = tk.Label(tw, text=self.text, justify="left",
                         background="#F1FA8C", foreground="black", relief="solid", borderwidth=1,
                         font=("Malgun Gothic", 9, "normal"), padx=5, pady=3)
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw: tw.destroy()

# [ALARM] 휴식 종료 임박 알림
class CountdownAlert:
    def __init__(self, master, seconds=30, sound_enabled=True):
        self.root = tk.Toplevel(master)
        self.sound_enabled = sound_enabled
        self.root.title("알림")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="#282A36")
        
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 300, 100 
        x = sw - w - 20
        y = sh - h - 100
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        frame = tk.Frame(self.root, bg="#282A36", highlightbackground="#BD93F9", highlightthickness=2)
        frame.pack(fill="both", expand=True)
        
        tk.Label(frame, text="⚡ 봇 출동 준비!", font=("Malgun Gothic", 11, "bold"), bg="#282A36", fg="#FF79C6").pack(pady=5)
        self.lbl_time = tk.Label(frame, text=f"{seconds}초 전", font=("Malgun Gothic", 16, "bold"), bg="#282A36", fg="#50FA7B")
        self.lbl_time.pack()

    def update_time(self, seconds):
        if not self.root.winfo_exists(): return
        self.lbl_time.config(text=f"{int(seconds)}초 전")
        if self.sound_enabled and WINSOUND_AVAILABLE and seconds <= 5:
            try: winsound.Beep(1000, 100)
            except: pass

    def close(self):
        try: self.root.destroy()
        except: pass

def load_config_from_file(path):
    if not path.exists(): return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        for k, v in DEFAULT_CONFIG.items():
            if k not in data: data[k] = v
        return data
    except: return DEFAULT_CONFIG.copy()

class FlowVisionApp:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / CONFIG_FILE
        self.cfg = load_config_from_file(self.cfg_path)
        
        self.running = False
        self.is_processing = False 
        self.prompts = []
        self.index = 0
        self.t_next = None
        self.alert_window = None
        self.relay_progress = 0 
        self.actor = HumanActor()
        
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1000x750") 
        self.root.configure(bg="#1E1E2E")
        
        try:
            icon_path = self.base.parent / "icon.ico"
            if icon_path.exists(): self.root.iconbitmap(str(icon_path))
        except: pass
        
        # [STYLE] Cyber-Modern UI
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.color_bg = "#1E1E2E"
        self.color_card = "#282A36"
        self.color_accent = "#BD93F9"
        self.color_success = "#50FA7B"
        self.color_error = "#FF5555"
        self.color_info = "#8BE9FD"
        self.color_text = "#F8F8F2"
        
        self.style.configure("TFrame", background=self.color_bg)
        self.style.configure("Card.TFrame", background=self.color_card, relief="flat")
        self.style.configure("TLabelframe", background=self.color_bg, foreground=self.color_accent)
        self.style.configure("TLabelframe.Label", background=self.color_bg, foreground=self.color_accent, font=("Malgun Gothic", 10, "bold"))
        self.style.configure("TLabel", background=self.color_bg, foreground=self.color_text)
        self.style.configure("TButton", background="#44475A", foreground="white", borderwidth=0, font=("Malgun Gothic", 9))
        self.style.map("TButton", background=[('active', '#6272A4')])
        self.style.configure("Horizontal.TProgressbar", background=self.color_accent, troughcolor="#44475A", bordercolor=self.color_card, thickness=15)
        self.style.configure("Action.TButton", background=self.color_success, foreground="#282A36", font=("Malgun Gothic", 10, "bold"))
        self.style.map("Action.TButton", background=[('active', '#FF79C6')])

        self._ensure_prompt_slots()
        self._build_ui()
        self.on_reload()
        self.root.after(1000, self._tick)

    def play_sound(self, category):
        if not self.cfg.get("sound_enabled", True) or not WINSOUND_AVAILABLE: return 
        try:
            if category == "start": winsound.MessageBeep(winsound.MB_OK)
            elif category == "success": winsound.Beep(800, 200)
            elif category == "finish": winsound.MessageBeep(winsound.MB_ICONHAND)
        except: pass

    def save_config(self):
        try: self.cfg_path.write_text(json.dumps(self.cfg, indent=4, ensure_ascii=False), encoding='utf-8')
        except: pass

    def _ensure_prompt_slots(self):
        if "prompt_slots" not in self.cfg or not self.cfg["prompt_slots"]:
            self.cfg["prompt_slots"] = [{"name": "기본 슬롯", "file": "flow_prompts.txt"}]
            self.cfg["active_prompt_slot"] = 0
            self.save_config()

    def update_status_label(self, text, color):
        self.lbl_main_status.config(text=text, fg=color)

    def _build_ui(self):
        # 1. Header
        header = tk.Frame(self.root, bg=self.color_card, height=60)
        header.pack(fill="x", side="top")
        tk.Label(header, text="🌊 FLOW VISION CONTROLLER", font=("Impact", 20), bg=self.color_card, fg=self.color_accent).pack(side="left", padx=20)
        self.lbl_main_status = tk.Label(header, text="READY", font=("Malgun Gothic", 12, "bold"), bg=self.color_card, fg="#6272A4")
        self.lbl_main_status.pack(side="right", padx=20)

        # 2. Body
        mid_frame = tk.Frame(self.root, bg=self.color_bg, pady=10)
        mid_frame.pack(fill="both", expand=True, padx=20)

        # --- Left: Settings ---
        left_card = ttk.LabelFrame(mid_frame, text=" ⚙️ SETTINGS ", padding=15)
        left_card.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        tk.Label(left_card, text="1. 마우스 타겟 지정", font=("Malgun Gothic", 9, "bold")).pack(anchor="w")
        btn_area = tk.Frame(left_card, bg=self.color_bg)
        btn_area.pack(fill="x", pady=5)
        
        b1 = ttk.Button(btn_area, text="입력창", width=8, command=lambda: self.start_capture("input"))
        b1.pack(side="left", padx=2)
        ToolTip(b1, "텍스트 입력 박스 지정")
        b2 = ttk.Button(btn_area, text="버튼", width=8, command=lambda: self.start_capture("submit"))
        b2.pack(side="left", padx=2)
        ToolTip(b2, "생성/제출 버튼 지정")
        b3 = ttk.Button(btn_area, text="딴짓", width=8, command=lambda: self.start_capture("afk"))
        b3.pack(side="left", padx=2)
        ToolTip(b3, "봇이 쉴 때 머무를 안전한 빈 공간 지정")
        
        self.lbl_coords = tk.Label(left_card, text=self._get_coord_text(), font=("Consolas", 8), fg="#6272A4")
        self.lbl_coords.pack(anchor="w", pady=(0, 15))
        
        tk.Label(left_card, text="2. 자동화 옵션", font=("Malgun Gothic", 9, "bold")).pack(anchor="w")
        
        c1 = tk.Checkbutton(left_card, text="🔊 소리 알림", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, fg=self.color_info, selectcolor=self.color_bg, activebackground=self.color_bg)
        self.sound_var = tk.BooleanVar(value=self.cfg.get("sound_enabled", True))
        c1.config(variable=self.sound_var)
        c1.pack(anchor="w")
        
        c2 = tk.Checkbutton(left_card, text="👻 AFK(딴짓) 모드", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, fg="#F1FA8C", selectcolor=self.color_bg, activebackground=self.color_bg)
        self.afk_var = tk.BooleanVar(value=self.cfg.get("afk_mode", False))
        c2.config(variable=self.afk_var)
        c2.pack(anchor="w")
        
        relay_f = tk.Frame(left_card, bg=self.color_bg)
        relay_f.pack(fill="x", pady=5)
        c3 = tk.Checkbutton(relay_f, text="🏃 이어달리기", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, fg="#FF79C6", selectcolor=self.color_bg, activebackground=self.color_bg)
        self.relay_var = tk.BooleanVar(value=self.cfg.get("relay_mode", False))
        c3.config(variable=self.relay_var)
        c3.pack(side="left")
        self.relay_cnt_var = tk.IntVar(value=self.cfg.get("relay_count", 1))
        sp = tk.Spinbox(relay_f, from_=1, to=10, width=3, textvariable=self.relay_cnt_var, command=self.on_option_toggle, bg=self.color_card, fg="white")
        sp.pack(side="left", padx=5)

        tk.Label(left_card, text="3. 작업 간격 (초)", font=("Malgun Gothic", 9, "bold")).pack(anchor="w", pady=(10, 5))
        self.entry_interval = tk.Entry(left_card, bg=self.color_card, fg=self.color_success, font=("Consolas", 12, "bold"), insertbackground="white")
        self.entry_interval.insert(0, str(self.cfg.get("interval_seconds", 180)))
        self.entry_interval.pack(fill="x", pady=5)

        tk.Frame(left_card, height=20, bg=self.color_bg).pack()
        self.btn_start = ttk.Button(left_card, text="▶ START AUTOMATION", style="Action.TButton", command=self.on_start)
        self.btn_start.pack(fill="x", ipady=10)
        self.btn_stop = ttk.Button(left_card, text="⏹ STOP", command=self.on_stop, state="disabled")
        self.btn_stop.pack(fill="x", pady=5)

        # --- Right: Dashboard ---
        right_panel = tk.Frame(mid_frame, bg=self.color_bg)
        right_panel.pack(side="right", fill="both", expand=True)
        
        prog_card = ttk.LabelFrame(right_panel, text=" 📊 TOTAL PROGRESS ", padding=15)
        prog_card.pack(fill="x", pady=(0, 10))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_card, variable=self.progress_var, maximum=100, mode='determinate', style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=5)
        info_f = tk.Frame(prog_card, bg=self.color_bg)
        info_f.pack(fill="x")
        self.lbl_prog_text = tk.Label(info_f, text="0 / 0 (0.0%)", font=("Consolas", 11, "bold"), fg=self.color_info)
        self.lbl_prog_text.pack(side="left")
        self.lbl_eta = tk.Label(info_f, text="--:-- 종료 예정", font=("Malgun Gothic", 10), fg="#6272A4")
        self.lbl_eta.pack(side="right")
        
        mon_card = ttk.LabelFrame(right_panel, text=" 👁️ BOT LIVE MONITOR ", padding=15)
        mon_card.pack(fill="both", expand=True)
        self.lbl_live_persona = tk.Label(mon_card, text="SLEEPING...", font=("Malgun Gothic", 18, "bold"), fg=self.color_accent)
        self.lbl_live_persona.pack(anchor="w")
        stat_f = tk.Frame(mon_card, bg=self.color_bg)
        stat_f.pack(fill="x", pady=15)
        
        tk.Label(stat_f, text="MOOD", fg="#6272A4").grid(row=0, column=0, sticky="w", padx=5)
        self.lbl_live_mood = tk.Label(stat_f, text="-", font=("Malgun Gothic", 12, "bold"), fg="white")
        self.lbl_live_mood.grid(row=1, column=0, sticky="w", padx=5)
        tk.Label(stat_f, text="SPEED", fg="#6272A4").grid(row=0, column=1, sticky="w", padx=30)
        self.speed_gauge = ttk.Progressbar(stat_f, length=120, mode='determinate')
        self.speed_gauge.grid(row=1, column=1, sticky="w", padx=30)
        self.lbl_speed_val = tk.Label(stat_f, text="x 1.0", font=("Consolas", 9), fg=self.color_accent)
        self.lbl_speed_val.grid(row=2, column=1, sticky="w", padx=30)
        tk.Label(stat_f, text="BATCH", fg="#6272A4").grid(row=0, column=2, sticky="w", padx=5)
        self.lbl_live_batch = tk.Label(stat_f, text="0 / 0", font=("Consolas", 12, "bold"), fg="white")
        self.lbl_live_batch.grid(row=1, column=2, sticky="w", padx=5)

        # 3. Bottom
        bottom = tk.Frame(self.root, bg=self.color_bg)
        bottom.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        file_f = tk.Frame(bottom, bg=self.color_bg)
        file_f.pack(fill="x", pady=5)
        tk.Label(file_f, text="📁 FILE:", font=("Consolas", 10, "bold"), fg=self.color_info).pack(side="left")
        self.slot_var = tk.StringVar()
        self.combo_slots = ttk.Combobox(file_f, textvariable=self.slot_var, state="readonly", width=12)
        self.combo_slots.pack(side="left", padx=5)
        self.combo_slots.bind("<<ComboboxSelected>>", self.on_slot_change)
        
        btn_nav = tk.Frame(file_f, bg=self.color_bg)
        btn_nav.pack(side="left", padx=10)
        ttk.Button(btn_nav, text="⏮", width=3, command=self.on_first).pack(side="left")
        ttk.Button(btn_nav, text="◀", width=3, command=self.on_prev).pack(side="left")
        self.lbl_nav_status = tk.Label(btn_nav, text="0/0", width=8, fg="white", font=("Consolas", 10))
        self.lbl_nav_status.pack(side="left")
        ttk.Button(btn_nav, text="▶", width=3, command=self.on_next).pack(side="left")
        ttk.Button(btn_nav, text="⏭", width=3, command=self.on_last).pack(side="left")
        
        ttk.Button(file_f, text="📂 OPEN", width=7, command=self.on_open_prompts).pack(side="right", padx=2)
        ttk.Button(file_f, text="🔄 REFRESH", width=10, command=self.on_reload).pack(side="right")

        txt_split = tk.Frame(bottom, bg=self.color_bg)
        txt_split.pack(fill="both", expand=True)
        p_frame = ttk.LabelFrame(txt_split, text=" PREVIEW ", padding=5)
        p_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.text_preview = ScrolledText(p_frame, height=6, bg=self.color_card, fg=self.color_text, borderwidth=0, font=("Consolas", 10))
        self.text_preview.pack(fill="both", expand=True)
        l_frame = ttk.LabelFrame(txt_split, text=" SYSTEM LOG ", padding=5)
        l_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        self.log_text = ScrolledText(l_frame, height=6, bg="#000000", fg="#8BE9FD", borderwidth=0, font=("Consolas", 10), state="disabled")
        self.log_text.pack(fill="both", expand=True)

    def on_option_toggle(self):
        self.cfg["afk_mode"] = self.afk_var.get()
        self.cfg["sound_enabled"] = self.sound_var.get()
        self.cfg["relay_mode"] = self.relay_var.get()
        try: self.cfg["relay_count"] = int(self.relay_cnt_var.get())
        except: self.cfg["relay_count"] = 1
        self.save_config()
        self.log(f"⚙️ 설정 동기화 완료")

    def _get_coord_text(self):
        ia, sa, aa = self.cfg.get('input_area'), self.cfg.get('submit_area'), self.cfg.get('afk_area')
        return f"입력창[{'✅' if ia else '❌'}] 버튼[{'✅' if sa else '❌'}] AFK[{'✅' if aa else '❌'}]"

    def log(self, msg):
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{ts}] {msg}\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        except: pass

    def start_capture(self, kind):
        def on_captured(x1, y1, x2, y2):
            self.cfg[f"{kind}_area"] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            self.save_config()
            self.lbl_coords.config(text=self._get_coord_text())
            messagebox.showinfo("성공", f"영역 저장 완료!")
        CaptureOverlay(self.root, on_captured, kind)

    def on_slot_change(self, event=None):
        idx = self.combo_slots.current()
        if idx >= 0:
            self.cfg["active_prompt_slot"] = idx
            self.cfg["prompts_file"] = self.cfg["prompt_slots"][idx]["file"]
            self.save_config()
            self.on_reload()

    def on_reload(self):
        try:
            path = self.base / self.cfg["prompts_file"]
            if not path.exists(): path.write_text("", encoding="utf-8")
            raw = path.read_text(encoding="utf-8")
            self.text_preview.delete("1.0", "end")
            self.text_preview.insert("1.0", raw)
            sep = self.cfg.get("prompts_separator", "|||")
            self.prompts = [p.strip() for p in raw.split(sep) if p.strip()]
            self.index = 0 if self.index >= len(self.prompts) else self.index
            self._update_progress_ui()
            self.log(f"로드 완료 ({len(self.prompts)}개)")
            slots = [s["name"] for s in self.cfg["prompt_slots"]]
            self.combo_slots["values"] = slots
            self.combo_slots.current(self.cfg["active_prompt_slot"])
        except: pass

    def _update_progress_ui(self):
        total = len(self.prompts)
        current = self.index
        self.lbl_nav_status.config(text=f"{current + 1} / {total}")
        if total > 0:
            pct = (current / total) * 100
            self.progress_var.set(pct)
            self.lbl_prog_text.config(text=f"{current} / {total} ({pct:.1f}%)")
        else:
            self.progress_var.set(0)
            self.lbl_prog_text.config(text="0 / 0 (0%)")

    def _update_monitor_ui(self):
        p_name = self.actor.current_persona_name
        mood = self.actor.current_mood
        speed = self.actor.cfg.get('speed_multiplier', 1.0)
        self.lbl_live_persona.config(text=p_name.upper())
        self.lbl_live_mood.config(text=mood.upper(), fg=self.color_info)
        self.speed_gauge['value'] = max(0, min(100, (speed - 0.5) * 66))
        self.lbl_speed_val.config(text=f"x{speed:.1f}")
        self.lbl_live_batch.config(text=f"{self.actor.processed_count} / {self.actor.current_batch_size}")

    def on_start(self):
        try:
            self.cfg["interval_seconds"] = int(self.entry_interval.get())
            self.save_config()
        except: pass
        if not (self.cfg.get('input_area') and self.cfg.get('submit_area')):
            messagebox.showwarning("주의", "먼저 영역을 설정해주세요.")
            return
        if self.relay_progress == 0:
            self.session_start_time = datetime.now()
            self.session_log = []
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.update_status_label("🚀 STARTING...", self.color_success)
        self.play_sound("start")
        self.actor.update_batch_size()
        self.actor.processed_count = 0
        self.t_next = time.time()

    def on_stop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.update_status_label("STOPPED", self.color_error)
        self.is_processing = False
        self.relay_progress = 0
        if self.alert_window:
            self.alert_window.close()
            self.alert_window = None

    def _tick(self):
        if self.running and self.t_next:
            remain = self.t_next - time.time()
            if remain > 0:
                if not self.is_processing:
                    self.update_status_label(f"⏳ WAITING... {int(remain)}s", "#F1FA8C")
                    if self.cfg.get("afk_mode") and self.cfg.get("afk_area"):
                        self.actor.idle_action(self.cfg["afk_area"])
            try: base = int(self.entry_interval.get())
            except: base = 180
            remain_cnt = len(self.prompts) - self.index
            total_sec = remain_cnt * base + max(0, int(remain))
            finish_time = datetime.fromtimestamp(time.time() + total_sec).strftime("%p %I:%M")
            self.lbl_eta.config(text=f"🏁 ETA: {finish_time}")

            if not self.is_processing and 0 < remain <= 30:
                if self.alert_window is None:
                    self.alert_window = CountdownAlert(self.root, remain, self.cfg.get("sound_enabled"))
                else:
                    self.alert_window.update_time(remain)
            
            if remain <= 0:
                if self.alert_window:
                    self.alert_window.close()
                    self.alert_window = None
                if not self.is_processing:
                    self.is_processing = True
                    threading.Thread(target=self._run_task, daemon=True).start()
                speed = self.actor.cfg.get('speed_multiplier', 1.0)
                interval = int(base + random.uniform(0, base * 0.3 * speed))
                self.t_next = time.time() + interval
        self.root.after(1000, self._tick)

    def _run_task(self):
        ia, sa = self.cfg.get('input_area'), self.cfg.get('submit_area')
        if not self.prompts or self.index >= len(self.prompts):
            self.save_session_report()
            if self.cfg.get("relay_mode"):
                curr = self.relay_progress + 1
                if curr < self.cfg.get("relay_count") and (self.cfg["active_prompt_slot"] + 1 < len(self.cfg["prompt_slots"])):
                    self.cfg["active_prompt_slot"] += 1
                    self.relay_progress = curr
                    self.index = 0
                    self.root.after(0, self.on_reload)
                    self.play_sound("success")
                    self.t_next = time.time() + 10
                    return
            self.on_stop()
            self.play_sound("finish")
            self.update_status_label("🎉 COMPLETE!", self.color_accent)
            return

        if self.actor.processed_count >= self.actor.current_batch_size:
            self.actor.take_bio_break(status_callback=lambda m: self.update_status_label(m, self.color_error))
            self.actor.current_batch_size = self.actor._get_random_batch_size()
            self.actor.processed_count = 0
            self.is_processing = False
            return

        try:
            self.actor.randomize_persona()
            self.root.after(0, self._update_monitor_ui)
            prompt = self.prompts[self.index]
            start_t = datetime.now()
            
            self.update_status_label("🖱️ MOVING...", "white")
            self.actor.move_to(random.randint(ia['x1'], ia['x2']), random.randint(ia['y1'], ia['y2']))
            pyautogui.click()
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            
            self.update_status_label("✍️ TYPING...", "white")
            self.actor.type_text(prompt, speed_callback=lambda s: self.root.after(0, lambda: self.lbl_speed_val.config(text=f"x{s}")))
            
            self.update_status_label("✅ DONE!", self.color_success)
            time.sleep(0.5)
            self.update_status_label("📖 REVIEWING...", self.color_info)
            self.actor.read_prompt_pause(prompt)
            
            self.update_status_label("🚀 SUBMITTING...", self.color_accent)
            if random.random() < self.cfg.get("enter_submit_rate", 0.5):
                time.sleep(0.5)
                pyautogui.press('enter')
            else:
                self.actor.move_to(random.randint(sa['x1'], sa['x2']), random.randint(sa['y1'], sa['y2']))
                self.actor.smart_click()
            
            self.log(f"SUCCESS #{self.index+1}")
            self.update_status_label("🎉 FINISHED!", self.color_success)
            self.play_sound("success")
            self.session_log.append({"index": self.index + 1, "prompt": prompt, "duration": f"{(datetime.now()-start_t).total_seconds():.1f}초"})
            self.actor.processed_count += 1
            self.index += 1
            
        except pyautogui.FailSafeException:
            self.log("🚨 FAILSAFE TRIGGERED!")
            self.update_status_label("🚨 EMERGENCY STOP", self.color_error)
            self.on_stop()
        except Exception as e:
            self.log(f"❌ ERROR: {e}")
            self.update_status_label("⚠️ RETRYING...", self.color_error)
            self.t_next = time.time() + 5
        finally:
            self.root.after(0, self._update_progress_ui)
            self.is_processing = False

    def on_first(self): self.index = 0; self._update_progress_ui()
    def on_prev(self): 
        if self.index > 0: self.index -= 1; self._update_progress_ui()
    def on_next(self):
        if self.index < len(self.prompts) - 1: self.index += 1; self._update_progress_ui()
    def on_last(self): self.index = len(self.prompts)-1; self._update_progress_ui()
    def on_open_prompts(self): os.startfile(self.base / self.cfg["prompts_file"])
    def on_rename_slot(self): pass
    def save_session_report(self): pass

if __name__ == "__main__":
    try: FlowVisionApp().root.mainloop()
    except Exception as e:
        with open("CRASH_LOG.txt", "w") as f: f.write(traceback.format_exc())
