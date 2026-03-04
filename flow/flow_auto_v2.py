import json
import os
import time
import random
import threading
import queue
import re
import calendar
import traceback 
from pathlib import Path
from datetime import datetime, timedelta
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

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    pystray = None
    Image = None
    TRAY_AVAILABLE = False

# [Playwright 핵심 모듈]
from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)
try:
    from playwright_stealth import stealth_sync
except ImportError:
    try:
        from playwright_stealth import Stealth

        def stealth_sync(page):
            try:
                Stealth().apply_stealth_sync(page)
            except Exception:
                return None
    except ImportError:
        def stealth_sync(_page):
            return None

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

APP_VERSION = "2026-03-03 Ver.01"
APP_NAME = f"Flow Veo 자동화 봇 (Ultimate V2) - {APP_VERSION}"
CONFIG_FILE = "flow_config.json"
DEFAULT_CONFIG = {
    "prompts_file": "flow_prompts.txt",
    "prompts_separator": "|||",
    "interval_seconds": 180,
    "start_url": "https://labs.google/flow",
    "input_selector": "textarea, [contenteditable='true']",
    "submit_selector": "button[type='submit']",
    "auto_open_new_project": True,
    "new_project_selector": "",
    "browser_headless": False,
    "browser_channel": "chrome",
    "browser_profile_dir": "flow_human_profile_pw",
    "input_area": None,  # 구버전 호환용(미사용)
    "submit_area": None,  # 구버전 호환용(미사용)
    "afk_area": None,  # 구버전 호환용(미사용)
    "afk_mode": False,
    "prompt_slots": [],
    "active_prompt_slot": 0,
    "sound_enabled": True,
    "relay_mode": False,
    "relay_count": 1,
    "relay_start_slot": None,
    "relay_end_slot": None,
    "relay_use_selection": False,
    "relay_selected_slots": [],
    "scheduled_start_enabled": False,
    "scheduled_start_at": "",
    "language_mode": "en",
    "input_mode": "typing", # typing, paste, mixed
    "asset_loop_enabled": False,
    "asset_loop_start": 1,
    "asset_loop_end": 1,
    "asset_loop_num_width": 0,
    "asset_loop_prefix": "S",
    "asset_loop_prompt_template": "{tag} : Naturally Seamless Loop animation.",
    "asset_start_selector": "",
    "asset_search_button_selector": "",
    "asset_search_input_selector": "",
    "download_mode": "video",  # video / image
    "download_video_quality": "1080P",
    "download_image_quality": "4K",
    "download_wait_seconds": 60,
    "download_search_input_selector": "",
    "download_video_filter_selector": "",
    "download_image_filter_selector": "",
    "download_video_card_selector": "",
    "download_image_card_selector": "",
    "download_video_more_selector": "",
    "download_image_more_selector": "",
    "download_video_menu_selector": "",
    "download_image_menu_selector": "",
    "download_video_quality_selector": "",
    "download_image_quality_selector": "",
    "enter_submit_rate": 0.5,
    "use_ref_images": False,
    "ref_image_count": 1,
    "add_btn1_area": None,
    "add_btn2_area": None,
    "add_btn3_area": None,
    "add_btn4_area": None,
    "add_btn5_area": None,
    "ref_img1_area": None,
    "ref_img2_area": None,
    "ref_img3_area": None,
    "ref_img4_area": None,
    "ref_img5_area": None
}

