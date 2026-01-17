import json
import os
import time
import random
import threading
import math
from pathlib import Path
from datetime import datetime
import ctypes
import importlib # [NEW] 모듈 재로딩용

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

# [비전 봇 핵심 모듈]
import pyautogui
import pyperclip

# [NEW] 인간 행동 엔진 탑재 (항상 최신 버전 로드)
try:
    import flow.human_behavior_v2 as hb
    importlib.reload(hb) # [CRITICAL] 수정된 코드 즉시 반영
    from flow.human_behavior_v2 import HumanActor
except ImportError:
    try:
        import human_behavior_v2 as hb
        importlib.reload(hb)
        from human_behavior_v2 import HumanActor
    except ImportError:
        # 경로 문제 시 그냥 임포트 시도
        from flow.human_behavior_v2 import HumanActor

# --- 윈도우 절전 방지 상수 ---
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# --- 설정 ---
APP_NAME = "Flow Veo Vision Bot (Ultimate)"
CONFIG_FILE = "flow_config.json"
DEFAULT_CONFIG = {
    "prompts_file": "flow_prompts.txt",
    "prompts_separator": "|||",
    "interval_seconds": 180,
    "input_area": None,   # {x1, y1, x2, y2}
    "submit_area": None,  # {x1, y1, x2, y2}
    "afk_area": None,     # [NEW] 딴짓 허용 영역 {x1, y1, x2, y2}
    "afk_mode": False,    # [NEW] 사용자 없음 모드 활성화 여부
    "prompt_slots": [],
    "active_prompt_slot": 0
}

# [알림창 클래스]
class CountdownAlert:
    def __init__(self, master, seconds=30):
        self.root = tk.Toplevel(master)
        self.root.title("봇 출동 알림")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="#282A36")
        
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 300, 100 # 높이를 조금 늘림
        x = sw - w - 20
        y = sh - h - 100
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        
        self.frame = tk.Frame(self.root, bg="#282A36", highlightbackground="#BD93F9", highlightthickness=2)
        self.frame.pack(fill="both", expand=True)
        
        self.lbl_title = tk.Label(self.frame, text="👻 비전 봇 출동 준비!", font=("Malgun Gothic", 11, "bold"), bg="#282A36", fg="#FF79C6")
        self.lbl_title.pack(pady=(5, 2))
        
        # [NEW] 한/영 전환 확인 메시지
        self.lbl_check = tk.Label(self.frame, text="⚠️ 영어(A)로 바꿨나요? ⚠️", font=("Malgun Gothic", 10, "bold"), bg="#282A36", fg="#F1FA8C")
        self.lbl_check.pack(pady=(0, 2))
        
        self.lbl_time = tk.Label(self.frame, text=f"{seconds}초 전", font=("Malgun Gothic", 16, "bold"), bg="#282A36", fg="#50FA7B")
        self.lbl_time.pack(pady=(0, 5))
        
        self.x = 0
        self.y = 0
        self.blink_state = False # 깜빡임 상태 변수

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
        
        # [NEW] 10초 전부터 긴급 깜빡임 효과 (Blink Effect)
        if sec_int <= 10:
            if self.blink_state:
                bg_color = "#FF5555" # 빨강 (위험!)
                fg_color = "#FFFFFF"
            else:
                bg_color = "#282A36" # 원래 색
                fg_color = "#FF5555"
            
            self.frame.config(bg=bg_color)
            self.lbl_title.config(bg=bg_color, fg=fg_color)
            self.lbl_check.config(bg=bg_color, fg="yellow" if self.blink_state else "#F1FA8C")
            self.lbl_time.config(bg=bg_color, fg=fg_color)
            
            self.blink_state = not self.blink_state # 상태 토글
        else:
            # 10초보다 많이 남았으면 평온한 상태 유지
            self.frame.config(bg="#282A36")
            self.lbl_time.config(fg="#50FA7B", bg="#282A36")
            self.lbl_check.config(bg="#282A36")
            self.lbl_title.config(bg="#282A36")

    def close(self):
        try:
            self.root.destroy()
        except: pass

