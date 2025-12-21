import os
import sys

# [Critical Fix] Python 3.12+ distutils 삭제 대응 패치
# undetected_chromedriver가 distutils.version.LooseVersion을 찾을 때 속여서 넘깁니다.
try:
    import distutils.version
except ImportError:
    import types
    # 1. 가짜 distutils 모듈 생성
    distutils = types.ModuleType("distutils")
    distutils.version = types.ModuleType("distutils.version")
    sys.modules["distutils"] = distutils
    sys.modules["distutils.version"] = distutils.version
    
    # 2. LooseVersion 구현 (packaging 라이브러리 활용)
    try:
        from packaging.version import Version as LooseVersion
    except ImportError:
        class LooseVersion:
            def __init__(self, vstring):
                self.vstring = str(vstring)
            def __ge__(self, other):
                return self.vstring >= str(other)
            def __str__(self):
                return self.vstring
            
    distutils.version.LooseVersion = LooseVersion

import json
import subprocess
import time
import random
# [물리적 입력 도구]
import pyautogui
import pyperclip

from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

# [Selenium 복구]
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


APP_NAME = "Flow Veo3.1 Auto – Moonlight Studio"

DEFAULT_FLOW_URL = "https://labs.google/fx/ko/tools/flow"

DEFAULT_CONFIG = {
    "prompts_file": "flow_prompts.txt",
    "prompts_separator": "|||",
    "check_interval_seconds": 1800,
    "flow_base_url": DEFAULT_FLOW_URL,
    "flow_project_url": "",
    "chrome_profile_dir": "flow_chrome_profile",
    "chrome_devtools_port": 9555,
    "chrome_executable": "",
    "input_selectors": [],
    "submit_selectors": [],
    "reset_selectors": [],
    "auto_download_enabled": False,
    "download_dir": "flow_downloads",
    "download_wait_seconds": 300,
    "download_index": 1,
    "download_selectors": [],
    "download_selector_main": "",
    "download_selector_quality": "",
    # 프롬프트 슬롯/저장 관련
    "prompt_slots": [],
    "active_prompt_slot": 0,
    "prompt_save_dir": "",
}