SLOT_FILE_REGEX = re.compile(r"^flow_prompts_slot_?(\d+)\.txt$", re.IGNORECASE)

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
        self.logs_dir = self.base.parent / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.running = False
        self.is_processing = False 
        self.prompts = []
        self.index = 0
        self.t_next = None
        self.scheduled_waiting = False
        self.scheduled_start_ts = None
        self.alert_window = None
        self.relay_progress = 0 
        self.playwright = None
        self.browser_context = None
        self.page = None
        self.action_log_path = None
        self.action_log_fp = None
        self.session_report_path = None
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.worker_stop_event = threading.Event()
        self.run_input_mode = None
        self.enter_only_submit = True
        self.asset_loop_items = []
        self.current_run_mode = None
        self.tray_icon = None
        self.tray_thread = None
        self.hidden_to_tray = False
        self._tray_warned_unavailable = False
        self.paused = False
        self.pause_remaining = None
        self.download_items = []
        self.download_index = 0
        self.download_session_log = []
        self.download_report_path = None

        self.actor = HumanActor(action_logger=self._action_log, status_callback=self._actor_status)
        self.actor.language_mode = self.cfg.get("language_mode", "en")
        
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self._set_initial_window_size()
        self.root.configure(bg="#FFFFFF")
        
        # [NEW] Responsive Grid Weight
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
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
                # 왼쪽(설정) 비중을 크게: 68% / 32%
                self.body_pane.sashpos(0, int(total_w * 0.68))
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

    def _actor_status(self, text):
        self.root.after(0, lambda: self.update_status_label(text, self.color_info))

    def _action_log(self, msg):
        if not self.action_log_fp:
            return
        try:
            self.action_log_fp.write(f"{msg}\n")
            self.action_log_fp.flush()
        except Exception:
            pass

    def _open_action_log(self, prefix="action_trace"):
        if self.action_log_fp:
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prefix = str(prefix or "action_trace").strip() or "action_trace"
        self.action_log_path = self.logs_dir / f"{safe_prefix}_{stamp}.log"
        self.action_log_fp = self.action_log_path.open("a", encoding="utf-8")
        self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] 액션 로그 파일 생성: {self.action_log_path}")
        self.log(f"🧾 행동 로그 저장 시작: {self.action_log_path.name}")

    def _close_action_log(self):
        if not self.action_log_fp:
            return
        try:
            self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] 액션 로그 종료")
            self.action_log_fp.close()
        except Exception:
            pass
        finally:
            self.action_log_fp = None

    def _resolve_profile_dir(self):
        profile_dir = (self.cfg.get("browser_profile_dir") or "flow_human_profile_pw").strip()
        profile_path = self.base / profile_dir
        profile_path.mkdir(parents=True, exist_ok=True)
        return profile_path

    def _ensure_browser_session(self):
        if self.page and not self.page.is_closed():
            return
        if self.playwright is None:
            self.playwright = sync_playwright().start()
        if self.browser_context:
            try:
                self.browser_context.close()
            except Exception:
                pass
            self.browser_context = None

        profile_path = self._resolve_profile_dir()
        # Windows에서 남아있는 profile lock 파일이 있으면 launch가 즉시 죽는 경우가 있어 정리
        for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            try:
                p = profile_path / lock_name
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        channel = (self.cfg.get("browser_channel") or "chrome").strip() or None
        headless = bool(self.cfg.get("browser_headless", False))
        viewport_w = random.randint(1366, 1720)
        viewport_h = random.randint(820, 980)

        def _launch_with(_profile_path, _channel):
            return self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(_profile_path),
                channel=_channel,
                headless=headless,
                viewport={"width": viewport_w, "height": viewport_h},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--start-maximized",
                ],
            )

        try:
            self.browser_context = _launch_with(profile_path, channel)
        except Exception as e1:
            # 1차 폴백: 채널 미지정(Playwright Chromium)
            self.log(f"⚠️ 브라우저 실행 1차 실패, Chromium 폴백 시도: {e1}")
            try:
                self.browser_context = _launch_with(profile_path, None)
            except Exception as e2:
                # 2차 폴백: 임시 프로필 디렉토리
                runtime_profile = self.base / f"flow_human_profile_pw_runtime_{int(time.time())}"
                runtime_profile.mkdir(parents=True, exist_ok=True)
                self.log(f"⚠️ 브라우저 실행 2차 실패, 임시 프로필 폴백 시도: {e2}")
                self.browser_context = _launch_with(runtime_profile, None)

        if self.browser_context.pages:
            self.page = self.browser_context.pages[0]
        else:
            self.page = self.browser_context.new_page()

        try:
            stealth_sync(self.page)
        except Exception as e:
            self.log(f"⚠️ stealth 적용 실패(계속 진행): {e}")

        self.actor.set_page(self.page)
        self.log("🌐 Playwright 브라우저 세션 연결 완료")
        self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] 브라우저 세션 생성")

    def _shutdown_browser(self):
        try:
            if self.browser_context:
                self.browser_context.close()
        except Exception:
            pass
        self.browser_context = None
        self.page = None

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        self.playwright = None

    def _ensure_worker_thread(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        self.worker_stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.log("🧵 자동화 작업 스레드 시작")

    def _stop_worker_thread(self):
        self.worker_stop_event.set()
        try:
            self.task_queue.put_nowait("shutdown_and_stop")
        except Exception:
            pass
        if self.worker_thread and self.worker_thread.is_alive():
            try:
                self.worker_thread.join(timeout=2.0)
            except Exception:
                pass
        self.worker_thread = None
        # 남은 큐를 비워 다음 시작 시 중복 실행 방지
        try:
            while True:
                self.task_queue.get_nowait()
        except queue.Empty:
            pass

    def _worker_loop(self):
        while not self.worker_stop_event.is_set():
            try:
                cmd = self.task_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if cmd == "stop":
                break
            if cmd == "shutdown_and_stop":
                try:
                    self._shutdown_browser()
                except Exception:
                    pass
                break
            if cmd == "run":
                try:
                    self._run_task()
                except Exception as e:
                    self.log(f"❌ 작업 스레드 예외: {e}")

    def _ensure_prompt_slots(self):
        changed = False
        if "prompt_slots" not in self.cfg or not self.cfg["prompt_slots"]:
            self.cfg["prompt_slots"] = [{"name": "기본 슬롯", "file": "flow_prompts.txt"}]
            self.cfg["active_prompt_slot"] = 0
            changed = True

        active = self._clamp_slot_index(self.cfg.get("active_prompt_slot", 0))
        if self.cfg.get("active_prompt_slot") != active:
            self.cfg["active_prompt_slot"] = active
            changed = True

        expected_file = self.cfg["prompt_slots"][active]["file"]
        if self.cfg.get("prompts_file") != expected_file:
            self.cfg["prompts_file"] = expected_file
            changed = True

        for key in ("relay_start_slot", "relay_end_slot"):
            val = self.cfg.get(key)
            if val is not None:
                clamped = self._clamp_slot_index(val, active)
                if val != clamped:
                    self.cfg[key] = clamped
                    changed = True

        selected_before = self.cfg.get("relay_selected_slots", [])
        selected_after = self._normalize_relay_selected_slots(selected_before)
        if selected_before != selected_after:
            self.cfg["relay_selected_slots"] = selected_after
            changed = True

        if changed:
            self.save_config()

    def _clamp_slot_index(self, idx, default=0):
        slots = self.cfg.get("prompt_slots", [])
        if not slots:
            return 0
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = default
        return max(0, min(len(slots) - 1, idx))

    def _get_effective_relay_range(self):
        slots = self.cfg.get("prompt_slots", [])
        if not slots:
            return 0, 0
        active = self._clamp_slot_index(self.cfg.get("active_prompt_slot", 0))
        start = self.cfg.get("relay_start_slot")
        end = self.cfg.get("relay_end_slot")

        if start is None or end is None:
            try:
                count = max(1, int(self.cfg.get("relay_count", 1)))
            except (TypeError, ValueError):
                count = 1
            start = active
            end = min(len(slots) - 1, start + count - 1)
        else:
            start = self._clamp_slot_index(start, active)
            end = self._clamp_slot_index(end, active)
            if start > end:
                start, end = end, start
        return start, end

    def _normalize_relay_selected_slots(self, selected):
        slots = self.cfg.get("prompt_slots", [])
        total = len(slots)
        if total <= 0:
            return []
        if not isinstance(selected, (list, tuple)):
            return []
        seen = set()
        out = []
        for raw in selected:
            try:
                idx = int(raw)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < total and idx not in seen:
                out.append(idx)
                seen.add(idx)
        out.sort()
        return out

    def _get_effective_relay_sequence(self):
        slots = self.cfg.get("prompt_slots", [])
        if not slots:
            return []
        if self.cfg.get("relay_use_selection"):
            selected = self._normalize_relay_selected_slots(self.cfg.get("relay_selected_slots", []))
            if selected:
                return selected
        start, end = self._get_effective_relay_range()
        return list(range(start, end + 1))

    def _sync_relay_range_controls(self):
        if not hasattr(self, "combo_relay_start") or not hasattr(self, "combo_relay_end"):
            return
        slots = [s["name"] for s in self.cfg.get("prompt_slots", [])]
        self.combo_relay_start["values"] = slots
        self.combo_relay_end["values"] = slots
        if not slots:
            return
        start, end = self._get_effective_relay_range()
        self.combo_relay_start.current(start)
        self.combo_relay_end.current(end)
        self._sync_relay_selection_label()

    def _sync_relay_selection_label(self):
        if not hasattr(self, "lbl_relay_pick"):
            return
        selected = self._normalize_relay_selected_slots(self.cfg.get("relay_selected_slots", []))
        slot_names = [self.cfg["prompt_slots"][i]["name"] for i in selected]
        mode_txt = "체크사용" if self.cfg.get("relay_use_selection") else "체크미사용"
        if slot_names:
            preview = ", ".join(slot_names[:2])
            if len(slot_names) > 2:
                preview += f" 외 {len(slot_names) - 2}개"
            txt = f"{mode_txt} | {preview}"
        else:
            txt = f"{mode_txt} | 선택 없음(범위 실행)"
        self.lbl_relay_pick.config(text=txt)

    def _make_unique_slot_name(self, base_name):
        existing = {s.get("name", "") for s in self.cfg.get("prompt_slots", [])}
        if base_name not in existing:
            return base_name
        suffix = 2
        while True:
            candidate = f"{base_name} ({suffix})"
            if candidate not in existing:
                return candidate
            suffix += 1

    def _build_asset_loop_items(self):
        if not self.cfg.get("asset_loop_enabled", False):
            return []

        try:
            start_num = int(self.cfg.get("asset_loop_start", 1))
        except (TypeError, ValueError):
            start_num = 1
        try:
            end_num = int(self.cfg.get("asset_loop_end", 1))
        except (TypeError, ValueError):
            end_num = start_num

        start_num = max(1, start_num)
        end_num = max(1, end_num)
        if start_num > end_num:
            start_num, end_num = end_num, start_num

        prefix = (self.cfg.get("asset_loop_prefix") or "S").strip() or "S"
        try:
            pad_width = int(self.cfg.get("asset_loop_num_width", 0))
        except (TypeError, ValueError):
            pad_width = 0
        pad_width = max(0, pad_width)
        template = (self.cfg.get("asset_loop_prompt_template") or "{tag} : Naturally Seamless Loop animation.").strip()
        if "{tag}" not in template:
            template = "{tag} : " + template

        max_items = 500
        items = []
        for n in range(start_num, end_num + 1):
            if len(items) >= max_items:
                break
            num_txt = str(n).zfill(pad_width) if pad_width > 0 else str(n)
            tag = f"{prefix}{num_txt}"
            prompt = template.replace("{tag}", tag).strip()
            items.append({"tag": tag, "prompt": prompt})
        return items

    def _build_download_items(self):
        try:
            start_num = int(self.cfg.get("asset_loop_start", 1))
        except (TypeError, ValueError):
            start_num = 1
        try:
            end_num = int(self.cfg.get("asset_loop_end", 1))
        except (TypeError, ValueError):
            end_num = start_num
        start_num = max(1, start_num)
        end_num = max(1, end_num)
        if start_num > end_num:
            start_num, end_num = end_num, start_num

        prefix = (self.cfg.get("asset_loop_prefix") or "S").strip() or "S"
        try:
            pad_width = int(self.cfg.get("asset_loop_num_width", 0))
        except (TypeError, ValueError):
            pad_width = 0
        if pad_width <= 0:
            pad_width = 2

        items = []
        max_items = 500
        for n in range(start_num, end_num + 1):
            if len(items) >= max_items:
                break
            tag = f"{prefix}{str(n).zfill(pad_width)}"
            items.append(tag)
        return items

    def _download_mode(self):
        mode = str(self.cfg.get("download_mode", "video") or "video").strip().lower()
        return "image" if mode == "image" else "video"

    def _download_quality(self, mode=None):
        mode = mode or self._download_mode()
        if mode == "image":
            val = str(self.cfg.get("download_image_quality", "4K") or "4K").strip().upper()
            return val if val in ("1K", "2K", "4K") else "4K"
        val = str(self.cfg.get("download_video_quality", "1080P") or "1080P").strip().upper()
        return val if val in ("720P", "1080P", "4K") else "1080P"

    def _download_search_input_candidates(self):
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get("download_search_input_selector", "")))
        cands.extend([
            "input[placeholder*='검색' i]",
            "input[aria-label*='검색' i]",
            "input[placeholder*='search' i]",
            "input[aria-label*='search' i]",
            "input[type='search']",
            "[role='searchbox']",
            "[role='textbox'][aria-label*='검색' i]",
            "[role='textbox'][aria-label*='search' i]",
            "[contenteditable='true'][aria-label*='검색' i]",
            "[contenteditable='true'][aria-label*='search' i]",
        ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _download_filter_candidates(self, mode):
        key = "download_image_filter_selector" if mode == "image" else "download_video_filter_selector"
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get(key, "")))
        if mode == "image":
            cands.extend([
                "button:has-text('이미지')",
                "[role='button']:has-text('이미지')",
                "button[aria-label*='이미지' i]",
                "[role='button'][aria-label*='이미지' i]",
                "button:has-text('Image')",
                "[role='button']:has-text('Image')",
                "button[aria-label*='image' i]",
            ])
        else:
            cands.extend([
                "button:has-text('영상')",
                "[role='button']:has-text('영상')",
                "button[aria-label*='영상' i]",
                "[role='button'][aria-label*='영상' i]",
                "button:has-text('Video')",
                "[role='button']:has-text('Video')",
                "button[aria-label*='video' i]",
            ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _download_card_candidates(self, mode):
        key = "download_image_card_selector" if mode == "image" else "download_video_card_selector"
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get(key, "")))
        cands.extend([
            "article",
            "[role='listitem']",
            "li",
            "div[class*='card' i]",
            "div[class*='tile' i]",
            "div[data-testid*='card' i]",
            "div[data-testid*='result' i]",
        ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _download_more_candidates(self, mode):
        key = "download_image_more_selector" if mode == "image" else "download_video_more_selector"
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get(key, "")))
        cands.extend([
            "button[aria-label*='더보기' i]",
            "[role='button'][aria-label*='더보기' i]",
            "button[aria-label*='more' i]",
            "[role='button'][aria-label*='more' i]",
            "button[title*='more' i]",
            "button:has-text('...')",
            "button:has-text('⋮')",
        ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _download_menu_candidates(self, mode):
        key = "download_image_menu_selector" if mode == "image" else "download_video_menu_selector"
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get(key, "")))
        cands.extend([
            "button:has-text('다운로드')",
            "[role='menuitem']:has-text('다운로드')",
            "[role='button']:has-text('다운로드')",
            "text=다운로드",
            "button:has-text('Download')",
            "[role='menuitem']:has-text('Download')",
            "text=Download",
        ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _download_quality_candidates(self, mode, quality):
        key = "download_image_quality_selector" if mode == "image" else "download_video_quality_selector"
        quality = str(quality or "").strip().upper()
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get(key, "")))
        if quality:
            cands.extend([
                f"button:has-text('{quality}')",
                f"[role='menuitem']:has-text('{quality}')",
                f"[role='option']:has-text('{quality}')",
                f"text={quality}",
            ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _resolve_download_search_input(self, timeout_sec=8):
        if not self.page:
            return None, None

        end_ts = time.time() + max(1, timeout_sec)
        best_loc = None
        best_sel = None
        best_score = float("-inf")
        viewport_w = 1600
        viewport_h = 900
        try:
            vp = self.page.viewport_size or {}
            viewport_w = int(vp.get("width", 1600))
            viewport_h = int(vp.get("height", 900))
        except Exception:
            pass

        positive_keys = ("search", "검색", "media", "all media")
        negative_keys = ("project", "title", "이름", "rename", "name", "prompt", "프롬프트", "무엇을 만들고")

        while time.time() < end_ts:
            for sel in self._download_search_input_candidates():
                try:
                    loc = self.page.locator(sel)
                    total = min(loc.count(), 20)
                except Exception:
                    continue
                for i in range(total):
                    cand = loc.nth(i)
                    try:
                        if not cand.is_visible(timeout=600):
                            continue
                        box = cand.bounding_box()
                    except Exception:
                        continue
                    if not box:
                        continue
                    if box["width"] < 100 or box["height"] < 20:
                        continue
                    score = 0.0
                    meta = self._locator_meta_text(cand)
                    if any(k in meta for k in positive_keys):
                        score += 450.0
                    if any(k in meta for k in negative_keys):
                        score -= 800.0
                    if box["width"] >= 280:
                        score += 220.0
                    elif box["width"] >= 180:
                        score += 80.0
                    else:
                        score -= 300.0
                    if box["y"] <= max(160, viewport_h * 0.22):
                        score += 120.0
                    else:
                        score -= 220.0
                    cx = box["x"] + box["width"] / 2.0
                    center_bias = abs(cx - (viewport_w / 2.0))
                    score -= center_bias * 0.25
                    if box["x"] < viewport_w * 0.18:
                        score -= 180.0
                    if score > best_score:
                        best_score = score
                        best_loc = cand
                        best_sel = sel
            if best_loc is not None and best_score >= -40:
                return best_loc, best_sel
            time.sleep(0.25)
        return best_loc, best_sel

    def _find_first_media_tile_box(self):
        if not self.page:
            return None
        try:
            return self.page.evaluate(
                """() => {
                    const isVisible = (el) => {
                        if (!el) return false;
                        const r = el.getBoundingClientRect();
                        if (!r || r.width < 160 || r.height < 90) return false;
                        const st = window.getComputedStyle(el);
                        if (!st) return false;
                        return st.display !== 'none' && st.visibility !== 'hidden' && st.opacity !== '0';
                    };
                    const candidates = Array.from(document.querySelectorAll("video, img, canvas"));
                    const boxes = [];
                    for (const el of candidates) {
                        if (!isVisible(el)) continue;
                        const r = el.getBoundingClientRect();
                        if (r.top < 70) continue;
                        boxes.push({x:r.left, y:r.top, width:r.width, height:r.height});
                    }
                    boxes.sort((a,b) => (a.y - b.y) || (a.x - b.x));
                    return boxes.length ? boxes[0] : null;
                }"""
            )
        except Exception:
            return None

    def _resolve_more_button_near_box(self, box):
        if (not self.page) or (not box):
            return None, None
        try:
            loc = self.page.locator("button, [role='button']")
            total = min(loc.count(), 250)
        except Exception:
            return None, None
        right_top_x = float(box["x"]) + float(box["width"]) - 18.0
        right_top_y = float(box["y"]) + 18.0
        best = None
        best_score = float("inf")
        for i in range(total):
            cand = loc.nth(i)
            try:
                if not cand.is_visible(timeout=500):
                    continue
                b = cand.bounding_box()
            except Exception:
                continue
            if not b:
                continue
            if b["x"] < box["x"] - 24 or b["x"] > (box["x"] + box["width"] + 24):
                continue
            if b["y"] < box["y"] - 30 or b["y"] > (box["y"] + min(140, box["height"] * 0.45)):
                continue
            if b["width"] > 110 or b["height"] > 70:
                continue
            cx = b["x"] + b["width"] / 2.0
            cy = b["y"] + b["height"] / 2.0
            score = abs(cx - right_top_x) + abs(cy - right_top_y)
            try:
                meta = cand.evaluate("""(el)=>((el.getAttribute('aria-label')||'')+' '+(el.getAttribute('title')||'')+' '+(el.innerText||'')).toLowerCase()""")
            except Exception:
                meta = ""
            if any(x in meta for x in ("더보기", "more", "menu", "...", "⋮", "︙")):
                score -= 220.0
            if score < best_score:
                best_score = score
                best = cand
        return (best, "") if best is not None else (None, None)

    def _asset_start_button_candidates(self):
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get("asset_start_selector", "")))
        cands.extend([
            "button:has-text('시작')",
            "[role='button']:has-text('시작')",
            "button:has-text('Start')",
            "[role='button']:has-text('Start')",
        ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _asset_search_button_candidates(self):
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get("asset_search_button_selector", "")))
        cands.extend([
            "button:has-text('에셋 검색')",
            "[role='button']:has-text('에셋 검색')",
            "button:has-text('Asset search')",
            "[role='button']:has-text('Asset search')",
            "button:has-text('Search assets')",
            "[role='button']:has-text('Search assets')",
        ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _asset_search_input_candidates(self):
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get("asset_search_input_selector", "")))
        cands.extend([
            "input[placeholder*='에셋 검색' i]",
            "input[aria-label*='에셋 검색' i]",
            "textarea[placeholder*='에셋 검색' i]",
            "textarea[aria-label*='에셋 검색' i]",
            "input[placeholder*='asset' i]",
            "input[aria-label*='asset' i]",
            "textarea[placeholder*='asset' i]",
            "textarea[aria-label*='asset' i]",
            "input[placeholder*='검색' i]",
            "input[aria-label*='검색' i]",
            "textarea[placeholder*='검색' i]",
            "textarea[aria-label*='검색' i]",
            "[role='textbox'][aria-label*='에셋' i]",
            "[role='textbox'][aria-label*='asset' i]",
            "[contenteditable='true'][aria-label*='에셋' i]",
            "[contenteditable='true'][aria-label*='asset' i]",
            "input[type='search']",
            "[role='searchbox']",
        ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _wait_best_locator(self, candidates, timeout_sec=8, prefer_enabled=True):
        end_ts = time.time() + max(1, timeout_sec)
        while time.time() < end_ts:
            loc, sel = self._resolve_best_locator(
                candidates,
                timeout_ms=900,
                prefer_enabled=prefer_enabled,
            )
            if loc is not None:
                return loc, sel
            time.sleep(0.25)
        return None, None

    def _click_with_actor_fallback(self, locator, label):
        if locator is None:
            return False
        try:
            self.actor.move_to_locator(locator, label=label)
            self.actor.smart_click(label=f"{label} 클릭")
            return True
        except Exception:
            pass
        try:
            locator.click(timeout=2500)
            return True
        except Exception:
            return False

    def _resolve_text_locator_any_frame(self, texts, timeout_ms=1200):
        if not self.page:
            return None, None
        if isinstance(texts, str):
            texts = [texts]
        texts = [t for t in texts if isinstance(t, str) and t.strip()]
        if not texts:
            return None, None

        frames = []
        try:
            frames = list(self.page.frames)
        except Exception:
            frames = [self.page.main_frame]
        if self.page.main_frame not in frames:
            frames.insert(0, self.page.main_frame)

        for fr in frames:
            for txt in texts:
                try:
                    loc = fr.get_by_text(txt, exact=False).first
                    if loc.count() <= 0:
                        continue
                    if not loc.is_visible(timeout=timeout_ms):
                        continue
                    return loc, f"text:{txt}"
                except Exception:
                    continue
        return None, None

    def _direct_fill_asset_search_via_dom(self, asset_tag):
        if (not self.page) or (not asset_tag):
            return False, "page/tag 없음"
        try:
            result = self.page.evaluate(
                """(payload) => {
                    const tag = String(payload.tag || "").trim();
                    if (!tag) return {ok:false, reason:"empty-tag"};

                    const searchKeys = ["asset", "search", "에셋", "검색"];
                    const promptKeys = ["무엇을 만들고 싶으신가요", "prompt", "프롬프트", "message", "메시지"];

                    const isVisible = (el) => {
                        if (!el) return false;
                        const r = el.getBoundingClientRect();
                        if (!r || r.width < 10 || r.height < 10) return false;
                        const st = window.getComputedStyle(el);
                        return st && st.display !== "none" && st.visibility !== "hidden" && st.opacity !== "0";
                    };

                    const metaText = (el) => {
                        const a = (k) => (el.getAttribute(k) || "");
                        return [
                            el.tagName || "",
                            el.id || "",
                            el.className || "",
                            a("name"),
                            a("placeholder"),
                            a("aria-label"),
                            a("title"),
                            (el.innerText || ""),
                        ].join(" ").toLowerCase();
                    };

                    const roots = [];
                    const q = [document];
                    while (q.length) {
                        const root = q.shift();
                        roots.push(root);
                        const hostNodes = root.querySelectorAll ? root.querySelectorAll("*") : [];
                        for (const h of hostNodes) {
                            if (h && h.shadowRoot) q.push(h.shadowRoot);
                        }
                    }

                    let best = null;
                    let bestScore = -1e9;
                    for (const root of roots) {
                        const nodes = root.querySelectorAll ? root.querySelectorAll("input, textarea, [contenteditable='true'], [role='searchbox'], [role='textbox']") : [];
                        for (const el of nodes) {
                            if (!isVisible(el)) continue;
                            const meta = metaText(el);
                            const r = el.getBoundingClientRect();
                            let score = 0;

                            const hasSearch = searchKeys.some(k => meta.includes(k));
                            const hasPrompt = promptKeys.some(k => meta.includes(k));
                            if (hasSearch) score += 450;
                            if (hasPrompt) score -= 700;

                            if ((el.tagName || "").toLowerCase() === "input") score += 80;
                            if ((el.getAttribute("type") || "").toLowerCase() === "search") score += 260;
                            if (r.width > 120 && r.width < 700) score += 70;
                            if (r.y > 0 && r.y < window.innerHeight * 0.9) score += 30;

                            if (score > bestScore) {
                                bestScore = score;
                                best = el;
                            }
                        }
                    }

                    if (!best || bestScore < 120) {
                        return {ok:false, reason:"search-input-not-found"};
                    }

                    best.focus();
                    try {
                        if ("value" in best) {
                            best.value = "";
                            best.dispatchEvent(new Event("input", {bubbles:true}));
                            best.value = tag;
                            best.dispatchEvent(new Event("input", {bubbles:true}));
                            best.dispatchEvent(new Event("change", {bubbles:true}));
                        } else {
                            best.textContent = "";
                            best.dispatchEvent(new InputEvent("input", {bubbles:true, data:""}));
                            best.textContent = tag;
                            best.dispatchEvent(new InputEvent("input", {bubbles:true, data:tag}));
                        }
                        return {ok:true, reason:"dom-filled"};
                    } catch (e) {
                        return {ok:false, reason:String(e)};
                    }
                }""",
                {"tag": asset_tag},
            )
            ok = bool(result and result.get("ok"))
            reason = (result or {}).get("reason", "")
            return ok, reason
        except Exception as e:
            return False, str(e)

    def _run_asset_loop_prestep(self, asset_tag):
        if (not self.page) or (not asset_tag):
            return

        self.log(f"🔁 S반복 사전단계 시작: {asset_tag}")
        start_locator, start_selector = self._wait_best_locator(
            self._asset_start_button_candidates(),
            timeout_sec=6,
            prefer_enabled=False,
        )
        if start_locator is not None:
            if self._click_with_actor_fallback(start_locator, "시작 버튼"):
                self.log(f"🟢 Step1 시작 클릭: {start_selector or '텍스트 탐색'}")
                self.actor.random_action_delay("시작 클릭 후 대기", 0.5, 1.6)
        else:
            start_locator, start_selector = self._resolve_text_locator_any_frame(["시작", "Start"], timeout_ms=1000)
            if start_locator is not None and self._click_with_actor_fallback(start_locator, "시작 버튼"):
                self.log(f"🟢 Step1 시작 클릭(문구탐색): {start_selector}")
                self.actor.random_action_delay("시작 클릭 후 대기", 0.5, 1.6)
            else:
                self.log("ℹ️ Step1 시작 버튼 미탐지(현재 화면 유지)")

        # 2-0) 에셋 검색 버튼 없이 바로 검색 입력칸이 열리는 UI 대응
        direct_input, _ = self._wait_best_locator(
            self._asset_search_input_candidates(),
            timeout_sec=4,
            prefer_enabled=False,
        )
        if direct_input is not None:
            try:
                direct_input.click(timeout=1200)
            except Exception:
                pass
            try:
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Backspace")
            except Exception:
                pass
            try:
                direct_input.fill(asset_tag)
            except Exception:
                try:
                    direct_input.type(asset_tag, delay=random.randint(25, 70))
                except Exception:
                    direct_input = None
            if direct_input is not None:
                self.page.keyboard.press("Enter")
                self.log(f"✅ Step2 에셋 검색 입력 완료(직접입력): {asset_tag}")
                self.actor.random_action_delay("에셋 검색 Enter 후 대기", 0.2, 1.0)
                return

        search_candidates = self._asset_search_button_candidates() + [
            "text=에셋 검색",
            "text=Asset search",
            "text=Search assets",
            "[aria-label*='에셋' i][aria-label*='검색' i]",
            "[title*='에셋' i][title*='검색' i]",
            "[aria-label*='asset' i][aria-label*='search' i]",
            "[title*='asset' i][title*='search' i]",
        ]
        search_locator, search_selector = self._wait_best_locator(
            search_candidates,
            timeout_sec=10,
            prefer_enabled=False,
        )
        if search_locator is None:
            search_locator, search_selector = self._resolve_text_locator_any_frame(
                ["에셋 검색", "Asset search", "Search assets"],
                timeout_ms=1200,
            )
        if search_locator is not None:
            if not self._click_with_actor_fallback(search_locator, "에셋 검색 버튼"):
                self.log("ℹ️ Step2 에셋 검색 클릭 실패, 입력칸 직접 탐색으로 전환")
            else:
                self.log(f"🔎 Step2 에셋 검색 클릭: {search_selector or '텍스트 탐색'}")
                self.actor.random_action_delay("에셋 검색 클릭 후 대기", 0.4, 1.6)

        search_input, _ = self._wait_best_locator(
            self._asset_search_input_candidates(),
            timeout_sec=8,
            prefer_enabled=False,
        )
        if search_input is None:
            # 클릭 후 포커스가 검색칸으로 이미 이동했을 수 있어 키보드 직접 입력 1회 폴백
            try:
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Backspace")
                self.page.keyboard.insert_text(asset_tag)
                self.page.keyboard.press("Enter")
                self.log(f"✅ Step2 에셋 검색 입력 완료(포커스 폴백): {asset_tag}")
                self.actor.random_action_delay("에셋 검색 Enter 후 대기", 0.3, 1.0)
                return
            except Exception:
                ok_dom, reason_dom = self._direct_fill_asset_search_via_dom(asset_tag)
                if ok_dom:
                    self.page.keyboard.press("Enter")
                    self.log(f"✅ Step2 에셋 검색 입력 완료(DOM 폴백): {asset_tag}")
                    self.actor.random_action_delay("에셋 검색 Enter 후 대기", 0.3, 1.0)
                    return
                raise RuntimeError(f"Step2 실패: 에셋 검색 입력창을 찾지 못했습니다. (dom={reason_dom})")

        try:
            search_input.click(timeout=1500)
        except Exception:
            pass
        try:
            self.page.keyboard.press("Control+A")
            self.page.keyboard.press("Backspace")
        except Exception:
            pass
        try:
            search_input.fill(asset_tag)
        except Exception:
            try:
                search_input.type(asset_tag, delay=random.randint(25, 70))
            except Exception:
                raise RuntimeError("에셋 검색 입력에 실패했습니다.")

        self.actor.random_action_delay("에셋 검색어 입력 후 대기", 0.1, 0.5)
        self.page.keyboard.press("Enter")
        self.log(f"✅ Step2 에셋 검색 입력 완료: {asset_tag}")
        self.actor.random_action_delay("에셋 검색 Enter 후 대기", 0.2, 1.0)

    def _apply_download_used_selectors(self, mode, used):
        if not isinstance(used, dict):
            return
        mapping = {
            "search_input": ("download_search_input_selector", None),
            "filter": ("download_image_filter_selector" if mode == "image" else "download_video_filter_selector", None),
            "card": ("download_image_card_selector" if mode == "image" else "download_video_card_selector", None),
            "more": ("download_image_more_selector" if mode == "image" else "download_video_more_selector", None),
            "menu": ("download_image_menu_selector" if mode == "image" else "download_video_menu_selector", None),
            "quality": ("download_image_quality_selector" if mode == "image" else "download_video_quality_selector", None),
        }
        var_mapping = {
            "download_search_input_selector": "download_search_input_selector_var",
            "download_image_filter_selector": "download_image_filter_selector_var",
            "download_video_filter_selector": "download_video_filter_selector_var",
            "download_image_card_selector": "download_image_card_selector_var",
            "download_video_card_selector": "download_video_card_selector_var",
            "download_image_more_selector": "download_image_more_selector_var",
            "download_video_more_selector": "download_video_more_selector_var",
            "download_image_menu_selector": "download_image_menu_selector_var",
            "download_video_menu_selector": "download_video_menu_selector_var",
            "download_image_quality_selector": "download_image_quality_selector_var",
            "download_video_quality_selector": "download_video_quality_selector_var",
        }
        for k, raw in used.items():
            cfg_key = mapping.get(k, (None, None))[0]
            val = str(raw or "").strip()
            if not cfg_key or not val:
                continue
            self.cfg[cfg_key] = val
            var_name = var_mapping.get(cfg_key)
            if var_name and hasattr(self, var_name):
                try:
                    getattr(self, var_name).set(val)
                except Exception:
                    pass

    def _click_download_filter(self, mode, used):
        filter_loc, filter_sel = self._resolve_best_locator(
            self._download_filter_candidates(mode),
            timeout_ms=1800,
            prefer_enabled=False,
        )
        if filter_loc is None:
            # 필터 버튼을 못 찾아도 현재 화면이 이미 해당 필터일 수 있어 실패로 보지 않는다.
            return False
        used["filter"] = filter_sel or ""
        self._click_with_actor_fallback(filter_loc, f"{'이미지' if mode == 'image' else '영상'} 필터")
        self.actor.random_action_delay("필터 적용 대기", 0.2, 0.9)
        return True

    def _resolve_more_button_from_card(self, card_loc, mode):
        # 카드 내부에서 우상단 작은 버튼(더보기)을 우선 추정한다.
        if card_loc is None:
            return None, None
        try:
            card_box = card_loc.bounding_box()
        except Exception:
            card_box = None
        if not card_box:
            return None, None

        try:
            inner = card_loc.locator("button, [role='button']")
            total = min(inner.count(), 30)
        except Exception:
            total = 0
            inner = None

        best = None
        best_score = float("inf")
        for i in range(total):
            cand = inner.nth(i)
            try:
                if not cand.is_visible(timeout=800):
                    continue
                box = cand.bounding_box()
            except Exception:
                continue
            if not box:
                continue
            if box["width"] < 12 or box["height"] < 12:
                continue
            cx = box["x"] + box["width"] / 2.0
            cy = box["y"] + box["height"] / 2.0
            right_top_x = card_box["x"] + card_box["width"] - 28.0
            right_top_y = card_box["y"] + 20.0
            score = abs(cx - right_top_x) + abs(cy - right_top_y)
            try:
                meta = cand.evaluate("""(el)=>((el.getAttribute('aria-label')||'')+' '+(el.innerText||'')).toLowerCase()""")
            except Exception:
                meta = ""
            if any(x in meta for x in ("더보기", "more", "menu", "...", "⋮")):
                score -= 250.0
            if score < best_score:
                best_score = score
                best = cand
        if best is not None:
            key = "download_image_more_selector" if mode == "image" else "download_video_more_selector"
            return best, self.cfg.get(key, "")
        return None, None

    def _run_single_download_flow(self, mode, tag, quality, dry_run=False, wait_sec=60):
        if not self.page:
            raise RuntimeError("브라우저 페이지가 없습니다.")
        mode = "image" if mode == "image" else "video"
        quality = self._download_quality(mode) if not quality else str(quality).strip().upper()
        wait_sec = max(10, min(120, int(wait_sec)))
        used = {"search_input": "", "filter": "", "card": "", "more": "", "menu": "", "quality": ""}

        self._click_download_filter(mode, used)

        search_loc, search_sel = self._resolve_download_search_input(timeout_sec=8)
        if search_loc is None:
            raise RuntimeError("검색 입력칸을 찾지 못했습니다.")
        used["search_input"] = search_sel or ""
        try:
            search_loc.click(timeout=1500)
        except Exception:
            pass
        try:
            self.page.keyboard.press("Control+A")
            self.page.keyboard.press("Backspace")
        except Exception:
            pass
        try:
            search_loc.fill(tag)
        except Exception:
            try:
                search_loc.type(tag, delay=random.randint(20, 60))
            except Exception as e:
                raise RuntimeError(f"검색어 입력 실패: {e}")
        self.page.keyboard.press("Enter")
        self.actor.random_action_delay("검색 결과 반영 대기", 0.4, 1.2)

        deadline = time.time() + wait_sec
        card_loc = None
        card_sel = None
        more_loc = None
        more_sel = None
        while time.time() < deadline:
            card_loc, card_sel = self._resolve_best_locator(
                self._download_card_candidates(mode),
                timeout_ms=1100,
                prefer_enabled=False,
            )
            if card_loc is not None:
                used["card"] = card_sel or ""
                try:
                    self.actor.move_to_locator(card_loc, label=f"결과 카드({tag})")
                except Exception:
                    try:
                        card_loc.hover(timeout=1000)
                    except Exception:
                        pass
                more_loc, more_sel = self._resolve_best_locator(
                    self._download_more_candidates(mode),
                    near_locator=card_loc,
                    timeout_ms=1000,
                    prefer_enabled=False,
                )
                if more_loc is None:
                    more_loc, more_sel = self._resolve_more_button_from_card(card_loc, mode)
                if more_loc is None:
                    try:
                        box = card_loc.bounding_box()
                    except Exception:
                        box = None
                    more_loc, more_sel = self._resolve_more_button_near_box(box)
            if more_loc is None:
                tile_box = self._find_first_media_tile_box()
                if tile_box:
                    try:
                        self.page.mouse.move(
                            float(tile_box["x"]) + float(tile_box["width"]) * 0.5,
                            float(tile_box["y"]) + float(tile_box["height"]) * 0.45,
                            steps=8,
                        )
                    except Exception:
                        pass
                    more_loc, more_sel = self._resolve_more_button_near_box(tile_box)
            if more_loc is not None:
                used["more"] = more_sel or ""
                break
            time.sleep(0.5)

        if more_loc is None:
            raise RuntimeError(f"더보기 버튼을 찾지 못했습니다. (대기 {wait_sec}초)")

        if not self._click_with_actor_fallback(more_loc, "더보기 버튼"):
            raise RuntimeError("더보기 버튼 클릭 실패")

        menu_loc, menu_sel = self._wait_best_locator(
            self._download_menu_candidates(mode),
            timeout_sec=7,
            prefer_enabled=False,
        )
        if menu_loc is None:
            menu_loc, menu_sel = self._resolve_text_locator_any_frame(["다운로드", "Download"], timeout_ms=1000)
        if menu_loc is None:
            raise RuntimeError("다운로드 메뉴를 찾지 못했습니다.")
        used["menu"] = menu_sel or ""

        try:
            self.actor.move_to_locator(menu_loc, label="다운로드 메뉴")
        except Exception:
            try:
                menu_loc.hover(timeout=1200)
            except Exception:
                pass
        self.actor.random_action_delay("품질 목록 표시 대기", 0.15, 0.6)

        quality_loc, quality_sel = self._wait_best_locator(
            self._download_quality_candidates(mode, quality),
            timeout_sec=7,
            prefer_enabled=False,
        )
        if quality_loc is None:
            quality_loc, quality_sel = self._resolve_text_locator_any_frame([quality], timeout_ms=1000)
        if quality_loc is None:
            raise RuntimeError(f"{quality} 품질 항목을 찾지 못했습니다.")
        used["quality"] = quality_sel or ""

        if dry_run:
            return {"used": used, "file": None}

        try:
            with self.page.expect_download(timeout=15000) as dl_info:
                if not self._click_with_actor_fallback(quality_loc, f"{quality} 품질"):
                    quality_loc.click(timeout=2500)
            dl = dl_info.value
            file_name = dl.suggested_filename or ""
        except Exception as e:
            raise RuntimeError(f"다운로드 시작 실패: {e}")

        return {"used": used, "file": file_name}

    def _parse_schedule_datetime(self, raw_text):
        txt = (raw_text or "").strip()
        if not txt:
            return None
        fmts = (
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
        )
        for fmt in fmts:
            try:
                return datetime.strptime(txt, fmt)
            except ValueError:
                continue
        return None

    def _show_completion_popup(self):
        def _done_ui():
            self.on_stop()
            self.play_sound("finish")
            self.update_status_label("🎉 전체 완료!", self.color_success)
            messagebox.showinfo("작업 완료", "모든 작업이 완료되어 자동으로 중지되었습니다.")
        self.root.after(0, _done_ui)

    def update_status_label(self, text, color):
        if color == "white": color = self.color_text
        self.lbl_main_status.config(text=text, fg=color)
        if hasattr(self, "lbl_hud_state"):
            self.lbl_hud_state.config(text=f"상태: {text}", fg=color)

    def _create_collapsible_section(self, parent, title, opened=False):
        wrap = tk.Frame(parent, bg=self.color_bg, highlightbackground="#E9ECEF", highlightthickness=1)
        wrap.pack(fill="x", pady=(6, 6))

        head = tk.Frame(wrap, bg=self.color_bg)
        head.pack(fill="x")

        state = {"open": bool(opened)}
        body = tk.Frame(wrap, bg=self.color_bg)

        btn = tk.Button(
            head,
            text="",
            anchor="w",
            relief="flat",
            borderwidth=0,
            bg=self.color_bg,
            activebackground=self.color_bg,
            fg=self.color_text,
            font=("Malgun Gothic", 10, "bold"),
            cursor="hand2",
            padx=8,
            pady=6,
        )
        btn.pack(fill="x")

        def _refresh():
            arrow = "▾" if state["open"] else "▸"
            btn.config(text=f"{arrow} {title}")
            if state["open"]:
                body.pack(fill="x", padx=8, pady=(2, 8))
            else:
                body.pack_forget()

        def _set_open(flag):
            state["open"] = bool(flag)
            _refresh()

        btn.config(command=lambda: _set_open(not state["open"]))
        _refresh()
        return body, _set_open

    def _set_mini_hud_collapsed(self, collapsed):
        if not hasattr(self, "mini_hud_body"):
            return
        self.mini_hud_collapsed = bool(collapsed)
        if self.mini_hud_collapsed:
            self.mini_hud_body.pack_forget()
            if hasattr(self, "btn_toggle_hud"):
                self.btn_toggle_hud.config(text="펼치기")
        else:
            self.mini_hud_body.pack(fill="x", pady=(4, 0))
            if hasattr(self, "btn_toggle_hud"):
                self.btn_toggle_hud.config(text="접기")

    def _toggle_mini_hud(self):
        self._set_mini_hud_collapsed(not getattr(self, "mini_hud_collapsed", False))

    def _build_ui(self):
        # 1. Header (High Visibility)
        header = tk.Frame(self.root, bg="#F8F9FA", height=72, highlightbackground="#DEE2E6", highlightthickness=1)
        header.pack(fill="x", side="top")
        
        title_f = tk.Frame(header, bg="#F8F9FA")
        title_f.pack(side="left", padx=20, pady=10)
        tk.Label(title_f, text="Flow Veo 자동화 봇", font=("Malgun Gothic", 20, "bold"), bg="#F8F9FA", fg="#343A40").pack(anchor="w")
        tk.Label(title_f, text="Ultimate V2 High-Vis Edition", font=("Malgun Gothic", 10), bg="#F8F9FA", fg="#868E96").pack(anchor="w")

        center_f = tk.Frame(header, bg="#F8F9FA")
        center_f.pack(side="left", fill="both", expand=True, padx=10)
        tk.Label(center_f, text="진행 상황", font=("Malgun Gothic", 10), bg="#F8F9FA", fg="#868E96").pack(anchor="center", pady=(10, 0))
        self.lbl_header_progress = tk.Label(center_f, text="0 / 0 (0.0%)", font=("Consolas", 13, "bold"), bg="#F8F9FA", fg=self.color_accent)
        self.lbl_header_progress.pack(anchor="center")

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
        
        # Playwright Target Settings
        tk.Label(left_card, text="1. 브라우저 대상 설정 (필수)", font=("Malgun Gothic", 11, "bold"), fg=self.color_text).pack(anchor="w", pady=(0, 5))

        tk.Label(left_card, text="시작 URL", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.start_url_var = tk.StringVar(value=self.cfg.get("start_url", "https://labs.google/flow"))
        self.entry_start_url = tk.Entry(left_card, textvariable=self.start_url_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_start_url.pack(fill="x", ipady=4, pady=(2, 8))
        self.entry_start_url.bind("<FocusOut>", self.on_option_toggle)

        tk.Label(left_card, text="입력창 CSS Selector", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.input_selector_var = tk.StringVar(value=self.cfg.get("input_selector", "textarea, [contenteditable='true']"))
        self.entry_input_selector = tk.Entry(left_card, textvariable=self.input_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_input_selector.pack(fill="x", ipady=4, pady=(2, 8))
        self.entry_input_selector.bind("<FocusOut>", self.on_option_toggle)

        tk.Label(left_card, text="제출 버튼 CSS Selector", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.submit_selector_var = tk.StringVar(value=self.cfg.get("submit_selector", "button[type='submit']"))
        self.entry_submit_selector = tk.Entry(left_card, textvariable=self.submit_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_submit_selector.pack(fill="x", ipady=4, pady=(2, 8))
        self.entry_submit_selector.bind("<FocusOut>", self.on_option_toggle)

        selector_tool_f = tk.Frame(left_card, bg=self.color_bg)
        selector_tool_f.pack(fill="x", pady=(0, 8))
        ttk.Button(selector_tool_f, text="🔍 Selector 자동 찾기", command=self.on_auto_detect_selectors).pack(side="left")
        ttk.Button(selector_tool_f, text="🧪 Selector 테스트", command=self.on_test_selectors).pack(side="left", padx=6)

        browser_f = tk.Frame(left_card, bg=self.color_bg)
        browser_f.pack(fill="x", pady=(0, 10))
        self.browser_headless_var = tk.BooleanVar(value=self.cfg.get("browser_headless", False))
        tk.Checkbutton(
            browser_f,
            text="헤드리스(화면 숨김)",
            variable=self.browser_headless_var,
            command=self.on_option_toggle,
            bg=self.color_bg,
            font=("Malgun Gothic", 9),
            activebackground=self.color_bg,
        ).pack(side="left")

        tk.Label(browser_f, text="채널:", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left", padx=(10, 4))
        self.browser_channel_var = tk.StringVar(value=self.cfg.get("browser_channel", "chrome"))
        self.combo_browser_channel = ttk.Combobox(
            browser_f,
            textvariable=self.browser_channel_var,
            state="readonly",
            width=10,
            font=("Malgun Gothic", 9),
            values=("chrome", "msedge", "chromium"),
        )
        self.combo_browser_channel.pack(side="left")
        self.combo_browser_channel.bind("<<ComboboxSelected>>", self.on_option_toggle)

        new_project_f = tk.Frame(left_card, bg=self.color_bg)
        new_project_f.pack(fill="x", pady=(0, 8))
        self.auto_new_project_var = tk.BooleanVar(value=self.cfg.get("auto_open_new_project", True))
        tk.Checkbutton(
            new_project_f,
            text="홈 화면이면 '새 프로젝트' 자동 클릭",
            variable=self.auto_new_project_var,
            command=self.on_option_toggle,
            bg=self.color_bg,
            font=("Malgun Gothic", 9),
            activebackground=self.color_bg,
        ).pack(side="left")

        tk.Label(left_card, text="새 프로젝트 버튼 selector(선택)", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.new_project_selector_var = tk.StringVar(value=self.cfg.get("new_project_selector", ""))
        self.entry_new_project_selector = tk.Entry(left_card, textvariable=self.new_project_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_new_project_selector.pack(fill="x", ipady=4, pady=(2, 8))
        self.entry_new_project_selector.bind("<FocusOut>", self.on_option_toggle)

        self.lbl_coords = tk.Label(left_card, text=self._get_coord_text(), font=("Consolas", 9), fg=self.color_accent, bg="#F1F3F5", padx=5, pady=4)
        self.lbl_coords.pack(fill="x", pady=(5, 16))
        
        # Options
        tk.Label(left_card, text="2. 옵션 설정", font=("Malgun Gothic", 11, "bold"), fg=self.color_text).pack(anchor="w", pady=(0, 5))
        
        op_f = tk.Frame(left_card, bg=self.color_bg)
        op_f.pack(fill="x")
        
        c1 = tk.Checkbutton(op_f, text="소리 켜기", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, font=("Malgun Gothic", 10), activebackground=self.color_bg)
        self.sound_var = tk.BooleanVar(value=self.cfg.get("sound_enabled", True))
        c1.config(variable=self.sound_var)
        c1.grid(row=0, column=0, sticky="w", padx=5)
        
        c2 = tk.Checkbutton(op_f, text="대기 중 랜덤 행동", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, fg="#D63384", selectcolor=self.color_bg, activebackground=self.color_bg, font=("Malgun Gothic", 10, "bold"))
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

        asset_body, _set_asset_open = self._create_collapsible_section(left_card, "S1~S# 에셋 자동 반복", opened=False)
        asset_f = tk.Frame(asset_body, bg=self.color_bg)
        asset_f.pack(fill="x", pady=6)
        self.asset_loop_var = tk.BooleanVar(value=self.cfg.get("asset_loop_enabled", False))
        tk.Checkbutton(
            asset_f,
            text="S번호 자동 반복 사용",
            variable=self.asset_loop_var,
            command=self.on_option_toggle,
            bg=self.color_bg,
            font=("Malgun Gothic", 10),
            activebackground=self.color_bg,
        ).pack(anchor="w")
        tk.Label(
            asset_f,
            text="동작: 시작 클릭 -> 에셋 검색에 S번호 입력 -> 프롬프트 입력",
            bg=self.color_bg,
            fg=self.color_text_sec,
            font=("Malgun Gothic", 9),
        ).pack(anchor="w", pady=(2, 6))

        asset_range_f = tk.Frame(asset_f, bg=self.color_bg)
        asset_range_f.pack(fill="x", pady=(0, 6))
        tk.Label(asset_range_f, text="시작 번호", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left")
        self.asset_loop_start_var = tk.StringVar(value=str(self.cfg.get("asset_loop_start", 1)))
        self.spin_asset_start = tk.Spinbox(
            asset_range_f,
            from_=1,
            to=9999,
            width=6,
            textvariable=self.asset_loop_start_var,
            command=self.on_option_toggle,
            bg="#FFFFFF",
            fg="black",
        )
        self.spin_asset_start.pack(side="left", padx=(6, 14))
        self.spin_asset_start.bind("<FocusOut>", self.on_option_toggle)
        self.spin_asset_start.bind("<Return>", self.on_option_toggle)

        tk.Label(asset_range_f, text="끝 번호", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left")
        self.asset_loop_end_var = tk.StringVar(value=str(self.cfg.get("asset_loop_end", 1)))
        self.spin_asset_end = tk.Spinbox(
            asset_range_f,
            from_=1,
            to=9999,
            width=6,
            textvariable=self.asset_loop_end_var,
            command=self.on_option_toggle,
            bg="#FFFFFF",
            fg="black",
        )
        self.spin_asset_end.pack(side="left", padx=(6, 0))
        self.spin_asset_end.bind("<FocusOut>", self.on_option_toggle)
        self.spin_asset_end.bind("<Return>", self.on_option_toggle)

        asset_prefix_f = tk.Frame(asset_f, bg=self.color_bg)
        asset_prefix_f.pack(fill="x", pady=(0, 6))
        tk.Label(asset_prefix_f, text="접두어", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left")
        self.asset_loop_prefix_var = tk.StringVar(value=self.cfg.get("asset_loop_prefix", "S"))
        self.entry_asset_prefix = tk.Entry(asset_prefix_f, textvariable=self.asset_loop_prefix_var, bg="#FFFFFF", fg="black", font=("Consolas", 10), width=8)
        self.entry_asset_prefix.pack(side="left", padx=(6, 0))
        self.entry_asset_prefix.bind("<FocusOut>", self.on_option_toggle)

        tk.Label(asset_f, text="프롬프트 템플릿 ({tag}=S1/S2... 로 치환)", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.asset_loop_template_var = tk.StringVar(
            value=self.cfg.get("asset_loop_prompt_template", "{tag} : Naturally Seamless Loop animation.")
        )
        self.entry_asset_template = tk.Entry(
            asset_f,
            textvariable=self.asset_loop_template_var,
            bg="#FFFFFF",
            fg="black",
            font=("Consolas", 10),
        )
        self.entry_asset_template.pack(fill="x", ipady=3, pady=(2, 0))
        self.entry_asset_template.bind("<FocusOut>", self.on_option_toggle)

        tk.Label(asset_f, text="시작 버튼 selector(선택)", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w", pady=(8, 0))
        self.asset_start_selector_var = tk.StringVar(value=self.cfg.get("asset_start_selector", ""))
        self.entry_asset_start_selector = tk.Entry(asset_f, textvariable=self.asset_start_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_asset_start_selector.pack(fill="x", ipady=3, pady=(2, 4))
        self.entry_asset_start_selector.bind("<FocusOut>", self.on_option_toggle)

        tk.Label(asset_f, text="에셋 검색 버튼 selector(선택)", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.asset_search_btn_selector_var = tk.StringVar(value=self.cfg.get("asset_search_button_selector", ""))
        self.entry_asset_search_btn_selector = tk.Entry(asset_f, textvariable=self.asset_search_btn_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_asset_search_btn_selector.pack(fill="x", ipady=3, pady=(2, 4))
        self.entry_asset_search_btn_selector.bind("<FocusOut>", self.on_option_toggle)

        tk.Label(asset_f, text="에셋 검색 입력칸 selector(선택)", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.asset_search_input_selector_var = tk.StringVar(value=self.cfg.get("asset_search_input_selector", ""))
        self.entry_asset_search_input_selector = tk.Entry(asset_f, textvariable=self.asset_search_input_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_asset_search_input_selector.pack(fill="x", ipady=3, pady=(2, 6))
        self.entry_asset_search_input_selector.bind("<FocusOut>", self.on_option_toggle)

        asset_btn_f = tk.Frame(asset_f, bg=self.color_bg)
        asset_btn_f.pack(fill="x", pady=(2, 0))
        ttk.Button(asset_btn_f, text="🔍 에셋 selector 자동찾기", command=self.on_auto_detect_asset_selectors).pack(side="left")
        ttk.Button(asset_btn_f, text="🧪 에셋 selector 테스트", command=self.on_test_asset_selectors).pack(side="left", padx=6)

        dl_body, _set_dl_open = self._create_collapsible_section(left_card, "다운로드 자동화", opened=False)
        dl_f = tk.Frame(dl_body, bg=self.color_bg)
        dl_f.pack(fill="x", pady=6)

        mode_f = tk.Frame(dl_f, bg=self.color_bg)
        mode_f.pack(fill="x", pady=(0, 6))
        tk.Label(mode_f, text="모드", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left")
        self.download_mode_var = tk.StringVar(value=self.cfg.get("download_mode", "video"))
        self.combo_download_mode = ttk.Combobox(
            mode_f,
            textvariable=self.download_mode_var,
            state="readonly",
            width=10,
            values=("video", "image"),
            font=("Malgun Gothic", 9),
        )
        self.combo_download_mode.pack(side="left", padx=(6, 0))
        self.combo_download_mode.bind("<<ComboboxSelected>>", self.on_option_toggle)

        q_f = tk.Frame(dl_f, bg=self.color_bg)
        q_f.pack(fill="x", pady=(0, 6))
        tk.Label(q_f, text="영상 품질", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left")
        self.download_video_quality_var = tk.StringVar(value=self.cfg.get("download_video_quality", "1080P"))
        self.combo_download_video_quality = ttk.Combobox(
            q_f,
            textvariable=self.download_video_quality_var,
            state="readonly",
            width=8,
            values=("1080P", "720P", "4K"),
            font=("Malgun Gothic", 9),
        )
        self.combo_download_video_quality.pack(side="left", padx=(6, 12))
        self.combo_download_video_quality.bind("<<ComboboxSelected>>", self.on_option_toggle)

        tk.Label(q_f, text="이미지 품질", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left")
        self.download_image_quality_var = tk.StringVar(value=self.cfg.get("download_image_quality", "4K"))
        self.combo_download_image_quality = ttk.Combobox(
            q_f,
            textvariable=self.download_image_quality_var,
            state="readonly",
            width=6,
            values=("4K", "2K", "1K"),
            font=("Malgun Gothic", 9),
        )
        self.combo_download_image_quality.pack(side="left", padx=(6, 0))
        self.combo_download_image_quality.bind("<<ComboboxSelected>>", self.on_option_toggle)

        tk.Label(dl_f, text="검색 입력 selector(공통)", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.download_search_input_selector_var = tk.StringVar(value=self.cfg.get("download_search_input_selector", ""))
        self.entry_download_search = tk.Entry(dl_f, textvariable=self.download_search_input_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_download_search.pack(fill="x", ipady=3, pady=(2, 4))
        self.entry_download_search.bind("<FocusOut>", self.on_option_toggle)

        tk.Label(dl_f, text="영상 필터 selector", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.download_video_filter_selector_var = tk.StringVar(value=self.cfg.get("download_video_filter_selector", ""))
        self.entry_download_video_filter = tk.Entry(dl_f, textvariable=self.download_video_filter_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_download_video_filter.pack(fill="x", ipady=3, pady=(2, 4))
        self.entry_download_video_filter.bind("<FocusOut>", self.on_option_toggle)

        tk.Label(dl_f, text="이미지 필터 selector", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(anchor="w")
        self.download_image_filter_selector_var = tk.StringVar(value=self.cfg.get("download_image_filter_selector", ""))
        self.entry_download_image_filter = tk.Entry(dl_f, textvariable=self.download_image_filter_selector_var, bg="#FFFFFF", fg="black", font=("Consolas", 10))
        self.entry_download_image_filter.pack(fill="x", ipady=3, pady=(2, 4))
        self.entry_download_image_filter.bind("<FocusOut>", self.on_option_toggle)

        d1 = tk.Frame(dl_f, bg=self.color_bg)
        d1.pack(fill="x", pady=(2, 0))
        ttk.Button(d1, text="🔍 이미지 다운로드 자동찾기", command=self.on_auto_detect_image_download_selectors).pack(side="left")
        ttk.Button(d1, text="🧪 이미지 다운로드 테스트", command=self.on_test_image_download_selectors).pack(side="left", padx=6)

        d2 = tk.Frame(dl_f, bg=self.color_bg)
        d2.pack(fill="x", pady=(6, 0))
        ttk.Button(d2, text="🔍 영상 다운로드 자동찾기", command=self.on_auto_detect_video_download_selectors).pack(side="left")
        ttk.Button(d2, text="🧪 영상 다운로드 테스트", command=self.on_test_video_download_selectors).pack(side="left", padx=6)

        # Relay (Accordion: 기본 접힘)
        relay_body, _set_relay_open = self._create_collapsible_section(left_card, "이어달리기 / 문서 선택", opened=False)
        relay_f = tk.Frame(relay_body, bg=self.color_bg)
        relay_f.pack(fill="x", pady=6)
        c3 = tk.Checkbutton(relay_f, text="이어달리기 (파일 순차 실행)", variable=tk.BooleanVar(), command=self.on_option_toggle, bg=self.color_bg, font=("Malgun Gothic", 10), activebackground=self.color_bg)
        self.relay_var = tk.BooleanVar(value=self.cfg.get("relay_mode", False))
        c3.config(variable=self.relay_var)
        c3.pack(side="left")

        tk.Label(relay_f, text="횟수:", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left", padx=(8, 2))
        self.relay_cnt_var = tk.IntVar(value=self.cfg.get("relay_count", 1))
        sp = tk.Spinbox(relay_f, from_=1, to=10, width=3, textvariable=self.relay_cnt_var, command=self.on_option_toggle, bg="#FFFFFF", fg="black")
        sp.pack(side="left", padx=5)

        relay_range_f = tk.Frame(relay_body, bg=self.color_bg)
        relay_range_f.pack(fill="x", pady=(0, 10))
        tk.Label(relay_range_f, text="이어달리기 범위:", bg=self.color_bg, font=("Malgun Gothic", 9, "bold")).pack(side="left")
        tk.Label(relay_range_f, text="시작", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left", padx=(8, 2))
        self.combo_relay_start = ttk.Combobox(relay_range_f, state="readonly", width=8, font=("Malgun Gothic", 9))
        self.combo_relay_start.pack(side="left")
        self.combo_relay_start.bind("<<ComboboxSelected>>", self.on_option_toggle)
        tk.Label(relay_range_f, text="끝", bg=self.color_bg, font=("Malgun Gothic", 9)).pack(side="left", padx=(6, 2))
        self.combo_relay_end = ttk.Combobox(relay_range_f, state="readonly", width=8, font=("Malgun Gothic", 9))
        self.combo_relay_end.pack(side="left")
        self.combo_relay_end.bind("<<ComboboxSelected>>", self.on_option_toggle)
        self._sync_relay_range_controls()

        relay_pick_f = tk.Frame(relay_body, bg=self.color_bg)
        relay_pick_f.pack(fill="x", pady=(0, 8))
        self.relay_pick_var = tk.BooleanVar(value=self.cfg.get("relay_use_selection", False))
        tk.Checkbutton(
            relay_pick_f,
            text="문서 체크 선택 사용",
            variable=self.relay_pick_var,
            command=self.on_option_toggle,
            bg=self.color_bg,
            font=("Malgun Gothic", 9),
            activebackground=self.color_bg
        ).pack(side="left")
        ttk.Button(relay_pick_f, text="문서 선택...", command=self.on_open_relay_selector).pack(side="left", padx=6)

        self.lbl_relay_pick = tk.Label(relay_body, text="", font=("Malgun Gothic", 9), fg=self.color_text_sec, bg=self.color_bg)
        self.lbl_relay_pick.pack(anchor="w", pady=(0, 8))
        self._sync_relay_selection_label()

        tk.Label(left_card, text="3. 작업 간격 (초)", font=("Malgun Gothic", 11, "bold"), fg=self.color_text).pack(anchor="w", pady=(20, 5))
        self.entry_interval = tk.Entry(left_card, bg="#FFFFFF", fg="black", font=("Consolas", 16, "bold"), justify="center", relief="solid", borderwidth=1)
        self.entry_interval.insert(0, str(self.cfg.get("interval_seconds", 180)))
        self.entry_interval.pack(fill="x", ipady=5)
        tk.Label(left_card, text="※ 설정한 시간마다 봇이 작동합니다.", font=("Malgun Gothic", 9), fg=self.color_text_sec).pack(anchor="w")

        # 예약 (Accordion: 기본 접힘)
        sched_body, _set_sched_open = self._create_collapsible_section(left_card, "예약 시작 설정(고급)", opened=False)
        sched_card = tk.Frame(sched_body, bg=self.color_bg)
        sched_card.pack(fill="x", pady=(14, 2))
        tk.Label(sched_card, text="4. 1회 예약 시작 (특정 날짜/시간)", font=("Malgun Gothic", 11, "bold"), fg=self.color_text).pack(anchor="w")
        self.schedule_var = tk.BooleanVar(value=self.cfg.get("scheduled_start_enabled", False))
        tk.Checkbutton(
            sched_card,
            text="예약 시작 사용",
            variable=self.schedule_var,
            command=self.on_option_toggle,
            bg=self.color_bg,
            font=("Malgun Gothic", 10),
            activebackground=self.color_bg
        ).pack(anchor="w", pady=(4, 2))
        self.schedule_text_var = tk.StringVar(value=self.cfg.get("scheduled_start_at", ""))
        self.entry_schedule_display = tk.Entry(
            sched_card,
            bg="#FFFFFF",
            fg="black",
            font=("Consolas", 11),
            justify="center",
            relief="solid",
            borderwidth=1,
            textvariable=self.schedule_text_var,
            state="readonly"
        )
        self.entry_schedule_display.pack(fill="x", ipady=4)
        tk.Label(
            sched_card,
            text="타이핑 없이 달력 버튼으로 선택하세요 👇",
            font=("Malgun Gothic", 9),
            fg=self.color_text_sec,
            bg=self.color_bg
        ).pack(anchor="w", pady=(2, 0))
        quick_f = tk.Frame(sched_card, bg=self.color_bg)
        quick_f.pack(fill="x", pady=(6, 0))
        ttk.Button(quick_f, text="📅 달력 선택", command=self.on_open_schedule_picker).pack(side="left")
        ttk.Button(quick_f, text="현재+5분", command=lambda: self.on_fill_schedule_time(5)).pack(side="left")
        ttk.Button(quick_f, text="현재+30분", command=lambda: self.on_fill_schedule_time(30)).pack(side="left", padx=6)
        ttk.Button(quick_f, text="예약 지우기", command=self.on_clear_schedule_time).pack(side="left")

        tk.Frame(left_card, height=12, bg=self.color_bg).pack()

        # --- Right: Dashboard (HUD Design) ---
        right_panel = tk.Frame(self.body_pane, bg=self.color_bg)

        self.body_pane.add(self.left_container, weight=7)
        self.body_pane.add(right_panel, weight=3)
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
        
        # 2. Mini HUD (핵심 정보만 표시)
        mon_card = ttk.LabelFrame(right_panel, text=" ⚡ Mini HUD ", padding=10)
        mon_card.pack(fill="x", pady=(0, 10))

        top_line = tk.Frame(mon_card, bg=self.color_bg)
        top_line.pack(fill="x")
        self.lbl_hud_state = tk.Label(top_line, text="상태: 준비 완료", font=("Malgun Gothic", 10, "bold"), fg=self.color_success, bg=self.color_bg)
        self.lbl_hud_state.pack(side="left")
        self.btn_toggle_hud = ttk.Button(top_line, text="펼치기", width=8, command=self._toggle_mini_hud)
        self.btn_toggle_hud.pack(side="right")
        self.lbl_hud_mode = tk.Label(
            top_line,
            text=f"입력: {self.cfg.get('input_mode', 'typing')}",
            font=("Consolas", 10, "bold"),
            fg=self.color_info,
            bg=self.color_bg,
        )
        self.lbl_hud_mode.pack(side="right", padx=(0, 8))

        self.mini_hud_body = tk.Frame(mon_card, bg=self.color_bg)
        self.lbl_hud_progress = tk.Label(
            self.mini_hud_body,
            text="진행: 0 / 0 | 배치: 0 / 0",
            font=("Consolas", 10, "bold"),
            fg=self.color_accent,
            bg=self.color_bg,
        )
        self.lbl_hud_progress.pack(anchor="w", pady=(6, 2))

        self.lbl_hud_persona = tk.Label(
            self.mini_hud_body,
            text="페르소나: INITIALIZING...",
            font=("Malgun Gothic", 10, "bold"),
            fg="#343A40",
            bg=self.color_bg,
        )
        self.lbl_hud_persona.pack(anchor="w")

        self.lbl_hud_meta = tk.Label(
            self.mini_hud_body,
            text="무드: - | 속도: x1.0 | 다음휴식: -",
            font=("Consolas", 10),
            fg=self.color_text_sec,
            bg=self.color_bg,
        )
        self.lbl_hud_meta.pack(anchor="w", pady=(2, 0))

        self.lbl_hud_trait = tk.Label(
            self.mini_hud_body,
            text="특징: -",
            font=("Malgun Gothic", 9),
            fg="#495057",
            bg=self.color_bg,
            wraplength=520,
            justify="left",
        )
        self.lbl_hud_trait.pack(anchor="w", pady=(4, 0))
        self._set_mini_hud_collapsed(True)

        ctrl_card = ttk.LabelFrame(right_panel, text=" ▶ 실행 컨트롤 ", padding=10)
        ctrl_card.pack(fill="x", pady=(0, 10))
        self.btn_start_prompt = ttk.Button(
            ctrl_card,
            text="▶ 프롬프트 자동화 시작",
            style="Action.TButton",
            command=self.on_start_prompt,
        )
        self.btn_start_prompt.pack(fill="x", ipady=12)
        self.btn_start_asset = ttk.Button(
            ctrl_card,
            text="▶ S반복 자동화 시작",
            command=self.on_start_asset,
        )
        self.btn_start_asset.pack(fill="x", ipady=10, pady=(8, 0))
        self.btn_start_download = ttk.Button(
            ctrl_card,
            text="▶ 다운로드 자동화 시작",
            command=self.on_start_download,
        )
        self.btn_start_download.pack(fill="x", ipady=10, pady=(8, 0))
        self.btn_pause = ttk.Button(ctrl_card, text="⏸ 일시정지", command=self.on_pause, state="disabled")
        self.btn_pause.pack(fill="x", pady=(8, 0), ipady=6)
        self.btn_resume = ttk.Button(ctrl_card, text="▶ 재개", command=self.on_resume, state="disabled")
        self.btn_resume.pack(fill="x", pady=(6, 0), ipady=6)
        self.btn_stop = ttk.Button(ctrl_card, text="⏹ 완전중지(브라우저 종료)", command=self.on_stop, state="disabled")
        self.btn_stop.pack(fill="x", pady=(6, 0), ipady=6)

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

        btn_sync = ttk.Button(file_top, text="🔄 슬롯 동기화", command=self.on_sync_slots)
        btn_sync.pack(side="left", padx=(6, 2))
        ToolTip(btn_sync, "flow_prompts_slot 숫자 파일을 자동으로 슬롯에 추가")

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

    def on_fill_schedule_time(self, plus_minutes):
        try:
            dt = datetime.now() + timedelta(minutes=int(plus_minutes))
            txt = dt.strftime("%Y-%m-%d %H:%M")
            self.schedule_text_var.set(txt)
            self.schedule_var.set(True)
            self.on_option_toggle()
            self.log(f"⏰ 예약 시간 입력: {txt}")
        except Exception as e:
            messagebox.showerror("오류", f"예약 시간 입력 실패: {e}")

    def on_clear_schedule_time(self):
        self.schedule_text_var.set("")
        self.schedule_var.set(False)
        self.on_option_toggle()
        self.log("🧹 예약 시간이 초기화되었습니다.")

    def on_open_schedule_picker(self):
        base_dt = self._parse_schedule_datetime(self.schedule_text_var.get())
        if base_dt is None:
            base_dt = datetime.now() + timedelta(minutes=5)

        state = {"year": base_dt.year, "month": base_dt.month, "day": base_dt.day}
        hour_var = tk.IntVar(value=base_dt.hour)
        min_var = tk.IntVar(value=base_dt.minute)

        win = tk.Toplevel(self.root)
        win.title("📅 예약 날짜/시간 선택")
        win.configure(bg="#FFFFFF")
        win.transient(self.root)
        win.grab_set()
        win.geometry("360x430")
        win.resizable(False, False)

        top = tk.Frame(win, bg="#FFFFFF")
        top.pack(fill="x", padx=12, pady=(12, 6))

        month_title = tk.Label(top, text="", font=("Malgun Gothic", 12, "bold"), bg="#FFFFFF", fg="#212529")
        month_title.pack(side="left", expand=True)

        cal_frame = tk.Frame(win, bg="#FFFFFF")
        cal_frame.pack(fill="x", padx=12, pady=6)

        week_names = ["월", "화", "수", "목", "금", "토", "일"]

        def _move_month(delta):
            y, m = state["year"], state["month"] + delta
            if m <= 0:
                y -= 1
                m = 12
            elif m >= 13:
                y += 1
                m = 1
            state["year"], state["month"] = y, m
            max_day = calendar.monthrange(y, m)[1]
            state["day"] = min(state["day"], max_day)
            _render_calendar()

        ttk.Button(top, text="◀", width=3, command=lambda: _move_month(-1)).pack(side="left")
        ttk.Button(top, text="▶", width=3, command=lambda: _move_month(1)).pack(side="right")

        def _select_day(day):
            state["day"] = day
            _render_calendar()

        def _render_calendar():
            for w in cal_frame.winfo_children():
                w.destroy()
            month_title.config(text=f"{state['year']}년 {state['month']}월")

            for col, wd in enumerate(week_names):
                fg = "#DC3545" if col == 6 else "#212529"
                tk.Label(
                    cal_frame,
                    text=wd,
                    width=4,
                    bg="#FFFFFF",
                    fg=fg,
                    font=("Malgun Gothic", 10, "bold")
                ).grid(row=0, column=col, padx=1, pady=2)

            month_weeks = calendar.monthcalendar(state["year"], state["month"])
            for row, week in enumerate(month_weeks, start=1):
                for col, day in enumerate(week):
                    if day == 0:
                        tk.Label(cal_frame, text=" ", width=4, bg="#FFFFFF").grid(row=row, column=col, padx=1, pady=1)
                        continue
                    selected = (day == state["day"])
                    bg = "#007AFF" if selected else "#F1F3F5"
                    fg = "white" if selected else ("#DC3545" if col == 6 else "#212529")
                    tk.Button(
                        cal_frame,
                        text=str(day),
                        width=4,
                        bg=bg,
                        fg=fg,
                        relief="flat",
                        activebackground="#0056b3" if selected else "#DEE2E6",
                        command=lambda d=day: _select_day(d)
                    ).grid(row=row, column=col, padx=1, pady=1)

        _render_calendar()

        time_frame = tk.Frame(win, bg="#FFFFFF")
        time_frame.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(time_frame, text="시간", bg="#FFFFFF", font=("Malgun Gothic", 10)).pack(side="left")
        tk.Spinbox(time_frame, from_=0, to=23, wrap=True, width=4, textvariable=hour_var, format="%02.0f").pack(side="left", padx=(6, 10))
        tk.Label(time_frame, text="분", bg="#FFFFFF", font=("Malgun Gothic", 10)).pack(side="left")
        tk.Spinbox(time_frame, from_=0, to=59, wrap=True, width=4, textvariable=min_var, format="%02.0f").pack(side="left", padx=(6, 0))

        btns = tk.Frame(win, bg="#FFFFFF")
        btns.pack(fill="x", padx=12, pady=(14, 12))

        def _pick_now():
            now = datetime.now()
            state["year"], state["month"], state["day"] = now.year, now.month, now.day
            hour_var.set(now.hour)
            min_var.set(now.minute)
            _render_calendar()

        def _confirm():
            try:
                picked = datetime(
                    year=state["year"],
                    month=state["month"],
                    day=state["day"],
                    hour=max(0, min(23, int(hour_var.get()))),
                    minute=max(0, min(59, int(min_var.get())))
                )
            except Exception:
                messagebox.showwarning("입력 오류", "날짜/시간을 다시 선택해주세요.")
                return

            txt = picked.strftime("%Y-%m-%d %H:%M")
            self.schedule_text_var.set(txt)
            self.schedule_var.set(True)
            self.on_option_toggle()
            self.log(f"📅 달력에서 예약 선택: {txt}")
            win.destroy()

        ttk.Button(btns, text="오늘", command=_pick_now).pack(side="left")
        ttk.Button(btns, text="취소", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="선택 완료", command=_confirm).pack(side="right", padx=6)

    def on_sync_slots(self):
        existing_files = {s.get("file") for s in self.cfg.get("prompt_slots", [])}
        discovered = []
        for path in self.base.iterdir():
            if not path.is_file():
                continue
            name = path.name
            m = SLOT_FILE_REGEX.match(name)
            if not m:
                continue
            discovered.append((int(m.group(1)), name))

        if not discovered:
            messagebox.showinfo("동기화", "동기화할 슬롯 파일이 없습니다.")
            self.log("ℹ️ 슬롯 동기화: 신규 파일 없음")
            return

        discovered.sort(key=lambda x: (x[0], x[1]))
        added = []
        for slot_num, file_name in discovered:
            if file_name in existing_files:
                continue
            slot_name = self._make_unique_slot_name(f"자동 슬롯 {slot_num}")
            self.cfg["prompt_slots"].append({"name": slot_name, "file": file_name})
            existing_files.add(file_name)
            added.append((slot_name, file_name))

        if not added:
            messagebox.showinfo("동기화", "이미 모든 슬롯이 등록되어 있습니다.")
            self.log("✅ 슬롯 동기화: 이미 최신 상태")
            return

        self.save_config()
        slots = [s["name"] for s in self.cfg["prompt_slots"]]
        self.combo_slots["values"] = slots
        self.combo_slots.current(self._clamp_slot_index(self.cfg.get("active_prompt_slot", 0)))
        self._sync_relay_range_controls()
        self._sync_relay_selection_label()
        added_preview = ", ".join([f"{n}({f})" for n, f in added[:3]])
        if len(added) > 3:
            added_preview += f" 외 {len(added) - 3}개"
        self.log(f"🔄 슬롯 동기화 완료: {len(added)}개 추가")
        messagebox.showinfo("동기화 완료", f"{len(added)}개 슬롯을 추가했습니다.\n{added_preview}")

    def on_option_toggle(self, event=None):
        self.cfg["afk_mode"] = self.afk_var.get()
        self.cfg["sound_enabled"] = self.sound_var.get()
        self.cfg["relay_mode"] = self.relay_var.get()
        self.cfg["scheduled_start_enabled"] = self.schedule_var.get() if hasattr(self, "schedule_var") else self.cfg.get("scheduled_start_enabled", False)
        self.cfg["scheduled_start_at"] = self.schedule_text_var.get().strip() if hasattr(self, "schedule_text_var") else self.cfg.get("scheduled_start_at", "")
        self.cfg["language_mode"] = "ko_en" if self.lang_var.get() else "en"
        self.cfg["asset_loop_enabled"] = self.asset_loop_var.get() if hasattr(self, "asset_loop_var") else self.cfg.get("asset_loop_enabled", False)
        raw_start = ""
        raw_end = ""
        try:
            if hasattr(self, "spin_asset_start"):
                raw_start = str(self.spin_asset_start.get()).strip()
            elif hasattr(self, "asset_loop_start_var"):
                raw_start = str(self.asset_loop_start_var.get()).strip()
        except Exception:
            raw_start = ""
        try:
            if hasattr(self, "spin_asset_end"):
                raw_end = str(self.spin_asset_end.get()).strip()
            elif hasattr(self, "asset_loop_end_var"):
                raw_end = str(self.asset_loop_end_var.get()).strip()
        except Exception:
            raw_end = ""

        try:
            asset_start = int(raw_start) if raw_start else int(self.cfg.get("asset_loop_start", 1))
        except Exception:
            asset_start = 1
        try:
            asset_end = int(raw_end) if raw_end else int(self.cfg.get("asset_loop_end", 1))
        except Exception:
            asset_end = asset_start
        self.cfg["asset_loop_start"] = max(1, asset_start)
        self.cfg["asset_loop_end"] = max(1, asset_end)

        # 시작/끝 번호를 01처럼 입력하면 자리수를 보존해 S01, S02... 형태로 생성
        requested_width = 0
        for raw in (raw_start, raw_end):
            if raw and raw.isdigit() and len(raw) > 1 and raw.startswith("0"):
                requested_width = max(requested_width, len(raw))
        try:
            prev_width = int(self.cfg.get("asset_loop_num_width", 0))
        except Exception:
            prev_width = 0
        if requested_width > 0:
            self.cfg["asset_loop_num_width"] = requested_width
        else:
            self.cfg["asset_loop_num_width"] = max(0, prev_width)

        asset_prefix = self.asset_loop_prefix_var.get().strip() if hasattr(self, "asset_loop_prefix_var") else str(self.cfg.get("asset_loop_prefix", "S"))
        self.cfg["asset_loop_prefix"] = asset_prefix or "S"
        asset_template = self.asset_loop_template_var.get().strip() if hasattr(self, "asset_loop_template_var") else str(self.cfg.get("asset_loop_prompt_template", ""))
        self.cfg["asset_loop_prompt_template"] = asset_template or "{tag} : Naturally Seamless Loop animation."
        self.cfg["asset_start_selector"] = self.asset_start_selector_var.get().strip() if hasattr(self, "asset_start_selector_var") else self.cfg.get("asset_start_selector", "")
        self.cfg["asset_search_button_selector"] = self.asset_search_btn_selector_var.get().strip() if hasattr(self, "asset_search_btn_selector_var") else self.cfg.get("asset_search_button_selector", "")
        self.cfg["asset_search_input_selector"] = self.asset_search_input_selector_var.get().strip() if hasattr(self, "asset_search_input_selector_var") else self.cfg.get("asset_search_input_selector", "")
        self.cfg["download_mode"] = self.download_mode_var.get().strip().lower() if hasattr(self, "download_mode_var") else self.cfg.get("download_mode", "video")
        if self.cfg["download_mode"] not in ("video", "image"):
            self.cfg["download_mode"] = "video"
        self.cfg["download_video_quality"] = self.download_video_quality_var.get().strip().upper() if hasattr(self, "download_video_quality_var") else str(self.cfg.get("download_video_quality", "1080P"))
        if self.cfg["download_video_quality"] not in ("720P", "1080P", "4K"):
            self.cfg["download_video_quality"] = "1080P"
        self.cfg["download_image_quality"] = self.download_image_quality_var.get().strip().upper() if hasattr(self, "download_image_quality_var") else str(self.cfg.get("download_image_quality", "4K"))
        if self.cfg["download_image_quality"] not in ("1K", "2K", "4K"):
            self.cfg["download_image_quality"] = "4K"
        self.cfg["download_search_input_selector"] = self.download_search_input_selector_var.get().strip() if hasattr(self, "download_search_input_selector_var") else self.cfg.get("download_search_input_selector", "")
        self.cfg["download_video_filter_selector"] = self.download_video_filter_selector_var.get().strip() if hasattr(self, "download_video_filter_selector_var") else self.cfg.get("download_video_filter_selector", "")
        self.cfg["download_image_filter_selector"] = self.download_image_filter_selector_var.get().strip() if hasattr(self, "download_image_filter_selector_var") else self.cfg.get("download_image_filter_selector", "")
        # 실행 중에는 시작 시 확정한 입력방식을 유지(중간 변경으로 typing/paste 뒤바뀜 방지)
        if self.running and self.run_input_mode in ("typing", "paste", "mixed"):
            self.cfg["input_mode"] = self.run_input_mode
            try:
                if self.input_mode_var.get() != self.run_input_mode:
                    self.input_mode_var.set(self.run_input_mode)
            except Exception:
                pass
        else:
            self.cfg["input_mode"] = self.input_mode_var.get()
        self.cfg["start_url"] = self.start_url_var.get().strip() if hasattr(self, "start_url_var") else self.cfg.get("start_url", "")
        self.cfg["input_selector"] = self.input_selector_var.get().strip() if hasattr(self, "input_selector_var") else self.cfg.get("input_selector", "")
        self.cfg["submit_selector"] = self.submit_selector_var.get().strip() if hasattr(self, "submit_selector_var") else self.cfg.get("submit_selector", "")
        self.cfg["auto_open_new_project"] = self.auto_new_project_var.get() if hasattr(self, "auto_new_project_var") else self.cfg.get("auto_open_new_project", True)
        self.cfg["new_project_selector"] = self.new_project_selector_var.get().strip() if hasattr(self, "new_project_selector_var") else self.cfg.get("new_project_selector", "")
        self.cfg["browser_headless"] = self.browser_headless_var.get() if hasattr(self, "browser_headless_var") else self.cfg.get("browser_headless", False)
        self.cfg["browser_channel"] = self.browser_channel_var.get().strip() if hasattr(self, "browser_channel_var") else self.cfg.get("browser_channel", "chrome")
        if hasattr(self, "lbl_coords"):
            self.lbl_coords.config(text=self._get_coord_text())
        try: self.cfg["relay_count"] = int(self.relay_cnt_var.get())
        except: self.cfg["relay_count"] = 1
        self.cfg["relay_use_selection"] = self.relay_pick_var.get() if hasattr(self, "relay_pick_var") else self.cfg.get("relay_use_selection", False)
        if hasattr(self, "combo_relay_start") and self.combo_relay_start.current() >= 0:
            self.cfg["relay_start_slot"] = self.combo_relay_start.current()
        if hasattr(self, "combo_relay_end") and self.combo_relay_end.current() >= 0:
            self.cfg["relay_end_slot"] = self.combo_relay_end.current()
        self.cfg["relay_selected_slots"] = self._normalize_relay_selected_slots(self.cfg.get("relay_selected_slots", []))
        self.save_config()
        self._sync_relay_selection_label()
        if hasattr(self, 'actor'):
            self.actor.language_mode = self.cfg["language_mode"]
        if hasattr(self, "lbl_hud_mode"):
            self.lbl_hud_mode.config(text=f"입력: {self.cfg['input_mode']}")
        self.log(f"⚙️ 설정 동기화 완료 (입력방식: {self.cfg['input_mode']})")

    def _pick_first_visible_selector(self, candidates):
        if not self.page:
            return None
        for sel in candidates:
            try:
                loc = self.page.locator(sel).first
                if loc.count() <= 0:
                    continue
                if loc.is_visible(timeout=1200):
                    return sel
            except Exception:
                continue
        return None

    def _normalize_candidate_list(self, value):
        out = []
        if isinstance(value, str):
            v = value.strip()
            if v:
                out.append(v)
        elif isinstance(value, (list, tuple)):
            for x in value:
                if isinstance(x, str):
                    v = x.strip()
                    if v:
                        out.append(v)
        return out

    def _input_candidates(self):
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get("input_selector", "")))
        cands.extend(self._normalize_candidate_list(self.cfg.get("input_selectors", [])))
        cands.extend([
            "textarea[placeholder*='무엇을 만들고 싶으신가요' i]",
            "textarea[aria-label*='무엇을 만들고 싶으신가요' i]",
            "[role='textbox'][aria-label*='무엇을 만들고 싶으신가요' i]",
            "[contenteditable='true'][aria-label*='무엇을 만들고 싶으신가요' i]",
            "#PINHOLE_TEXT_AREA_ELEMENT_ID",
            "textarea#PINHOLE_TEXT_AREA_ELEMENT_ID",
            "[id*='PINHOLE' i]",
            "textarea:not([placeholder*='검색' i]):not([aria-label*='검색' i]):not([placeholder*='asset' i]):not([aria-label*='asset' i])",
            "[role='textbox']:not([aria-label*='검색' i]):not([aria-label*='asset' i])",
            "[contenteditable='true']:not([aria-label*='검색' i]):not([aria-label*='asset' i])",
            "textarea",
            "[contenteditable='true']",
            "[contenteditable='plaintext-only']",
            "div[contenteditable='true']",
            "div[contenteditable='plaintext-only']",
            "[role='textbox']",
            "div.ProseMirror[contenteditable='true']",
            "div[data-lexical-editor='true']",
            "textarea[placeholder*='무엇을 만들' i]",
            "textarea[aria-label*='무엇을 만들' i]",
            "textarea[placeholder*='프롬프트' i]",
            "textarea[aria-label*='프롬프트' i]",
            "textarea[placeholder*='prompt' i]",
            "textarea[placeholder*='message' i]",
            "textarea[placeholder*='메시지' i]",
            "textarea[aria-label*='prompt' i]",
            "textarea[aria-label*='message' i]",
        ])
        # 중복 제거(순서 유지)
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _submit_candidates(self):
        cands = []
        cands.extend(self._normalize_candidate_list(self.cfg.get("submit_selector", "")))
        cands.extend(self._normalize_candidate_list(self.cfg.get("submit_selectors", [])))
        cands.extend([
            "button[type='submit']",
            "button[aria-label*='generate' i]",
            "button[aria-label*='생성' i]",
            "button[aria-label*='보내' i]",
            "button[aria-label*='send' i]",
            "button[aria-label*='submit' i]",
            "[role='button'][aria-label*='생성' i]",
            "[role='button'][aria-label*='보내' i]",
            "[role='button'][aria-label*='send' i]",
            "button:has-text('Generate')",
            "button:has-text('생성')",
            "button:has-text('보내기')",
            # 마지막 fallback으로만 사용
            "button[aria-label*='create' i]",
            "button:has-text('Create')",
        ])
        seen = set()
        uniq = []
        for x in cands:
            if x not in seen:
                uniq.append(x)
                seen.add(x)
        return uniq

    def _resolve_submit_by_geometry(self, input_locator, timeout_ms=1200):
        """
        텍스트 기반 selector가 부정확할 때, 입력창 오른쪽의 실제 전송 버튼을 기하학적으로 추정한다.
        """
        if (not self.page) or (input_locator is None):
            return None
        try:
            ib = input_locator.bounding_box()
        except Exception:
            ib = None
        if not ib:
            return None

        ix = ib["x"]
        iy = ib["y"]
        iw = ib["width"]
        ih = ib["height"]
        input_cx = ix + iw / 2.0
        input_cy = iy + ih / 2.0
        input_right = ix + iw

        best = None
        best_score = float("inf")
        try:
            loc = self.page.locator("button, [role='button']")
            total = loc.count()
        except Exception:
            return None

        upper = min(total, 250)
        for i in range(upper):
            cand = loc.nth(i)
            try:
                if not cand.is_visible(timeout=timeout_ms):
                    continue
            except Exception:
                continue
            try:
                if not cand.is_enabled(timeout=200):
                    continue
            except Exception:
                pass
            try:
                b = cand.bounding_box()
            except Exception:
                b = None
            if not b:
                continue
            if b["width"] < 18 or b["height"] < 18:
                continue

            cx = b["x"] + b["width"] / 2.0
            cy = b["y"] + b["height"] / 2.0
            score = 0.0

            # 입력창 행과 가까운 버튼(특히 우측)을 선호
            score += abs(cy - input_cy) * 3.0
            score += abs(cx - (input_right - 24.0)) * 1.5

            # 입력창보다 너무 위쪽(상단바)은 강한 패널티
            if cy < (iy - 180):
                score += 3000.0
            # 입력창 왼쪽에 있는 버튼(+) 등은 패널티
            if cx < (ix + iw * 0.45):
                score += 900.0

            try:
                meta = cand.evaluate(
                    """(el) => ((el.getAttribute('aria-label') || '') + ' ' + (el.innerText || '')).toLowerCase()"""
                )
            except Exception:
                meta = ""
            if meta:
                if any(x in meta for x in ("menu", "메뉴", "설정", "setting", "도움", "help", "프로젝트")):
                    score += 1600.0
                if any(x in meta for x in ("생성", "generate", "send", "보내")):
                    score -= 350.0

            if score < best_score:
                best_score = score
                best = cand

        return best

    def _resolve_visible_locator(self, candidates, timeout_ms=1200):
        if not self.page:
            return None, None
        # main frame 우선
        for sel in candidates:
            try:
                loc = self.page.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=timeout_ms):
                    return loc, sel
            except Exception:
                continue
        # iframe 탐색
        try:
            for fr in self.page.frames:
                if fr == self.page.main_frame:
                    continue
                for sel in candidates:
                    try:
                        loc = fr.locator(sel).first
                        if loc.count() > 0 and loc.is_visible(timeout=timeout_ms):
                            return loc, sel
                    except Exception:
                        continue
        except Exception:
            pass
        return None, None

    def _resolve_best_locator(self, candidates, near_locator=None, timeout_ms=1200, prefer_enabled=True, reject_fn=None):
        """
        selector가 여러 개 매칭될 때 가장 적절한 요소를 고르는 함수.
        - near_locator가 있으면 그 근처의 요소를 우선 선택
        - 비활성(disabled) 요소는 강한 패널티
        """
        if not self.page:
            return None, None

        near_cx = None
        near_cy = None
        if near_locator is not None:
            try:
                nb = near_locator.bounding_box()
                if nb:
                    near_cx = nb["x"] + nb["width"] / 2.0
                    near_cy = nb["y"] + nb["height"] / 2.0
            except Exception:
                pass

        best = None
        best_selector = None
        best_score = float("inf")

        def _consider(loc, sel):
            nonlocal best, best_selector, best_score
            try:
                total = loc.count()
            except Exception:
                return
            if total <= 0:
                return
            # 너무 많은 요소일 때 과도한 탐색 방지
            upper = min(total, 20)
            for i in range(upper):
                cand = loc.nth(i)
                try:
                    if not cand.is_visible(timeout=timeout_ms):
                        continue
                except Exception:
                    continue
                if reject_fn is not None:
                    try:
                        if reject_fn(cand, sel):
                            continue
                    except Exception:
                        pass
                try:
                    box = cand.bounding_box()
                except Exception:
                    box = None
                if not box:
                    continue

                score = 0.0
                try:
                    enabled = cand.is_enabled(timeout=300)
                except Exception:
                    enabled = True
                # 입력 전 단계에서는 제출 버튼이 disabled일 수 있어 과도 패널티를 피한다.
                if not enabled and prefer_enabled:
                    score += 1200.0

                # 너무 작은 요소는 오탐 가능성이 큼
                if box["width"] < 20 or box["height"] < 12:
                    score += 3000.0

                if near_cx is not None and near_cy is not None:
                    cx = box["x"] + box["width"] / 2.0
                    cy = box["y"] + box["height"] / 2.0
                    dx = cx - near_cx
                    dy = cy - near_cy
                    score += (dx * dx + dy * dy) ** 0.5
                else:
                    score += float(i)

                if score < best_score:
                    best_score = score
                    best = cand
                    best_selector = sel

        # main frame
        for sel in candidates:
            try:
                _consider(self.page.locator(sel), sel)
            except Exception:
                continue

        # iframes
        try:
            for fr in self.page.frames:
                if fr == self.page.main_frame:
                    continue
                for sel in candidates:
                    try:
                        _consider(fr.locator(sel), sel)
                    except Exception:
                        continue
        except Exception:
            pass

        return best, best_selector

    def _locator_meta_text(self, locator):
        try:
            return locator.evaluate(
                """(el) => {
                    const a = (name) => (el.getAttribute(name) || "");
                    const parts = [
                        (el.tagName || ""),
                        (el.id || ""),
                        (el.className || ""),
                        a("name"),
                        a("placeholder"),
                        a("aria-label"),
                        a("title"),
                        (el.innerText || ""),
                    ];
                    return parts.join(" ").toLowerCase();
                }"""
            ) or ""
        except Exception:
            return ""

    def _is_asset_search_like_locator(self, locator):
        meta = self._locator_meta_text(locator)
        if not meta:
            return False
        search_keys = ("asset", "search", "에셋", "검색", "swap_horiz", "swap")
        prompt_keys = ("무엇을 만들고 싶으신가요", "prompt", "프롬프트", "message", "메시지")
        has_search = any(k in meta for k in search_keys)
        has_prompt = any(k in meta for k in prompt_keys)
        return has_search and (not has_prompt)

    def _resolve_prompt_input_locator(self, input_selector, timeout_ms=2500):
        # 동적 UI에서 ref 재할당이 발생해도 매번 "프롬프트 입력칸"을 다시 찾도록 강제한다.
        candidates = self._normalize_candidate_list(input_selector)
        for sel in self._input_candidates():
            if sel not in candidates:
                candidates.append(sel)

        input_loc, resolved_selector = self._resolve_best_locator(
            candidates,
            timeout_ms=timeout_ms,
            reject_fn=lambda cand, _sel: self._is_asset_search_like_locator(cand),
        )
        if input_loc is not None:
            return input_loc, resolved_selector

        # 2차 폴백: 사용자 지정 selector만은 마지막으로 1회 허용(예외 케이스 대비)
        input_loc, resolved_selector = self._resolve_best_locator(
            self._normalize_candidate_list(input_selector),
            timeout_ms=max(1200, int(timeout_ms * 0.8)),
        )
        if input_loc is not None and (not self._is_asset_search_like_locator(input_loc)):
            return input_loc, resolved_selector

        return None, None

    def _read_input_text(self, input_locator):
        if input_locator is None:
            return ""
        try:
            val = input_locator.evaluate(
                """(el) => {
                    if (!el) return "";
                    if ("value" in el && typeof el.value === "string") return el.value;
                    return (el.innerText || el.textContent || "");
                }"""
            )
            return (val or "").strip()
        except Exception:
            return ""

    def _is_generation_indicator_visible(self):
        if not self.page:
            return False
        indicators = [
            "button:has-text('생성 중')",
            "button:has-text('처리 중')",
            "button:has-text('중지')",
            "button:has-text('취소')",
            "button:has-text('Stop')",
            "button:has-text('Cancel')",
            "text=/생성 중|Generating/i",
        ]
        for sel in indicators:
            try:
                loc = self.page.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=250):
                    return True
            except Exception:
                continue
        return False

    def _confirm_submission_started(self, input_locator, before_text, timeout_sec=12):
        """
        제출 직후 실제로 동작이 시작됐는지 검증.
        """
        end_ts = time.time() + max(2, timeout_sec)
        before_text = (before_text or "").strip()
        while time.time() < end_ts:
            if self._is_generation_indicator_visible():
                return True
            current = self._read_input_text(input_locator)
            # 입력창이 비워졌거나 크게 변하면 제출 성공으로 판단
            if before_text and current != before_text:
                if len(current) <= max(2, int(len(before_text) * 0.4)):
                    return True
                # 완전히 같은 프롬프트가 아니면 일부 변형도 성공으로 인정
                if current[:40] != before_text[:40]:
                    return True
            time.sleep(0.5)
        return False

    def _is_input_visible(self, input_selector):
        if not self.page:
            return False
        loc, _ = self._resolve_prompt_input_locator(input_selector, timeout_ms=1200)
        return loc is not None

    def _wait_until_input_visible(self, input_selector, timeout_sec=18):
        if not self.page:
            return False
        end_ts = time.time() + max(1, timeout_sec)
        while time.time() < end_ts:
            if self._is_input_visible(input_selector):
                return True
            time.sleep(0.6)
        return False

    def _try_open_new_project_if_needed(self, input_selector):
        if not self.page:
            return False
        if self._is_input_visible(input_selector):
            return True
        if not self.cfg.get("auto_open_new_project", True):
            return False

        custom_selector = (self.cfg.get("new_project_selector") or "").strip()
        candidates = []
        if custom_selector:
            candidates.append(custom_selector)

        candidates.extend([
            "button:has-text('새 프로젝트')",
            "button:has-text('새 프로젝트 만들기')",
            "[role='button']:has-text('새 프로젝트')",
            "a:has-text('새 프로젝트')",
            "button:has-text('Create')",
            "[role='button']:has-text('Create')",
            "button:has-text('New project')",
            "button:has-text('New Project')",
            "button:has-text('Create new')",
            "[role='button']:has-text('New project')",
            "a:has-text('New project')",
        ])

        clicked = False
        for sel in candidates:
            try:
                loc = self.page.locator(sel).first
                if loc.count() <= 0:
                    continue
                if not loc.is_visible(timeout=1000):
                    continue
                self.log(f"🧭 새 프로젝트 버튼 감지: {sel}")
                try:
                    self.actor.move_to_locator(loc, label="새 프로젝트 버튼")
                    self.actor.smart_click(label="새 프로젝트 버튼 클릭")
                except Exception:
                    loc.click(timeout=3000)
                try:
                    # 랜덤 클릭 실패 대비해서 Playwright 직접 클릭 한 번 더 시도
                    loc.click(timeout=2500)
                except Exception:
                    pass
                clicked = True
                break
            except Exception:
                continue

        if not clicked:
            return False

        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        return self._wait_until_input_visible(input_selector, timeout_sec=20)

    def _pick_input_selector_by_dom_heuristic(self):
        if not self.page:
            return None
        try:
            return self.page.evaluate(
                """() => {
                    const isVisible = (el) => {
                        if (!el) return false;
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 20 || rect.height < 12) return false;
                        const style = window.getComputedStyle(el);
                        return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
                    };
                    const all = Array.from(document.querySelectorAll("textarea, [contenteditable='true'], [role='textbox']"));
                    const visible = all.filter(isVisible);
                    if (!visible.length) return null;

                    const score = (el) => {
                        const tag = (el.tagName || '').toLowerCase();
                        const ph = (el.getAttribute('placeholder') || '').toLowerCase();
                        const ar = (el.getAttribute('aria-label') || '').toLowerCase();
                        const ce = el.getAttribute('contenteditable');
                        const r = el.getBoundingClientRect();
                        let s = r.width * r.height;
                        if (tag === 'textarea') s += 100000;
                        if (ce === 'true' || ce === 'plaintext-only') s += 20000;
                        if (ph.includes('무엇을 만들') || ar.includes('무엇을 만들')) s += 120000;
                        if (ph.includes('프롬프트') || ar.includes('프롬프트')) s += 90000;
                        if (ph.includes('prompt') || ph.includes('message') || ph.includes('메시지')) s += 80000;
                        if (ar.includes('prompt') || ar.includes('message') || ar.includes('메시지')) s += 80000;
                        if (ph.includes('asset') || ph.includes('search') || ph.includes('에셋') || ph.includes('검색')) s -= 220000;
                        if (ar.includes('asset') || ar.includes('search') || ar.includes('에셋') || ar.includes('검색')) s -= 220000;
                        return s;
                    };
                    visible.sort((a, b) => score(b) - score(a));
                    const el = visible[0];

                    const id = el.getAttribute('id');
                    if (id) return `#${CSS.escape(id)}`;

                    const name = el.getAttribute('name');
                    if (name) {
                        const tag = el.tagName.toLowerCase();
                        return `${tag}[name="${name.replace(/"/g, '\\\\"')}"]`;
                    }

                    const ar = el.getAttribute('aria-label');
                    if (ar) {
                        const tag = el.tagName.toLowerCase();
                        return `${tag}[aria-label*="${ar.replace(/"/g, '\\\\"')}"]`;
                    }

                    const ph = el.getAttribute('placeholder');
                    if (ph) {
                        const tag = el.tagName.toLowerCase();
                        return `${tag}[placeholder*="${ph.replace(/"/g, '\\\\"')}"]`;
                    }

                    const tag = el.tagName.toLowerCase();
                    if (el.getAttribute('contenteditable') === 'true') return `${tag}[contenteditable='true']`;
                    if (el.getAttribute('contenteditable') === 'plaintext-only') return `${tag}[contenteditable='plaintext-only']`;
                    if (el.getAttribute('role') === 'textbox') return `${tag}[role='textbox']`;
                    return tag;
                }"""
            )
        except Exception:
            return None

    def on_auto_detect_selectors(self):
        if self.running:
            messagebox.showwarning("안내", "자동화 실행 중에는 selector 탐색을 할 수 없습니다.\n먼저 중지 후 시도해주세요.")
            return
        self.on_option_toggle()
        self._auto_detect_selectors_worker()

    def _auto_detect_selectors_worker(self):
        try:
            self.update_status_label("🔍 selector 자동 탐색 중...", self.color_info)
            self._ensure_browser_session()
            self.actor.set_page(self.page)

            start_url = (self.cfg.get("start_url") or "").strip()
            if start_url:
                if start_url not in (self.page.url or ""):
                    self.page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
                time.sleep(random.uniform(1.0, 2.5))
            input_hint = (self.cfg.get("input_selector") or "").strip() or "#PINHOLE_TEXT_AREA_ELEMENT_ID, textarea, [contenteditable='true'], [role='textbox']"
            self._try_open_new_project_if_needed(input_hint)

            submit_candidates = self._submit_candidates()

            found_input_loc, found_input = self._resolve_prompt_input_locator(
                self.cfg.get("input_selector", ""),
                timeout_ms=1400,
            )
            if not found_input:
                found_input = self._pick_input_selector_by_dom_heuristic()
                if found_input:
                    found_input_loc, _ = self._resolve_best_locator(
                        self._normalize_candidate_list(found_input),
                        timeout_ms=1200,
                    )
            found_submit = None
            # 입력창을 찾은 경우에만 제출 버튼을 확정(홈 화면 Create 오탐 방지)
            if found_input:
                _, found_submit = self._resolve_best_locator(
                    submit_candidates,
                    near_locator=found_input_loc,
                    timeout_ms=1200,
                )
                if not found_submit:
                    # 근접 기준으로 못 찾으면 일반 visible 기준으로 1회 폴백
                    _, found_submit = self._resolve_visible_locator(submit_candidates, timeout_ms=1200)

            if found_input:
                self.input_selector_var.set(found_input)
                self.cfg["input_selector"] = found_input
            if found_submit:
                self.submit_selector_var.set(found_submit)
                self.cfg["submit_selector"] = found_submit
            self.save_config()
            self.lbl_coords.config(text=self._get_coord_text())
            if found_input and found_submit:
                self.log(f"✅ 자동 탐색 성공 | 입력: {found_input} | 제출: {found_submit}")
                self.update_status_label("✅ selector 자동 탐색 완료", self.color_success)
            else:
                self.log(f"⚠️ 자동 탐색 부분 성공 | 입력: {found_input or '미탐지'} | 제출: {found_submit or '미탐지'}")
                self.update_status_label("⚠️ 일부 selector 미탐지", self.color_error)
        except Exception as e:
            self.log(f"❌ selector 자동 탐색 실패: {e}")
            self.update_status_label("❌ selector 자동 탐색 실패", self.color_error)

    def on_test_selectors(self):
        if self.running:
            messagebox.showwarning("안내", "자동화 실행 중에는 selector 테스트를 할 수 없습니다.\n먼저 중지 후 시도해주세요.")
            return
        self.on_option_toggle()
        self._test_selectors_worker()

    def _test_selectors_worker(self):
        try:
            self.update_status_label("🧪 selector 테스트 중...", self.color_info)
            self._ensure_browser_session()
            self.actor.set_page(self.page)

            start_url = (self.cfg.get("start_url") or "").strip()
            input_selector = (self.cfg.get("input_selector") or "").strip()
            submit_selector = (self.cfg.get("submit_selector") or "").strip()

            def _check_once():
                try:
                    input_loc, _ = self._resolve_prompt_input_locator(
                        input_selector,
                        timeout_ms=2200,
                    )
                    input_ok_local = input_loc is not None
                except Exception:
                    input_ok_local = False
                try:
                    submit_loc, _ = self._resolve_best_locator(
                        self._normalize_candidate_list(submit_selector) or self._submit_candidates(),
                        near_locator=input_loc if input_ok_local else None,
                        timeout_ms=2200,
                    )
                    submit_ok_local = submit_loc is not None
                except Exception:
                    submit_ok_local = False
                return input_ok_local, submit_ok_local

            # 1차: 현재 화면에서 바로 검사 (사용자가 이미 편집화면일 수 있음)
            input_ok, submit_ok = _check_once()

            # 2차: 실패 시에만 시작 URL 이동 + 새 프로젝트 자동 진입 시도 후 재검사
            if not (input_ok and submit_ok):
                if start_url:
                    self.page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
                self._try_open_new_project_if_needed(
                    input_selector or "#PINHOLE_TEXT_AREA_ELEMENT_ID, textarea, [contenteditable='true'], [role='textbox']"
                )
                # 동적 렌더링 대기 후 재검사
                for _ in range(6):
                    time.sleep(0.7)
                    input_ok, submit_ok = _check_once()
                    if input_ok and submit_ok:
                        break

            self.log(
                f"🧪 selector 테스트 결과 | URL({self.page.url}) | 입력({input_selector}): {'OK' if input_ok else 'FAIL'} | "
                f"제출({submit_selector}): {'OK' if submit_ok else 'FAIL'}"
            )
            if input_ok and submit_ok:
                self.update_status_label("✅ selector 테스트 통과", self.color_success)
            else:
                self.update_status_label("⚠️ selector 확인 필요", self.color_error)
        except Exception as e:
            self.log(f"❌ selector 테스트 실패: {e}")
            self.update_status_label("❌ selector 테스트 실패", self.color_error)

    def on_auto_detect_asset_selectors(self):
        if self.running:
            messagebox.showwarning("안내", "자동화 실행 중에는 selector 탐색을 할 수 없습니다.\n먼저 중지 후 시도해주세요.")
            return
        self.on_option_toggle()
        self._auto_detect_asset_selectors_worker()

    def _auto_detect_asset_selectors_worker(self):
        try:
            self.update_status_label("🔍 에셋 selector 자동 탐색 중...", self.color_info)
            self._ensure_browser_session()
            self.actor.set_page(self.page)

            start_url = (self.cfg.get("start_url") or "").strip()
            if start_url and start_url not in (self.page.url or ""):
                self.page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(random.uniform(1.0, 2.3))

            start_loc, start_sel = self._wait_best_locator(
                self._asset_start_button_candidates(),
                timeout_sec=7,
                prefer_enabled=False,
            )
            search_candidates = self._asset_search_button_candidates() + [
                "text=에셋 검색",
                "text=Asset search",
                "text=Search assets",
            ]
            search_loc, search_sel = self._wait_best_locator(
                search_candidates,
                timeout_sec=9,
                prefer_enabled=False,
            )
            if start_loc is None:
                start_loc, start_sel = self._resolve_text_locator_any_frame(["시작", "Start"], timeout_ms=1000)
            if search_loc is None:
                search_loc, search_sel = self._resolve_text_locator_any_frame(
                    ["에셋 검색", "Asset search", "Search assets"],
                    timeout_ms=1200,
                )

            input_loc, input_sel = self._wait_best_locator(
                self._asset_search_input_candidates(),
                timeout_sec=2,
                prefer_enabled=False,
            )
            if (input_loc is None) and (search_loc is not None):
                try:
                    search_loc.click(timeout=2000)
                    self.actor.random_action_delay("에셋 검색 입력칸 표시 대기", 0.3, 1.2)
                except Exception:
                    pass
                input_loc, input_sel = self._wait_best_locator(
                    self._asset_search_input_candidates(),
                    timeout_sec=8,
                    prefer_enabled=False,
                )

            if start_sel:
                self.cfg["asset_start_selector"] = start_sel
                if hasattr(self, "asset_start_selector_var"):
                    self.asset_start_selector_var.set(start_sel)
            if search_sel:
                self.cfg["asset_search_button_selector"] = search_sel
                if hasattr(self, "asset_search_btn_selector_var"):
                    self.asset_search_btn_selector_var.set(search_sel)
            if input_sel:
                self.cfg["asset_search_input_selector"] = input_sel
                if hasattr(self, "asset_search_input_selector_var"):
                    self.asset_search_input_selector_var.set(input_sel)
            self.save_config()

            self.log(
                "🔍 에셋 selector 자동탐색 결과 | "
                f"시작: {start_sel or '미탐지'} | 에셋검색: {search_sel or '미탐지'} | 검색입력: {input_sel or '미탐지'}"
            )
            if start_sel and input_sel:
                self.update_status_label("✅ 에셋 selector 자동탐색 완료", self.color_success)
            else:
                self.update_status_label("⚠️ 에셋 selector 일부 미탐지", self.color_error)
        except Exception as e:
            self.log(f"❌ 에셋 selector 자동탐색 실패: {e}")
            self.update_status_label("❌ 에셋 selector 자동탐색 실패", self.color_error)

    def on_test_asset_selectors(self):
        if self.running:
            messagebox.showwarning("안내", "자동화 실행 중에는 selector 테스트를 할 수 없습니다.\n먼저 중지 후 시도해주세요.")
            return
        self.on_option_toggle()
        self._test_asset_selectors_worker()

    def _test_asset_selectors_worker(self):
        try:
            self.update_status_label("🧪 에셋 selector 테스트 중...", self.color_info)
            self._ensure_browser_session()
            self.actor.set_page(self.page)

            start_url = (self.cfg.get("start_url") or "").strip()
            if start_url and start_url not in (self.page.url or ""):
                self.page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(random.uniform(0.8, 1.8))

            start_candidates = self._normalize_candidate_list(self.cfg.get("asset_start_selector", "")) or self._asset_start_button_candidates()
            search_candidates = self._normalize_candidate_list(self.cfg.get("asset_search_button_selector", "")) or self._asset_search_button_candidates()
            input_candidates = self._normalize_candidate_list(self.cfg.get("asset_search_input_selector", "")) or self._asset_search_input_candidates()

            start_loc, start_sel = self._resolve_best_locator(start_candidates, timeout_ms=2200, prefer_enabled=False)
            search_loc, search_sel = self._resolve_best_locator(search_candidates + ["text=에셋 검색", "text=Asset search"], timeout_ms=2200, prefer_enabled=False)
            if start_loc is None:
                start_loc, start_sel = self._resolve_text_locator_any_frame(["시작", "Start"], timeout_ms=1000)
            if search_loc is None:
                search_loc, search_sel = self._resolve_text_locator_any_frame(
                    ["에셋 검색", "Asset search", "Search assets"],
                    timeout_ms=1200,
                )

            input_loc, input_sel = self._resolve_best_locator(input_candidates, timeout_ms=1800, prefer_enabled=False)
            if (input_loc is None) and (search_loc is not None):
                try:
                    search_loc.click(timeout=2000)
                except Exception:
                    pass
                self.actor.random_action_delay("검색 입력칸 확인 대기", 0.3, 1.0)
                input_loc, input_sel = self._resolve_best_locator(input_candidates, timeout_ms=3000, prefer_enabled=False)

            start_ok = start_loc is not None
            search_ok = search_loc is not None
            input_ok = input_loc is not None
            # 일부 UI는 버튼 없이 검색 입력칸이 바로 노출되므로 search 버튼은 선택 항목으로 처리
            flow_ok = start_ok and input_ok

            self.log(
                f"🧪 에셋 selector 테스트 | 시작({start_sel or start_candidates[0] if start_candidates else '-'})={'OK' if start_ok else 'FAIL'} | "
                f"에셋검색({search_sel or search_candidates[0] if search_candidates else '-'})={'OK' if search_ok else 'FAIL'} | "
                f"검색입력({input_sel or input_candidates[0] if input_candidates else '-'})={'OK' if input_ok else 'FAIL'}"
            )
            if flow_ok:
                self.update_status_label("✅ 에셋 selector 테스트 통과", self.color_success)
            else:
                self.update_status_label("⚠️ 에셋 selector 확인 필요", self.color_error)
        except Exception as e:
            self.log(f"❌ 에셋 selector 테스트 실패: {e}")
            self.update_status_label("❌ 에셋 selector 테스트 실패", self.color_error)

    def on_auto_detect_image_download_selectors(self):
        if self.running:
            messagebox.showwarning("안내", "자동화 실행 중에는 selector 탐색을 할 수 없습니다.\n먼저 중지 후 시도해주세요.")
            return
        self.on_option_toggle()
        self._auto_detect_download_selectors_worker("image")

    def on_auto_detect_video_download_selectors(self):
        if self.running:
            messagebox.showwarning("안내", "자동화 실행 중에는 selector 탐색을 할 수 없습니다.\n먼저 중지 후 시도해주세요.")
            return
        self.on_option_toggle()
        self._auto_detect_download_selectors_worker("video")

    def _auto_detect_download_selectors_worker(self, mode):
        mode = "image" if mode == "image" else "video"
        mode_txt = "이미지" if mode == "image" else "영상"
        opened_here = False
        try:
            if not self.action_log_fp:
                self._open_action_log("download_trace")
                opened_here = True
            self.update_status_label(f"🔍 {mode_txt} 다운로드 selector 자동 탐색 중...", self.color_info)
            self._ensure_browser_session()
            self.actor.set_page(self.page)

            start_url = (self.cfg.get("start_url") or "").strip()
            if start_url and start_url not in (self.page.url or ""):
                self.page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(random.uniform(0.8, 1.6))

            items = self._build_download_items()
            tag = items[0] if items else "S01"
            quality = self._download_quality(mode)
            result = self._run_single_download_flow(mode=mode, tag=tag, quality=quality, dry_run=True, wait_sec=25)
            self._apply_download_used_selectors(mode, result.get("used", {}))
            self.save_config()
            used = result.get("used", {})
            self.log(
                f"🔍 {mode_txt} 다운로드 selector 자동탐색 결과 | "
                f"검색입력: {used.get('search_input') or '미탐지'} | "
                f"필터: {used.get('filter') or '미탐지'} | "
                f"카드: {used.get('card') or '미탐지'} | "
                f"더보기: {used.get('more') or '미탐지'} | "
                f"다운로드: {used.get('menu') or '미탐지'} | "
                f"품질: {used.get('quality') or '미탐지'}"
            )
            self.update_status_label(f"✅ {mode_txt} 다운로드 selector 자동탐색 완료", self.color_success)
        except Exception as e:
            self.log(f"❌ {mode_txt} 다운로드 selector 자동탐색 실패: {e}")
            self.update_status_label(f"❌ {mode_txt} 다운로드 selector 자동탐색 실패", self.color_error)
        finally:
            if opened_here:
                self._close_action_log()

    def on_test_image_download_selectors(self):
        if self.running:
            messagebox.showwarning("안내", "자동화 실행 중에는 selector 테스트를 할 수 없습니다.\n먼저 중지 후 시도해주세요.")
            return
        self.on_option_toggle()
        self._test_download_selectors_worker("image")

    def on_test_video_download_selectors(self):
        if self.running:
            messagebox.showwarning("안내", "자동화 실행 중에는 selector 테스트를 할 수 없습니다.\n먼저 중지 후 시도해주세요.")
            return
        self.on_option_toggle()
        self._test_download_selectors_worker("video")

    def _test_download_selectors_worker(self, mode):
        mode = "image" if mode == "image" else "video"
        mode_txt = "이미지" if mode == "image" else "영상"
        opened_here = False
        try:
            if not self.action_log_fp:
                self._open_action_log("download_trace")
                opened_here = True
            self.update_status_label(f"🧪 {mode_txt} 다운로드 selector 테스트 중...", self.color_info)
            self._ensure_browser_session()
            self.actor.set_page(self.page)

            start_url = (self.cfg.get("start_url") or "").strip()
            if start_url and start_url not in (self.page.url or ""):
                self.page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(random.uniform(0.8, 1.6))

            items = self._build_download_items()
            default_tag = items[0] if items else "S01"
            tag = simpledialog.askstring(
                f"{mode_txt} 다운로드 테스트",
                "테스트할 태그를 입력하세요. (예: S01)",
                initialvalue=default_tag,
                parent=self.root,
            )
            if tag is None:
                self.update_status_label(f"ℹ️ {mode_txt} 다운로드 테스트 취소됨", self.color_info)
                return
            tag = (tag or "").strip()
            if not tag:
                messagebox.showwarning("입력 오류", "태그를 입력해주세요.")
                self.update_status_label(f"⚠️ {mode_txt} 다운로드 테스트 취소", self.color_error)
                return

            quality = self._download_quality(mode)
            result = self._run_single_download_flow(mode=mode, tag=tag, quality=quality, dry_run=False, wait_sec=60)
            self._apply_download_used_selectors(mode, result.get("used", {}))
            self.save_config()
            self.log(f"🧪 {mode_txt} 다운로드 selector 테스트 성공 | 태그: {tag} | 품질: {quality} | 파일: {result.get('file') or '-'}")
            self.update_status_label(f"✅ {mode_txt} 다운로드 selector 테스트 통과", self.color_success)
        except Exception as e:
            self.log(f"❌ {mode_txt} 다운로드 selector 테스트 실패: {e}")
            self.update_status_label(f"❌ {mode_txt} 다운로드 selector 테스트 실패", self.color_error)
        finally:
            if opened_here:
                self._close_action_log()

    def on_open_relay_selector(self):
        slots = self.cfg.get("prompt_slots", [])
        if not slots:
            messagebox.showwarning("주의", "선택할 문서가 없습니다.")
            return

        selected = set(self._normalize_relay_selected_slots(self.cfg.get("relay_selected_slots", [])))
        win = tk.Toplevel(self.root)
        win.title("이어달리기 문서 선택")
        win.transient(self.root)
        win.grab_set()
        win.configure(bg="#FFFFFF")
        win.geometry("420x520")

        tk.Label(win, text="실행할 문서를 체크하세요", font=("Malgun Gothic", 11, "bold"), bg="#FFFFFF").pack(anchor="w", padx=12, pady=(12, 6))

        list_frame = tk.Frame(win, bg="#FFFFFF")
        list_frame.pack(fill="both", expand=True, padx=12, pady=6)

        canvas = tk.Canvas(list_frame, bg="#FFFFFF", highlightthickness=0)
        scrolly = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="#FFFFFF")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrolly.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrolly.pack(side="right", fill="y")

        vars_selected = []
        for i, slot in enumerate(slots):
            v = tk.BooleanVar(value=(i in selected))
            vars_selected.append(v)
            text = f"{i+1}. {slot['name']} ({slot['file']})"
            tk.Checkbutton(inner, text=text, variable=v, bg="#FFFFFF", font=("Malgun Gothic", 10), anchor="w").pack(fill="x", pady=2)

        btn_f = tk.Frame(win, bg="#FFFFFF")
        btn_f.pack(fill="x", padx=12, pady=10)

        def _set_all(flag):
            for var in vars_selected:
                var.set(flag)

        def _save():
            picked = [i for i, var in enumerate(vars_selected) if var.get()]
            self.cfg["relay_selected_slots"] = picked
            self.cfg["relay_use_selection"] = bool(picked)
            self.relay_pick_var.set(bool(picked))
            self.save_config()
            self._sync_relay_selection_label()
            if picked:
                self.log(f"✅ 체크 문서 저장 완료 ({len(picked)}개)")
            else:
                self.log("ℹ️ 체크 문서가 비어 있어 기존 범위 방식으로 실행됩니다.")
            win.destroy()

        ttk.Button(btn_f, text="전체선택", command=lambda: _set_all(True)).pack(side="left")
        ttk.Button(btn_f, text="전체해제", command=lambda: _set_all(False)).pack(side="left", padx=6)
        ttk.Button(btn_f, text="저장", command=_save).pack(side="right")

    def _get_coord_text(self):
        url_ok = bool((self.cfg.get("start_url") or "").strip())
        input_ok = bool((self.cfg.get("input_selector") or "").strip())
        submit_ok = bool((self.cfg.get("submit_selector") or "").strip())
        return f"URL[{'✅' if url_ok else '❌'}] 입력Selector[{'✅' if input_ok else '❌'}] 제출Selector[{'✅' if submit_ok else '❌'}]"

    def _get_img_coord_text(self):
        return "Playwright 모드에서는 이미지 좌표 지정 기능을 사용하지 않습니다."

    def log(self, msg):
        if hasattr(self, 'log_window'):
            self.log_window.log(msg)
        self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def start_capture(self, kind):
        messagebox.showinfo("안내", "Playwright 전환 버전에서는 화면 좌표 캡처를 사용하지 않습니다.\nURL/Selector 입력값을 사용해주세요.")

    def on_slot_change(self, event=None):
        idx = self.combo_slots.current()
        if idx >= 0:
            self.cfg["active_prompt_slot"] = idx
            self.cfg["prompts_file"] = self.cfg["prompt_slots"][idx]["file"]
            self.save_config()
            self.on_reload()

    def on_reload(self):
        try:
            if self.cfg.get("asset_loop_enabled"):
                self.asset_loop_items = self._build_asset_loop_items()
                self.prompts = [item["prompt"] for item in self.asset_loop_items]
                raw = "\n".join(self.prompts)
                if hasattr(self, "log_window"):
                    self.log_window.set_preview(raw)
            else:
                self.asset_loop_items = []
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
            if self.cfg.get("asset_loop_enabled"):
                self.log(f"로드 완료 (S반복 {len(self.prompts)}개)")
            else:
                self.log(f"로드 완료 ({len(self.prompts)}개)")
            slots = [s["name"] for s in self.cfg["prompt_slots"]]
            self.combo_slots["values"] = slots
            self.combo_slots.current(self.cfg["active_prompt_slot"])
            self._sync_relay_range_controls()
            self._sync_relay_selection_label()
        except: pass

    def _update_progress_ui(self):
        if self.current_run_mode == "download":
            total = len(self.download_items)
            current = self.download_index
        else:
            total = len(self.prompts)
            current = self.index
        shown = 0 if total == 0 else min(current + 1, total)
        self.lbl_nav_status.config(text=f"{shown} / {total}")
        if total > 0:
            pct = (min(current, total) / total) * 100
            self.progress_var.set(pct)
            self.lbl_prog_text.config(text=f"{min(current, total)} / {total} ({pct:.1f}%)")
            if hasattr(self, "lbl_header_progress"):
                self.lbl_header_progress.config(text=f"{min(current, total)} / {total} ({pct:.1f}%)")
        else:
            self.progress_var.set(0)
            self.lbl_prog_text.config(text="0 / 0 (0%)")
            if hasattr(self, "lbl_header_progress"):
                self.lbl_header_progress.config(text="0 / 0 (0.0%)")
        if hasattr(self, "lbl_hud_progress"):
            try:
                processed = getattr(self.actor, "processed_count", 0)
                batch_size = getattr(self.actor, "current_batch_size", 0)
            except Exception:
                processed = 0
                batch_size = 0
            self.lbl_hud_progress.config(text=f"진행: {min(current, total)} / {total} | 배치: {processed} / {batch_size}")

    def _update_monitor_ui(self):
        # 미니 HUD 갱신: 핵심 정보만 짧게 표시
        try:
            p_name = self.actor.current_persona_name
            mood = self.actor.current_mood
            speed_mult = self.actor.cfg.get('speed_multiplier', 1.0)

            processed = self.actor.processed_count
            batch_size = self.actor.current_batch_size
            next_break = max(0, batch_size - processed)
            active_traits = self.actor.get_active_traits()
            total = len(self.prompts)
            current = min(self.index, total)
            real_speed = 1.0 / speed_mult if speed_mult > 0 else 0.0

            if hasattr(self, "lbl_hud_progress"):
                self.lbl_hud_progress.config(text=f"진행: {current} / {total} | 배치: {processed} / {batch_size}")
            if hasattr(self, "lbl_hud_persona"):
                self.lbl_hud_persona.config(text=f"페르소나: {p_name}")
            if hasattr(self, "lbl_hud_meta"):
                self.lbl_hud_meta.config(text=f"무드: {mood} | 속도: x{real_speed:.1f} | 다음휴식: {next_break}")
            if hasattr(self, "lbl_hud_trait"):
                if active_traits:
                    self.lbl_hud_trait.config(text=f"특징: {active_traits[0]}")
                else:
                    self.lbl_hud_trait.config(text="특징: 기본 모드")
        except Exception as e:
            print(f"Failed to update monitor UI: {e}")

    def _set_run_mode(self, mode):
        self.current_run_mode = mode
        if mode in ("prompt", "asset"):
            use_asset = (mode == "asset")
            self.cfg["asset_loop_enabled"] = use_asset
            if hasattr(self, "asset_loop_var"):
                self.asset_loop_var.set(use_asset)
        self.save_config()

    def on_start_prompt(self):
        self._set_run_mode("prompt")
        self.on_start()

    def on_start_asset(self):
        self._set_run_mode("asset")
        self.on_start()

    def on_start_download(self):
        self._set_run_mode("download")
        self.on_start()

    def on_start(self):
        if self.running:
            self.log("ℹ️ 이미 자동화가 실행 중입니다.")
            return
        if self.paused:
            self.on_resume()
            return
        run_mode = self.current_run_mode or ("asset" if self.cfg.get("asset_loop_enabled") else "prompt")
        is_download_mode = (run_mode == "download")
        if not is_download_mode:
            self.on_reload() # 시작 시 프롬프트 최신화
        try:
            self.cfg["interval_seconds"] = int(self.entry_interval.get())
        except: pass
        self.cfg["scheduled_start_enabled"] = self.schedule_var.get() if hasattr(self, "schedule_var") else self.cfg.get("scheduled_start_enabled", False)
        self.cfg["scheduled_start_at"] = self.schedule_text_var.get().strip() if hasattr(self, "schedule_text_var") else self.cfg.get("scheduled_start_at", "")
        self.save_config()

        if (not is_download_mode) and self.cfg.get("asset_loop_enabled") and self.cfg.get("relay_mode"):
            self.cfg["relay_mode"] = False
            if hasattr(self, "relay_var"):
                self.relay_var.set(False)
            self.save_config()
            self.log("ℹ️ S반복 모드에서는 이어달리기를 자동 해제합니다.")

        if (not is_download_mode) and self.cfg.get("relay_mode"):
            seq = self._get_effective_relay_sequence()
            if not seq:
                messagebox.showwarning("주의", "이어달리기 대상 문서가 없습니다.")
                return
            start_slot, end_slot = seq[0], seq[-1]
            if self.cfg.get("active_prompt_slot") != start_slot:
                self.cfg["active_prompt_slot"] = start_slot
                self.cfg["prompts_file"] = self.cfg["prompt_slots"][start_slot]["file"]
                self.save_config()
                self.on_reload()
            self.index = 0
            self._update_progress_ui()
            if self.cfg.get("relay_use_selection") and self.cfg.get("relay_selected_slots"):
                self.log(f"🏃 체크 문서 이어달리기 시작 ({len(seq)}개)")
            else:
                self.log(f"🏃 이어달리기 범위: {self.cfg['prompt_slots'][start_slot]['name']} → {self.cfg['prompt_slots'][end_slot]['name']}")

        if is_download_mode:
            if not self.cfg.get("start_url", "").strip():
                messagebox.showwarning("주의", "시작 URL을 먼저 입력해주세요.")
                return
            self.download_items = self._build_download_items()
            self.download_index = 0
            self.download_session_log = []
            if not self.download_items:
                messagebox.showwarning("주의", "다운로드 대상 S번호가 비어 있습니다.\n시작/끝 번호를 확인해주세요.")
                return
            self._update_progress_ui()
            self.cfg["scheduled_start_enabled"] = False
            self.cfg["scheduled_start_at"] = ""
            if hasattr(self, "schedule_var"):
                self.schedule_var.set(False)
            if hasattr(self, "schedule_text_var"):
                self.schedule_text_var.set("")
            self.save_config()
        else:
            if not (self.cfg.get("start_url", "").strip() and self.cfg.get("input_selector", "").strip()):
                messagebox.showwarning("주의", "시작 URL / 입력 셀렉터를 먼저 입력해주세요.")
                return
            
            if not self.prompts and not self.cfg.get("relay_mode"):
                if self.cfg.get("asset_loop_enabled"):
                    messagebox.showwarning("주의", "S반복 목록이 비어 있습니다.\n시작/끝 번호를 확인해주세요.")
                else:
                    messagebox.showwarning("주의", "프롬프트 파일이 비어있습니다!\n먼저 프롬프트를 입력하고 저장을 눌러주세요.")
                return
            
            if self.index >= len(self.prompts):
                self.index = 0
                self._update_progress_ui()

        scheduled_dt = None
        if (not is_download_mode) and self.cfg.get("scheduled_start_enabled"):
            raw = self.cfg.get("scheduled_start_at", "")
            scheduled_dt = self._parse_schedule_datetime(raw)
            if not scheduled_dt:
                messagebox.showwarning(
                    "예약 시간 형식 오류",
                    "예약 시간 형식이 잘못되었습니다.\n예시처럼 입력해주세요: 2026-02-26 21:30"
                )
                return
            if scheduled_dt <= datetime.now():
                messagebox.showwarning("예약 시간 오류", "예약 시간은 현재 시각보다 미래여야 합니다.")
                return

        if self.relay_progress == 0:
            self.session_start_time = datetime.now()
            self.session_log = []
            self._open_action_log("download_trace" if is_download_mode else "action_trace")
            self.session_report_path = self.logs_dir / f"session_report_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}.json"
            if is_download_mode:
                self.download_report_path = self.logs_dir / f"download_report_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}.json"
        self.running = True
        self.paused = False
        self.pause_remaining = None
        if hasattr(self, "btn_start_prompt"):
            self.btn_start_prompt.config(state="disabled")
        if hasattr(self, "btn_start_asset"):
            self.btn_start_asset.config(state="disabled")
        if hasattr(self, "btn_start_download"):
            self.btn_start_download.config(state="disabled")
        if hasattr(self, "btn_pause"):
            self.btn_pause.config(state="normal")
        if hasattr(self, "btn_resume"):
            self.btn_resume.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.update_status_label("🚀 시작 중...", self.color_success)
        self.play_sound("start")
        self.on_option_toggle()
        if is_download_mode:
            mode_label = "영상" if self._download_mode() == "video" else "이미지"
            self.log(f"🚀 다운로드 자동화 시작 ({mode_label}, {len(self.download_items)}개)")
        elif self.cfg.get("asset_loop_enabled"):
            self.log("🚀 S반복 자동화 시작")
        else:
            self.log("🚀 프롬프트 자동화 시작")
        if not is_download_mode:
            # 실행 시점 입력방식 고정: 중간에 설정이 바뀌어도 현재 런에는 영향 없게 한다.
            self.run_input_mode = (self.cfg.get("input_mode", "paste") or "paste").strip().lower()
            if self.run_input_mode not in ("typing", "paste", "mixed"):
                self.run_input_mode = "paste"
            self.cfg["input_mode"] = self.run_input_mode
            self.input_mode_var.set(self.run_input_mode)
            self.save_config()
            try:
                self.combo_input_mode.config(state="disabled")
            except Exception:
                pass
            self.log(f"🔒 실행 입력방식 고정: {self.run_input_mode}")
        else:
            self.run_input_mode = None
        # 안정성 우선: UI(Selector 테스트)와 작업 스레드 간 Playwright 세션 충돌 방지
        # 실행 시작 시 기존 세션을 정리하고, 작업 스레드에서 세션을 새로 만든다.
        try:
            has_existing = bool(self.browser_context and self.page and (not self.page.is_closed()))
        except Exception:
            has_existing = False
        if has_existing:
            self.log("♻️ 실행 전 브라우저 세션 정리(스레드 충돌 방지)")
        self._shutdown_browser()
        self._ensure_worker_thread()
        try:
            self.actor.update_batch_size()
            self.actor.processed_count = 0
        except: pass
        if scheduled_dt:
            self.scheduled_waiting = True
            self.scheduled_start_ts = scheduled_dt.timestamp()
            self.t_next = self.scheduled_start_ts
            self.update_status_label(f"⏰ 예약 대기: {scheduled_dt.strftime('%Y-%m-%d %H:%M')}", self.color_info)
            self.log(f"⏰ 1회 예약 설정 완료: {scheduled_dt.strftime('%Y-%m-%d %H:%M')}")
        else:
            self.scheduled_waiting = False
            self.scheduled_start_ts = None
            self.t_next = time.time() # 즉시 시작

    def on_pause(self):
        if self.paused:
            return
        if (not self.running) and (not self.is_processing):
            return
        self.paused = True
        self.running = False
        if self.t_next:
            self.pause_remaining = max(1, int(self.t_next - time.time()))
        else:
            self.pause_remaining = 1
        self.scheduled_waiting = False
        self.scheduled_start_ts = None
        if hasattr(self, "btn_pause"):
            self.btn_pause.config(state="disabled")
        if hasattr(self, "btn_resume"):
            self.btn_resume.config(state="normal")
        self.btn_stop.config(state="normal")
        self.update_status_label("⏸ 일시정지", self.color_info)
        self.log("⏸ 자동화 일시정지 (브라우저/탭 유지)")

    def on_resume(self):
        if not self.paused:
            return
        self.paused = False
        self.running = True
        if hasattr(self, "btn_pause"):
            self.btn_pause.config(state="normal")
        if hasattr(self, "btn_resume"):
            self.btn_resume.config(state="disabled")
        if hasattr(self, "btn_start_prompt"):
            self.btn_start_prompt.config(state="disabled")
        if hasattr(self, "btn_start_asset"):
            self.btn_start_asset.config(state="disabled")
        if hasattr(self, "btn_start_download"):
            self.btn_start_download.config(state="disabled")
        self.btn_stop.config(state="normal")
        self._ensure_worker_thread()
        wait_sec = max(1, int(self.pause_remaining or 1))
        self.pause_remaining = None
        if not self.is_processing:
            self.t_next = time.time() + wait_sec
        self.update_status_label("▶ 재개됨", self.color_success)
        self.log(f"▶ 자동화 재개 (다음 작업까지 약 {wait_sec}초)")

    def on_stop(self):
        prev_mode = self.current_run_mode
        self.running = False
        self.paused = False
        self.pause_remaining = None
        if hasattr(self, "btn_start_prompt"):
            self.btn_start_prompt.config(state="normal")
        if hasattr(self, "btn_start_asset"):
            self.btn_start_asset.config(state="normal")
        if hasattr(self, "btn_start_download"):
            self.btn_start_download.config(state="normal")
        if hasattr(self, "btn_pause"):
            self.btn_pause.config(state="disabled")
        if hasattr(self, "btn_resume"):
            self.btn_resume.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.update_status_label("중지됨", self.color_error)
        self.is_processing = False
        self.relay_progress = 0
        self.scheduled_waiting = False
        self.scheduled_start_ts = None
        if self.alert_window:
            self.alert_window.close()
            self.alert_window = None
        if prev_mode == "download":
            self.save_download_report()
        else:
            self.save_session_report()
        self._stop_worker_thread()
        self._shutdown_browser()
        self._close_action_log()
        self.run_input_mode = None
        self.current_run_mode = None
        self.download_items = []
        self.download_index = 0
        self.download_session_log = []
        self.download_report_path = None
        try:
            self.combo_input_mode.config(state="readonly")
        except Exception:
            pass

    def _create_tray_image(self):
        if Image is None:
            return None
        icon_path = self.base.parent / "icon.ico"
        try:
            if icon_path.exists():
                return Image.open(str(icon_path))
        except Exception:
            pass
        try:
            # fallback: 단색 아이콘
            img = Image.new("RGB", (64, 64), color=(0, 122, 255))
            return img
        except Exception:
            return None

    def _start_tray_icon(self):
        if not TRAY_AVAILABLE:
            return False
        if self.tray_icon is not None:
            return True

        image = self._create_tray_image()
        if image is None:
            return False

        def _on_open(icon, item):
            try:
                self.root.after(0, self.show_from_tray)
            except Exception:
                pass

        def _on_exit(icon, item):
            try:
                self.root.after(0, self.on_tray_exit_request)
            except Exception:
                pass

        menu = pystray.Menu(
            pystray.MenuItem("열기", _on_open, default=True),
            pystray.MenuItem("종료", _on_exit),
        )
        self.tray_icon = pystray.Icon("flow_veo_bot", image, APP_NAME, menu)

        def _run():
            try:
                self.tray_icon.run()
            except Exception:
                pass

        self.tray_thread = threading.Thread(target=_run, daemon=True)
        self.tray_thread.start()
        return True

    def _stop_tray_icon(self):
        icon = self.tray_icon
        self.tray_icon = None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
        t = self.tray_thread
        self.tray_thread = None
        if t and t.is_alive():
            try:
                t.join(timeout=1.5)
            except Exception:
                pass

    def hide_to_tray(self):
        if not self._start_tray_icon():
            if not self._tray_warned_unavailable:
                self._tray_warned_unavailable = True
                messagebox.showwarning("트레이 미지원", "트레이 기능이 없어 창만 숨깁니다.\n(pystray/Pillow 설치 시 트레이 사용 가능)")
            self.root.withdraw()
            self.hidden_to_tray = True
            return
        self.root.withdraw()
        if hasattr(self, "log_window") and self.log_window:
            try:
                self.log_window.root.withdraw()
            except Exception:
                pass
        self.hidden_to_tray = True
        self.log("🧩 트레이로 숨김")

    def show_from_tray(self):
        self.hidden_to_tray = False
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def on_tray_exit_request(self):
        if not messagebox.askyesno("종료 확인", "정말 프로그램을 종료할까요?"):
            return
        self.on_exit()

    def on_window_close(self):
        self.hide_to_tray()

    def on_exit(self):
        if self.current_run_mode == "download":
            self.save_download_report()
        else:
            self.save_session_report()
        self.running = False
        self._stop_worker_thread()
        self._shutdown_browser()
        self._close_action_log()
        self._stop_tray_icon()
        self.run_input_mode = None
        self.current_run_mode = None
        try:
            self.root.destroy()
        except Exception:
            pass

    def _tick(self):
        if self.running and self.t_next:
            remain = self.t_next - time.time()
            if remain > 0:
                if not self.is_processing:
                    if self.scheduled_waiting:
                        self.update_status_label(f"⏰ 예약 대기 중... {int(remain)}초", self.color_info)
                    else:
                        self.update_status_label(f"⏳ 대기 중... {int(remain)}초", "#FFC107")

                    # 예약 대기 중이 아니고, 랜덤 행동 옵션이 켜져 있으면 페이지 내부에서 가벼운 행동 수행
                    if (self.current_run_mode != "download") and (not self.scheduled_waiting) and self.cfg.get("afk_mode") and random.random() < 0.3:
                        try:
                            self.actor.random_behavior_routine()
                        except Exception:
                            pass
            
            try: base = int(self.entry_interval.get())
            except: base = 180
            if self.current_run_mode == "download":
                remain_cnt = len(self.download_items) - self.download_index
            else:
                remain_cnt = len(self.prompts) - self.index
            total_sec = remain_cnt * base + max(0, int(remain))
            finish_time = datetime.fromtimestamp(time.time() + total_sec).strftime("%p %I:%M")
            self.lbl_eta.config(text=f"🏁 종료 예정: {finish_time}")

            if self.scheduled_waiting:
                if self.alert_window:
                    self.alert_window.close()
                    self.alert_window = None
            elif not self.is_processing and 0 < remain <= 30:
                if self.alert_window is None:
                    self.alert_window = CountdownAlert(self.root, remain, self.cfg.get("sound_enabled"))
                else:
                    self.alert_window.update_time(remain)
            
            if remain <= 0:
                if self.alert_window:
                    self.alert_window.close()
                    self.alert_window = None
                if not self.is_processing:
                    if self.scheduled_waiting:
                        self.scheduled_waiting = False
                        self.scheduled_start_ts = None
                        self.log("⏰ 예약 시각 도달! 자동화를 시작합니다.")
                    self.is_processing = True
                    self._ensure_worker_thread()
                    self.task_queue.put("run")
                if self.current_run_mode == "download":
                    interval = max(1, int(base))
                else:
                    try:
                        speed = self.actor.cfg.get('speed_multiplier', 1.0)
                    except: speed = 1.0
                    interval = int(base + random.uniform(0, base * 0.3 * speed))
                self.t_next = time.time() + interval
        self.root.after(1000, self._tick)

    def _run_task(self):
        print(f"[{datetime.now()}] Task started")
        if self.current_run_mode == "download":
            self._run_download_task()
            return
        self.on_reload() # 각 작업 시작 전 프롬프트 최신화
        self.log("작업 스레드 시작 (프롬프트 동기화 완료)")
        if not self.prompts or self.index >= len(self.prompts):
            print("No prompts or index out of range")
            self.log("프롬프트 없음 또는 범위 초과")
            self.save_session_report()
            if self.cfg.get("relay_mode"):
                seq = self._get_effective_relay_sequence()
                if not seq:
                    self._show_completion_popup()
                    return
                curr_slot = self._clamp_slot_index(self.cfg.get("active_prompt_slot", 0))
                try:
                    pos = seq.index(curr_slot)
                except ValueError:
                    pos = -1
                    for i, slot_idx in enumerate(seq):
                        if slot_idx > curr_slot:
                            pos = i - 1
                            break
                    else:
                        pos = len(seq) - 1
                next_pos = pos + 1
                if next_pos < len(seq):
                    next_slot = seq[next_pos]
                    self.cfg["active_prompt_slot"] = next_slot
                    self.cfg["prompts_file"] = self.cfg["prompt_slots"][next_slot]["file"]
                    self.save_config()
                    self.relay_progress += 1
                    self.index = 0
                    self.root.after(0, self.on_reload)
                    if 0 <= pos < len(seq):
                        prev_name = self.cfg["prompt_slots"][seq[pos]]["name"]
                    else:
                        prev_name = "시작"
                    self.log(f"🏃 이어달리기 이동: {prev_name} → {self.cfg['prompt_slots'][next_slot]['name']}")
                    self.play_sound("success")
                    self.t_next = time.time() + 10
                    return
            self._show_completion_popup()
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
            # 작업 스레드 전용 세션 생성
            self._ensure_browser_session()
            self.actor.set_page(self.page)
            start_url = (self.cfg.get("start_url") or "").strip()
            input_selector = (self.cfg.get("input_selector") or "").strip()
            input_mode = self.run_input_mode if self.run_input_mode in ("typing", "paste", "mixed") else self.cfg.get("input_mode", "paste")

            if not (start_url and input_selector):
                raise RuntimeError("URL 또는 입력 selector 설정이 비어 있습니다.")

            # 현재 URL이 다르면 시작 페이지로 이동
            current_url = self.page.url or ""
            if (not current_url) or (start_url not in current_url):
                self.log(f"🌐 페이지 이동: {start_url}")
                self.page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
                self.actor.random_action_delay("페이지 로딩 안정화", 1.0, 3.0)

            prompt = self.prompts[self.index]
            asset_tag = None
            if self.cfg.get("asset_loop_enabled"):
                if 0 <= self.index < len(self.asset_loop_items):
                    asset_tag = self.asset_loop_items[self.index].get("tag")
                if not asset_tag:
                    m = re.match(r"^\s*([A-Za-z]+[0-9]+)\s*:", prompt)
                    if m:
                        asset_tag = m.group(1)
                if asset_tag:
                    # S반복 모드는 Step1/Step2(시작/에셋검색)를 먼저 수행해야 입력창이 활성화되는 경우가 있다.
                    self.update_status_label(f"🔁 에셋 준비 중... ({asset_tag})", self.color_info)
                    self._run_asset_loop_prestep(asset_tag)

            # 실행 시점 안정화: 입력창이 늦게 뜨는 경우를 대비해 충분히 대기
            input_probe = self._normalize_candidate_list(input_selector)
            for sel in self._input_candidates():
                if sel not in input_probe:
                    input_probe.append(sel)

            already_ready = self._wait_until_input_visible(input_probe, timeout_sec=12)
            if not already_ready:
                opened = self._try_open_new_project_if_needed(input_probe)
                if opened:
                    self.log("✅ 편집 화면 감지(입력창 확인)")
                else:
                    self.log("ℹ️ 새 프로젝트 자동 진입 실패 또는 불필요 - 현재 화면에서 계속 진행")
                # 새 프로젝트 클릭 후 렌더링 대기
                self._wait_until_input_visible(input_probe, timeout_sec=15)
            else:
                self.log("✅ 편집 화면 감지(입력창 확인)")

            print("Randomizing persona...")
            try:
                self.actor.randomize_persona()
                self.root.after(0, self._update_monitor_ui)
            except Exception as e:
                print(f"Persona update failed: {e}")
                self.log(f"⚠️ 페르소나 업데이트 오류: {e}")

            start_t = datetime.now()

            input_locator, resolved_input_selector = self._resolve_prompt_input_locator(
                input_selector,
                timeout_ms=2800,
            )
            if input_locator is None:
                raise RuntimeError("프롬프트 입력칸을 찾지 못했습니다(에셋 검색칸 제외). selector 자동찾기/테스트를 다시 실행해주세요.")

            # 자동으로 더 좋은 selector를 찾았으면 설정 동기화
            if resolved_input_selector and resolved_input_selector != input_selector:
                self.cfg["input_selector"] = resolved_input_selector
                self.root.after(0, lambda v=resolved_input_selector: self.input_selector_var.set(v))
            self.save_config()

            if self.cfg.get("afk_mode") and random.random() < 0.5:
                self.actor.random_behavior_routine()

            self.update_status_label("🧹 입력창 초기화 중...", "white")
            self.actor.clear_input_field(input_locator, label="입력창")

            print(f"Typing prompt: {prompt[:20]}...")
            self.update_status_label("✍️ 프롬프트 입력 중...", "white")
            self.actor.type_text(prompt, input_locator=input_locator, mode=input_mode)

            self.update_status_label("✅ 입력 완료!", self.color_success)
            self.update_status_label("📖 검토 중...", self.color_info)
            self.actor.read_prompt_pause(prompt)
            before_submit_text = self._read_input_text(input_locator)

            # 전체 흐름 불규칙성을 위해 가끔 예측 불가 행동 추가
            if random.random() < 0.35:
                self.actor.hesitate_on_submit()

            # 최종 제출
            print("Submitting...")
            self.update_status_label("🚀 제출 중...", self.color_accent)
            submitted = False
            attempt_notes = []
            self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] 제출 정책: Enter 전용")

            def _attempt_enter():
                try:
                    input_locator.click(timeout=1200)
                except Exception:
                    pass
                self.actor.random_action_delay("Enter 제출 전 딜레이", 0.3, 2.0)
                self.page.keyboard.press("Enter")
                self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] 제출 시도: Enter")
                ok = self._confirm_submission_started(input_locator, before_submit_text, timeout_sec=12)
                if not ok:
                    self.page.keyboard.press("Control+Enter")
                    self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] 제출 시도: Ctrl+Enter")
                    ok = self._confirm_submission_started(input_locator, before_submit_text, timeout_sec=8)
                attempt_notes.append(f"Enter={'OK' if ok else 'FAIL'}")
                return ok

            submitted = _attempt_enter()
            if not submitted:
                self.actor.random_action_delay("Enter 재시도 전 딜레이", 0.3, 1.4)
                submitted = _attempt_enter()
            if not submitted:
                try:
                    input_locator.focus()
                except Exception:
                    pass
                self.actor.random_action_delay("최종 Enter 재시도 전 딜레이", 0.3, 1.4)
                self.page.keyboard.press("Enter")
                self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] 제출 시도: Enter(최종)")
                submitted = self._confirm_submission_started(input_locator, before_submit_text, timeout_sec=8)
                attempt_notes.append(f"EnterFinal={'OK' if submitted else 'FAIL'}")

            if not submitted:
                raise RuntimeError(f"제출 확인 실패(생성 시작 신호 없음): {', '.join(attempt_notes)}")

            self._action_log(
                f"[{datetime.now().strftime('%H:%M:%S')}] 제출 검증 완료: {', '.join(attempt_notes) if attempt_notes else 'OK'}"
            )

            print("Task success")
            self.log(f"성공 #{self.index+1}")
            self.update_status_label("🎉 작업 완료!", self.color_success)
            self.play_sound("success")
            self.session_log.append({"index": self.index + 1, "prompt": prompt, "duration": f"{(datetime.now()-start_t).total_seconds():.1f}초"})
            self.actor.processed_count += 1
            self.index += 1
            self._action_log(f"[{datetime.now().strftime('%H:%M:%S')}] 프롬프트 #{self.index} 처리 완료")
        except PlaywrightTimeoutError as e:
            print(f"TIMEOUT in run_task: {e}")
            self.log(f"⏳ 요소 대기 시간 초과: {e}")
            self.update_status_label("⚠️ 요소 탐색 시간 초과", self.color_error)
            self.t_next = time.time() + 5
        except PlaywrightError as e:
            print(f"PLAYWRIGHT ERROR in run_task: {e}")
            self.log(f"❌ Playwright 오류: {e}")
            self.update_status_label("⚠️ 브라우저 오류 재시도...", self.color_error)
            self.t_next = time.time() + 5
            self._shutdown_browser()
        except Exception as e:
            print(f"ERROR in run_task: {e}")
            traceback.print_exc()
            self.log(f"❌ 오류: {e}")
            self.update_status_label("⚠️ 재시도 대기...", self.color_error)
            self.t_next = time.time() + 5
        finally:
            # 같은 worker 스레드에서 연속 작업을 수행하므로 브라우저 세션을 유지한다.
            # (중지/종료/치명 오류 시에만 세션 종료)
            self.root.after(0, self._update_progress_ui)
            self.is_processing = False

    def _run_download_task(self):
        print(f"[{datetime.now()}] Download task started")
        self.log("다운로드 작업 스레드 시작")
        if not self.download_items or self.download_index >= len(self.download_items):
            self.log("다운로드 대상 없음 또는 범위 초과")
            self.save_download_report()
            self._show_completion_popup()
            self.is_processing = False
            return

        start_url = (self.cfg.get("start_url") or "").strip()
        mode = self._download_mode()
        quality = self._download_quality(mode)
        tag = self.download_items[self.download_index]
        started_at = datetime.now()

        try:
            self._ensure_browser_session()
            self.actor.set_page(self.page)
            current_url = self.page.url or ""
            if (not current_url) or (start_url and start_url not in current_url):
                self.log(f"🌐 페이지 이동: {start_url}")
                self.page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
                self.actor.random_action_delay("페이지 로딩 안정화", 1.0, 2.0)

            self.update_status_label(f"⬇️ 다운로드 중... {tag}", self.color_info)
            wait_sec = int(self.cfg.get("download_wait_seconds", 60) or 60)
            result = self._run_single_download_flow(
                mode=mode,
                tag=tag,
                quality=quality,
                dry_run=False,
                wait_sec=wait_sec,
            )
            self._apply_download_used_selectors(mode, result.get("used", {}))
            self.save_config()
            file_name = result.get("file") or ""
            self.download_session_log.append({
                "tag": tag,
                "mode": mode,
                "quality": quality,
                "status": "success",
                "file_name": file_name,
                "started_at": started_at.isoformat(),
                "ended_at": datetime.now().isoformat(),
                "error": "",
            })
            self.log(f"✅ 다운로드 성공: {tag} ({mode}/{quality}) {file_name}")
            self.play_sound("success")
        except Exception as e:
            self.download_session_log.append({
                "tag": tag,
                "mode": mode,
                "quality": quality,
                "status": "failed",
                "file_name": "",
                "started_at": started_at.isoformat(),
                "ended_at": datetime.now().isoformat(),
                "error": str(e),
            })
            self.log(f"⚠️ 다운로드 실패: {tag} | 이유: {e}")
            self.update_status_label(f"⚠️ 실패 후 다음으로 이동: {tag}", self.color_error)
        finally:
            self.download_index += 1
            self.root.after(0, self._update_progress_ui)
            self.is_processing = False
            if self.download_index >= len(self.download_items):
                self._show_completion_popup()

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
            self._sync_relay_range_controls()
            self._sync_relay_selection_label()
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
        self._sync_relay_range_controls()
        self._sync_relay_selection_label()
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
        old_selected = self._normalize_relay_selected_slots(self.cfg.get("relay_selected_slots", []))
        self.cfg["prompt_slots"].pop(idx)
        
        # 인덱스 조정
        if self.cfg["active_prompt_slot"] >= len(self.cfg["prompt_slots"]):
            self.cfg["active_prompt_slot"] = len(self.cfg["prompt_slots"]) - 1
        elif self.cfg["active_prompt_slot"] == idx:
            # 현재 활성화된 슬롯을 삭제한 경우
            self.cfg["active_prompt_slot"] = 0

        for key in ("relay_start_slot", "relay_end_slot"):
            val = self.cfg.get(key)
            if val is not None and val >= len(self.cfg["prompt_slots"]):
                self.cfg[key] = len(self.cfg["prompt_slots"]) - 1

        new_selected = []
        for sidx in old_selected:
            if sidx == idx:
                continue
            if sidx > idx:
                new_selected.append(sidx - 1)
            else:
                new_selected.append(sidx)
        self.cfg["relay_selected_slots"] = self._normalize_relay_selected_slots(new_selected)
        if self.cfg.get("relay_use_selection") and not self.cfg["relay_selected_slots"]:
            self.cfg["relay_use_selection"] = False
            if hasattr(self, "relay_pick_var"):
                self.relay_pick_var.set(False)
            
        self.save_config()
        
        # UI 갱신
        slots = [s["name"] for s in self.cfg["prompt_slots"]]
        self.combo_slots["values"] = slots
        self.combo_slots.current(self.cfg["active_prompt_slot"])
        self._sync_relay_range_controls()
        self._sync_relay_selection_label()
        self.on_slot_change()
        self.log(f"🗑️ 슬롯 삭제됨: {slot_name}")
        messagebox.showinfo("성공", f"'{slot_name}' 슬롯이 목록에서 제거되었습니다.")

    def save_session_report(self):
        if not hasattr(self, "session_log"):
            return
        if self.session_report_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_report_path = self.logs_dir / f"session_report_{stamp}.json"
        try:
            payload = {
                "created_at": datetime.now().isoformat(),
                "started_at": getattr(self, "session_start_time", datetime.now()).isoformat() if hasattr(getattr(self, "session_start_time", None), "isoformat") else str(getattr(self, "session_start_time", "")),
                "prompt_file": self.cfg.get("prompts_file"),
                "total_processed": len(self.session_log),
                "entries": self.session_log,
            }
            self.session_report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.log(f"🧾 세션 리포트 저장: {self.session_report_path.name}")
        except Exception as e:
            self.log(f"⚠️ 세션 리포트 저장 실패: {e}")

    def save_download_report(self):
        if not hasattr(self, "download_session_log"):
            return
        if self.download_report_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.download_report_path = self.logs_dir / f"download_report_{stamp}.json"
        try:
            failed = [x for x in self.download_session_log if x.get("status") != "success"]
            payload = {
                "created_at": datetime.now().isoformat(),
                "started_at": getattr(self, "session_start_time", datetime.now()).isoformat() if hasattr(getattr(self, "session_start_time", None), "isoformat") else str(getattr(self, "session_start_time", "")),
                "mode": self._download_mode(),
                "video_quality": self._download_quality("video"),
                "image_quality": self._download_quality("image"),
                "total": len(self.download_session_log),
                "success": len(self.download_session_log) - len(failed),
                "failed": len(failed),
                "failed_tags": [x.get("tag", "") for x in failed],
                "entries": self.download_session_log,
            }
            self.download_report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.log(f"🧾 다운로드 리포트 저장: {self.download_report_path.name}")
        except Exception as e:
            self.log(f"⚠️ 다운로드 리포트 저장 실패: {e}")

if __name__ == "__main__":
    try: FlowVisionApp().root.mainloop()
    except Exception as e:
        with open("CRASH_LOG.txt", "w") as f: f.write(traceback.format_exc())