# [좌표/영역 캡처 오버레이] - 드래그 지원
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
        
        # 안내 텍스트
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
        # 드래그 시작 시 사각형 생성
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="#FF5555", width=3)

    def on_drag(self, event):
        if self.start_x is None: return
        # 사각형 크기 업데이트
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)
        self.label.config(text=f"드래그 중...\n({self.start_x},{self.start_y}) ~ ({event.x},{event.y})")

    def on_release(self, event):
        if self.start_x is None: return
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        
        # 좌표 정렬 (왼쪽위, 오른쪽아래)
        final_x1 = min(x1, x2)
        final_y1 = min(y1, y2)
        final_x2 = max(x1, x2)
        final_y2 = max(y1, y2)
        
        # 너무 작은 영역(클릭 실수) 방지
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

class HumanConfigWindow:
    def __init__(self, master, actor):
        self.actor = actor
        self.root = tk.Toplevel(master)
        self.root.title("🤖 실시간 인격 모니터 (Live Persona)")
        self.root.geometry("550x900")
        self.root.configure(bg="#282A36")
        
        # 스크롤 캔버스
        canvas = tk.Canvas(self.root, bg="#282A36", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.frame = tk.Frame(canvas, bg="#282A36")
        
        self.frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 헤더
        tk.Label(self.frame, text="🕵️ 현재 봇의 인격 상태", font=("Malgun Gothic", 14, "bold"), bg="#282A36", fg="#FF79C6").pack(pady=10)
        
        self.lbl_persona = tk.Label(self.frame, text="...", font=("Malgun Gothic", 12, "bold"), bg="#282A36", fg="#50FA7B")
        self.lbl_persona.pack(pady=5)
        
        tk.Label(self.frame, text="* 이 값들은 '작업 배치'마다 자동으로 랜덤 변경됩니다.\n* 저장이 불가능하며, 매번 새로운 패턴을 생성합니다.", 
                 font=("Malgun Gothic", 9), bg="#282A36", fg="#F8F8F2", justify="center").pack(pady=(0, 20))

        self.scales = {}
        self.entries = {}

        # 1. 생체 역학
        self.add_section("1. 생체 역학 (Biomechanics)")
        self.add_scale("speed_multiplier", "속도 배율 (낮을수록 빠름)", 0.5, 3.0)
        self.add_scale("hesitation_rate", "이동 중 멈칫 확률", 0.0, 1.0)
        self.add_scale("overshoot_rate", "오버슈트 확률", 0.0, 1.0)
        self.add_scale("micro_correction_rate", "미세 경로 수정 강도", 0.0, 1.0)

        # 2. 상호작용
        self.add_section("2. 입력 & 클릭 디테일")
        self.add_scale("typo_rate", "오타 발생 확률", 0.0, 0.2)
        self.add_scale("breathing_rate", "숨 고르기 빈도", 0.0, 0.5)
        self.add_scale("click_hesitation_rate", "클릭 전 망설임", 0.0, 1.0)
        self.add_scale("double_click_mistake", "더블클릭 실수", 0.0, 0.2)

        # 3. 환경
        self.add_section("3. 딴짓 & 심리")
        self.add_scale("distraction_rate", "딴짓 종합 확률", 0.0, 1.0)
        self.add_scale("gaze_simulation", "시선 확인 확률", 0.0, 1.0)
        self.add_scale("empty_click_rate", "빈 공간 실수 확률", 0.0, 0.5)
        self.add_scale("fatigue_factor", "피로도 누적 속도", 0.0, 0.5)

        # 4. 스케줄
        self.add_section("4. 현재 스케줄 설정")
        self.add_dual_display("batch_min", "batch_max", "배치 작업 개수 범위")
        self.add_dual_display("break_min_sec", "break_max_sec", "휴식 시간 범위 (초)")
        self.add_dual_display("work_start_hour", "work_end_hour", "활동 시간")
        self.add_scale("weekend_skip_rate", "주말 건너뛸 확률", 0.0, 1.0)

        # 리셋 버튼
        btn_frame = tk.Frame(self.root, bg="#282A36", pady=20)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="🎲 인격 리셋 (Randomize Now)", command=self.randomize).pack(side="bottom", ipadx=20, ipady=10)

        self.refresh_ui()

    def add_section(self, title):
        tk.Label(self.frame, text=title, font=("Malgun Gothic", 11, "bold"), bg="#282A36", fg="#8BE9FD", anchor="w").pack(fill="x", padx=10, pady=(15, 5))
        tk.Frame(self.frame, bg="#44475A", height=1).pack(fill="x", padx=10, pady=(0, 10))

    def add_scale(self, key, text, from_, to):
        frame = tk.Frame(self.frame, bg="#282A36", padx=10, pady=2)
        frame.pack(fill="x")
        
        lbl = tk.Label(frame, text=f"{text}: 0.00", bg="#282A36", fg="white", width=35, anchor="w")
        lbl.pack(side="left")
        
        scale = tk.Scale(frame, from_=from_, to=to, resolution=0.01, orient="horizontal", 
                         bg="#282A36", fg="white", highlightthickness=0, length=150, state="disabled")
        scale.pack(side="right")
        
        self.scales[key] = (scale, lbl, text)

    def add_dual_display(self, key1, key2, text):
        frame = tk.Frame(self.frame, bg="#282A36", padx=10, pady=2)
        frame.pack(fill="x")
        lbl = tk.Label(frame, text=f"{text}: 0 ~ 0", bg="#282A36", fg="white", anchor="w")
        lbl.pack(side="top", fill="x")
        self.entries[(key1, key2)] = (lbl, text)

    def refresh_ui(self):
        # 1. 인격 이름 업데이트
        p_name = self.actor.current_persona_name
        self.lbl_persona.config(text=f"현재 인격: {p_name}")
        
        # 2. 스케일 업데이트
        for key, (scale, lbl, text) in self.scales.items():
            val = self.actor.cfg.get(key, 0)
            scale.config(state="normal")
            scale.set(val)
            scale.config(state="disabled") # 읽기 전용 느낌
            lbl.config(text=f"{text}: {val:.2f}")

        # 3. 듀얼 디스플레이 업데이트
        for (k1, k2), (lbl, text) in self.entries.items():
            v1 = self.actor.cfg.get(k1, 0)
            v2 = self.actor.cfg.get(k2, 0)
            lbl.config(text=f"{text}: {v1} ~ {v2}")

    def randomize(self):
        self.actor.randomize_persona()
        self.refresh_ui()
        messagebox.showinfo("변경 완료", f"새로운 인격 '{self.actor.current_persona_name}'이(가) 적용되었습니다.")

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
        self.config_window = None # [NEW] 설정창 제어용 변수
        
        # [NEW] 인간 행동 모듈 인스턴스
        self.actor = HumanActor()
        
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("800x850")
        self.root.configure(bg="#1E1E2E")
        
        try:
            icon_path = self.base.parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except: pass

        self._ensure_prompt_slots()
        self._build_ui()
        self.on_reload()
        
        self.root.after(1000, self._tick)

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
        """윈도우가 절전 모드로 들어가는 것을 방지합니다."""
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            self.log("☕ 불침번 활성화: 작업 중에는 화면이 꺼지지 않습니다.")
        except: pass

    def _allow_sleep(self):
        """윈도우 절전 모드를 다시 허용합니다."""
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self.log("💤 불침번 해제: 이제 윈도우 설정에 따라 절전 모드가 가능합니다.")
        except: pass

    def on_start(self):
        # [NEW] 영역 설정 확인
        ia = self.cfg.get('input_area')
        sa = self.cfg.get('submit_area')
        
        # 구버전 호환용 (혹시 좌표만 있으면 경고)
        if not ia and self.cfg.get('input_coords'):
            messagebox.showwarning("업그레이드 알림", "입력창 위치를 '드래그' 방식으로 다시 설정해주세요!")
            return
        if not sa and self.cfg.get('submit_coords'):
            messagebox.showwarning("업그레이드 알림", "생성 버튼 위치를 '드래그' 방식으로 다시 설정해주세요!")
            return

        if not ia or not sa:
            messagebox.showwarning("주의", "먼저 [입력창]과 [생성 버튼]의 영역을 설정해주세요.")
            return
            
        self._prevent_sleep()
        
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.entry_interval.config(state="disabled")
        self.t_next = time.time()
        self.lbl_status.config(text="🚀 자동화 시작!", fg="#50FA7B")
        
        # [NEW] 시작 시 배치 사이즈 재설정 및 카운터 초기화
        self.actor.update_batch_size()
        self.actor.processed_count = 0

    def on_stop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.entry_interval.config(state="normal")
        self.lbl_status.config(text="⏹ 멈춤 (설정 변경 가능)", fg="#FF5555")
        
        self._allow_sleep()
        
        if self.alert_window:
            self.alert_window.close()
            self.alert_window = None

    def on_human_config(self):
        if self.config_window is None or not self.config_window.root.winfo_exists():
            self.config_window = HumanConfigWindow(self.root, self.actor)
        else:
            self.config_window.root.lift()

    def _build_ui(self):
        main = self.root

        # 1. 상태 바
        header_frame = tk.Frame(main, bg="#282A36", height=40)
        header_frame.pack(fill="x")
        
        self.lbl_status = tk.Label(header_frame, text="준비됨", font=("Malgun Gothic", 12, "bold"), bg="#282A36", fg="#F8F8F2")
        self.lbl_status.pack(side="left", padx=10, pady=5)
        
        self.lbl_eta = tk.Label(header_frame, text="-", font=("Malgun Gothic", 10), bg="#282A36", fg="#6272A4")
        self.lbl_eta.pack(side="right", padx=10, pady=5)

        # 2. 좌표 설정
        coord_frame = tk.LabelFrame(main, text=" 1. 영역 설정 (드래그) ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=10, pady=5)
        coord_frame.pack(fill="x", padx=20, pady=5)
        
        btn_box = tk.Frame(coord_frame, bg="#1E1E2E")
        btn_box.pack(fill="x")
        ttk.Button(btn_box, text="⬛ 입력창 영역 지정", command=lambda: self.start_capture("input")).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_box, text="⬛ 생성 버튼 영역 지정", command=lambda: self.start_capture("submit")).pack(side="left", expand=True, fill="x", padx=2)
        # [NEW] 딴짓 영역 버튼
        ttk.Button(btn_box, text="🟩 딴짓(AFK) 영역 지정", command=lambda: self.start_capture("afk")).pack(side="left", expand=True, fill="x", padx=2)
        
        self.lbl_coords = tk.Label(coord_frame, text=self._get_coord_text(), bg="#1E1E2E", fg="#8BE9FD")
        self.lbl_coords.pack(pady=2)

        # 3. 실행 제어
        run_frame = tk.LabelFrame(main, text=" 2. 실행 제어 ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=10, pady=5)
        run_frame.pack(fill="x", padx=20, pady=5)
        
        ctrl_box = tk.Frame(run_frame, bg="#1E1E2E")
        ctrl_box.pack(fill="x")
        
        # [NEW] 사용자 없음 모드 체크박스
        self.afk_var = tk.BooleanVar(value=self.cfg.get("afk_mode", False))
        chk_afk = tk.Checkbutton(ctrl_box, text="👻 사용자 없음 모드 (AFK)", variable=self.afk_var, 
                                 command=self.on_afk_toggle, bg="#1E1E2E", fg="#F1FA8C", selectcolor="#1E1E2E", activebackground="#1E1E2E", activeforeground="#F1FA8C")
        chk_afk.pack(side="top", anchor="w", padx=5, pady=5)
        
        inner_box = tk.Frame(ctrl_box, bg="#1E1E2E")
        inner_box.pack(fill="x", pady=5)
        
        tk.Label(inner_box, text="간격(초):", bg="#1E1E2E", fg="white").pack(side="left")
        self.entry_interval = tk.Entry(inner_box, width=5)
        self.entry_interval.insert(0, str(self.cfg.get("interval_seconds", 180)))
        self.entry_interval.pack(side="left", padx=5)
        
        self.btn_start = ttk.Button(inner_box, text="🌙 조용히 시작", style="Accent.TButton", command=self.on_start)
        self.btn_start.pack(side="left", padx=10, fill="x", expand=True)
        self.btn_stop = ttk.Button(inner_box, text="🛑 멈추기", command=self.on_stop, state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True)

        # [NEW] 인간화 설정 버튼 추가
        ttk.Button(run_frame, text="⚙️ 인간화 설정 (Humanizer)", command=self.on_human_config).pack(fill="x", pady=5)

        # 4. 프롬프트 & 로그
        bottom_frame = tk.Frame(main, bg="#1E1E2E")
        bottom_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        left_frame = tk.LabelFrame(bottom_frame, text=" 프롬프트 ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=5, pady=5)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        toolbar1 = tk.Frame(left_frame, bg="#1E1E2E")
        toolbar1.pack(fill="x")
        
        self.slot_var = tk.StringVar()
        slots = [s["name"] for s in self.cfg["prompt_slots"]]
        self.combo_slots = ttk.Combobox(toolbar1, textvariable=self.slot_var, values=slots, state="readonly", width=10)
        self.combo_slots.pack(side="left", padx=1)
        self.combo_slots.bind("<<ComboboxSelected>>", self.on_slot_change)
        current_idx = self.cfg.get("active_prompt_slot", 0)
        if 0 <= current_idx < len(slots):
            self.combo_slots.current(current_idx)
            
        ttk.Button(toolbar1, text="✏️", width=3, command=self.on_rename_slot).pack(side="left", padx=1)
        ttk.Button(toolbar1, text="💾", width=3, command=self.on_save_prompts).pack(side="right", padx=1)
        ttk.Button(toolbar1, text="🔄", width=3, command=self.on_reload).pack(side="right", padx=1)
        ttk.Button(toolbar1, text="📂", width=3, command=self.on_open_prompts).pack(side="right", padx=1)
        
        nav_box = tk.Frame(left_frame, bg="#1E1E2E")
        nav_box.pack(fill="x", pady=2)
        ttk.Button(nav_box, text="◀", width=3, command=self.on_prev).pack(side="left")
        self.lbl_pos = tk.Label(nav_box, text="0/0", bg="#1E1E2E", fg="white", font=("Consolas", 9))
        self.lbl_pos.pack(side="left", expand=True)
        ttk.Button(nav_box, text="▶", width=3, command=self.on_next).pack(side="right")

        self.text_preview = ScrolledText(left_frame, height=10, bg="#282A36", fg="#F8F8F2", insertbackground="white", font=("Consolas", 9))
        self.text_preview.pack(fill="both", expand=True)

        right_frame = tk.LabelFrame(bottom_frame, text=" 진행 로그 ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=5, pady=5)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.log_text = ScrolledText(right_frame, height=10, bg="#000000", fg="#00FF00", font=("Consolas", 9), state="disabled")
        self.log_text.pack(fill="both", expand=True)

    def on_afk_toggle(self):
        self.cfg["afk_mode"] = self.afk_var.get()
        self.save_config()
        mode_text = "ON 🟢" if self.cfg["afk_mode"] else "OFF ⚪"
        self.log(f"👻 사용자 없음 모드 (AFK): {mode_text}")

    def _get_coord_text(self):
        ia = self.cfg.get('input_area')
        sa = self.cfg.get('submit_area')
        aa = self.cfg.get('afk_area')
        
        i_text = "미설정"
        s_text = "미설정"
        a_text = "미설정"
        
        if ia:
            w, h = ia['x2'] - ia['x1'], ia['y2'] - ia['y1']
            i_text = f"✅설정됨 ({w}x{h})"
        if sa:
            w, h = sa['x2'] - sa['x1'], sa['y2'] - sa['y1']
            s_text = f"✅설정됨 ({w}x{h})"
        if aa:
            w, h = aa['x2'] - aa['x1'], aa['y2'] - aa['y1']
            a_text = f"✅설정됨 ({w}x{h})"
            
        return f"상태: 입력창[{i_text}] / 버튼[{s_text}] / 딴짓[{a_text}]"

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
            self._show()
            self.lbl_status.config(text=f"로드 완료 ({len(self.prompts)}개)", fg="#8BE9FD")
        except Exception as e:
            self.lbl_status.config(text=f"로드 실패: {e}", fg="#FF5555")

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
        if self.prompts and 0 <= self.index < len(self.prompts):
            self.lbl_pos.config(text=f"{self.index + 1} / {len(self.prompts)}")
        else:
            self.lbl_pos.config(text="0 / 0")

    def _tick(self):
        if self.running and self.t_next:
            remain = self.t_next - time.time()
            if remain > 0:
                self.lbl_status.config(text=f"⏳ 다음 작업까지 {int(remain)}초...", fg="#F1FA8C")
                
                # [NEW] 사용자 없음 모드 (AFK) 실행
                # 대기 시간 동안 가만히 있지 않고 딴짓을 함
                if self.cfg.get("afk_mode") and self.cfg.get("afk_area"):
                    self.actor.idle_action(self.cfg["afk_area"])
            
            # ETA 계산
            try: base = int(self.entry_interval.get())
            except: base = 60
            remain_cnt = len(self.prompts) - self.index
            total_sec = remain_cnt * base + max(0, int(remain))
            finish_time = datetime.fromtimestamp(time.time() + total_sec).strftime("%p %I:%M")
            self.lbl_eta.config(text=f"📅 예상 완료: {finish_time} (약 {total_sec//60}분 남음)")

            # 알림창
            if 0 < remain <= 30:
                if self.alert_window is None:
                    self.alert_window = CountdownAlert(self.root, remain)
                else:
                    self.alert_window.update_time(remain)
            
            if remain <= 0:
                if self.alert_window:
                    self.alert_window.close()
                    self.alert_window = None
                
                # 작업 실행
                self._run_task()
                
                # [CHAOS] 대기 시간 초랜덤 계산 (안전Floor 보장형)
                # 설정한 base(예: 180초)는 무조건 최소값으로 보장!
                # 봇의 속도 배율(speed)이 클수록(느릴수록) 추가 대기 시간이 늘어남
                speed = self.actor.cfg.get('speed_multiplier', 1.0)
                
                # 추가 대기 시간 = base의 0% ~ (speed * 100)% 만큼 랜덤 추가
                # 예: 60초 설정, speed 1.5 인격 -> 60초 + (0~90초 랜덤) = 60~150초 사이
                extra_chaos = random.uniform(0, base * speed)
                interval = int(base + extra_chaos)
                
                self.t_next = time.time() + interval
                self.log(f"🎲 [Safe Chaos] 다음 간격: {interval}초 (최소 {base}초 보장 + {extra_chaos:.1f}초 멍때림)")
        else:
            self.lbl_eta.config(text="-")
        
        self.root.after(1000, self._tick)

    def _run_task(self):
        # [NEW] 1. 스케줄 체크 (활동 시간이 아니면 스킵)
        is_active, reason = self.actor.check_schedule()
        if not is_active:
            self.log(f"⛔ {reason} - 잠시 대기합니다.")
            self.lbl_status.config(text=f"🌙 {reason}...", fg="#6272A4")
            # 다음 틱에서 다시 체크하도록 시간만 살짝 밈
            self.t_next = time.time() + 300 # 5분 뒤 재확인
            return

        # [NEW] 2. 배치 사이즈 체크 (일정 개수 수행 후 강제 휴식)
        if self.actor.processed_count >= self.actor.current_batch_size:
            self.log(f"🛑 배치 목표({self.actor.current_batch_size}개) 달성! 휴식 모드 진입.")
            self.lbl_status.config(text="☕ 재충전 중...", fg="#FF5555")
            
            duration = self.actor.take_bio_break()
            
            self.actor.update_batch_size() # 다음 배치 사이즈 설정
            self.log(f"☕ 휴식 끝! 다음 배치는 {self.actor.current_batch_size}개 예정.")
            # 휴식 시간이 끝났으므로 이번 턴은 넘기고 다음 턴에 작업 시작
            return

        if not self.prompts or self.index >= len(self.prompts):
            self.running = False
            self.lbl_status.config(text="🎉 모든 작업 완료!", fg="#BD93F9")
            self.log("작업 완료")
            messagebox.showinfo("완료", "모든 프롬프트를 처리했습니다.")
            self.on_stop()
            return

        self._show()
        prompt = self.prompts[self.index]
        
        # [CORE] 매 작업마다 인격을 리셋 (완전 무작위 패턴)
        self.actor.randomize_persona()
        
        # [LIVE] 설정창이 켜져 있다면, 슬라이더를 자동으로 움직여서 보여줌!
        if self.config_window and self.config_window.root.winfo_exists():
            self.config_window.refresh_ui()
            
        self.log(f"▶ 진행: {self.index+1}/{len(self.prompts)} (인격: {self.actor.current_persona_name})")
        
        # [NEW] 영역에서 랜덤 좌표 추출
        ia = self.cfg.get('input_area')
        sa = self.cfg.get('submit_area')
        
        if not ia or not sa:
            self.log("❌ 영역 설정이 필요합니다.")
            self.running = False
            self.on_stop()
            return

        try:
            # [NEW] 0. 작업 전 랜덤 딴짓 (20% 확률)
            mood_icon = {"Hasty": "⚡", "Relaxed": "☕", "Tired": "😴", "Normal": "🙂"}.get(self.actor.current_mood, "🙂")
            self.lbl_status.config(text=f"{mood_icon} [{self.actor.current_mood}] 준비 중...", fg="#FFB86C")
            
            # [Feature 8] 딴짓하다 포커스 잃음
            self.actor.simulate_focus_loss()
            self.actor.random_behavior_routine()

            # [NEW] 1. 입력창 이동 (지정된 영역 내 랜덤)
            self.lbl_status.config(text="🖱️ 입력창 이동...", fg="white")
            
            # 지정된 박스 안에서 랜덤 좌표 생성
            ix_rand = random.randint(ia['x1'], ia['x2'])
            iy_rand = random.randint(ia['y1'], ia['y2'])
            
            # [수정] 입력창 갈 때는 아주 화려하게! (wild_approach=True)
            self.actor.move_to(ix_rand, iy_rand, wild_approach=True)
            pyautogui.click() # 여기서 딱 한 번 클릭!

            # 2. 내용 지우기
            time.sleep(random.uniform(0.2, 0.5))
            pyautogui.hotkey("ctrl", "a")
            time.sleep(random.uniform(0.1, 0.3))
            pyautogui.press("backspace")
            
            # [NEW] 3. 가끔 빈 공간 실수 (설정값 사용)
            if random.random() < self.actor.cfg["empty_click_rate"]:
                self.actor.click_empty_space() # 클릭 안함 (움직임만)
                # 실수했으니 다시 입력창으로 (여기도 랜덤)
                ix_retry = random.randint(ia['x1'], ia['x2'])
                iy_retry = random.randint(ia['y1'], ia['y2'])
                self.actor.move_to(ix_retry, iy_retry, overshoot=False)
                pyautogui.click() # 다시 돌아와서 클릭 (총 2회 클릭 유지)

            # [NEW] 3.5 시선 시뮬레이션 (입력 전 확인)
            if random.random() < self.actor.cfg["gaze_simulation"]:
                self.actor.simulate_gaze()

            # [NEW] 4. 입력 (오타 포함)
            self.lbl_status.config(text="✍️ 입력 중...", fg="white")
            self.actor.type_text(prompt, input_area=ia)
            
            # [NEW] 5. 검토 (글자 수 비례 & 긁기)
            self.lbl_status.config(text="📖 검토 중...", fg="#8BE9FD")
            
            # [Feature 1] 읽으면서 긁적긁적 (하이라이트 습관)
            if random.random() < 0.5:
                self.actor.highlight_text_habit()
            else:
                self.actor.subconscious_drag()
            
            # 글자 수 비례해서 읽기
            self.actor.read_prompt_pause(prompt)
            
            # [NEW] 6. 제출 (엔터 or 클릭)
            # [Feature 11] 엔터로 제출하기
            if random.random() < self.actor.cfg.get("enter_submit_rate", 0.0):
                self.lbl_status.config(text="↵ 엔터 제출!", fg="#50FA7B")
                self.log("↵ [Human] Enter Key Submit")
                time.sleep(random.uniform(0.2, 0.5))
                pyautogui.press('enter')
            else:
                # 기존 클릭 방식
                self.lbl_status.config(text="🖱️ 클릭 제출...", fg="white")
                
                # [Smart Click] 타원형 영역 계산
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
                
                # [Feature 4] 제출 전 망설임
                self.actor.hesitate_on_submit(sx_rand, sy_rand)
                
                self.actor.move_to(sx_rand, sy_rand)
                time.sleep(random.uniform(0.1, 0.3))
                self.actor.smart_click()
            
            self.log(f"✅ 제출 완료")
            
            # 카운트 증가
            self.actor.processed_count += 1
            
            # [NEW] 7. 제출 후 마우스 치우기 or 딴짓
            if random.random() < 0.4:
                self.actor.aimless_drag()
                self.actor.shake_mouse() # [Feature 3]

        except Exception as e:
            self.log(f"❌ 오류: {e}")
            self.running = False
            self.on_stop()
        
        finally:
            self.index += 1

if __name__ == "__main__":
    FlowVisionApp().root.mainloop()
