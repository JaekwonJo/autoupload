import json
import os
import time
import random
import threading
import math
from pathlib import Path
from datetime import datetime
import ctypes
import importlib 
import winsound 

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

# [비전 봇 핵심 모듈]
import pyautogui
import pyperclip

# [NEW] 인간 행동 엔진 탑재 (항상 최신 버전 로드)
try:
    import flow.human_behavior_v2 as hb
    importlib.reload(hb) 
    from flow.human_behavior_v2 import HumanActor
except ImportError:
    try:
        import human_behavior_v2 as hb
        importlib.reload(hb)
        from human_behavior_v2 import HumanActor
    except ImportError:
        from flow.human_behavior_v2 import HumanActor

# --- 윈도우 절전 방지 상수 ---
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# --- 설정 ---
APP_NAME = "Flow Veo Vision Bot (Ultimate V2)"
CONFIG_FILE = "flow_config.json"
DEFAULT_CONFIG = {
    "prompts_file": "flow_prompts.txt",
    "prompts_separator": "|||",
    "interval_seconds": 180,
    "input_area": None,   # {x1, y1, x2, y2}
    "submit_area": None,  # {x1, y1, x2, y2}
    "afk_area": None,     # {x1, y1, x2, y2}
    "afk_mode": False,    
    "prompt_slots": [],
    "active_prompt_slot": 0,
    "sound_enabled": True,
    "relay_mode": False,
    "relay_count": 1
}

# [알림창 클래스]
class CountdownAlert:
    def __init__(self, master, seconds=30, sound_enabled=True):
        self.master_app = master 
        self.sound_enabled = sound_enabled
        self.root = tk.Toplevel(master)
        self.root.title("봇 출동 알림")
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
        
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        
        self.frame = tk.Frame(self.root, bg="#282A36", highlightbackground="#BD93F9", highlightthickness=2)
        self.frame.pack(fill="both", expand=True)
        
        self.lbl_title = tk.Label(self.frame, text="👻 비전 봇 출동 준비!", font=("Malgun Gothic", 11, "bold"), bg="#282A36", fg="#FF79C6")
        self.lbl_title.pack(pady=(5, 2))
        
        self.lbl_check = tk.Label(self.frame, text="⚠️ 영어(A)로 바꿨나요? ⚠️", font=("Malgun Gothic", 10, "bold"), bg="#282A36", fg="#F1FA8C")
        self.lbl_check.pack(pady=(0, 2))
        
        self.lbl_time = tk.Label(self.frame, text=f"{seconds}초 전", font=("Malgun Gothic", 16, "bold"), bg="#282A36", fg="#50FA7B")
        self.lbl_time.pack(pady=(0, 5))
        
        self.x = 0
        self.y = 0
        self.blink_state = False 

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def update_time(self, seconds):
        if not self.root.winfo_exists(): return
        
        sec_int = int(seconds)
        self.lbl_time.config(text=f"{sec_int}초 전")
        
        if self.sound_enabled:
            if sec_int == 30:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif sec_int == 10:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            elif 0 < sec_int <= 5:
                winsound.Beep(1000, 100)
        
        if sec_int <= 10:
            if self.blink_state:
                bg_color = "#FF5555" 
                fg_color = "#FFFFFF"
            else:
                bg_color = "#282A36" 
                fg_color = "#FF5555"
            
            self.frame.config(bg=bg_color)
            self.lbl_title.config(bg=bg_color, fg=fg_color)
            self.lbl_check.config(bg=bg_color, fg="yellow" if self.blink_state else "#F1FA8C")
            self.lbl_time.config(bg=bg_color, fg=fg_color)
            
            self.blink_state = not self.blink_state 
        else:
            self.frame.config(bg="#282A36")
            self.lbl_time.config(fg="#50FA7B", bg="#282A36")
            self.lbl_check.config(bg="#282A36")
            self.lbl_title.config(bg="#282A36")

    def close(self):
        try:
            self.root.destroy()
        except: pass

class CaptureOverlay:
    def __init__(self, master, on_capture, kind_text):
        self.on_capture = on_capture
        self.root = tk.Toplevel(master)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.3)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black", cursor="crosshair")
        
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.label = tk.Label(self.root, text=f"{kind_text} 영역을 마우스로 드래그하세요\n(ESC: 취소)", 
                              bg="#FF79C6", fg="black", font=("Malgun Gothic", 12, "bold"))
        self.label.place(x=0, y=0)
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        self.root.bind("<Button-1>", self.on_press)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Escape>", self.close)
        self.root.bind("<Motion>", self.on_move)

    def on_move(self, event):
        self.label.place(x=event.x + 20, y=event.y + 20)

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="#FF5555", width=3)

    def on_drag(self, event):
        if self.start_x is None: return
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)
        self.label.config(text=f"드래그 중...\n({self.start_x},{self.start_y}) ~ ({event.x},{event.y})")

    def on_release(self, event):
        if self.start_x is None: return
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        
        final_x1 = min(x1, x2)
        final_y1 = min(y1, y2)
        final_x2 = max(x1, x2)
        final_y2 = max(y1, y2)
        
        if (final_x2 - final_x1) < 5 or (final_y2 - final_y1) < 5:
            self.label.config(text="영역이 너무 작습니다. 다시 드래그하세요.")
            self.canvas.delete(self.rect_id)
            self.start_x = None
            return

        self.root.destroy()
        self.on_capture(final_x1, final_y1, final_x2, final_y2)

    def close(self, event=None):
        self.root.destroy()

