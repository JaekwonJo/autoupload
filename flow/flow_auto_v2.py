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

APP_NAME = "Flow Veo 자동화 봇 (Ultimate V2)"
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
    "relay_count": 1,
    "language_mode": "en",
    "input_mode": "typing", # typing, paste, mixed
    "use_ref_images": False,
    "ref_image_count": 1,
    "add_btn1_area": None,
    "add_btn2_area": None,
    "add_btn3_area": None,
    "add_btn4_area": None,
    "ref_img1_area": None,
    "ref_img2_area": None,
    "ref_img3_area": None,
    "ref_img4_area": None
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
                         background="#F8F9FA", foreground="black", relief="solid", borderwidth=1,
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
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg="#F8F9FA")
        
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 350, 120
        x = sw - w - 20
        y = sh - h - 100
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        frame = tk.Frame(self.root, bg="#FFFFFF", highlightbackground="#007AFF", highlightthickness=3)
        frame.pack(fill="both", expand=True)
        
        tk.Label(frame, text="⚡ 봇 출동 준비!", font=("Malgun Gothic", 12, "bold"), bg="#FFFFFF", fg="#007AFF").pack(pady=10)
        self.lbl_time = tk.Label(frame, text=f"{seconds}초 전", font=("Malgun Gothic", 20, "bold"), bg="#FFFFFF", fg="#DC3545")
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