def load_or_create_config(path: Path) -> dict:
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    for key, value in DEFAULT_CONFIG.items():
        cfg.setdefault(key, value)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def save_config(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prompts(prompts_path: Path, separator: str) -> list[str]:
    if not prompts_path.exists():
        prompts_path.write_text("", encoding="utf-8")
        return []
    raw = prompts_path.read_text(encoding="utf-8")
    parts = [part.strip() for part in raw.split(separator)]
    return [p for p in parts if p]


class FlowApp:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / "flow_config.json"
        self.cfg = load_or_create_config(self.cfg_path)
        
        # 다운로드 기록 로드 (중복 방지용)
        self.history_path = self.base / "flow_history.json"
        self.history = self.load_history()

        # 프롬프트 슬롯 초기화
        self._ensure_prompt_slots()

        # 다운로드 설정 정리(1단계/2단계 버튼 분리)
        self._normalize_download_config()

        # 현재 활성 슬롯의 파일을 실제 사용 파일로 반영
        self._apply_active_slot_to_prompts_file()

        self.prompts = load_prompts(self.base / self.cfg["prompts_file"], self.cfg["prompts_separator"])
        self.index = 0
        self.running = False
        self.t_next: float | None = None

        # 세션 통계 (한 번의 자동 작업)
        self.session_start_time: float | None = None
        self.session_total_prompts: int = 0
        self.session_success: int = 0
        self.session_fail: int = 0

        # 타이머 라벨 애니메이션 상태
        self._pulse_phase: int = 0

        # logging
        self.log_dir = self.base / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / f"flow_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        try:
            self.log_file = open(self.log_path, "a", encoding="utf-8")
        except Exception:
            self.log_file = None  # type: ignore[assignment]

        try:
            self.root = tk.Tk()
            self.root.title(APP_NAME)
            
            # --- 아이콘 설정 (Icon Setting) ---
            try:
                # 1. 현재 실행 위치에 icon.ico가 있는지 확인
                if os.path.exists("icon.ico"):
                    self.root.iconbitmap("icon.ico")
                # 2. 혹은 스크립트가 있는 폴더에 icon.ico가 있는지 확인
                elif os.path.exists(os.path.join(os.path.dirname(__file__), "icon.ico")):
                    self.root.iconbitmap(os.path.join(os.path.dirname(__file__), "icon.ico"))
                # 3. 상위 폴더(루트) 확인
                elif os.path.exists(os.path.join(os.path.dirname(__file__), "..", "icon.ico")):
                    self.root.iconbitmap(os.path.join(os.path.dirname(__file__), "..", "icon.ico"))
            except Exception:
                pass # 아이콘 로드 실패 시 무시 (기본 아이콘 사용)
            # -------------------------------

            self.root.geometry("980x740")
            self.root.minsize(900, 660)
            self.root.configure(bg="#050816")
        except Exception as exc:
            # Windows 전용 비상 알림 시도
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(0, f"Tk 초기화 오류:\n{exc}", APP_NAME, 0x10)
            except Exception:
                print(f"[FATAL] Tk 초기화 오류: {exc}")
            try:
                crash = self.log_dir / f"flow_crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                crash.write_text(f"Tk 초기화 오류: {exc}\n", encoding="utf-8")
            except Exception:
                pass
            raise

        self.interval_var = tk.IntVar(
            value=max(30, min(7200, int(self.cfg.get("check_interval_seconds", 1800))))
        )
        self.status_var = tk.StringVar(value="아직 아무 것도 시작하지 않았어요.")
        self.total_time_var = tk.StringVar(value="작업 완료까지 남은 시간: -")
        self.project_url_var = tk.StringVar(
            value=(
                str(self.cfg.get("flow_project_url") or "").strip()
                or str(self.cfg.get("flow_base_url") or DEFAULT_FLOW_URL)
            )
        )

        # Selenium state
        self.driver: webdriver.Chrome | None = None
        self.driver_ready = False

        self._apply_styles()
        self._build_ui()
        self.log(f"{APP_NAME} 시작 – 로그 파일: {self.log_path}")
        self._show()
        self._tick()

    # ------------------- history helpers -------------------
    def load_history(self) -> set[str]:
        if not self.history_path.exists():
            return set()
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
            return set(data)
        except Exception:
            return set()

    def save_history(self):
        try:
            self.history_path.write_text(json.dumps(list(self.history), indent=2), encoding="utf-8")
        except Exception:
            pass

    def _get_unique_id(self, driver: webdriver.Chrome, button_el) -> str | None:
        """
        다운로드 버튼 주변의 고유한 정보(이미지 주소 등)를 찾아서 ID로 반환합니다.
        못 찾으면 None을 반환합니다 (이 경우 중복 체크 불가).
        """
        try:
            # 버튼의 조상(컨테이너)을 타고 올라가며 img 태그 탐색
            # 보통 3~4단계 위에 카드 컨테이너가 있음
            parent = button_el
            for _ in range(5):
                parent = parent.find_element(By.XPATH, "..")
                try:
                    # 컨테이너 안의 이미지 태그 찾기
                    imgs = parent.find_elements(By.TAG_NAME, "img")
                    for img in imgs:
                        src = img.get_attribute("src")
                        if src and "http" in src:
                            # 썸네일 주소가 보통 고유함 (URL 파라미터 제외하고 저장해도 되지만, 전체가 안전)
                            return src
                except Exception:
                    pass
        except Exception:
            pass
        return None

    # ------------------- config helpers -------------------
    def _ensure_prompt_slots(self):
        slots = self.cfg.get("prompt_slots")
        if not isinstance(slots, list):
            slots = []

        base_file = str(self.cfg.get("prompts_file") or "flow_prompts.txt")

        # 슬롯이 전혀 없다면, 1번 슬롯에 현재 파일을 연결
        if not slots:
            slots = [
                {
                    "name": "기본 프롬프트",
                    "file": base_file,
                }
            ]

        # 10개까지 기본 슬롯 채우기
        while len(slots) < 10:
            idx = len(slots)
            slots.append(
                {
                    "name": f"슬롯 {idx + 1}",
                    "file": f"flow_prompts_slot{idx + 1}.txt",
                }
            )

        self.cfg["prompt_slots"] = slots[:10]

        idx = self.cfg.get("active_prompt_slot", 0)
        if not isinstance(idx, int) or not (0 <= idx < len(self.cfg["prompt_slots"])):
            idx = 0
        self.cfg["active_prompt_slot"] = idx
        save_config(self.cfg_path, self.cfg)

    def _apply_active_slot_to_prompts_file(self):
        slots = self.cfg.get("prompt_slots", [])
        idx = int(self.cfg.get("active_prompt_slot", 0))
        if isinstance(slots, list) and 0 <= idx < len(slots):
            slot = slots[idx]
            rel = str(slot.get("file") or "").strip() or str(self.cfg.get("prompts_file") or "flow_prompts.txt")
            slot["file"] = rel
            self.cfg["prompts_file"] = rel
            self.cfg["prompt_slots"][idx] = slot
            save_config(self.cfg_path, self.cfg)

    def _normalize_download_config(self):
        sels = list(self.cfg.get("download_selectors", []) or [])
        main = str(self.cfg.get("download_selector_main") or "").strip()
        quality = str(self.cfg.get("download_selector_quality") or "").strip()

        # 예전 설정을 그대로 가져오는 경우: 리스트의 앞 2개를 1/2단계로 사용
        if not main and sels:
            main = sels[0]
        if not quality and len(sels) > 1:
            quality = sels[1]

        self.cfg["download_selector_main"] = main
        self.cfg["download_selector_quality"] = quality
        # 리스트는 1단계 → 2단계 순으로 재구성
        new_list = [s for s in (main, quality) if s]
        self.cfg["download_selectors"] = new_list
        save_config(self.cfg_path, self.cfg)

    # ------------------- UI -------------------
    def _apply_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        # 기본 버튼 스타일
        style.configure(
            "TButton",
            font=("Pretendard", 11, "bold"),
            padding=(14, 8),
            relief="flat",
            borderwidth=0,
            background="#433B91",
            foreground="#F7F4FF",
        )
        style.map(
            "TButton",
            background=[("active", "#5C4EE5"), ("disabled", "#2F2A54")],
            foreground=[("disabled", "#7F76B0")],
        )

        # 중요 액션(시작 버튼 등)
        style.configure(
            "Primary.TButton",
            font=("Pretendard", 12, "bold"),
            padding=(18, 10),
            background="#5C4EE5",
            foreground="#FFFFFF",
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#7B66FF"), ("disabled", "#2F2A54")],
            foreground=[("disabled", "#AFA8D9")],
        )

        # 위험/정지 버튼
        style.configure(
            "Danger.TButton",
            font=("Pretendard", 12, "bold"),
            padding=(18, 10),
            background="#F25F5C",
            foreground="#FFFFFF",
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#FF8A80"), ("disabled", "#4B1F24")],
            foreground=[("disabled", "#F4C7C7")],
        )

        # 보조 액션(다운로드/슬롯 관리 등)
        style.configure(
            "Accent.TButton",
            font=("Pretendard", 10, "bold"),
            padding=(10, 6),
            background="#2D9CDB",
            foreground="#F5FBFF",
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#56CCF2"), ("disabled", "#1B4F72")],
            foreground=[("disabled", "#AFCDEB")],
        )

        # 서브 버튼(네비게이션 등)
        style.configure(
            "Ghost.TButton",
            font=("Pretendard", 10, "bold"),
            padding=(10, 6),
            background="#151527",
            foreground="#DDD6FF",
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#23234A"), ("disabled", "#090914")],
            foreground=[("disabled", "#7770A0")],
        )

        style.configure(
            "TCheckbutton",
            font=("Pretendard", 10, "bold"),
            background="#050816",
            foreground="#F7F4FF",
        )
        style.map(
            "TCheckbutton",
            background=[("active", "#2F2A54")],
            foreground=[("disabled", "#7F76B0")],
        )

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#080A1A")
        header.pack(fill="x")

        title = tk.Label(
            header,
            text="🌙  Flow Veo3.1 Auto – Moonlight Studio",
            font=("Pretendard", 24, "bold"),
            fg="#F8F4FF",
            bg="#080A1A",
        )
        title.pack(pady=(18, 4))

        subtitle = tk.Label(
            header,
            text="하루의 리듬에 맞춰 조용히 영상 프롬프트를 흘려보내는 작은 스튜디오",
            font=("Pretendard", 12),
            fg="#B8B2D6",
            bg="#080A1A",
        )
        subtitle.pack(pady=(0, 10))

        body = tk.Frame(self.root, bg="#050816")
        body.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        # Project URL line
        url_frame = tk.Frame(body, bg="#050816")
        url_frame.pack(fill="x", pady=(4, 10))

        tk.Label(
            url_frame,
            text="Flow 프로젝트 주소",
            font=("Pretendard", 11, "bold"),
            fg="#DCD5FF",
            bg="#050816",
        ).pack(side="left", padx=(0, 8))

        self.url_entry = tk.Entry(
            url_frame,
            textvariable=self.project_url_var,
            font=("Consolas", 10),
            fg="#FDF7FF",
            bg="#0B0614",
            insertbackground="#FDF7FF",
            relief="flat",
        )
        self.url_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(url_frame, text="💾 저장", command=self.on_save_project_url).pack(
            side="left", padx=(8, 4)
        )
        ttk.Button(url_frame, text="🌐 Flow 열기", command=self.on_open_site).pack(
            side="left", padx=(4, 0)
        )

        # Prompt / capture controls
        controls = tk.Frame(body, bg="#050816")
        controls.pack(fill="x", pady=(4, 8))

        # 1줄: 프롬프트 파일 관련 + 슬롯 관리
        ttk.Button(controls, text="📄 프롬프트 열기", style="Ghost.TButton", command=self.on_open_prompts).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        ttk.Button(controls, text="🔄 다시 불러오기", style="Ghost.TButton", command=self.on_reload).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )
        ttk.Button(controls, text="💾 프롬프트 저장", style="Accent.TButton", command=self.on_save_prompts).grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )
        ttk.Button(controls, text="⭐ 프롬프트 슬롯 관리", style="Accent.TButton", command=self.on_manage_slots).grid(
            row=0, column=3, padx=4, pady=4, sticky="ew"
        )

        # 2줄: 네비게이션 + 타겟 지정
        ttk.Button(controls, text="⏮ 맨 처음", style="Ghost.TButton", command=self.on_first).grid(
            row=1, column=0, padx=4, pady=4, sticky="ew"
        )
        ttk.Button(controls, text="◀ 이전", style="Ghost.TButton", command=self.on_prev).grid(
            row=1, column=1, padx=4, pady=4, sticky="ew"
        )
        ttk.Button(controls, text="다음 ▶", style="Ghost.TButton", command=self.on_next).grid(
            row=1, column=2, padx=4, pady=4, sticky="ew"
        )
        ttk.Button(controls, text="맨 마지막 ⏭", style="Ghost.TButton", command=self.on_last).grid(
            row=1, column=3, padx=4, pady=4, sticky="ew"
        )
        ttk.Button(controls, text="🖊️ 입력칸 지정", style="Ghost.TButton", command=self.on_capture_input).grid(
            row=1, column=4, padx=4, pady=4, sticky="ew"
        )
        ttk.Button(controls, text="🌱 생성 버튼 지정", style="Ghost.TButton", command=self.on_capture_submit).grid(
            row=1, column=5, padx=4, pady=4, sticky="ew"
        )

        for col in range(6):
            controls.grid_columnconfigure(col, weight=1)

        # Interval + toggles
        timer_frame = tk.Frame(body, bg="#050816")
        timer_frame.pack(fill="x", pady=(4, 6))

        tk.Label(
            timer_frame,
            text="⏱ 간격(초)",
            font=("Pretendard", 11, "bold"),
            fg="#DCD5FF",
            bg="#050816",
        ).grid(row=0, column=0, padx=(0, 8))

        spin = ttk.Spinbox(
            timer_frame,
            from_=30,
            to=7200,
            increment=30,
            width=8,
            textvariable=self.interval_var,
            justify="center",
            command=self._on_interval,
        )
        spin.grid(row=0, column=1, padx=(0, 12))
        spin.bind("<Return>", lambda e: self._on_interval())

        tk.Label(
            timer_frame,
            text="30초 – 2시간 사이, 오늘의 리듬에 맞게 조절해 주세요.",
            font=("Pretendard", 9),
            fg="#AFA8D9",
            bg="#050816",
        ).grid(row=0, column=2, sticky="w")

        # Start / stop row
        run_frame = tk.Frame(body, bg="#050816")
        run_frame.pack(fill="x", pady=(4, 10))

        ttk.Button(run_frame, text="🌙 조용히 시작", style="Primary.TButton", command=self.on_start).grid(
            row=0, column=0, padx=6, pady=4, sticky="ew"
        )
        ttk.Button(run_frame, text="⚡ 이번 프롬프트만", style="Accent.TButton", command=self.on_now).grid(
            row=0, column=1, padx=6, pady=4, sticky="ew"
        )
        ttk.Button(run_frame, text="🛑 멈추기", style="Danger.TButton", command=self.on_stop).grid(
            row=0, column=2, padx=6, pady=4, sticky="ew"
        )

        self.auto_next_var = tk.BooleanVar(value=True)
        # 자동 다운로드 기본값 해제 (사용자 요청: 생성과 다운로드 분리)
        self.auto_dl_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            run_frame,
            text="⏭ 자동 다음 프롬프트",
            variable=self.auto_next_var,
        ).grid(row=0, column=3, padx=(6, 6), pady=4, sticky="w")

        # Download controls
        dl_frame = tk.Frame(body, bg="#050816")
        dl_frame.pack(fill="x", pady=(0, 6))

        ttk.Checkbutton(
            dl_frame,
            text="🎞 자동 다운로드",
            variable=self.auto_dl_var,
            command=self.on_toggle_auto_download,
        ).grid(row=0, column=0, padx=(0, 6), pady=2, sticky="w")

        ttk.Button(dl_frame, text="💾 지금 다운로드(1개)", command=self.on_download_now).grid(
            row=0, column=1, padx=6, pady=2, sticky="w"
        )
        ttk.Button(dl_frame, text="📁 다운로드 폴더", command=self.on_pick_download_dir).grid(
            row=0, column=2, padx=6, pady=2, sticky="w"
        )
        
        # 일괄 다운로드 버튼 추가
        ttk.Button(
            dl_frame, 
            text="📥 기존 영상 싹쓸이 다운로드", 
            style="Accent.TButton",
            command=self.on_start_bulk_download
        ).grid(row=0, column=3, padx=6, pady=2, sticky="w")

        ttk.Button(
            dl_frame,
            text="🎯 1단계 버튼 지정",
            style="Ghost.TButton",
            command=self.on_capture_download_step1,
        ).grid(row=1, column=0, columnspan=2, padx=6, pady=2, sticky="ew")
        ttk.Button(
            dl_frame,
            text="🎯 2단계 버튼 지정",
            style="Ghost.TButton",
            command=self.on_capture_download_step2,
        ).grid(row=1, column=2, columnspan=2, padx=6, pady=2, sticky="ew")

        for col in range(4):
            dl_frame.grid_columnconfigure(col, weight=1)

        # Info row
        info = tk.Frame(body, bg="#050816")
        info.pack(fill="x", pady=(0, 4))

        self.pos_label = tk.Label(
            info,
            text="0 / 0",
            font=("Pretendard", 10, "bold"),
            fg="#C7B8FF",
            bg="#050816",
        )
        self.pos_label.pack(side="left", padx=(0, 8))

        self.total_time_label = tk.Label(
            info,
            textvariable=self.total_time_var,
            font=("Pretendard", 10, "bold"),
            fg="#FFD166",
            bg="#151527",
            padx=10,
            pady=3,
        )
        self.total_time_label.pack(side="left", padx=(0, 8))

        self.countdown_label = tk.Label(
            info,
            textvariable=self.status_var,
            font=("Pretendard", 11, "bold"),
            fg="#F8F9FF",
            bg="#151527",
            padx=10,
            pady=3,
        )
        self.countdown_label.pack(side="right")

        # Splitter for script viewer / log – user can drag the bar
        paned = tk.PanedWindow(
            body,
            orient="vertical",
            sashrelief="flat",
            sashwidth=4,
            bg="#050816",
            bd=0,
            relief="flat",
        )
        paned.pack(fill="both", expand=True, pady=(4, 4))

        top_frame = tk.Frame(paned, bg="#050816")
        bottom_frame = tk.Frame(paned, bg="#050816")
        paned.add(top_frame, minsize=120)   # 최소 높이
        paned.add(bottom_frame, minsize=80) # 최소 높이
        try:
            paned.sash_place(0, 0, int(self.root.winfo_height() * 0.55))
        except Exception:
            pass

        # Current prompt viewer (read-only script)
        self.text = ScrolledText(
            top_frame,
            wrap="word",
            bg="#0B0614",
            fg="#FDF7FF",
            insertbackground="#FDF7FF",
            relief="flat",
            font=("Consolas", 12),
        )
        self.text.pack(fill="both", expand=True, pady=(2, 6))
        self.text.configure(state="disabled")

        # Live log
        tk.Label(
            bottom_frame,
            text="🌌 오늘의 작은 기록들",
            font=("Pretendard", 10, "bold"),
            fg="#C7B8FF",
            bg="#050816",
        ).pack(anchor="w", pady=(0, 2))

        self.log_text = ScrolledText(
            bottom_frame,
            height=6,
            bg="#0B0614",
            fg="#FDF7FF",
            insertbackground="#FDF7FF",
            relief="flat",
            font=("Consolas", 10),
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    # ------------------- logging helpers -------------------
    def log(self, message: str):
        line = f"{datetime.now().strftime('%H:%M:%S')} | {message}"
        try:
            if self.log_file:
                self.log_file.write(line + "\n")
                self.log_file.flush()
        except Exception:
            pass
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass

    # ------------------- small UI callbacks -------------------
    def _on_interval(self):
        try:
            v = int(self.interval_var.get() or 1800)
        except Exception:
            v = int(self.cfg.get("check_interval_seconds", 1800))
        v = max(30, min(7200, v))
        self.interval_var.set(v)
        self.cfg["check_interval_seconds"] = v
        save_config(self.cfg_path, self.cfg)
        if self.running:
            self.t_next = time.time() + v
        mins, secs = divmod(v, 60)
        if mins:
            self.status_var.set(f"간격 {mins}분 {secs:02d}초로 저장했어요.")
        else:
            self.status_var.set(f"간격 {secs}초로 저장했어요.")
        # 간격 변경 시 전체 남은 시간도 갱신
        self._update_total_time_label()

    def on_save_project_url(self):
        url = self.project_url_var.get().strip()
        self.cfg["flow_project_url"] = url
        save_config(self.cfg_path, self.cfg)
        if url:
            self.status_var.set("프로젝트 주소를 저장했어요.")
            self.log(f"프로젝트 URL 설정: {url}")
        else:
            self.status_var.set("프로젝트 주소를 비우고 기본 Flow 메인으로 돌아갑니다.")
            self.log("프로젝트 URL 삭제 – 기본 Flow 메인 사용")

    def on_open_prompts(self):
        p = self.base / self.cfg["prompts_file"]
        try:
            if os.name == "nt":
                os.startfile(str(p))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"프롬프트 파일을 열 수 없습니다: {exc}")

    def on_save_prompts(self):
        """현재 프롬프트 파일을 날짜/시간 + 슬롯 이름으로 백업 저장."""
        p = self.base / self.cfg["prompts_file"]
        if not p.exists():
            messagebox.showwarning(
                APP_NAME,
                "현재 프롬프트 파일이 아직 생성되지 않았어요.\n먼저 '프롬프트 열기'로 내용을 만들어 주세요.",
            )
            return

        if not messagebox.askyesno(
            APP_NAME,
            "현재 프롬프트 목록을 별도 파일로 저장하시겠어요?\n"
            "완료한 작업을 기록하거나, 나중에 다시 참고할 때 사용할 수 있습니다.",
        ):
            return

        slots = self.cfg.get("prompt_slots", [])
        idx = int(self.cfg.get("active_prompt_slot", 0))
        base_name = ""
        if isinstance(slots, list) and 0 <= idx < len(slots):
            base_name = str(slots[idx].get("name") or "").strip()
        if not base_name:
            base_name = Path(self.cfg["prompts_file"]).stem

        # 예: 251126_프롬프트이름.txt (yyMMdd_HHmm 형식)
        ts = datetime.now().strftime("%y%m%d_%H%M")
        initial = f"{ts}_{base_name}.txt"
        initial_dir = self.cfg.get("prompt_save_dir") or str(self.base)

        filename = filedialog.asksaveasfilename(
            title="프롬프트 저장",
            defaultextension=".txt",
            initialdir=initial_dir,
            initialfile=initial,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            text = p.read_text(encoding="utf-8")
            Path(filename).write_text(text, encoding="utf-8")
            self.cfg["prompt_save_dir"] = str(Path(filename).parent)
            save_config(self.cfg_path, self.cfg)
            self.status_var.set(f"프롬프트를 저장했어요: {filename}")
            self.log(f"프롬프트 백업 저장: {filename}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"프롬프트 저장에 실패했습니다: {exc}")
            self.log(f"프롬프트 저장 오류: {exc}")

    def on_reload(self):
        current = (
            self.prompts[self.index]
            if self.prompts and 0 <= self.index < len(self.prompts)
            else None
        )
        self.prompts = load_prompts(
            self.base / self.cfg["prompts_file"], self.cfg["prompts_separator"]
        )
        if not self.prompts:
            self.index = 0
        else:
            if current in self.prompts:
                self.index = self.prompts.index(current)
            else:
                self.index = min(self.index, len(self.prompts) - 1)
        self._show()
        self.status_var.set("프롬프트를 다시 불러왔어요.")
        self.log(f"프롬프트 로드: 총 {len(self.prompts)}개")

    def on_first(self):
        if not self.prompts:
            return
        if self.index != 0:
            self.index = 0
            self._show()
            if self.running:
                self.t_next = time.time() + int(self.interval_var.get())
            self.log(f"맨 처음 프롬프트로 이동: {self.index + 1}/{len(self.prompts)}")

    def on_prev(self):
        if not self.prompts:
            return
        if self.index > 0:
            self.index -= 1
            self._show()
            if self.running:
                self.t_next = time.time() + int(self.interval_var.get())
            self.log(f"이전 프롬프트로 이동: {self.index + 1}/{len(self.prompts)}")

    def on_next(self):
        if not self.prompts:
            return
        if self.index < len(self.prompts) - 1:
            self.index += 1
            self._show()
            if self.running:
                self.t_next = time.time() + int(self.interval_var.get())
            self.log(f"다음 프롬프트로 이동: {self.index + 1}/{len(self.prompts)}")

    def on_last(self):
        if not self.prompts:
            return
        last_idx = len(self.prompts) - 1
        if self.index != last_idx:
            self.index = last_idx
            self._show()
            if self.running:
                self.t_next = time.time() + int(self.interval_var.get())
            self.log(f"맨 마지막 프롬프트로 이동: {self.index + 1}/{len(self.prompts)}")

    def on_manage_slots(self):
        """최대 10개까지 프롬프트 슬롯 이름/선택 관리."""
        slots = self.cfg.get("prompt_slots", [])
        active = int(self.cfg.get("active_prompt_slot", 0))

        win = tk.Toplevel(self.root)
        win.title("프롬프트 슬롯 관리")
        win.configure(bg="#050816")
        win.geometry("420x360")

        tk.Label(
            win,
            text="📁 프롬프트 슬롯 (최대 10개)",
            font=("Pretendard", 12, "bold"),
            fg="#F5F3FF",
            bg="#050816",
        ).pack(pady=(12, 4))

        list_frame = tk.Frame(win, bg="#050816")
        list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        lb = tk.Listbox(
            list_frame,
            bg="#0B0614",
            fg="#FDF7FF",
            font=("Pretendard", 10),
            selectbackground="#5C4EE5",
            selectforeground="#FFFFFF",
            activestyle="none",
        )
        lb.pack(fill="both", expand=True, side="left")

        sb = tk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.configure(yscrollcommand=sb.set)

        def refresh_list():
            lb.delete(0, "end")
            cur_active = int(self.cfg.get("active_prompt_slot", 0))
            current_slots = self.cfg.get("prompt_slots", [])
            for i, slot in enumerate(current_slots):
                name = str(slot.get("name") or f"슬롯 {i + 1}")
                mark = "★" if i == cur_active else " "
                file_name = str(slot.get("file") or "")
                lb.insert("end", f"{mark} {i + 1}. {name}   ({file_name})")

        refresh_list()
        if 0 <= active < lb.size():
            lb.selection_set(active)
            lb.see(active)

        btn_frame = tk.Frame(win, bg="#050816")
        btn_frame.pack(fill="x", pady=(4, 10))

        def on_choose():
            sel = lb.curselection()
            if not sel:
                return
            idx_sel = int(sel[0])
            slots_local = self.cfg.get("prompt_slots", [])
            if not (0 <= idx_sel < len(slots_local)):
                return
            slot = slots_local[idx_sel]
            rel = str(slot.get("file") or "").strip() or f"flow_prompts_slot{idx_sel + 1}.txt"
            slot["file"] = rel
            self.cfg["prompt_slots"][idx_sel] = slot
            self.cfg["active_prompt_slot"] = idx_sel
            self.cfg["prompts_file"] = rel
            save_config(self.cfg_path, self.cfg)

            self.prompts = load_prompts(self.base / rel, self.cfg["prompts_separator"])
            self.index = 0
            self._show()

            self.status_var.set(f"슬롯 {idx_sel + 1} 선택: {slot.get('name') or f'슬롯 {idx_sel + 1}'}")
            self.log(
                f"프롬프트 슬롯 변경: {idx_sel + 1}번 – 이름={slot.get('name')} / 파일={rel} / 총 {len(self.prompts)}개"
            )

            refresh_list()

        def on_rename():
            sel = lb.curselection()
            if not sel:
                return
            idx_sel = int(sel[0])
            slots_local = self.cfg.get("prompt_slots", [])
            if not (0 <= idx_sel < len(slots_local)):
                return
            slot = slots_local[idx_sel]
            current_name = str(slot.get("name") or f"슬롯 {idx_sel + 1}")
            new_name = simpledialog.askstring(
                APP_NAME,
                f"{idx_sel + 1}번 슬롯 이름을 입력해 주세요.",
                initialvalue=current_name,
                parent=win,
            )
            if not new_name:
                return
            slot["name"] = new_name.strip()
            self.cfg["prompt_slots"][idx_sel] = slot
            save_config(self.cfg_path, self.cfg)
            self.log(f"슬롯 이름 변경: {idx_sel + 1} -> {slot['name']}")
            refresh_list()

        ttk.Button(btn_frame, text="이 슬롯 사용", style="Accent.TButton", command=on_choose).pack(
            side="left", padx=4
        )
        ttk.Button(btn_frame, text="이름 변경", style="Ghost.TButton", command=on_rename).pack(
            side="left", padx=4
        )
        ttk.Button(btn_frame, text="닫기", style="Ghost.TButton", command=win.destroy).pack(
            side="right", padx=4
        )

    def on_open_site(self):
        try:
            d = self._get_driver()
        except Exception as exc:
            self.status_var.set("Chrome 연결에 실패했어요.")
            self.log(f"Chrome 연결 실패: {exc}")
            messagebox.showerror(APP_NAME, f"Chrome 연결 실패: {exc}")
            return
        try:
            self._navigate(d)
            self.status_var.set("Flow 페이지를 열었어요.")
            self.log("Flow 페이지 열기 완료")
        except Exception as exc:
            self.status_var.set("페이지 이동에 실패했어요.")
            self.log(f"페이지 이동 실패: {exc}")

    def on_start(self):
        if not self.prompts:
            messagebox.showwarning(APP_NAME, "프롬프트가 비어 있습니다.\nflow_prompts.txt 파일을 먼저 채워 주세요.")
            return
        # 새 자동 작업 세션 초기화
        self.session_start_time = time.time()
        self.session_total_prompts = len(self.prompts) - self.index
        self.session_success = 0
        self.session_fail = 0

        self.running = True
        ok = self._auto_submit_current()
        
        # 랜덤 변동 추가 (-5초 ~ +30초)
        base_iv = int(self.interval_var.get())
        variation = random.randint(-5, 30)
        final_iv = max(10, base_iv + variation) # 최소 10초 보장
        self.t_next = time.time() + final_iv
        
        self.status_var.set(
            f"자동 시작됨 (다음: {final_iv}초 후)"
            if ok
            else "시작했으나 전송 실패"
        )
        self.log(
            "자동 제출 시작 – 즉시 1회 실행 성공"
            if ok
            else "자동 제출 시작 – 즉시 1회 실행 실패"
        )
        if ok and self.auto_next_var.get():
            if self.index < len(self.prompts) - 1:
                self.index += 1
                self._show()

    def on_stop(self):
        was_running = self.running
        self.running = False
        self.t_next = None
        if was_running and self.session_start_time is not None:
            # 중간에 수동으로 멈춘 경우 요약
            self._log_session_summary(completed=False)
        else:
            self.status_var.set("지금은 멈춰 두었어요.")
            self.log("정지됨")

    def on_now(self):
        ok = self._auto_submit_current()
        self.status_var.set("이번 프롬프트를 보냈어요." if ok else "이번 프롬프트 전송에 실패했어요.")
        self.log("즉시 제출 완료" if ok else "즉시 제출 실패")
        if ok and self.auto_next_var.get():
            if self.index < len(self.prompts) - 1:
                self.index += 1
                self._show()

    def _show(self):
        total = len(self.prompts)
        pos = self.index + 1 if total else 0
        self.pos_label.config(text=f"{pos} / {total}")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        if total:
            self.text.insert("1.0", self.prompts[self.index])
        else:
            self.text.insert("1.0", "flow_prompts.txt 파일에 프롬프트를 `|||` 로 나누어 적어 주세요.")
        self.text.configure(state="disabled")

    def _tick(self):
        if self.running and self.t_next:
            remain = int(self.t_next - time.time())
            if remain <= 0:
                ok = self._auto_submit_current()
                
                # 랜덤 변동 추가 (-5초 ~ +30초)
                base_iv = int(self.interval_var.get())
                variation = random.randint(-5, 30)
                final_iv = max(10, base_iv + variation)
                self.t_next = time.time() + final_iv
                
                if ok and self.auto_next_var.get():
                    if self.index < len(self.prompts) - 1:
                        self.index += 1
                        self._show()
                    else:
                        # 모든 프롬프트 완료
                        self.running = False
                        self.t_next = None
                        self._log_session_summary(completed=True)
                        self.root.after(200, self._tick)
                        return
                self.status_var.set("자동 제출 완료" if ok else "자동 제출 실패")
            else:
                remain = max(0, remain)
                mins, secs = divmod(remain, 60)
                if mins:
                    self.status_var.set(f"다음 프롬프트까지 {mins}분 {secs:02d}초")
                else:
                    self.status_var.set(f"다음 프롬프트까지 {secs}초")
                self._update_total_time_label(remain)
                self._update_timer_pulse(remain)
        else:
            # 멈춰 있을 때는 타이머 스타일만 초기화
            self._reset_timer_pulse()
        self.root.after(1000, self._tick)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.mainloop()

    # ------------------- Chrome / Selenium helpers -------------------
    def _get_devtools_port(self) -> int:
        try:
            return int(self.cfg.get("chrome_devtools_port", 9555))
        except Exception:
            return 9555

    # ------------------- download helpers -------------------
    def _get_download_dir(self) -> Path:
        d = Path(self.cfg.get("download_dir", str(self.base / "flow_downloads")))
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _resolve_chrome_path(self) -> str:
        override = str(self.cfg.get("chrome_executable", "")).strip()
        candidates: list[Path] = []
        if override:
            candidates.append(Path(override))
        
        # Windows 크롬 기본 경로 총망라
        candidates += [
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        ]
        
        for p in candidates:
            if p and p.exists():
                return str(p)
                
        # 못 찾으면 에러 메시지 띄움
        messagebox.showerror("오류", "크롬 브라우저를 찾을 수 없습니다.\n구글 크롬이 설치되어 있는지 확인해주세요.")
        raise FileNotFoundError("Chrome 실행 파일을 찾지 못했습니다.")

    def _is_debug_port_alive(self, port: int) -> bool:
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1):
                return True
        except Exception:
            return False

    def _ensure_chrome_ready(self, port: int) -> bool:
        if self._is_debug_port_alive(port):
            self.log(f"Chrome 디버그 포트 {port} 감지됨 (이미 실행 중)")
            return True
            
        chrome = self._resolve_chrome_path()
        profile = self.base / self.cfg.get("chrome_profile_dir", "flow_human_profile")
        profile.mkdir(parents=True, exist_ok=True)
        
        # [강력 실행] 윈도우 start 명령어로 강제 실행
        # 긴 명령어 문자열 생성
        args = [
            f'"{chrome}"',
            f"--remote-debugging-port={port}",
            f'--user-data-dir="{profile}"',
            "--profile-directory=Default",
            "--no-first-run",
            "--disable-popup-blocking",
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars"
        ]
        cmd_str = " ".join(args)
        
        try:
            self.log("🚀 Chrome 강제 실행 시도 (Shell Start)...")
            # shell=True와 start 명령어로 윈도우가 직접 창을 띄우게 함
            subprocess.Popen(f'start "" {cmd_str}', shell=True)
        except Exception as e:
            self.log(f"Chrome 실행 실패: {e}")
            messagebox.showerror("실패", "크롬 실행 명령을 보냈으나 실패했습니다.")
            return False
            
        # 포트가 열릴 때까지 대기
        self.log("크롬 창이 뜨기를 기다리는 중...")
        for i in range(30):
            if self._is_debug_port_alive(port):
                self.log(f"✅ Chrome 준비 완료! ({i+1}초 소요)")
                return True
            time.sleep(1)
            
        self.log("Chrome 실행 대기 시간 초과")
        messagebox.showwarning("확인 필요", "크롬 실행 명령은 보냈으나 연결되지 않았습니다.\n혹시 크롬 창이 떴다면 닫지 말고 다시 실행해보세요.")
        return False

    def _get_driver(self):
        if self.driver:
            try:
                _ = self.driver.current_url
                return self.driver
            except Exception:
                self.driver = None
                self.driver_ready = False

        port = self._get_devtools_port()
        if not self._ensure_chrome_ready(port):
            raise RuntimeError("Chrome을 실행할 수 없습니다.")

        # 이미 실행된 크롬에 연결
        options = ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        
        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(3)
        self.driver_ready = True
        
        self.log("Chrome 세션 연결 성공")
        return self.driver


    def _get_target_url(self) -> str:
        url = str(self.cfg.get("flow_project_url") or "").strip()
        if not url:
            url = str(self.cfg.get("flow_base_url") or DEFAULT_FLOW_URL)
        return url

    def _navigate(self, d: webdriver.Chrome):
        url = self._get_target_url()
        try:
            current = d.current_url or ""
        except Exception:
            current = ""
        try:
            if url not in current:
                d.get(url)
        except Exception:
            d.get(url)

    def _find_input_by_config(self, d: webdriver.Chrome):
        selectors = list(self.cfg.get("input_selectors", []))
        for s in selectors:
            try:
                for el in d.find_elements(By.CSS_SELECTOR, s):
                    try:
                        if el.is_displayed() and el.size.get("height", 0) >= 30:
                            return el
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    def _wait_input(self, d: webdriver.Chrome, timeout: int = 90):
        # 우선 사용자가 직접 지정한 입력칸부터 시도
        el = self._find_input_by_config(d)
        if el is not None:
            return el

        selectors = ["textarea", "div[contenteditable='true']", "div[role='textbox']"]

        def finder(_d: webdriver.Chrome):
            for s in selectors:
                els = _d.find_elements(By.CSS_SELECTOR, s)
                for el2 in els:
                    try:
                        if el2.is_displayed() and el2.size.get("height", 0) >= 30:
                            return el2
                    except Exception:
                        continue
            return False

        try:
            el = WebDriverWait(d, timeout, poll_frequency=1).until(finder)
            return el
        except Exception:
            return None

    # ------------------- automation core -------------------
    def _sanitize_bmp(self, s: str) -> str:
        # Remove non-BMP characters (e.g., some emoji) to avoid ChromeDriver errors
        return "".join(ch for ch in s if ord(ch) <= 0xFFFF)

    def _read_element_text(self, d: webdriver.Chrome, el) -> str:
        """Return best-effort textual content of an input/textarea/editor element."""
        try:
            value = d.execute_script(
                """
                var el = arguments[0];
                if (!el) return '';
                var v = (el.value || el.innerText || el.textContent || '');
                return String(v);
                """,
                el,
            )
            if isinstance(value, str):
                return value
        except Exception:
            pass
        try:
            return (el.text or "")  # type: ignore[return-value]
        except Exception:
            return ""

    def _extract_flow_prompt(self, raw: str) -> str:
        """Flow 전용: '장면', '영상 프롬프트:', '장면설명:' 포맷을 사용하면
        실제 Flow에는 영상 프롬프트 + 장면설명을 하나의 문장으로 합쳐 넣습니다.
        그런 키워드가 없으면 전체 문자열을 그대로 사용합니다.
        """
        text = raw.strip()
        if not text:
            return text

        # 줄 단위로 정리
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return ""

        # 첫 줄이 '장면 7' 같은 제목이면 버림
        if lines[0].startswith("장면 "):
            lines = lines[1:]

        joined = "\n".join(lines)

        # '영상 프롬프트:' / '장면설명:' 패턴 찾기
        marker = "영상 프롬프트:"
        idx = joined.find(marker)
        if idx == -1:
            # 키워드가 없다면 전체 프롬프트 그대로 사용
            return text

        tail = joined[idx + len(marker) :].strip()
        desc_marker = "장면설명:"
        desc_idx = tail.find(desc_marker)

        if desc_idx == -1:
            # 장면설명이 없으면 영상 프롬프트만
            video = tail.strip()
            return video or text

        # 영상 프롬프트 / 장면설명 각각 분리
        video = tail[:desc_idx].strip()
        desc = tail[desc_idx + len(desc_marker) :].strip()

        if not video and not desc:
            return text

        # 줄바꿈 없이 하나의 텍스트로 합치기
        if video and desc:
            return f"{video}  {desc}"
        return video or desc or text

    def _copy_to_clipboard(self, text: str):
        """Copy text to system clipboard via Tk root, mimicking Ctrl+C."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
            self.log(f"클립보드에 프롬프트 복사({len(text)}자)")
        except Exception as exc:
            self.log(f"클립보드 복사 실패: {exc}")

    # ------------------- timer helpers -------------------
    def _update_total_time_label(self, remain_next: int | None = None):
        """전체 작업 완료까지 남은 시간을 계산해 라벨에 표시."""
        if not self.running or self.t_next is None or self.session_start_time is None:
            self.total_time_var.set("작업 완료까지 남은 시간: -")
            return

        try:
            interval = int(self.interval_var.get() or self.cfg.get("check_interval_seconds", 1800))
        except Exception:
            interval = int(self.cfg.get("check_interval_seconds", 1800))

        done = self.session_success + self.session_fail
        remaining_prompts = max(0, self.session_total_prompts - done)
        if remaining_prompts <= 0:
            self.total_time_var.set("작업 완료까지 남은 시간: 0초")
            return

        if remain_next is None:
            remain_next = max(0, int(self.t_next - time.time()))
        else:
            remain_next = max(0, remain_next)

        # 현재 간격 내 남은 시간 + 이후 남은 프롬프트 * 간격
        total_secs = (remaining_prompts - 1) * interval + remain_next
        total_secs = max(0, int(total_secs))
        hours, rem = divmod(total_secs, 3600)
        mins, secs = divmod(rem, 60)

        if hours:
            self.total_time_var.set(f"작업 완료까지 약 {hours}시간 {mins:02d}분 {secs:02d}초")
        elif mins:
            self.total_time_var.set(f"작업 완료까지 약 {mins}분 {secs:02d}초")
        else:
            self.total_time_var.set(f"작업 완료까지 약 {secs}초")

    def _update_timer_pulse(self, remain_next: int):
        """다음 프롬프트/전체 시간 라벨에 가벼운 애니메이션 효과."""
        self._pulse_phase = (self._pulse_phase + 1) % 20

        # 다음 프롬프트가 10초 이하로 남으면 강하게 강조
        if remain_next <= 10:
            fg = "#FFE66D" if self._pulse_phase < 10 else "#FF6B6B"
            bg = "#2D132C" if self._pulse_phase < 10 else "#4A1A2C"
        else:
            fg = "#F8F9FF" if self._pulse_phase < 10 else "#D0D4FF"
            bg = "#151527" if self._pulse_phase < 10 else "#1E213A"

        try:
            self.countdown_label.config(fg=fg, bg=bg)
            self.total_time_label.config(
                fg="#FFD166",
                bg="#1E213A" if self._pulse_phase < 10 else "#151527",
            )
        except Exception:
            pass

    def _reset_timer_pulse(self):
        try:
            self.countdown_label.config(fg="#B8B2D6", bg="#050816")
            self.total_time_label.config(fg="#FFD166", bg="#151527")
        except Exception:
            pass

    # ------------------- session summary helpers -------------------
    def _log_session_summary(self, completed: bool):
        if self.session_start_time is None or self.session_total_prompts <= 0:
            return

        elapsed = max(0, int(time.time() - self.session_start_time))
        hours, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)

        done = self.session_success + self.session_fail
        succeed = self.session_success
        failed = self.session_fail

        state = "완료" if completed else "중간에 중단"
        summary = (
            f"작업 요약 ({state}) – 목표 {self.session_total_prompts}개 중 "
            f"실행 {done}개 (성공 {succeed}개, 실패 {failed}개), "
            f"총 소요 {hours}시간 {mins}분 {secs:02d}초"
        )
        self.log(summary)

        if completed:
            self.status_var.set(
                f"모든 프롬프트 완료 – 총 {done}개, 약 {hours}시간 {mins}분 {secs:02d}초 소요 🌙"
            )
        else:
            self.status_var.set(
                f"작업을 중간에 멈췄어요. (실행 {done}개, 성공 {succeed}개, 실패 {failed}개)"
            )

        # 다음 세션을 위해 초기화
        self.session_start_time = None

    def _human_click(self, d: webdriver.Chrome, el):
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'});", el)
        except Exception:
            pass
        try:
            from selenium.webdriver.common.action_chains import ActionChains

            ActionChains(d).move_to_element(el).pause(0.1).click().perform()
            time.sleep(0.05)
        except Exception:
            try:
                el.click()
            except Exception:
                try:
                    d.execute_script("arguments[0].click();", el)
                except Exception:
                    return False
        return True

    def _insert_text_cdp(self, d: webdriver.Chrome, text: str) -> bool:
        # Use DevTools to insert text at caret for better compatibility with React editors
        try:
            for chunk in text.split("\n"):
                if chunk:
                    d.execute_cdp_cmd("Input.insertText", {"text": chunk})
                d.execute_cdp_cmd(
                    "Input.dispatchKeyEvent",
                    {"type": "keyDown", "key": "Enter", "code": "Enter"},
                )
                d.execute_cdp_cmd(
                    "Input.dispatchKeyEvent",
                    {"type": "keyUp", "key": "Enter", "code": "Enter"},
                )
            return True
        except Exception:
            return False

    def _press_submit_heuristic(self, d: webdriver.Chrome, el) -> bool:
        """Attempt to auto-find a submit/generate button near the input element."""
        labels = [
            "generate",
            "create",
            "submit",
            "send",
            "start",
            "run",
            "generate video",
            "create video",
            "생성",
            "만들기",
            "제출",
            "시작",
            "실행",
            "영상 만들기",
            "비디오 생성",
        ]

        def match_button(btn) -> bool:
            try:
                if not btn.is_displayed() or not btn.is_enabled():
                    return False
            except Exception:
                return False
            txt = ""
            try:
                txt = (btn.text or "").strip()
            except Exception:
                txt = ""
            if not txt:
                try:
                    txt = (btn.get_attribute("aria-label") or "").strip()
                except Exception:
                    txt = ""
            if not txt:
                return False
            low = txt.lower()
            return any(k in low for k in labels)

        def try_click_buttons(buttons) -> bool:
            for b in buttons:
                if match_button(b):
                    try:
                        self._human_click(d, b)
                        time.sleep(0.1)
                        return True
                    except Exception:
                        continue
            return False

        containers = []
        cur = el
        for _ in range(4):
            if not cur:
                break
            containers.append(cur)
            try:
                parent = cur.find_element(By.XPATH, "..")
            except Exception:
                parent = None
            cur = parent

        for c in containers:
            try:
                buttons = c.find_elements(
                    By.CSS_SELECTOR,
                    "button, [role='button'], a[role='button'], div[role='button']",
                )
            except Exception:
                buttons = []
            if try_click_buttons(buttons):
                return True

        try:
            all_buttons = d.find_elements(
                By.CSS_SELECTOR,
                "button, [role='button'], a[role='button'], div[role='button']",
            )
        except Exception:
            all_buttons = []
        return try_click_buttons(all_buttons)

    def _fill_via_keys(self, d: webdriver.Chrome, el, text: str) -> bool:
        """
        [물리적 입력 모드 - 정밀 타격 버전]
        """
        text = self._sanitize_bmp(text)
        
        try:
            self.log("🖱️ 좌표 계산 및 이동 중...")
            
            target_x = 0
            target_y = 0
            
            # [우선순위 1] 사용자가 직접 지정한 좌표가 있으면 사용
            saved_coords = self.cfg.get("input_coords")
            if saved_coords:
                target_x = int(saved_coords.get("x", 0))
                target_y = int(saved_coords.get("y", 0))
                self.log(f"📍 저장된 좌표 사용: {target_x}, {target_y}")
            
            # [우선순위 2] 없으면 자동 계산
            if target_x == 0 or target_y == 0:
                metrics = d.execute_script("""
                    const rect = arguments[0].getBoundingClientRect();
                    const uiHeight = window.outerHeight - window.innerHeight;
                    return {
                        x: window.screenX + rect.left + rect.width / 2,
                        y: window.screenY + rect.top + rect.height / 2 + (uiHeight * 0.8)
                    };
                """, el)
                target_x = int(metrics['x'])
                target_y = int(metrics['y'])
            
            # 2. 마우스 이동 및 클릭
            pyautogui.moveTo(target_x, target_y, duration=0.5)
            pyautogui.click()
            time.sleep(0.5)
            
            # 3. 입력 시작
            self.log("👻 유령 키보드 입력 시작")
            
            # 기존 내용 지우기
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('backspace')
            time.sleep(0.2)
            
            # 붙여넣기
            pyperclip.copy(text)
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            
            # 연기 (오타 수정 척)
            if random.random() < 0.3:
                pyautogui.press('left')
                time.sleep(0.1)
                pyautogui.press('right')
            
            self.log("✅ 물리적 입력 완료")
            return True
            
        except Exception as e:
            self.log(f"❌ 물리 입력 실패: {e}")
            return False

    def _snapshot_files(self, d: Path) -> set[str]:
        try:
            return {p.name for p in d.iterdir() if p.is_file()}
        except Exception:
            return set()

    def _wait_new_file(self, d: Path, before: set[str], timeout: int) -> Path | None:
        end = time.time() + timeout
        while time.time() < end:
            try:
                for p in d.iterdir():
                    if (
                        p.is_file()
                        and not str(p).endswith(".crdownload")
                        and p.name not in before
                    ):
                        return p
            except Exception:
                pass
            time.sleep(0.5)
        return None

    def _finalize_download(self, p: Path) -> Path:
        # Flow 가 내려준 원래 파일 이름을 그대로 사용합니다.
        # (이전에는 1.mp4, 2.mp4 처럼 번호로 다시 이름을 붙였음)
        return p

    def _count_download_buttons(self, d: webdriver.Chrome) -> int:
        sels = list(self.cfg.get("download_selectors", []))
        if not sels:
            return 0
        main_sel = sels[0]
        try:
            elements = d.find_elements(By.CSS_SELECTOR, main_sel)
            # 화면에 보이고 활성화된 것만 카운트
            return len([el for el in elements if el.is_displayed() and el.is_enabled()])
        except Exception:
            return 0

    def _wait_and_download(self, pre_count: int = 0) -> bool:
        """
        영상 생성이 완료될 때까지 기다렸다가(최대 download_wait_seconds),
        다운로드 버튼이 나타나면 순서대로 클릭합니다.
        가장 최근(화면 하단)에 있는 버튼을 우선적으로 찾습니다.
        pre_count: 이전에 존재하던 버튼 개수. 이 개수보다 많아져야 '새 버튼'으로 인식합니다.
        """
        sels = list(self.cfg.get("download_selectors", []))
        if not sels:
            self.log("다운로드 셀렉터가 설정되어 있지 않습니다.")
            return False

        try:
            d = self._get_driver()
        except Exception as exc:
            self.log(f"Chrome 연결 실패(다운로드): {exc}")
            return False

        # 설정된 대기 시간 (기본 300초)
        max_wait = int(self.cfg.get("download_wait_seconds", 300))
        start_time = time.time()

        self.log(f"영상 생성 대기 시작 (최대 {max_wait}초, 이전 버튼 {pre_count}개)...")

        # 1단계 버튼(메인)을 찾을 때까지 루프
        main_sel = sels[0]
        found_main = None

        while time.time() - start_time < max_wait:
            # 남은 시간 UI 표시
            elapsed = int(time.time() - start_time)
            self.status_var.set(f"영상 생성 기다리는 중... ({elapsed}초 경과)")
            self.root.update()

            try:
                # 모든 매칭되는 버튼을 찾아서
                elements = d.find_elements(By.CSS_SELECTOR, main_sel)
                # 화면에 보이고 활성화된 것만 필터링
                valid_elements = [el for el in elements if el.is_displayed() and el.is_enabled()]
                
                # 조건: 버튼이 존재하고, 이전 개수보다 많아야 함 (새로운 버튼 등장)
                # 단, pre_count가 0이고 valid가 있으면(첫 생성) 통과
                if valid_elements and len(valid_elements) > pre_count:
                    # 가장 마지막(최신) 요소를 타겟으로 함
                    found_main = valid_elements[-1]
                    break
            except Exception:
                pass

            time.sleep(1)

        if not found_main:
            self.log(f"시간 초과: {max_wait}초 동안 새 다운로드 버튼을 찾지 못했습니다.")
            return False

        # 1단계 클릭
        try:
            self.log("다운로드 1단계(메인) 버튼 클릭")
            self._human_click(d, found_main)
        except Exception as exc:
            self.log(f"1단계 클릭 중 오류: {exc}")
            return False

        # 만약 2단계(화질 선택 등)가 있다면
        if len(sels) > 1:
            quality_sel = sels[1]
            self.log("다운로드 2단계(옵션) 버튼 찾는 중...")
            
            # 팝업이 뜨기를 잠시 기다림 (최대 10초)
            step2_start = time.time()
            found_quality = None
            
            # 우선순위 키워드 (사용자가 720p를 언급했으므로 이를 우선)
            priority_keywords = ["720", "mp4", "download", "저장"]

            while time.time() - step2_start < 10:
                self.root.update()
                try:
                    elements = d.find_elements(By.CSS_SELECTOR, quality_sel)
                    valid_elements = [el for el in elements if el.is_displayed() and el.is_enabled()]
                    
                    if valid_elements:
                        # 1. 키워드 매칭 시도
                        for el in valid_elements:
                            txt = (self._read_element_text(d, el) or "").lower()
                            # aria-label도 확인
                            aria = (el.get_attribute("aria-label") or "").lower()
                            combined = txt + " " + aria
                            
                            if any(k in combined for k in priority_keywords):
                                found_quality = el
                                self.log(f"2단계 버튼 키워드 매칭 성공: {txt or aria}")
                                break
                        
                        # 2. 매칭된 게 없으면 마지막 요소 선택
                        if not found_quality:
                            found_quality = valid_elements[-1]
                            self.log("2단계 버튼: 마지막 요소 선택")
                        
                        break
                except Exception:
                    pass
                time.sleep(0.5)

            if found_quality:
                try:
                    self.log("다운로드 2단계(옵션) 버튼 클릭")
                    self._human_click(d, found_quality)
                except Exception as exc:
                    self.log(f"2단계 클릭 중 오류: {exc}")
            else:
                self.log("2단계 버튼을 찾지 못했습니다(1단계만 클릭됨).")

        self.log("다운로드 동작 완료 – 파일 저장을 확인해 주세요.")
        return True

    def _press_reset(self, d: webdriver.Chrome, el) -> bool:
        for sel in list(self.cfg.get("reset_selectors", [])):
            try:
                for b in d.find_elements(By.CSS_SELECTOR, sel):
                    if b.is_displayed() and b.is_enabled():
                        try:
                            b.click()
                            return True
                        except Exception:
                            try:
                                d.execute_script("arguments[0].click();", b)
                                return True
                            except Exception:
                                pass
            except Exception:
                continue
        try:
            el.click()
            el.send_keys(Keys.CONTROL, "a")
            time.sleep(0.05)
            el.send_keys(Keys.BACKSPACE)
            time.sleep(0.05)
            return True
        except Exception:
            return False

    def _select_style_heuristic(self, d: webdriver.Chrome) -> bool:
        # 스타일 선택이 필수일 수 있으므로, 가장 일반적인 스타일 하나를 시도합니다.
        targets = ["Cinematic", "Film Noir", "Digital Art", "Anime"]
        for t in targets:
            try:
                xpath = f"//*[contains(text(), '{t}')]"
                els = d.find_elements(By.XPATH, xpath)
                for el in els:
                    if el.is_displayed():
                        self._human_click(d, el)
                        self.log(f"스타일 선택 시도: {t}")
                        time.sleep(0.5)
                        return True
            except:
                pass
        return False

    def _press_submit(self, d: webdriver.Chrome, el) -> bool:
        # [우선순위 0] 사용자가 직접 지정한 좌표가 있으면 무조건 클릭 (PyAutoGUI)
        saved_coords = self.cfg.get("submit_coords")
        if saved_coords:
            try:
                tx = int(saved_coords.get("x", 0))
                ty = int(saved_coords.get("y", 0))
                if tx > 0 and ty > 0:
                    self.log(f"📍 저장된 생성 버튼 좌표 클릭: {tx}, {ty}")
                    pyautogui.moveTo(tx, ty, duration=0.5)
                    pyautogui.click()
                    time.sleep(0.5)
                    return True
            except Exception as e:
                self.log(f"좌표 클릭 실패: {e}")

        # 1. 설정된 selector 우선 클릭 (가장 정확함)
        selectors = self.cfg.get("submit_selectors", [])
        for sel in selectors:
            try:
                btns = d.find_elements(By.CSS_SELECTOR, sel)
                for b in btns:
                    if b.is_displayed():
                        self.log("설정된 생성 버튼 클릭")
                        self._human_click(d, b)
                        time.sleep(0.5)
                        return True
            except: pass

        # 2. 휴리스틱(텍스트/aria-label 기반) 탐색
        if self._press_submit_heuristic(d, el):
            return True
        
        # 3. 실패 시, 엔터키 전송 시도
        try:
            el.send_keys(Keys.CONTROL, Keys.ENTER)
            time.sleep(0.5)
            return True
        except Exception:
            pass
            
        return False

    def _auto_submit_current(self) -> bool:
        if not self.prompts:
            return False
        try:
            d = self._get_driver()
        except Exception as exc:
            self.status_var.set(f"Chrome 오류: {exc}")
            self.log(f"Chrome 오류: {exc}")
            return False
        self._navigate(d)
        el = self._wait_input(d, timeout=90)
        if not el:
            self.status_var.set("입력창을 찾지 못했어요.")
            self.log("입력창을 찾지 못했습니다.")
            return False
        
        # [수정] 자동 다운로드 로직 완전 삭제! (제출만 집중)
        
        cur_no = self.index + 1
        total = len(self.prompts)
        prefix = f"[프롬프트 {cur_no}/{total}]"
        self.log(f"{prefix} 입력칸 초기화 시도")
        self._press_reset(d, el)
        raw = self.prompts[self.index]
        
        text = raw
        self.log(f"{prefix} 프롬프트 준비: {len(text)}자")
        
        # 1. 텍스트 입력 (휴먼 타이핑)
        ok_fill = self._fill_via_keys(d, el, text)
        if not ok_fill:
            self.status_var.set("프롬프트 입력에 실패했어요.")
            self.log(f"{prefix} 입력 실패")
            if self.session_start_time is not None:
                self.session_fail += 1
            return False
            
        # 2. 스타일 선택 (필수)
        time.sleep(0.5)
        self._select_style_heuristic(d)
        
        self.log(f"{prefix} 입력 완료, 생성 버튼 누르기 시도")
        
        # 3. 제출 버튼 클릭
        ok_submit = self._press_submit(d, el)
        self.log(f"{prefix} 제출 성공" if ok_submit else f"{prefix} 제출 실패")

        if self.session_start_time is not None:
            if ok_submit:
                self.session_success += 1
            else:
                self.session_fail += 1

        # [수정] 제출 후 다운로드 시도하던 코드 삭제됨.
        return ok_submit

    # ------------------- selector capture -------------------
    def _capture_button(self, kind: str):
        try:
            d = self._get_driver()
        except Exception as exc:
            self.log(f"Chrome 연결 실패: {exc}")
            messagebox.showerror(APP_NAME, f"Chrome 연결 실패: {exc}")
            return
        self._navigate(d)
        js = """
        (function(){
          var KIND = "%s";
          if (window.__cap && window.__cap.active) return;
          function cssEscape(s){ return (window.CSS&&CSS.escape)?CSS.escape(s):s.replace(/([#.;,:+*~'>"\\[\\]\\(\\) ])/g,'\\\\$1'); }
          function uniqueSelector(el){
            if(!el) return '';
            const attrs=['data-testid','aria-label','data-id','id','name','type'];
            for(const a of attrs){
              try{
                const v=el.getAttribute(a);
                if(v){
                  // 다운로드 버튼(download1/download2)을 지정할 때는
                  // Flow 가 매번 바꾸는 일회용 id(radix-:...:) 는 무시합니다.
                  if(a==='id'){
                    if(KIND.indexOf('download')!==0){
                      return '#'+cssEscape(v);
                    }
                    continue;
                  }
                  return el.tagName.toLowerCase()+'['+a+'="'+String(v).replace(/"/g,'\\"')+'"]';
                }
              }catch(e){}
            }
            const parts=[];
            let n=el, depth=0;
            while(n&&n.nodeType===1&&n!==document.body&&depth<6){
              let p=n.tagName.toLowerCase();
              const rawClass = (n.className||'').trim();
              const cls = rawClass ? rawClass.split(/\\s+/).filter(c => c && !c.startsWith('__cap')) : [];
              if(cls.length&&cls.join('').length<40){
                p+='.'+cls.map(cssEscape).join('.');
              }else{
                let i=1,s=n;
                while((s=s.previousElementSibling)!=null){
                  if(s.tagName===n.tagName) i++;
                }
                p+=':nth-of-type('+i+')';
              }
              parts.unshift(p);
              // 다운로드 버튼(download1/download2)을 지정할 때는
              // Flow 의 일회용 id(radix-:...:) 를 피하기 위해 id 를 무시합니다.
              if(n.id && KIND.indexOf('download')!==0){
                parts.unshift('#'+cssEscape(n.id));
                break;
              }
              n=n.parentElement;
              depth++;
            }
            return parts.join(' > ');
          }
          const style=document.createElement('style');
          style.textContent='.__cap_mark{outline:2px solid #ffb3ff!important;cursor: crosshair!important;transition: outline 0.1s ease-out;}';
          document.documentElement.appendChild(style);
          const state={active:true,done:false,cancel:false,sel:'',prev:null,cleanup(){
            ['mouseover','mouseout','click','mousedown','mouseup','pointerdown','pointerup','keydown'].forEach(ev=>document.removeEventListener(ev,handler,true));
            try{style.remove();}catch(e){}
            try{ if(state.prev) state.prev.classList.remove('__cap_mark'); }catch(e){}
            state.active=false;
          }};
          function handler(e){
            if(e.type==='mouseover'){
              try{
                if(state.prev) state.prev.classList.remove('__cap_mark');
                state.prev=e.target;
                e.target.classList.add('__cap_mark');
              }catch(err){}
              return;
            }
            if(e.type==='mouseout'){
              try{ e.target.classList.remove('__cap_mark'); }catch(err){}
              return;
            }
            if(e.type==='keydown'){
              if(e.key==='Escape'){
                e.preventDefault(); e.stopPropagation();
                state.cancel=true; state.done=true; state.cleanup(); window.__cap=state; return;
              }
              if(e.key==='Enter' || e.key.toLowerCase()==='s'){
                e.preventDefault(); e.stopPropagation();
                const t=state.prev;
                state.sel=uniqueSelector(t);
                
                // [좌표 계산] 화면상 절대 좌표 (PyAutoGUI용)
                const rect = t.getBoundingClientRect();
                const winX = window.screenX || window.screenLeft || 0;
                const winY = window.screenY || window.screenTop || 0;
                // 상단 UI 높이 추정 (전체화면이 아닐 때)
                const uiH = (window.outerHeight - window.innerHeight) || 0;
                
                state.coords = {
                    x: Math.round(winX + rect.left + (rect.width/2)),
                    y: Math.round(winY + rect.top + (rect.height/2) + (uiH * 0.8)) // 상단바 보정
                };
                
                state.done=true; state.cleanup(); window.__cap=state; return;
              }
              return;
            }
            if(e.type==='click' && KIND==='download1'){
              // 1단계(메인) 다운로드 버튼은 '클릭'으로 지정합니다.
              // 클릭 동작은 그대로 Flow 쪽으로도 전달됩니다.
              try{ state.prev = e.target; }catch(err){}
              try{
                const t = state.prev;
                state.sel = uniqueSelector(t);
                state.done = true;
                state.cleanup();
                window.__cap = state;
              }catch(err){}
              return;
            }
          }
          ['mouseover','mouseout','click','mousedown','mouseup','pointerdown','pointerup','keydown'].forEach(ev=>document.addEventListener(ev,handler,true));
          window.__cap=state;
        })();
        """ % kind
        try:
            d.execute_script(js)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"지정 모드 스크립트 실행 실패: {exc}")
            return

        if kind == "input":
            self.status_var.set("입력칸 위로 마우스를 올린 뒤 Enter 를 눌러주세요. (Esc 취소)")
        elif kind == "submit":
            self.status_var.set("생성 버튼 위로 마우스를 올린 뒤 Enter 를 눌러주세요. (Esc 취소)")
        elif kind == "download1":
            self.status_var.set("1단계 다운로드 버튼(팝업을 여는 버튼)을 클릭해 주세요.")
        elif kind == "download2":
            self.status_var.set(
                "2단계 다운로드 버튼(720p/1080p 등)을 지정합니다.\n"
                "1) 먼저 1단계 버튼을 눌러 팝업을 띄운 뒤\n"
                "2) 원하는 품질 버튼 위에 마우스를 올리고 Enter 를 눌러주세요. (Esc 취소)"
            )
        else:
            self.status_var.set("다운로드 버튼을 클릭해서 지정해 주세요. (Esc 취소)")

        start = time.time()
        picked = None
        picked_coords = None
        while time.time() - start < 60:
            try:
                # coords도 같이 반환받음
                res = d.execute_script(
                    "return window.__cap && window.__cap.done ? {sel: window.__cap.sel, coords: window.__cap.coords, cancel: window.__cap.cancel} : null;"
                )
            except Exception:
                res = None
            if res:
                if res.get("cancel"):
                    self.status_var.set("지정을 취소했어요.")
                    return
                picked = (res.get("sel") or "").strip()
                picked_coords = res.get("coords")
                break
            time.sleep(0.1)

        if not picked:
            self.status_var.set("시간이 지나 지정을 마치지 못했어요.")
            return

        if kind == "input":
            key = "input_selectors"
            if picked_coords:
                self.cfg["input_coords"] = picked_coords
        elif kind == "submit":
            key = "submit_selectors"
            if picked_coords:
                self.cfg["submit_coords"] = picked_coords
        elif kind == "download1":
            key = "download_selector_main"
        elif kind == "download2":
            key = "download_selector_quality"
        else:
            key = "download_selectors"

        if key in ("download_selector_main", "download_selector_quality"):
            # 1단계/2단계 다운로드 버튼은 각각 하나의 셀렉터만 사용
            self.cfg[key] = picked
            # 리스트는 1단계 → 2단계 순으로 재구성
            main = str(self.cfg.get("download_selector_main") or "").strip()
            quality = str(self.cfg.get("download_selector_quality") or "").strip()
            lst = [s for s in (main, quality) if s]
            self.cfg["download_selectors"] = lst
        else:
            cur = list(self.cfg.get(key, []))
            # 다운로드 버튼은 여러 단계를 순서대로 클릭해야 하므로,
            # 새로 지정한 셀렉터를 "맨 뒤"에 붙여서 앞에서부터 차례로 실행되게 합니다.
            if key == "download_selectors":
                new_list = [s for s in cur if s != picked] + [picked]
            else:
                # 나머지는 최근 지정한 것을 우선 사용
                new_list = [picked] + [s for s in cur if s != picked]
            self.cfg[key] = new_list
        save_config(self.cfg_path, self.cfg)
        label_map = {
            "input_selectors": "입력칸",
            "submit_selectors": "생성 버튼",
            "download_selectors": "다운로드 버튼",
            "download_selector_main": "다운로드 1단계 버튼",
            "download_selector_quality": "다운로드 2단계 버튼",
        }
        label = label_map.get(key, key)
        self.status_var.set(f"{label} 지정 완료: {picked}")
        self.log(f"{label} 지정: {picked}")

    def on_capture_input(self):
        self._capture_button(kind="input")

    def on_capture_submit(self):
        self._capture_button(kind="submit")

    def on_capture_download(self):
        self._capture_button(kind="download")

    def on_capture_download_step1(self):
        # 1단계: 메인 다운로드 버튼 (팝업을 여는 버튼)
        self._capture_button(kind="download1")

    def on_capture_download_step2(self):
        # 2단계: 720p/1080p 등 품질 선택 버튼
        self._capture_button(kind="download2")

    # ------------------- download UI callbacks -------------------
    def on_pick_download_dir(self):
        cur = str(self._get_download_dir())
        try:
            from tkinter import filedialog

            chosen = filedialog.askdirectory(initialdir=cur, title="다운로드 폴더 선택")
        except Exception:
            chosen = None
        if not chosen:
            return
        self.cfg["download_dir"] = chosen
        save_config(self.cfg_path, self.cfg)
        self.status_var.set(f"다운로드 폴더: {chosen}")
        self.log(f"다운로드 폴더 선택: {chosen}")

    def on_toggle_auto_download(self):
        enabled = bool(self.auto_dl_var.get())
        self.cfg["auto_download_enabled"] = enabled
        save_config(self.cfg_path, self.cfg)
        self.status_var.set("자동 다운로드 켬" if enabled else "자동 다운로드 끔")
        self.log("자동 다운로드 켬" if enabled else "자동 다운로드 끔")

    def on_download_now(self):
        ok = self._attempt_download()
        self.status_var.set("다운로드 완료" if ok else "다운로드 실패")
        self.log("수동 다운로드 완료" if ok else "수동 다운로드 실패")

    def on_start_bulk_download(self):
        if self.running:
            self.on_stop()
            time.sleep(0.5)
        
        if not messagebox.askyesno(
            APP_NAME,
            "📥 기존 영상 일괄 다운로드를 시작할까요?\n\n"
            "1. Flow 화면을 맨 위(또는 다운로드를 시작할 위치)로 스크롤해 주세요.\n"
            "2. '예'를 누르면 화면에 보이는 영상부터 순서대로 다운로드하고, 자동으로 스크롤을 내립니다.\n"
            "3. [스마트 중복 방지] 이미 다운로드한 영상(썸네일 기준)은 건너뜁니다.\n"
            "4. 멈추려면 '🛑 멈추기' 버튼을 누르세요."
        ):
            return

        self.running = True
        self.status_var.set("일괄 다운로드 시작...")
        self.log(f"일괄 다운로드 모드 시작 (현재 기록된 영상: {len(self.history)}개)")
        # 별도 스레드 대신 after로 루프 처리
        self.root.after(100, self._run_bulk_download_loop)

    def _run_bulk_download_loop(self):
        if not self.running:
            return

        try:
            d = self._get_driver()
        except Exception as exc:
            self.log(f"Chrome 연결 실패: {exc}")
            self.running = False
            return

        sels = list(self.cfg.get("download_selectors", []))
        if not sels:
            self.status_var.set("다운로드 버튼이 지정되지 않았어요.")
            self.running = False
            return

        main_sel = sels[0]
        quality_sel = sels[1] if len(sels) > 1 else None

        # 현재 화면에서 버튼들 찾기
        try:
            all_buttons = d.find_elements(By.CSS_SELECTOR, main_sel)
            # 화면에 보이는 것만
            visible_buttons = [b for b in all_buttons if b.is_displayed() and b.is_enabled()]
        except Exception:
            visible_buttons = []

        if not visible_buttons:
            self.log("화면에 다운로드 버튼이 안 보여요. 스크롤을 시도합니다.")
            d.execute_script("window.scrollBy(0, 500);")
            self.root.after(2000, self._run_bulk_download_loop)
            return

        self.status_var.set(f"화면에서 {len(visible_buttons)}개 발견. 처리 시작...")
        
        count_processed = 0
        for i, btn in enumerate(visible_buttons):
            if not self.running:
                break
            
            # [중복 방지] 고유 ID(썸네일 주소) 확인
            uid = self._get_unique_id(d, btn)
            if uid and uid in self.history:
                self.log(f"영상 {i+1}: 이미 다운로드한 영상입니다 (Skip)")
                continue

            # 스크롤해서 버튼이 잘 보이게 함
            try:
                self._human_click(d, btn) # 1단계 클릭 (메인)
                time.sleep(0.5)
                
                # 2단계(화질) 처리
                downloaded_ok = False
                if quality_sel:
                    # 팝업 대기
                    found_quality = None
                    # 우선순위 키워드
                    priority_keywords = ["720", "mp4", "download", "저장"]
                    
                    for _ in range(5): # 최대 2.5초 대기
                        try:
                            q_elements = d.find_elements(By.CSS_SELECTOR, quality_sel)
                            q_valid = [qe for qe in q_elements if qe.is_displayed()]
                            if q_valid:
                                # 키워드 검색
                                for qe in q_valid:
                                    txt = (self._read_element_text(d, qe) or "").lower()
                                    aria = (qe.get_attribute("aria-label") or "").lower()
                                    combined = txt + " " + aria
                                    if any(k in combined for k in priority_keywords):
                                        found_quality = qe
                                        break
                                
                                if not found_quality:
                                    found_quality = q_valid[-1] # 없으면 마지막
                                break
                        except Exception:
                            pass
                        time.sleep(0.5)
                        self.root.update()

                    if found_quality:
                        self._human_click(d, found_quality)
                        self.log(f"영상 {i+1} 다운로드 클릭 완료")
                        downloaded_ok = True
                        count_processed += 1
                        time.sleep(1.0) # 다운로드 시작 대기
                    else:
                        self.log(f"영상 {i+1}: 2단계 버튼을 못 찾았습니다.")
                        # 팝업 닫기 위해 다른 곳 클릭하거나 ESC
                        try:
                            webdriver.ActionChains(d).send_keys(Keys.ESCAPE).perform()
                        except:
                            pass
                else:
                    # 1단계만 있는 경우 (바로 다운로드라고 가정)
                    downloaded_ok = True
                    count_processed += 1
                
                # 성공 시 기록 저장
                if downloaded_ok and uid:
                    self.history.add(uid)
                    self.save_history()

            except Exception as e:
                self.log(f"버튼 처리 중 오류 (무시하고 계속): {e}")

        if self.running:
            # 한 화면 처리가 끝났으므로 스크롤 다운
            self.log("현재 화면 처리 완료. 아래로 스크롤합니다.")
            d.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
            # 로딩 대기 후 재귀 호출
            self.root.after(3000, self._run_bulk_download_loop)


if __name__ == "__main__":
    FlowApp().run()