def load_config_from_file(path):
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        return data
    except:
        return DEFAULT_CONFIG.copy()

# [Legacy] 팝업 설정창은 유지 (원할 때 상세 확인용)
class HumanConfigWindow:
    def __init__(self, master, actor):
        self.actor = actor
        self.root = tk.Toplevel(master)
        self.root.title("🤖 상세 인격 분석표")
        self.root.geometry("500x600")
        self.root.configure(bg="#282A36")
        
        tk.Label(self.root, text="이 창은 '상세 값' 확인용입니다.\n메인 화면의 대시보드에서 요약 정보를 볼 수 있습니다.", 
                 fg="#BD93F9", bg="#282A36", font=("Malgun Gothic", 10)).pack(pady=20)
        
        # 간단히 닫기 버튼만 제공 (메인 대시보드로 유도)
        ttk.Button(self.root, text="닫기", command=self.root.destroy).pack(pady=20)

class FlowVisionApp:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / CONFIG_FILE
        self.cfg = load_config_from_file(self.cfg_path)
        
        self.running = False
        self.prompts = []
        self.index = 0
        self.t_next = None
        self.alert_window = None
        self.config_window = None
        
        self.relay_progress = 0 
        
        self.actor = HumanActor()
        
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("950x700") # 가로로 넓게 확장
        self.root.configure(bg="#1E1E2E")
        
        try:
            icon_path = self.base.parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except: pass
        
        # [THEME] 스타일 설정
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 다크 테마 컬러 팔레트
        # BG: #1E1E2E, FG: #F8F8F2, Purple: #BD93F9, Pink: #FF79C6, Green: #50FA7B
        self.style.configure("TFrame", background="#1E1E2E")
        self.style.configure("TLabelframe", background="#1E1E2E", foreground="#BD93F9")
        self.style.configure("TLabelframe.Label", background="#1E1E2E", foreground="#BD93F9", font=("Malgun Gothic", 10, "bold"))
        self.style.configure("TLabel", background="#1E1E2E", foreground="#F8F8F2")
        self.style.configure("TButton", background="#44475A", foreground="white", borderwidth=1, focuscolor="none")
        self.style.map("TButton", background=[('active', '#6272A4')])
        
        # 프로그레스바 스타일
        self.style.configure("Horizontal.TProgressbar", background="#BD93F9", troughcolor="#44475A", bordercolor="#44475A", lightcolor="#BD93F9", darkcolor="#BD93F9")
        
        # Accent Button
        self.style.configure("Accent.TButton", background="#50FA7B", foreground="#282A36", font=("Malgun Gothic", 10, "bold"))
        self.style.map("Accent.TButton", background=[('active', '#FF79C6')])

        self._ensure_prompt_slots()
        self._build_ui()
        self.on_reload()
        
        self.root.after(1000, self._tick)

    def play_sound(self, category):
        if not self.cfg.get("sound_enabled", True):
            return 
        try:
            if category == "start":
                winsound.MessageBeep(winsound.MB_OK)
            elif category == "success":
                winsound.Beep(800, 200)
            elif category == "finish":
                winsound.MessageBeep(winsound.MB_ICONHAND)
        except: pass

    def save_config(self):
        try:
            self.cfg_path.write_text(json.dumps(self.cfg, indent=4, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            print(f"Config save failed: {e}")

    def _ensure_prompt_slots(self):
        if "prompt_slots" not in self.cfg or not self.cfg["prompt_slots"]:
            self.cfg["prompt_slots"] = [{"name": "기본 슬롯", "file": "flow_prompts.txt"}]
            self.cfg["active_prompt_slot"] = 0
            self.save_config()

    def _prevent_sleep(self):
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            self.log("☕ 불침번 활성화: 작업 중에는 화면이 꺼지지 않습니다.")
        except: pass

    def _allow_sleep(self):
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self.log("💤 불침번 해제: 이제 윈도우 설정에 따라 절전 모드가 가능합니다.")
        except: pass

    def on_start(self):
        ia = self.cfg.get('input_area')
        sa = self.cfg.get('submit_area')
        
        if not ia or not sa:
            messagebox.showwarning("주의", "먼저 [입력창]과 [생성 버튼]의 영역을 설정해주세요.")
            return
            
        self._prevent_sleep()
        
        if self.relay_progress == 0:
            self.session_start_time = datetime.now()
            self.session_log = []
        
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.t_next = time.time()
        self.update_status_label("🚀 자동화 시작!", "#50FA7B")
        
        self.play_sound("start")

        self.actor.update_batch_size()
        self.actor.processed_count = 0

    def on_stop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.update_status_label("⏹ 멈춤", "#FF5555")
        
        self.relay_progress = 0 
        self._allow_sleep()
        
        if self.alert_window:
            self.alert_window.close()
            self.alert_window = None

    def on_human_config(self):
        if self.config_window is None or not self.config_window.root.winfo_exists():
            self.config_window = HumanConfigWindow(self.root, self.actor)
        else:
            self.config_window.root.lift()

    def update_status_label(self, text, color):
        self.lbl_main_status.config(text=text, fg=color)

    # [UI Construction - Refactored for Dashboard]
    def _build_ui(self):
        # 3단 레이아웃: Top(Title), Middle(Content), Bottom(Logs)
        
        # 1. Top Header
        top_frame = tk.Frame(self.root, bg="#1E1E2E", pady=10)
        top_frame.pack(fill="x", side="top")
        
        tk.Label(top_frame, text=APP_NAME, font=("Malgun Gothic", 16, "bold"), bg="#1E1E2E", fg="#BD93F9").pack(side="left", padx=20)
        self.lbl_main_status = tk.Label(top_frame, text="Ready", font=("Malgun Gothic", 14, "bold"), bg="#1E1E2E", fg="#6272A4")
        self.lbl_main_status.pack(side="right", padx=20)

        # 2. Middle Section (Left: Control, Right: Dashboard)
        mid_frame = tk.Frame(self.root, bg="#1E1E2E")
        mid_frame.pack(fill="both", expand=True, padx=20)

        # --- Left Panel (Controls & Setup) ---
        left_panel = tk.LabelFrame(mid_frame, text=" 🎮 Control Panel ", padding=10)
        left_panel.pack(side="left", fill="both", expand=False, padx=(0, 10), ipadx=5)
        
        # A. 영역 설정
        tk.Label(left_panel, text="1. 영역 지정 (필수)", font=("Malgun Gothic", 10, "bold")).pack(anchor="w", pady=(0, 5))
        btn_grid = tk.Frame(left_panel, bg="#1E1E2E")
        btn_grid.pack(fill="x", pady=5)
        ttk.Button(btn_grid, text="⬛ 입력창", command=lambda: self.start_capture("input")).pack(side="left", fill="x", expand=True, padx=1)
        ttk.Button(btn_grid, text="⬛ 버튼", command=lambda: self.start_capture("submit")).pack(side="left", fill="x", expand=True, padx=1)
        ttk.Button(btn_grid, text="🟩 AFK", command=lambda: self.start_capture("afk")).pack(side="left", fill="x", expand=True, padx=1)
        
        self.lbl_coords = tk.Label(left_panel, text=self._get_coord_text(), font=("Malgun Gothic", 8), fg="#6272A4")
        self.lbl_coords.pack(anchor="w", pady=(0, 10))
        
        # B. 옵션 스위치
        tk.Label(left_panel, text="2. 환경 설정", font=("Malgun Gothic", 10, "bold")).pack(anchor="w", pady=(5, 5))
        
        # Sound
        self.sound_var = tk.BooleanVar(value=self.cfg.get("sound_enabled", True))
        chk_sound = tk.Checkbutton(left_panel, text="🔊 효과음 켜기", variable=self.sound_var, command=self.on_option_toggle,
                                   bg="#1E1E2E", fg="#8BE9FD", selectcolor="#1E1E2E", activebackground="#1E1E2E", activeforeground="#8BE9FD", font=("Malgun Gothic", 9))
        chk_sound.pack(anchor="w")

        # AFK
        self.afk_var = tk.BooleanVar(value=self.cfg.get("afk_mode", False))
        chk_afk = tk.Checkbutton(left_panel, text="👻 AFK(딴짓) 모드", variable=self.afk_var, command=self.on_option_toggle,
                                   bg="#1E1E2E", fg="#F1FA8C", selectcolor="#1E1E2E", activebackground="#1E1E2E", activeforeground="#F1FA8C", font=("Malgun Gothic", 9))
        chk_afk.pack(anchor="w")
        
        # Relay
        relay_box = tk.Frame(left_panel, bg="#1E1E2E", pady=5)
        relay_box.pack(fill="x", anchor="w")
        self.relay_var = tk.BooleanVar(value=self.cfg.get("relay_mode", False))
        chk_relay = tk.Checkbutton(relay_box, text="🏃 이어달리기", variable=self.relay_var, command=self.on_option_toggle,
                                   bg="#1E1E2E", fg="#FF79C6", selectcolor="#1E1E2E", activebackground="#1E1E2E", activeforeground="#FF79C6", font=("Malgun Gothic", 9))
        chk_relay.pack(side="left")
        
        self.relay_cnt_var = tk.IntVar(value=self.cfg.get("relay_count", 1))
        tk.Spinbox(relay_box, from_=1, to=10, width=3, textvariable=self.relay_cnt_var, command=self.on_option_toggle, 
                   bg="#282A36", fg="white", buttonbackground="#44475A").pack(side="left", padx=5)
        tk.Label(relay_box, text="개 연속", bg="#1E1E2E", fg="#FF79C6", font=("Malgun Gothic", 9)).pack(side="left")

        # Interval
        tk.Label(left_panel, text="3. 시간 간격 (초)", font=("Malgun Gothic", 10, "bold")).pack(anchor="w", pady=(15, 5))
        self.entry_interval = tk.Entry(left_panel, bg="#282A36", fg="#50FA7B", insertbackground="white", font=("Consolas", 11))
        self.entry_interval.insert(0, str(self.cfg.get("interval_seconds", 180)))
        self.entry_interval.pack(fill="x", padx=5)

        # Action Buttons
        tk.Frame(left_panel, height=20, bg="#1E1E2E").pack() # Spacer
        self.btn_start = ttk.Button(left_panel, text="🌙 시작 (START)", style="Accent.TButton", command=self.on_start)
        self.btn_start.pack(fill="x", pady=5, ipady=5)
        
        self.btn_stop = ttk.Button(left_panel, text="🛑 정지 (STOP)", command=self.on_stop, state="disabled")
        self.btn_stop.pack(fill="x", pady=2)


        # --- Right Panel (Dashboard & Monitor) ---
        right_panel = tk.Frame(mid_frame, bg="#1E1E2E")
        right_panel.pack(side="right", fill="both", expand=True)
        
        # 1. Progress Dashboard
        dash_frame = tk.LabelFrame(right_panel, text=" 📊 Live Progress ", padding=10)
        dash_frame.pack(fill="x", pady=(0, 10))
        
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(dash_frame, variable=self.progress_var, maximum=100, mode='determinate', style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=5)
        
        # Info Labels
        info_grid = tk.Frame(dash_frame, bg="#1E1E2E")
        info_grid.pack(fill="x")
        
        self.lbl_prog_text = tk.Label(info_grid, text="대기 중...", font=("Consolas", 10), fg="#8BE9FD", bg="#1E1E2E")
        self.lbl_prog_text.pack(side="left")
        
        self.lbl_eta = tk.Label(info_grid, text="--:-- 종료 예정", font=("Consolas", 10), fg="#6272A4", bg="#1E1E2E")
        self.lbl_eta.pack(side="right")
        
        # 2. Persona Monitor (Read-Only)
        monitor_frame = tk.LabelFrame(right_panel, text=" 👁️ Bot Monitor (Read-Only) ", padding=10)
        monitor_frame.pack(fill="both", expand=True)
        
        # Persona Name Big Display
        tk.Label(monitor_frame, text="Current Persona", font=("Malgun Gothic", 9), fg="#6272A4").pack(anchor="w")
        self.lbl_live_persona = tk.Label(monitor_frame, text="Waiting...", font=("Malgun Gothic", 16, "bold"), fg="#50FA7B")
        self.lbl_live_persona.pack(anchor="w", pady=(0, 10))
        
        # Grid for Stats
        stat_grid = tk.Frame(monitor_frame, bg="#1E1E2E")
        stat_grid.pack(fill="x", pady=5)
        
        # Col 1: Mood
        tk.Label(stat_grid, text="Mood (기분)", fg="#6272A4", font=("Malgun Gothic", 9)).grid(row=0, column=0, sticky="w", padx=10)
        self.lbl_live_mood = tk.Label(stat_grid, text="-", fg="white", font=("Malgun Gothic", 11, "bold"))
        self.lbl_live_mood.grid(row=1, column=0, sticky="w", padx=10)
        
        # Col 2: Speed Gauge (Visual only)
        tk.Label(stat_grid, text="Typing Speed", fg="#6272A4", font=("Malgun Gothic", 9)).grid(row=0, column=1, sticky="w", padx=20)
        self.live_speed_bar = ttk.Progressbar(stat_grid, length=150, mode='determinate', style="Horizontal.TProgressbar")
        self.live_speed_bar.grid(row=1, column=1, sticky="w", padx=20)
        self.lbl_live_speed_text = tk.Label(stat_grid, text="x 1.0", fg="#BD93F9", font=("Consolas", 9))
        self.lbl_live_speed_text.grid(row=2, column=1, sticky="w", padx=20)

        # Col 3: Batch Goal
        tk.Label(stat_grid, text="Batch Goal", fg="#6272A4", font=("Malgun Gothic", 9)).grid(row=0, column=2, sticky="w", padx=10)
        self.lbl_live_batch = tk.Label(stat_grid, text="- / -", fg="white", font=("Malgun Gothic", 11, "bold"))
        self.lbl_live_batch.grid(row=1, column=2, sticky="w", padx=10)


        # 3. Bottom Section (Prompts & Logs)
        bottom_frame = tk.Frame(self.root, bg="#1E1E2E")
        bottom_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Prompt Selector
        prompt_bar = tk.Frame(bottom_frame, bg="#1E1E2E")
        prompt_bar.pack(fill="x", pady=5)
        
        tk.Label(prompt_bar, text="📁 Prompt File:", fg="#F8F8F2", bg="#1E1E2E").pack(side="left")
        
        self.slot_var = tk.StringVar()
        slots = [s["name"] for s in self.cfg["prompt_slots"]]
        self.combo_slots = ttk.Combobox(prompt_bar, textvariable=self.slot_var, values=slots, state="readonly", width=15)
        self.combo_slots.pack(side="left", padx=5)
        self.combo_slots.bind("<<ComboboxSelected>>", self.on_slot_change)
        
        if 0 <= self.cfg.get("active_prompt_slot", 0) < len(slots):
            self.combo_slots.current(self.cfg.get("active_prompt_slot", 0))

        ttk.Button(prompt_bar, text="✏️", width=3, command=self.on_rename_slot).pack(side="left", padx=1)
        ttk.Button(prompt_bar, text="📂 열기", command=self.on_open_prompts).pack(side="left", padx=5)
        ttk.Button(prompt_bar, text="🔄 새로고침", command=self.on_reload).pack(side="left", padx=5)

        # Log & Preview Split
        split_frame = tk.Frame(bottom_frame, bg="#1E1E2E")
        split_frame.pack(fill="both", expand=True)
        
        # Left: Preview
        p_frame = tk.LabelFrame(split_frame, text=" 미리보기 ", padding=5)
        p_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.text_preview = ScrolledText(p_frame, height=8, bg="#282A36", fg="#F8F8F2", insertbackground="white", font=("Consolas", 9))
        self.text_preview.pack(fill="both", expand=True)
        
        # Right: Logs
        l_frame = tk.LabelFrame(split_frame, text=" 시스템 로그 ", padding=5)
        l_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        self.log_text = ScrolledText(l_frame, height=8, bg="black", fg="#00FF00", font=("Consolas", 9), state="disabled")
        self.log_text.pack(fill="both", expand=True)

    # [NEW] 옵션 저장 통합 함수
    def on_option_toggle(self):
        self.cfg["afk_mode"] = self.afk_var.get()
        self.cfg["sound_enabled"] = self.sound_var.get()
        self.cfg["relay_mode"] = self.relay_var.get()
        try:
            self.cfg["relay_count"] = int(self.relay_cnt_var.get())
        except:
            self.cfg["relay_count"] = 1
            
        self.save_config()
        self.log(f"⚙️ 설정 변경됨: 소리[{'ON' if self.cfg['sound_enabled'] else 'OFF'}], 이어달리기[{'ON' if self.cfg['relay_mode'] else 'OFF'} / {self.cfg['relay_count']}개]")

    def _get_coord_text(self):
        ia = self.cfg.get('input_area')
        sa = self.cfg.get('submit_area')
        aa = self.cfg.get('afk_area')
        
        i_text = "미설정"
        s_text = "미설정"
        a_text = "미설정"
        
        if ia:
            w, h = ia['x2'] - ia['x1'], ia['y2'] - ia['y1']
            i_text = "✅OK"
        if sa:
            w, h = sa['x2'] - sa['x1'], sa['y2'] - sa['y1']
            s_text = "✅OK"
        if aa:
            w, h = aa['x2'] - aa['x1'], aa['y2'] - aa['y1']
            a_text = "✅OK"
            
        return f"Input[{i_text}] Btn[{s_text}] AFK[{a_text}]"

    def log(self, msg):
        print(msg)
        try:
            if hasattr(self, "log_text"):
                ts = datetime.now().strftime("%H:%M:%S")
                self.log_text.config(state="normal")
                self.log_text.insert("end", f"[{ts}] {msg}\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except: pass

    def start_capture(self, kind):
        if kind == "input": kind_text = "입력창"
        elif kind == "submit": kind_text = "생성 버튼"
        else: kind_text = "딴짓(AFK)"
        
        def on_captured(x1, y1, x2, y2):
            area = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            if kind == "input":
                self.cfg["input_area"] = area
            elif kind == "submit":
                self.cfg["submit_area"] = area
            else:
                self.cfg["afk_area"] = area
                
            self.save_config()
            self.lbl_coords.config(text=self._get_coord_text(), fg="#8BE9FD")
            messagebox.showinfo("성공", f"{kind_text} 영역 저장 완료!\n({x1},{y1}) ~ ({x2},{y2})")
            
        CaptureOverlay(self.root, on_captured, kind_text)

    def on_slot_change(self, event=None):
        idx = self.combo_slots.current()
        if idx >= 0:
            self.cfg["active_prompt_slot"] = idx
            slot = self.cfg["prompt_slots"][idx]
            self.cfg["prompts_file"] = slot["file"]
            self.save_config()
            self.on_reload()

    def on_rename_slot(self):
        idx = self.combo_slots.current()
        if idx < 0: return
        current_name = self.cfg["prompt_slots"][idx]["name"]
        new_name = simpledialog.askstring("이름 변경", "새 이름을 입력하세요:", initialvalue=current_name)
        if new_name:
            self.cfg["prompt_slots"][idx]["name"] = new_name
            self.save_config()
            slots = [s["name"] for s in self.cfg["prompt_slots"]]
            self.combo_slots["values"] = slots
            self.combo_slots.current(idx)
            self.slot_var.set(new_name)

    def on_open_prompts(self):
        try:
            os.startfile(self.base / self.cfg["prompts_file"])
        except Exception as e:
            messagebox.showerror("오류", f"파일 열기 실패: {e}")

    def on_save_prompts(self):
        try:
            content = self.text_preview.get("1.0", "end-1c")
            path = self.base / self.cfg["prompts_file"]
            path.write_text(content, encoding="utf-8")
            self.on_reload()
            messagebox.showinfo("저장 완료", "프롬프트 파일이 저장되었습니다!")
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {e}")

    def on_reload(self):
        try:
            path = self.base / self.cfg["prompts_file"]
            if not path.exists(): path.write_text("", encoding="utf-8")
            raw = path.read_text(encoding="utf-8")
            self.text_preview.delete("1.0", "end")
            self.text_preview.insert("1.0", raw)
            sep = self.cfg.get("prompts_separator", "|||")
            self.prompts = [p.strip() for p in raw.split(sep) if p.strip()]
            if self.index >= len(self.prompts): self.index = 0
            
            # [UI Update] 진행률 즉시 갱신
            self._update_progress_ui()
            self.log(f"로드 완료 ({len(self.prompts)}개)")
        except Exception as e:
            self.log(f"로드 실패: {e}")

    def on_first(self):
        self.index = 0
        self._show()

    def on_prev(self):
        if self.index > 0: self.index -= 1
        self._show()

    def on_next(self):
        if self.index < len(self.prompts) - 1: self.index += 1
        self._show()

    def on_last(self):
        if self.prompts: self.index = len(self.prompts) - 1
        self._show()

    def _show(self):
        # UI 업데이트는 _update_progress_ui 에서 처리
        self._update_progress_ui()

    def _update_progress_ui(self):
        total = len(self.prompts)
        current = self.index
        
        # 1. Progress Bar & Text
        if total > 0:
            pct = (current / total) * 100
            self.progress_var.set(pct)
            self.lbl_prog_text.config(text=f"Progress: {current}/{total} ({pct:.1f}%)")
        else:
            self.progress_var.set(0)
            self.lbl_prog_text.config(text="No Prompts")

    def _update_monitor_ui(self):
        # Live Monitor 업데이트 (봇의 현재 상태 표시)
        p_name = self.actor.current_persona_name
        mood = self.actor.current_mood
        speed = self.actor.cfg.get('speed_multiplier', 1.0)
        
        self.lbl_live_persona.config(text=p_name)
        self.lbl_live_mood.config(text=f"{mood}")
        
        # Mood에 따라 색상 변경
        mood_color = {"Hasty": "#FF5555", "Relaxed": "#50FA7B", "Tired": "#6272A4", "Normal": "#8BE9FD"}.get(mood, "white")
        self.lbl_live_mood.config(fg=mood_color)
        
        # Speed Visual (역수: 낮을수록 빠름 -> 바는 높게)
        # speed 0.5 (Fast) -> 100%, speed 3.0 (Slow) -> 10%
        visual_speed = max(0, min(100, (3.5 - speed) * 33)) 
        self.live_speed_bar['value'] = visual_speed
        self.lbl_live_speed_text.config(text=f"x{speed:.1f}")
        
        # Batch Count
        self.lbl_live_batch.config(text=f"{self.actor.processed_count} / {self.actor.current_batch_size}")


    def _tick(self):
        if self.running and self.t_next:
            remain = self.t_next - time.time()
            if remain > 0:
                self.update_status_label(f"⏳ 대기 중... {int(remain)}초", "#F1FA8C")
                
                if self.cfg.get("afk_mode") and self.cfg.get("afk_area"):
                    self.actor.idle_action(self.cfg["afk_area"])
            
            try: base = int(self.entry_interval.get())
            except: base = 60
            remain_cnt = len(self.prompts) - self.index
            total_sec = remain_cnt * base + max(0, int(remain))
            finish_time = datetime.fromtimestamp(time.time() + total_sec).strftime("%p %I:%M")
            self.lbl_eta.config(text=f"🏁 예상 종료: {finish_time}")

            if 0 < remain <= 30:
                if self.alert_window is None:
                    self.alert_window = CountdownAlert(self.root, remain, sound_enabled=self.cfg.get("sound_enabled", True))
                else:
                    self.alert_window.update_time(remain)
            
            if remain <= 0:
                if self.alert_window:
                    self.alert_window.close()
                    self.alert_window = None
                
                self._run_task()
                
                speed = self.actor.cfg.get('speed_multiplier', 1.0)
                extra_chaos = random.uniform(0, base * speed)
                interval = int(base + extra_chaos)
                
                self.t_next = time.time() + interval
                self.log(f"🎲 [Safe Chaos] 다음 간격: {interval}초 (최소 {base}초 + 랜덤 {extra_chaos:.1f}초)")
        else:
            self.lbl_eta.config(text="--:--")
        
        self.root.after(1000, self._tick)

    def save_session_report(self):
        end_time = datetime.now()
        start_time = getattr(self, "session_start_time", end_time)
        total_duration = end_time - start_time
        
        prompt_file = self.cfg.get("prompts_file", "unknown")
        
        log_dir = self.base / "logs"
        log_dir.mkdir(exist_ok=True)
        prompt_name_only = Path(prompt_file).stem
        filename = f"Report_{prompt_name_only}_{end_time.strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = log_dir / filename
        
        lines = []
        lines.append(f"==========================================")
        lines.append(f"   [{APP_NAME}] 작업 완료 보고서")
        lines.append(f"==========================================")
        lines.append(f"■ 작업 일자: {end_time.strftime('%Y-%m-%d')}")
        lines.append(f"■ 프롬프트 파일: {prompt_file}")
        lines.append(f"■ 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"■ 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"■ 총 소요 시간: {total_duration}")
        lines.append(f"■ 처리된 장면: {len(self.session_log)}개")
        lines.append(f"==========================================")
        lines.append(f"\n[상세 내역]")
        
        total_scene_time = 0.0
        for log in self.session_log:
            lines.append(f"------------------------------------------")
            lines.append(f"장면 #{log['index']}")
            lines.append(f"- 시작 시각: {log['start']}")
            lines.append(f"- 종료 시각: {log['end']}")
            lines.append(f"- 소요 시간: {log['duration']}")
            lines.append(f"- 프롬프트: {log['prompt']}")
            
            try:
                dur_val = float(log['duration'].replace('초', ''))
                total_scene_time += dur_val
            except: pass
            
        avg_time = 0
        if self.session_log:
            avg_time = total_scene_time / len(self.session_log)
            
        lines.append(f"------------------------------------------")
        lines.append(f"\n[최종 요약]")
        lines.append(f"- 평균 장면 생성 시간: {avg_time:.2f}초")
        lines.append(f"- 총 작업 시간: {total_duration}")
        lines.append(f"\n보고서 생성 완료: {file_path}")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as e:
            print(f"파일 저장 실패: {e}")
            
        summary = (
            f"🎊 모든 작업이 완료되었습니다! 🎊\n\n"
            f"📅 시작: {start_time.strftime('%H:%M:%S')}\n"
            f"📅 종료: {end_time.strftime('%H:%M:%S')}\n"
            f"⏱ 총 소요: {total_duration}\n"
            f"🎬 처리 장면: {len(self.session_log)}개\n"
            f"⚡ 평균 속도: {avg_time:.2f}초\n\n"
            f"📂 로그 저장됨:\n{filename}"
        )
        
        is_relay_running = self.cfg.get("relay_mode") and (self.relay_progress + 1 < self.cfg.get("relay_count"))
        if not is_relay_running:
            messagebox.showinfo("작업 완료 보고서", summary)

    def _run_task(self):
        is_active, reason = self.actor.check_schedule()
        if not is_active:
            self.log(f"⛔ {reason} - 잠시 대기합니다.")
            self.update_status_label(f"🌙 {reason}...", "#6272A4")
            self.t_next = time.time() + 300 
            return

        if self.actor.processed_count >= self.actor.current_batch_size:
            self.log(f"🛑 배치 목표({self.actor.current_batch_size}개) 달성! 휴식 모드 진입.")
            self.update_status_label("☕ 재충전 중...", "#FF5555")
            duration = self.actor.take_bio_break()
            self.actor.update_batch_size()
            self.log(f"☕ 휴식 끝! 다음 배치는 {self.actor.current_batch_size}개 예정.")
            return

        if not self.prompts or self.index >= len(self.prompts):
            self.save_session_report() 
            
            if self.cfg.get("relay_mode", False):
                target_count = self.cfg.get("relay_count", 1)
                current_progress = self.relay_progress + 1 
                
                if current_progress < target_count:
                    next_slot_idx = self.cfg["active_prompt_slot"] + 1
                    
                    if next_slot_idx < len(self.cfg["prompt_slots"]):
                        self.log(f"🏃 [이어달리기] {current_progress}번 완료 -> {current_progress + 1}번 슬롯으로 이동합니다!")
                        
                        self.cfg["active_prompt_slot"] = next_slot_idx
                        self.combo_slots.current(next_slot_idx) 
                        self.on_slot_change() 
                        
                        self.relay_progress = current_progress
                        self.index = 0 
                        
                        self.play_sound("success")
                        
                        self.t_next = time.time() + 10 
                        self.log("⏳ 슬롯 교체 중... 10초 뒤 시작합니다.")
                        return
                    else:
                        self.log("🚫 [이어달리기] 더 이상 다음 슬롯이 없습니다.")
                else:
                    self.log(f"🏁 [이어달리기] 목표 달성 ({target_count}개 슬롯 완료)!")

            self.running = False
            self.update_status_label("🎉 완료!", "#BD93F9")
            self.log("작업 완료")
            self.play_sound("finish") 
            self.on_stop()
            return

        self._show()
        prompt = self.prompts[self.index]
        task_start_time = datetime.now()
        
        # [CORE Logic] Randomize Persona
        self.actor.randomize_persona()
        # [UI Update] Refresh Monitor with new stats
        self._update_monitor_ui()
        
        if self.config_window and self.config_window.root.winfo_exists():
            self.config_window.refresh_ui()
            
        self.log(f"▶ 진행: {self.index+1}/{len(self.prompts)} (인격: {self.actor.current_persona_name})")
        
        ia = self.cfg.get('input_area')
        sa = self.cfg.get('submit_area')
        
        if not ia or not sa:
            self.log("❌ 영역 설정이 필요합니다.")
            self.running = False
            self.on_stop()
            return

        try:
            # Mood Icon Update
            mood_icon = {"Hasty": "⚡", "Relaxed": "☕", "Tired": "😴", "Normal": "🙂"}.get(self.actor.current_mood, "🙂")
            self.update_status_label(f"{mood_icon} [{self.actor.current_mood}] 작업 중...", "#FFB86C")
            
            self.play_sound("start")

            self.actor.simulate_focus_loss()
            self.actor.random_behavior_routine()

            self.update_status_label("🖱️ 입력창 이동...", "white")
            
            ix_rand = random.randint(ia['x1'], ia['x2'])
            iy_rand = random.randint(ia['y1'], ia['y2'])
            self.actor.move_to(ix_rand, iy_rand, wild_approach=True)
            pyautogui.click() 

            time.sleep(random.uniform(0.2, 0.5))
            pyautogui.hotkey("ctrl", "a")
            time.sleep(random.uniform(0.1, 0.3))
            pyautogui.press("backspace")
            
            if random.random() < self.actor.cfg["empty_click_rate"]:
                self.actor.click_empty_space() 
                ix_retry = random.randint(ia['x1'], ia['x2'])
                iy_retry = random.randint(ia['y1'], ia['y2'])
                self.actor.move_to(ix_retry, iy_retry, overshoot=False)
                pyautogui.click() 

            if random.random() < self.actor.cfg["gaze_simulation"]:
                self.actor.simulate_gaze()

            self.update_status_label("✍️ 입력 중...", "white")
            self.actor.type_text(prompt, input_area=ia)
            
            self.update_status_label("📖 검토 중...", "#8BE9FD")
            if random.random() < 0.5:
                self.actor.highlight_text_habit()
            else:
                self.actor.subconscious_drag()
            
            self.actor.read_prompt_pause(prompt)
            
            if random.random() < self.actor.cfg.get("enter_submit_rate", 0.0):
                self.update_status_label("↵ 엔터 제출!", "#50FA7B")
                self.log("↵ [Human] Enter Key Submit")
                time.sleep(random.uniform(0.2, 0.5))
                pyautogui.press('enter')
            else:
                self.update_status_label("🖱️ 클릭 제출...", "white")
                
                s_w = sa['x2'] - sa['x1']
                s_h = sa['y2'] - sa['y1']
                center_x = sa['x1'] + s_w / 2
                center_y = sa['y1'] + s_h / 2
                
                while True:
                    cand_x = random.randint(sa['x1'], sa['x2'])
                    cand_y = random.randint(sa['y1'], sa['y2'])
                    norm_x = (cand_x - center_x) / (s_w / 2)
                    norm_y = (cand_y - center_y) / (s_h / 2)
                    if (norm_x**2 + norm_y**2) <= 1.0:
                        sx_rand, sy_rand = cand_x, cand_y
                        break
                
                self.actor.hesitate_on_submit(sx_rand, sy_rand)
                self.actor.move_to(sx_rand, sy_rand)
                time.sleep(random.uniform(0.1, 0.3))
                self.actor.smart_click()
            
            self.log(f"✅ 제출 완료")
            self.play_sound("success") 
            
            task_end_time = datetime.now()
            duration_sec = (task_end_time - task_start_time).total_seconds()
            self.session_log.append({
                "index": self.index + 1,
                "prompt": prompt,
                "start": task_start_time.strftime("%H:%M:%S"),
                "end": task_end_time.strftime("%H:%M:%S"),
                "duration": f"{duration_sec:.2f}초"
            })
            
            self.actor.processed_count += 1
            
            if random.random() < 0.4:
                self.actor.aimless_drag()
                self.actor.shake_mouse() 

        except Exception as e:
            self.log(f"❌ 오류: {e}")
            self.running = False
            self.on_stop()
        
        finally:
            self.index += 1
            self._update_progress_ui() # Update progress bar

if __name__ == "__main__":
    FlowVisionApp().root.mainloop()