class CaptureOverlay:
    def __init__(self, master, callback, kind):
        self.master = master
        self.callback = callback
        self.kind = kind
        self.top = tk.Toplevel(master)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-alpha", 0.3)
        self.top.attributes("-topmost", True)
        self.top.configure(bg="black", cursor="cross")
        self.top.bind("<Button-1>", self.on_press)
        self.top.bind("<B1-Motion>", self.on_drag)
        self.top.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self.canvas = tk.Canvas(self.top, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.start_x = None
        self.start_y = None
        self.rect = None

    def on_press(self, event):
        self.start_x = self.top.winfo_pointerx() - self.top.winfo_rootx()
        self.start_y = self.top.winfo_pointery() - self.top.winfo_rooty()
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="#00FF00", width=4)

    def on_drag(self, event):
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if self.start_x is None: return
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        self.top.destroy()
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5: return
        self.callback(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

def load_config_from_file(path):
    if not path.exists(): return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        for k, v in DEFAULT_CONFIG.items():
            if k not in data: data[k] = v
        return data
    except: return DEFAULT_CONFIG.copy()

class LogWindow:
    def __init__(self, master, app=None):
        self.root = tk.Toplevel(master)
        self.app = app
        self.root.title("📜 시스템 로그 & 프롬프트 모니터")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = min(920, max(640, int(sw * 0.62)))
        h = min(760, max(480, int(sh * 0.72)))
        x = max((sw - w) // 2 + 20, 0)
        y = max((sh - h) // 2 + 20, 0)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(560, 420)
        self.root.configure(bg="#212529")
        
        # [NEW] 마법의 칸막이 (PanedWindow) 설치
        self.paned = ttk.Panedwindow(self.root, orient="vertical")
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. Prompt Preview Section
        self.frame_top = tk.Frame(self.paned, bg="#212529")
        self.paned.add(self.frame_top, weight=1) # 비중 설정

        # 상단 레이블과 새로고침 버튼을 담을 프레임
        top_f = tk.Frame(self.frame_top, bg="#212529")
        top_f.pack(fill="x", pady=(0, 5))

        lbl1 = tk.Label(top_f, text="📝 현재 로드된 프롬프트 (미리보기)", font=("Malgun Gothic", 11, "bold"), bg="#212529", fg="#FFC107")
        lbl1.pack(side="left")

        if self.app:
            btn_refresh = tk.Button(top_f, text="🔄 즉시 새로고침 (Reload)", command=self.app.on_reload,
                                     bg="#007AFF", fg="white", font=("Malgun Gothic", 9, "bold"), padx=10)
            btn_refresh.pack(side="right")
        
        self.text_preview = ScrolledText(self.frame_top, bg="#343A40", fg="#F8F9FA", 
                                         font=("Consolas", 11), insertbackground="white", borderwidth=1, relief="solid")
        self.text_preview.pack(fill="both", expand=True)

        # 2. System Log Section
        self.frame_bottom = tk.Frame(self.paned, bg="#212529")
        self.paned.add(self.frame_bottom, weight=2) # 로그 칸을 더 크게

        lbl2 = tk.Label(self.frame_bottom, text="💻 시스템 작동 로그", font=("Malgun Gothic", 11, "bold"), bg="#212529", fg="#20C997")
        lbl2.pack(anchor="w", pady=(10, 5))

        self.log_text = ScrolledText(self.frame_bottom, bg="black", fg="#00FF00", 
                                     font=("Consolas", 10), state="disabled", borderwidth=1, relief="solid")
        self.log_text.pack(fill="both", expand=True)
        
        btn_close = ttk.Button(self.root, text="창 닫기 (백그라운드 유지)", command=self.root.withdraw)
        btn_close.pack(pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.root.withdraw)

    def log(self, msg):
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{ts}] {msg}\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        except: pass
    
    def set_preview(self, text):
        try:
            self.text_preview.delete("1.0", "end")
            self.text_preview.insert("1.0", text)
        except: pass
    
    def show(self):
        self.root.deiconify()
        self.root.lift()

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
        self.actor.language_mode = self.cfg.get("language_mode", "en")
        
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self._set_initial_window_size()
        self.root.configure(bg="#FFFFFF")
        
        # [NEW] Responsive Grid Weight
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # [NEW] Log Window Instance
        self.log_window = LogWindow(self.root, self)
        self.log_window.root.withdraw() # Start hidden
        
        try:
            icon_path = self.base.parent / "icon.ico"
            if icon_path.exists(): self.root.iconbitmap(str(icon_path))
        except: pass
        
        # [STYLE] High Visibility Theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.color_bg = "#FFFFFF"
        self.color_card = "#F1F3F5"
        self.color_accent = "#007AFF" # Blue
        self.color_success = "#28A745" # Green
        self.color_error = "#DC3545" # Red
        self.color_info = "#17A2B8"
        self.color_text = "#212529"
        self.color_text_sec = "#868E96"
        
        self.style.configure("TFrame", background=self.color_bg)
        self.style.configure("Card.TFrame", background=self.color_card, relief="flat")
        self.style.configure("TLabelframe", background=self.color_bg, foreground=self.color_accent, borderwidth=2, relief="groove")
        self.style.configure("TLabelframe.Label", background=self.color_bg, foreground=self.color_accent, font=("Malgun Gothic", 12, "bold"))
        self.style.configure("TLabel", background=self.color_bg, foreground=self.color_text, font=("Malgun Gothic", 10))
        
        # Button Styles
        self.style.configure("TButton", background="#E9ECEF", foreground="black", borderwidth=1, font=("Malgun Gothic", 10, "bold"))
        self.style.map("TButton", background=[('active', '#DEE2E6')])
        
        # Progress Bar
        self.style.configure("Horizontal.TProgressbar", background=self.color_success, troughcolor="#E9ECEF", bordercolor="#DEE2E6", thickness=20)
        
        # Big Action Button
        self.style.configure("Action.TButton", background=self.color_accent, foreground="white", font=("Malgun Gothic", 14, "bold"))
        self.style.map("Action.TButton", background=[('active', '#0056b3'), ('disabled', '#ADB5BD')])

        self._ensure_prompt_slots()
        self._build_ui()
        self.on_reload()
        self.root.after(1000, self._tick)

    def _set_initial_window_size(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = min(1260, max(980, int(sw * 0.94)))
        h = min(920, max(680, int(sh * 0.86)))
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 2, 0)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(860, 620)

    def _init_body_sash(self):
        try:
            total_w = self.body_pane.winfo_width()
            if total_w > 0:
                self.body_pane.sashpos(0, int(total_w * 0.44))
        except:
            pass

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
        if color == "white": color = self.color_text
        self.lbl_main_status.config(text=text, fg=color)

    def _build_ui(self):
        # 1. Header (High Visibility)
        header = tk.Frame(self.root, bg="#F8F9FA", height=72, highlightbackground="#DEE2E6", highlightthickness=1)
        header.pack(fill="x", side="top")
        
        title_f = tk.Frame(header, bg="#F8F9FA")
        title_f.pack(side="left", padx=20, pady=10)
        tk.Label(title_f, text="Flow Veo 자동화 봇", font=("Malgun Gothic", 20, "bold"), bg="#F8F9FA", fg="#343A40").pack(anchor="w")
        tk.Label(title_f, text="Ultimate V2 High-Vis Edition", font=("Malgun Gothic", 10), bg="#F8F9FA", fg="#868E96").pack(anchor="w")

        status_f = tk.Frame(header, bg="#F8F9FA")
        status_f.pack(side="right", padx=30, fill="y")
        tk.Label(status_f, text="현재 상태", font=("Malgun Gothic", 10), bg="#F8F9FA", fg="#868E96").pack(anchor="e")
        self.lbl_main_status = tk.Label(status_f, text="준비 완료", font=("Malgun Gothic", 16, "bold"), bg="#F8F9FA", fg=self.color_success)
        self.lbl_main_status.pack(anchor="e")

        # 2. Body
        mid_frame = tk.Frame(self.root, bg=self.color_bg, pady=10)
        mid_frame.pack(fill="both", expand=True, padx=8)

        self.body_pane = ttk.Panedwindow(mid_frame, orient="horizontal")
        self.body_pane.pack(fill="both", expand=True)

        # --- Left: Settings (Scrollable) ---
        self.left_container = tk.Frame(self.body_pane, bg=self.color_bg, width=440)
        self.left_container.pack_propagate(False) # 고정 너비 유지

        canvas = tk.Canvas(self.left_container, bg=self.color_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.left_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.color_bg)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=max(e.width - 2, 240)))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 마우스 휠 지원
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        left_card = ttk.LabelFrame(scrollable_frame, text=" ⚙️ 기본 설정 ", padding=15)
        left_card.pack(fill="x", padx=5, pady=5)
        
        # Target Buttons
        tk.Label(left_card, text="1. 화면 인식 영역 지정 (필수)", font=("Malgun Gothic", 11, "bold"), fg=self.color_text).pack(anchor="w", pady=(0, 5))
        btn_area = tk.Frame(left_card, bg=self.color_bg)
        btn_area.pack(fill="x", pady=5)
        
        b1 = ttk.Button(btn_area, text="🟦 입력창 지정", width=12, command=lambda: self.start_capture("input"))
        b1.pack(side="left", padx=5)
        b2 = ttk.Button(btn_area, text="🟩 버튼 지정", width=12, command=lambda: self.start_capture("submit"))
        b2.pack(side="left", padx=5)
        b3 = ttk.Button(btn_area, text="⬜ 딴짓 영역", width=12, command=lambda: self.start_capture("afk"))
        b3.pack(side="left", padx=5)
        
        self.lbl_coords = tk.Label(left_card, text=self._get_coord_text(), font=("Consolas", 10), fg=self.color_accent, bg="#F1F3F5", padx=5, pady=2)
        self.lbl_coords.pack(fill="x", pady=(5, 20))
        
        # Options
        tk.Label(left_card, text="2. 옵션 설정", font=("Malgun Gothic", 11, "bold"), fg=self.color_text).pack(anchor="w", pady=(0, 5))
        
        op_f = tk.Frame(left_card, bg=self.color_bg)
        op_f.pack(fill="x")
        
        c1 = tk.Checkbutton(op_f, text="소리 켜기", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, font=("Malgun Gothic", 10), activebackground=self.color_bg)
        self.sound_var = tk.BooleanVar(value=self.cfg.get("sound_enabled", True))
        c1.config(variable=self.sound_var)
        c1.grid(row=0, column=0, sticky="w", padx=5)
        
        c2 = tk.Checkbutton(op_f, text="AFK(딴짓) 모드", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, fg="#D63384", selectcolor=self.color_bg, activebackground=self.color_bg, font=("Malgun Gothic", 10, "bold"))
        self.afk_var = tk.BooleanVar(value=self.cfg.get("afk_mode", False))
        c2.config(variable=self.afk_var)
        c2.grid(row=0, column=1, sticky="w", padx=5)
        
        c_lang = tk.Checkbutton(op_f, text="한글+영어 모드", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, font=("Malgun Gothic", 10), activebackground=self.color_bg)
        self.lang_var = tk.BooleanVar(value=(self.cfg.get("language_mode", "en") == "ko_en"))
        c_lang.config(variable=self.lang_var)
        c_lang.grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
        
        # [NEW] Input Mode Selection
        tk.Label(left_card, text="⌨️ 입력 방식 선택", font=("Malgun Gothic", 10, "bold"), bg=self.color_bg).pack(anchor="w", pady=(15, 0))
        self.input_mode_var = tk.StringVar(value=self.cfg.get("input_mode", "typing"))
        mode_f = tk.Frame(left_card, bg=self.color_bg)
        mode_f.pack(fill="x", pady=5)
        
        self.combo_input_mode = ttk.Combobox(mode_f, textvariable=self.input_mode_var, state="readonly", font=("Malgun Gothic", 10))
        self.combo_input_mode['values'] = ("typing", "paste", "mixed")
        self.combo_input_mode.pack(side="left", fill="x", expand=True)
        self.combo_input_mode.bind("<<ComboboxSelected>>", self.on_option_toggle)
        
        mode_map = {"typing": "⌨️ 타이핑", "paste": "📋 복사붙여넣기", "mixed": "🔀 혼용(랜덤)"}
        # 콤보박스 표시용 맵핑 (선택 사항)
        
        # --- [NEW] Reference Image Settings ---
        img_card = ttk.LabelFrame(left_card, text=" 🖼️ 레퍼런스 이미지 설정 ", padding=10)
        img_card.pack(fill="x", pady=(20, 0))

        img_op_f = tk.Frame(img_card, bg=self.color_bg)
        img_op_f.pack(fill="x")
        
        self.use_ref_var = tk.BooleanVar(value=self.cfg.get("use_ref_images", False))
        tk.Checkbutton(img_op_f, text="이미지 참조 사용", variable=self.use_ref_var, command=self.on_option_toggle, 
                       bg=self.color_bg, font=("Malgun Gothic", 9, "bold")).pack(side="left")
        
        tk.Label(img_op_f, text="개수:", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left", padx=(10, 2))
        self.ref_count_var = tk.IntVar(value=self.cfg.get("ref_image_count", 1))
        tk.Spinbox(img_op_f, from_=1, to=4, width=2, textvariable=self.ref_count_var, command=self.on_option_toggle).pack(side="left")

        img_btn_f = tk.Frame(img_card, bg=self.color_bg)
        img_btn_f.pack(fill="x", pady=5)
        
        # 4개의 행으로 구성된 지정 버튼들
        for i in range(1, 5):
            tk.Label(img_btn_f, text=f"Set {i}:", font=("Consolas", 8, "bold"), bg=self.color_bg).grid(row=i-1, column=0, padx=2)
            ttk.Button(img_btn_f, text=f"➕{i} 지정", width=8, command=lambda x=i: self.start_capture(f"add_btn{x}")).grid(row=i-1, column=1, padx=2, pady=1)
            ttk.Button(img_btn_f, text=f"🖼️{i} 지정", width=8, command=lambda x=i: self.start_capture(f"ref_img{x}")).grid(row=i-1, column=2, padx=2, pady=1)
        
        self.lbl_img_coords = tk.Label(img_card, text=self._get_img_coord_text(), font=("Consolas", 8), fg=self.color_text_sec, bg=self.color_bg)
        self.lbl_img_coords.pack(fill="x")

        # Relay
        relay_f = tk.Frame(left_card, bg=self.color_bg)
        relay_f.pack(fill="x", pady=10)
        c3 = tk.Checkbutton(relay_f, text="이어달리기 (파일 순차 실행)", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, font=("Malgun Gothic", 10), activebackground=self.color_bg)
        self.relay_var = tk.BooleanVar(value=self.cfg.get("relay_mode", False))
        c3.config(variable=self.relay_var)
        c3.pack(side="left")
        
        self.relay_cnt_var = tk.IntVar(value=self.cfg.get("relay_count", 1))
        sp = tk.Spinbox(relay_f, from_=1, to=10, width=3, textvariable=self.relay_cnt_var, command=self.on_option_toggle, bg="#FFFFFF", fg="black")
        sp.pack(side="left", padx=5)

        tk.Label(left_card, text="3. 작업 간격 (초)", font=("Malgun Gothic", 11, "bold"), fg=self.color_text).pack(anchor="w", pady=(20, 5))
        self.entry_interval = tk.Entry(left_card, bg="#FFFFFF", fg="black", font=("Consolas", 16, "bold"), justify="center", relief="solid", borderwidth=1)
        self.entry_interval.insert(0, str(self.cfg.get("interval_seconds", 180)))
        self.entry_interval.pack(fill="x", ipady=5)
        tk.Label(left_card, text="※ 설정한 시간마다 봇이 작동합니다.", font=("Malgun Gothic", 9), fg=self.color_text_sec).pack(anchor="w")

        tk.Frame(left_card, height=30, bg=self.color_bg).pack()
        self.btn_start = ttk.Button(left_card, text="▶ 자동화 시작", style="Action.TButton", command=self.on_start)
        self.btn_start.pack(fill="x", ipady=15)
        self.btn_stop = ttk.Button(left_card, text="⏹ 중지", command=self.on_stop, state="disabled")
        self.btn_stop.pack(fill="x", pady=10, ipady=5)

        # --- Right: Dashboard (HUD Design) ---
        right_panel = tk.Frame(self.body_pane, bg=self.color_bg)

        self.body_pane.add(self.left_container, weight=4)
        self.body_pane.add(right_panel, weight=6)
        self.root.after(120, self._init_body_sash)
        
        # 1. Progress Card
        prog_card = ttk.LabelFrame(right_panel, text=" 📊 진행 상황 ", padding=10)
        prog_card.pack(fill="x", pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_card, variable=self.progress_var, maximum=100, mode='determinate', style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=5)
        
        info_f = tk.Frame(prog_card, bg=self.color_bg)
        info_f.pack(fill="x")
        self.lbl_prog_text = tk.Label(info_f, text="0 / 0 (0.0%)", font=("Consolas", 14, "bold"), fg=self.color_accent, bg=self.color_bg)
        self.lbl_prog_text.pack(side="left")
        self.lbl_eta = tk.Label(info_f, text="종료 예정: --:--", font=("Malgun Gothic", 10), fg=self.color_text_sec, bg=self.color_bg)
        self.lbl_eta.pack(side="right", pady=4)
        
        # 2. Human Monitor (HUD)
        mon_card = ttk.LabelFrame(right_panel, text=" 👁️ Human Action HUD ", padding=15)
        mon_card.pack(fill="both", expand=True)
        
        # Top Header: Persona & Mood
        hud_header = tk.Frame(mon_card, bg="#F1F3F5", padx=10, pady=10, relief="groove", borderwidth=1)
        hud_header.pack(fill="x", pady=(0, 10))
        
        tk.Label(hud_header, text="CURRENT PERSONA", font=("Consolas", 8), fg="#868E96", bg="#F1F3F5").pack(anchor="w")
        self.lbl_live_persona = tk.Label(hud_header, text="INITIALIZING...", font=("Malgun Gothic", 14, "bold"), fg="#343A40", bg="#F1F3F5")
        self.lbl_live_persona.pack(anchor="w")
        
        tk.Frame(hud_header, height=1, bg="#DEE2E6").pack(fill="x", pady=5) # Divider
        
        mood_f = tk.Frame(hud_header, bg="#F1F3F5")
        mood_f.pack(fill="x")
        self.lbl_live_mood = tk.Label(mood_f, text="MOOD: -", font=("Consolas", 11, "bold"), fg=self.color_info, bg="#F1F3F5")
        self.lbl_live_mood.pack(side="left")
        self.lbl_live_speed = tk.Label(mood_f, text="SPEED: x1.0", font=("Consolas", 11, "bold"), fg=self.color_success, bg="#F1F3F5")
        self.lbl_live_speed.pack(side="right")

        # Detailed Stats Grid
        stats_f = tk.Frame(mon_card, bg=self.color_bg)
        stats_f.pack(fill="x", pady=5)
        
        # Helper to create stat row
        self.stat_labels = {}
        def add_stat(row, col, label, key, color="#495057"):
            f = tk.Frame(stats_f, bg=self.color_bg)
            f.grid(row=row, column=col, sticky="ew", padx=5, pady=2)
            tk.Label(f, text=label, font=("Malgun Gothic", 9), fg="#868E96", bg=self.color_bg).pack(anchor="w")
            l = tk.Label(f, text="-", font=("Consolas", 11, "bold"), fg=color, bg=self.color_bg)
            l.pack(anchor="w")
            self.stat_labels[key] = l
            stats_f.grid_columnconfigure(col, weight=1)

        # Row 0
        add_stat(0, 0, "피로도 (Fatigue)", "fatigue", "#FFC107")
        add_stat(0, 1, "오타 확률 (Typo)", "typo", "#FD7E14")
        # Row 1
        add_stat(1, 0, "망설임 (Hesitation)", "hesitation", "#6f42c1")
        add_stat(1, 1, "초점 상실 (Loss)", "focus_loss", "#E83E8C")
        # Row 2
        add_stat(2, 0, "오버슈트 (Overshoot)", "overshoot", "#20C997")
        add_stat(2, 1, "미세 보정 (Micro)", "correction", "#17A2B8")
        # Row 3
        add_stat(3, 0, "현재 배치 (Batch)", "batch", "#343A40")
        add_stat(3, 1, "다음 휴식 (Bio Break)", "break", "#007AFF")

        # Active Traits List
        tk.Label(mon_card, text="ACTIVE BEHAVIOR TRAITS", font=("Consolas", 9, "bold"), fg="#ADB5BD", bg=self.color_bg).pack(anchor="w", pady=(15, 5))
        
        self.traits_frame = tk.Frame(mon_card, bg="#F8F9FA", relief="sunken", borderwidth=1)
        self.traits_frame.pack(fill="both", expand=True)
        
        self.list_traits = tk.Listbox(self.traits_frame, height=4, bg="#F8F9FA", fg="#495057", 
                                      font=("Malgun Gothic", 9), relief="flat", highlightthickness=0, selectbackground="#E9ECEF")
        self.list_traits.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        scrolly = ttk.Scrollbar(self.traits_frame, orient="vertical", command=self.list_traits.yview)
        scrolly.pack(side="right", fill="y")
        self.list_traits.config(yscrollcommand=scrolly.set)

        # 3. Bottom
        bottom = tk.Frame(self.root, bg=self.color_bg)
        bottom.pack(fill="x", expand=False, padx=20, pady=(0, 16))
        
        file_top = tk.Frame(bottom, bg=self.color_bg)
        file_top.pack(fill="x", pady=5)
        tk.Label(file_top, text="📁 프롬프트 파일 선택:", font=("Malgun Gothic", 11, "bold"), fg=self.color_text).pack(side="left")
        
        self.slot_var = tk.StringVar()
        self.combo_slots = ttk.Combobox(file_top, textvariable=self.slot_var, state="readonly", width=12, font=("Malgun Gothic", 10))
        self.combo_slots.pack(side="left", padx=10)
        self.combo_slots.bind("<<ComboboxSelected>>", self.on_slot_change)
        
        # [NEW] Rename Button
        ttk.Button(file_top, text="✏️", width=3, command=self.on_rename_slot).pack(side="left", padx=2)
        
        # [NEW] Add Slot Button
        btn_add = ttk.Button(file_top, text="➕", width=3, command=self.on_add_slot)
        btn_add.pack(side="left", padx=2)
        ToolTip(btn_add, "새로운 프롬프트 슬롯 추가")

        # [NEW] Delete Slot Button
        btn_del = ttk.Button(file_top, text="🗑️", width=3, command=self.on_delete_slot)
        btn_del.pack(side="left", padx=2)
        ToolTip(btn_del, "현재 프롬프트 슬롯 삭제")

        ttk.Button(file_top, text="📂 파일 열기", command=self.on_open_prompts).pack(side="right", padx=5)
        ttk.Button(file_top, text="🔄 새로고침", command=self.on_reload).pack(side="right")

        file_nav = tk.Frame(bottom, bg=self.color_bg)
        file_nav.pack(fill="x", pady=(2, 0))
        btn_nav = tk.Frame(file_nav, bg=self.color_bg)
        btn_nav.pack(side="left")
        
        # [NEW] First / Prev
        ttk.Button(btn_nav, text="⏮", width=3, command=self.on_first).pack(side="left", padx=1)
        ttk.Button(btn_nav, text="◀", width=3, command=self.on_prev).pack(side="left", padx=1)
        
        # [NEW] Direct Jump Entry
        tk.Label(btn_nav, text="번호 이동:", font=("Malgun Gothic", 9), bg=self.color_bg).pack(side="left", padx=(5, 2))
        self.ent_jump = tk.Entry(btn_nav, width=5, font=("Consolas", 10), justify="center", relief="solid", borderwidth=1)
        self.ent_jump.pack(side="left", padx=2)
        self.ent_jump.bind("<Return>", self.on_direct_jump)
        ToolTip(self.ent_jump, "이동할 번호 입력 후 엔터(Enter)")
        
        # [NEW] Jump (Clickable Label)
        self.lbl_nav_status = tk.Label(btn_nav, text="0 / 0", width=10, fg=self.color_text, 
                                       font=("Consolas", 11, "bold"), cursor="hand2", bg="#E9ECEF", relief="flat")
        self.lbl_nav_status.pack(side="left", padx=5)
        self.lbl_nav_status.bind("<Button-1>", self.on_jump_to)
        ToolTip(self.lbl_nav_status, "클릭하여 번호로 이동")
        
        # [NEW] Next / Last
        ttk.Button(btn_nav, text="▶", width=3, command=self.on_next).pack(side="left", padx=1)
        ttk.Button(btn_nav, text="⏭", width=3, command=self.on_last).pack(side="left", padx=1)
        
        # [NEW] Log & Refresh Buttons
        btn_f = tk.Frame(bottom, bg=self.color_bg)
        btn_f.pack(fill="x", pady=16)

        btn_log = tk.Button(btn_f, text="📜 로그 및 미리보기 창 열기", command=self.log_window.show, 
                            bg="#343A40", fg="#00FF00", font=("Malgun Gothic", 12, "bold"), relief="raised", borderwidth=3)
        btn_log.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=10)

        btn_refresh_big = tk.Button(btn_f, text="🔄 프롬프트 새로고침 (Reload)", command=self.on_reload, 
                                     bg="#007AFF", fg="white", font=("Malgun Gothic", 12, "bold"), relief="raised", borderwidth=3)
        btn_refresh_big.pack(side="right", fill="x", expand=True, padx=(5, 0), ipady=10)

    def on_option_toggle(self, event=None):
        self.cfg["afk_mode"] = self.afk_var.get()
        self.cfg["sound_enabled"] = self.sound_var.get()
        self.cfg["relay_mode"] = self.relay_var.get()
        self.cfg["language_mode"] = "ko_en" if self.lang_var.get() else "en"
        self.cfg["input_mode"] = self.input_mode_var.get()
        self.cfg["use_ref_images"] = self.use_ref_var.get()
        try: self.cfg["ref_image_count"] = int(self.ref_count_var.get())
        except: self.cfg["ref_image_count"] = 1
        try: self.cfg["relay_count"] = int(self.relay_cnt_var.get())
        except: self.cfg["relay_count"] = 1
        self.save_config()
        if hasattr(self, 'actor'):
            self.actor.language_mode = self.cfg["language_mode"]
        self.log(f"⚙️ 설정 동기화 완료 (입력방식: {self.cfg['input_mode']})")

    def _get_coord_text(self):
        ia, sa, aa = self.cfg.get('input_area'), self.cfg.get('submit_area'), self.cfg.get('afk_area')
        return f"입력창[{'✅' if ia else '❌'}] 버튼[{'✅' if sa else '❌'}] AFK[{'✅' if aa else '❌'}]"

    def _get_img_coord_text(self):
        c = self.cfg
        res = []
        for i in range(1, 5):
            btn = "✅" if c.get(f"add_btn{i}_area") else "❌"
            img = "✅" if c.get(f"ref_img{i}_area") else "❌"
            res.append(f"{i}[{btn}/{img}]")
        return " | ".join(res)

    def log(self, msg):
        if hasattr(self, 'log_window'):
            self.log_window.log(msg)

    def start_capture(self, kind):
        def on_captured(x1, y1, x2, y2):
            self.cfg[f"{kind}_area"] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            self.save_config()
            self.lbl_coords.config(text=self._get_coord_text())
            if hasattr(self, 'lbl_img_coords'):
                self.lbl_img_coords.config(text=self._get_img_coord_text())
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
            
            # [NEW] Send to Log Window
            if hasattr(self, 'log_window'):
                self.log_window.set_preview(raw)
            
            sep = self.cfg.get("prompts_separator", "|||")
            self.prompts = [p.strip() for p in raw.split(sep) if p.strip()]
            if self.prompts:
                if self.running and self.index >= len(self.prompts):
                    # 완료 상태(index == len)를 유지해서 자동 재시작을 방지
                    self.index = len(self.prompts)
                else:
                    self.index = min(self.index, len(self.prompts) - 1)
            else:
                self.index = 0
            self._update_progress_ui()
            self.log(f"로드 완료 ({len(self.prompts)}개)")
            slots = [s["name"] for s in self.cfg["prompt_slots"]]
            self.combo_slots["values"] = slots
            self.combo_slots.current(self.cfg["active_prompt_slot"])
        except: pass

    def _update_progress_ui(self):
        total = len(self.prompts)
        current = self.index
        shown = 0 if total == 0 else min(current + 1, total)
        self.lbl_nav_status.config(text=f"{shown} / {total}")
        if total > 0:
            pct = (min(current, total) / total) * 100
            self.progress_var.set(pct)
            self.lbl_prog_text.config(text=f"{min(current, total)} / {total} ({pct:.1f}%)")
        else:
            self.progress_var.set(0)
            self.lbl_prog_text.config(text="0 / 0 (0%)")

    def _update_monitor_ui(self):
        # Update labels with the latest data from the actor
        try:
            p_name = self.actor.current_persona_name
            mood = self.actor.current_mood
            speed_mult = self.actor.cfg.get('speed_multiplier', 1.0)
            
            # --- Key Stats ---
            fatigue = self.actor.get_fatigue_factor()
            typo_rate = self.actor.cfg.get("typo_rate", 0)
            hesitation = self.actor.cfg.get("hesitation_before_click", 0)
            
            # Additional Stats for HUD
            overshoot = self.actor.cfg.get("overshoot_rate", 0)
            correction = self.actor.cfg.get("micro_correction_rate", 0)
            focus_loss = self.actor.cfg.get("window_focus_switch_rate", 0)
            
            # Batch Info
            processed = self.actor.processed_count
            batch_size = self.actor.current_batch_size
            next_break = max(0, batch_size - processed)

            # Update UI Elements
            self.lbl_live_persona.config(text=p_name.upper())
            self.lbl_live_mood.config(text=f"MOOD: {mood.upper()}")
            
            # Speed: Show as "x 1.2" (Inverse of multiplier if multiplier < 1 is fast? 
            # Usually lower multiplier = faster delay in code.
            # But let's show "Speed" as 'Fast' or 'Slow'. 
            # If mult=0.5 -> delay is half -> Speed x2.0
            real_speed = 1.0 / speed_mult if speed_mult > 0 else 0
            self.lbl_live_speed.config(text=f"SPEED: x{real_speed:.1f}")

            # Update Grid Labels using the dictionary
            def set_text(key, txt):
                if key in self.stat_labels: self.stat_labels[key].config(text=txt)

            set_text("fatigue", f"{fatigue:.0%}") # 100% means fresh? Or fatigued?
            # Code says: factor = 1.0 - (elapsed...*0.005). So 1.0 is Fresh.
            # Let's display "Condition" instead of Fatigue? 
            # Or label it "Fatigue: 20%" if factor is 0.8?
            # User asks for "Fatigue". If 1.0 is full speed, then fatigue is 0%.
            fatigue_pct = (1.0 - fatigue)
            set_text("fatigue", f"{fatigue_pct:.0%}")
            
            set_text("typo", f"{typo_rate:.1%}")
            set_text("hesitation", f"{hesitation:.0%}")
            set_text("focus_loss", f"{focus_loss:.0%}")
            set_text("overshoot", f"{overshoot:.0%}")
            set_text("correction", f"{correction:.0%}")
            set_text("batch", f"{processed} / {batch_size}")
            set_text("break", f"{next_break} left")

            # Update active traits list
            self.list_traits.delete(0, 'end')
            active_traits = self.actor.get_active_traits()
            
            if not active_traits:
                self.list_traits.insert('end', "  - Standard Mode -")
                self.list_traits.itemconfig(0, {'fg': '#ADB5BD'})
            else:
                for trait in active_traits:
                    self.list_traits.insert('end', f"  • {trait}")
                    
        except Exception as e:
            print(f"Failed to update monitor UI: {e}")

    def on_start(self):
        self.on_reload() # 시작 시 프롬프트 최신화
        try:
            self.cfg["interval_seconds"] = int(self.entry_interval.get())
            self.save_config()
        except: pass
        if not (self.cfg.get('input_area') and self.cfg.get('submit_area')):
            messagebox.showwarning("주의", "먼저 영역을 설정해주세요.")
            return
        
        if not self.prompts:
            messagebox.showwarning("주의", "프롬프트 파일이 비어있습니다!\n먼저 프롬프트를 입력하고 저장을 눌러주세요.")
            return
        
        if self.index >= len(self.prompts):
            self.index = 0
            self._update_progress_ui()

        if self.relay_progress == 0:
            self.session_start_time = datetime.now()
            self.session_log = []
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.update_status_label("🚀 시작 중...", self.color_success)
        self.play_sound("start")
        try:
            self.actor.update_batch_size()
            self.actor.processed_count = 0
        except: pass
        self.t_next = time.time() # 즉시 시작

    def on_stop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.update_status_label("중지됨", self.color_error)
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
                    self.update_status_label(f"⏳ 대기 중... {int(remain)}초 (비상은 마우스 구석으로!)", "#FFC107") # Amber
                    
                    # [NEW] 대기 중 마우스 산책 (클릭 절대 금지!)
                    if random.random() < 0.3: # 30% 확률로 조금씩 움직임
                        try:
                            # AFK 영역이 있으면 그 안에서, 없으면 화면 전체에서 살짝 산책
                            area = self.cfg.get("afk_area")
                            if area:
                                tx = random.randint(area['x1'], area['x2'])
                                ty = random.randint(area['y1'], area['y2'])
                            else:
                                sw, sh = pyautogui.size()
                                tx, ty = random.randint(100, sw-100), random.randint(100, sh-100)
                            
                            # 아주 천천히 부드럽게 이동
                            self.actor.move_to(tx, ty, overshoot=False)
                        except: pass
            
            try: base = int(self.entry_interval.get())
            except: base = 180
            remain_cnt = len(self.prompts) - self.index
            total_sec = remain_cnt * base + max(0, int(remain))
            finish_time = datetime.fromtimestamp(time.time() + total_sec).strftime("%p %I:%M")
            self.lbl_eta.config(text=f"🏁 종료 예정: {finish_time}")

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
                try:
                    speed = self.actor.cfg.get('speed_multiplier', 1.0)
                except: speed = 1.0
                interval = int(base + random.uniform(0, base * 0.3 * speed))
                self.t_next = time.time() + interval
        self.root.after(1000, self._tick)

    def _run_task(self):
        print(f"[{datetime.now()}] Task started")
        self.on_reload() # 각 작업 시작 전 프롬프트 최신화
        self.log("작업 스레드 시작 (프롬프트 동기화 완료)")
        ia, sa = self.cfg.get('input_area'), self.cfg.get('submit_area')
        if not self.prompts or self.index >= len(self.prompts):
            print("No prompts or index out of range")
            self.log("프롬프트 없음 또는 범위 초과")
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
            self.update_status_label("🎉 전체 완료!", self.color_success)
            return

        try:
            if self.actor.processed_count >= self.actor.current_batch_size:
                print("Bio break triggered")
                self.actor.take_bio_break(status_callback=lambda m: self.update_status_label(m, self.color_error))
                self.actor.current_batch_size = self.actor._get_random_batch_size()
                self.actor.processed_count = 0
                self.is_processing = False
                return
        except Exception as e:
            print(f"Bio break check failed: {e}")
            self.log(f"⚠️ 휴식 체크 오류: {e}")

        try:
            print("Randomizing persona...")
            try:
                self.actor.randomize_persona()
                self.root.after(0, self._update_monitor_ui)
            except Exception as e:
                print(f"Persona update failed: {e}")
                self.log(f"⚠️ 페르소나 업데이트 오류: {e}")

            prompt = self.prompts[self.index]
            start_t = datetime.now()
            
            # [ORDER CHANGE] 1. 레퍼런스 이미지 먼저 첨부 (텍스트 입력 전이 가장 안정적)
            if self.cfg.get("use_ref_images"):
                count = self.cfg.get("ref_image_count", 1)
                for i in range(1, count + 1):
                    add_btn = self.cfg.get(f"add_btn{i}_area")
                    img_area = self.cfg.get(f"ref_img{i}_area")
                    
                    if add_btn and img_area:
                        self.update_status_label(f"🖼️ 세트 {i} 첨부 중...", self.color_info)
                        # 1. 해당 단계의 + 버튼 클릭
                        self.actor.move_to(random.randint(add_btn['x1'], add_btn['x2']), 
                                          random.randint(add_btn['y1'], add_btn['y2']))
                        pyautogui.click()
                        time.sleep(1.2 + random.random()) # 메뉴 열리는 시간 대기
                        
                        # 2. 해당 단계의 이미지 클릭
                        self.actor.move_to(random.randint(img_area['x1'], img_area['x2']), 
                                          random.randint(img_area['y1'], img_area['y2']))
                        self.actor.smart_click()
                        time.sleep(1.5 + random.random()) # 첨부 반영 대기
                    else:
                        self.log(f"⚠️ 세트 {i} 영역 설정 미비로 건너뜁니다.")

            # [ORDER CHANGE] 2. 프롬프트 입력창으로 이동 및 입력
            if ia:
                print(f"Moving to input area: {ia}")
                self.update_status_label("🖱️ 이동 중...", "white")
                self.actor.move_to(random.randint(ia['x1'], ia['x2']), random.randint(ia['y1'], ia['y2']))
                pyautogui.click()
                time.sleep(0.5)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.press("backspace")
            
            print(f"Typing prompt: {prompt[:20]}...")
            mode = self.cfg.get("input_mode", "typing")
            
            # 입력 방식 분기 로직
            current_action = "typing"
            if mode == "paste":
                current_action = "paste"
            elif mode == "mixed":
                current_action = random.choice(["typing", "paste"])
            
            if current_action == "paste":
                self.update_status_label("📋 복사 붙여넣기 중...", "white")
                pyperclip.copy(prompt)
                time.sleep(random.uniform(0.3, 0.7))
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.5)
            else:
                self.update_status_label("✍️ 타이핑 중...", "white")
                self.actor.type_text(prompt, speed_callback=lambda s: self.root.after(0, lambda: self.lbl_speed_val.config(text=f"x{s}")))
            
            self.update_status_label("✅ 입력 완료!", self.color_success)
            time.sleep(0.5)

            self.update_status_label("📖 검토 중...", self.color_info)
            self.actor.read_prompt_pause(prompt)
            
            # 3. 최종 제출
            print("Submitting...")
            self.update_status_label("🚀 제출 중...", self.color_accent)
            if random.random() < self.cfg.get("enter_submit_rate", 0.5):
                time.sleep(0.5)
                pyautogui.press('enter')
            else:
                if sa:
                    self.actor.move_to(random.randint(sa['x1'], sa['x2']), random.randint(sa['y1'], sa['y2']))
                    self.actor.smart_click()
            
            print("Task success")
            self.log(f"성공 #{self.index+1}")
            self.update_status_label("🎉 작업 완료!", self.color_success)
            self.play_sound("success")
            self.session_log.append({"index": self.index + 1, "prompt": prompt, "duration": f"{(datetime.now()-start_t).total_seconds():.1f}초"})
            self.actor.processed_count += 1
            self.index += 1
            
        except pyautogui.FailSafeException:
            print("FAILSAFE TRIGGERED")
            self.log("🚨 FAILSAFE 작동됨!")
            self.update_status_label("🚨 비상 정지", self.color_error)
            self.on_stop()
        except Exception as e:
            print(f"ERROR in run_task: {e}")
            traceback.print_exc()
            self.log(f"❌ 오류: {e}")
            self.update_status_label("⚠️ 재시도 대기...", self.color_error)
            self.t_next = time.time() + 5
        finally:
            self.root.after(0, self._update_progress_ui)
            self.is_processing = False

    def on_first(self): 
        self.index = 0
        self._update_progress_ui()
        
    def on_prev(self): 
        if self.index > 0: self.index -= 1; self._update_progress_ui()
        
    def on_next(self):
        if self.index < len(self.prompts) - 1: self.index += 1; self._update_progress_ui()
        
    def on_last(self): 
        if self.prompts: self.index = len(self.prompts)-1
        self._update_progress_ui()
        
    def on_jump_to(self, event=None):
        if not self.prompts: return
        total = len(self.prompts)
        try:
            target = simpledialog.askinteger("이동", f"이동할 번호를 입력하세요 (1 ~ {total}):", parent=self.root)
            if target is not None:
                idx = target - 1
                if 0 <= idx < total:
                    self.index = idx
                    self._update_progress_ui()
                    self.log(f"🚀 {target}번으로 점프!")
                else:
                    messagebox.showwarning("범위 초과", "존재하지 않는 번호입니다.")
        except: pass

    def on_direct_jump(self, event=None):
        if not self.prompts: return
        try:
            val = self.ent_jump.get().strip()
            if not val: return
            target = int(val)
            total = len(self.prompts)
            idx = target - 1
            if 0 <= idx < total:
                self.index = idx
                self._update_progress_ui()
                self.log(f"🚀 {target}번으로 직접 이동!")
                self.ent_jump.delete(0, 'end')
                self.root.focus() # 포커스 해제
            else:
                messagebox.showwarning("범위 초과", f"1부터 {total} 사이의 숫자를 입력하세요.")
        except ValueError:
            messagebox.showerror("오류", "숫자만 입력 가능합니다.")

    def on_open_prompts(self): os.startfile(self.base / self.cfg["prompts_file"])
    
    def on_rename_slot(self):
        idx = self.combo_slots.current()
        if idx < 0: return
        
        current_name = self.cfg["prompt_slots"][idx]["name"]
        new_name = simpledialog.askstring("이름 변경", "새로운 슬롯 이름을 입력하세요:", initialvalue=current_name)
        
        if new_name:
            self.cfg["prompt_slots"][idx]["name"] = new_name
            self.save_config()
            
            # UI Update
            slots = [s["name"] for s in self.cfg["prompt_slots"]]
            self.combo_slots["values"] = slots
            self.combo_slots.current(idx)
            self.log(f"📝 슬롯 이름 변경: {current_name} -> {new_name}")

    def on_add_slot(self):
        new_name = simpledialog.askstring("슬롯 추가", "새로운 슬롯의 이름을 입력하세요:")
        if not new_name: return
        
        # 파일명 생성 (중복 피하기)
        slot_id = 1
        while True:
            new_file = f"flow_prompts_slot_{slot_id}.txt"
            if not any(s["file"] == new_file for s in self.cfg["prompt_slots"]):
                break
            slot_id += 1
            
        # 파일 생성
        try:
            (self.base / new_file).write_text("", encoding="utf-8")
        except Exception as e:
            messagebox.showerror("오류", f"파일 생성 실패: {e}")
            return
            
        # 설정 추가
        self.cfg["prompt_slots"].append({"name": new_name, "file": new_file})
        self.save_config()
        
        # UI 갱신
        slots = [s["name"] for s in self.cfg["prompt_slots"]]
        self.combo_slots["values"] = slots
        new_idx = len(self.cfg["prompt_slots"]) - 1
        self.combo_slots.current(new_idx)
        self.on_slot_change()
        self.log(f"➕ 새 슬롯 추가됨: {new_name} ({new_file})")
        messagebox.showinfo("성공", f"'{new_name}' 슬롯이 추가되었습니다!")

    def on_delete_slot(self):
        if len(self.cfg["prompt_slots"]) <= 1:
            messagebox.showwarning("삭제 불가", "최소 하나 이상의 슬롯은 유지해야 합니다.")
            return
            
        idx = self.combo_slots.current()
        if idx < 0: return
        
        slot_name = self.cfg["prompt_slots"][idx]["name"]
        if not messagebox.askyesno("슬롯 삭제", f"'{slot_name}' 슬롯을 삭제할까요?\n(실제 파일은 안전을 위해 삭제되지 않습니다)"):
            return
            
        # 설정 제거
        self.cfg["prompt_slots"].pop(idx)
        
        # 인덱스 조정
        if self.cfg["active_prompt_slot"] >= len(self.cfg["prompt_slots"]):
            self.cfg["active_prompt_slot"] = len(self.cfg["prompt_slots"]) - 1
        elif self.cfg["active_prompt_slot"] == idx:
            # 현재 활성화된 슬롯을 삭제한 경우
            self.cfg["active_prompt_slot"] = 0
            
        self.save_config()
        
        # UI 갱신
        slots = [s["name"] for s in self.cfg["prompt_slots"]]
        self.combo_slots["values"] = slots
        self.combo_slots.current(self.cfg["active_prompt_slot"])
        self.on_slot_change()
        self.log(f"🗑️ 슬롯 삭제됨: {slot_name}")
        messagebox.showinfo("성공", f"'{slot_name}' 슬롯이 목록에서 제거되었습니다.")

    def save_session_report(self): pass

if __name__ == "__main__":
    try: FlowVisionApp().root.mainloop()
    except Exception as e:
        with open("CRASH_LOG.txt", "w") as f: f.write(traceback.format_exc())
