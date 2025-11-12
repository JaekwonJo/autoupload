import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from urllib.parse import parse_qs, unquote, urlparse

import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from tkinter.scrolledtext import ScrolledText

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


APP_NAME = "Sora2 Auto – Aurora Horizon"

DEFAULT_CONFIG = {
    "prompts_file": "prompts.txt",
    "prompts_separator": "|||",
    "check_interval_seconds": 1500,
    "status_update_seconds": 60,
    "prompts_per_cycle": 1,
    "auto_resume": True,
    "log_dir": "logs",
    "chrome_profile_dir": "chrome_profile_plus",
    "chrome_devtools_port": 9222,
    "chrome_executable": "",
    "sora_url": "https://sora.chatgpt.com/drafts",
    "auto_download_enabled": False,
    "download_dir": "downloads",
    "download_check_seconds": 5,
    "download_wait_seconds": 180,
    "download_batch_limit": 10,
    "prompt_sets": [
        {"id": "set1", "label": "세트 1", "file": "prompts.txt"},
        {"id": "set2", "label": "세트 2", "file": "prompts_set2.txt"},
        {"id": "set3", "label": "세트 3", "file": "prompts_set3.txt"},
        {"id": "set4", "label": "세트 4", "file": "prompts_set4.txt"},
        {"id": "set5", "label": "세트 5", "file": "prompts_set5.txt"},
    ],
    "active_prompt_set": "set1",
    "submit_selectors": [
        "button[aria-label*='Submit']",
        "button[aria-label*='Send']",
        "button[aria-label*='Create']",
        "button[type='submit']",
        "button[data-testid*='submit']",
        "button[data-testid*='send']",
        "button[class*='submit']",
        "button[class*='send']",
        "[data-testid*='Submit']",
    ],
}

TRANSLATE_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TRANSLATE_LOWER = TRANSLATE_UPPER.lower()


def load_or_create_config(path: Path) -> dict:
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    if "prompt_sets" not in cfg:
        primary = cfg.get("prompts_file", DEFAULT_CONFIG["prompts_file"])
        cfg["prompt_sets"] = [
            {"id": "set1", "label": "세트 1", "file": primary},
            {"id": "set2", "label": "세트 2", "file": "prompts_set2.txt"},
            {"id": "set3", "label": "세트 3", "file": "prompts_set3.txt"},
            {"id": "set4", "label": "세트 4", "file": "prompts_set4.txt"},
            {"id": "set5", "label": "세트 5", "file": "prompts_set5.txt"},
        ]
    cfg.setdefault("active_prompt_set", cfg.get("prompt_sets", [{}])[0].get("id", "set1"))
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
    prompts = [part.strip() for part in raw.split(separator)]
    return [p for p in prompts if p]


def load_or_init_state(state_path: Path, prompts: list[str], auto_resume: bool) -> dict:
    state: Optional[dict] = None
    if auto_resume and state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            state = None

    if not isinstance(state, dict):
        state = {
            "remaining_prompts": prompts.copy(),
            "completed_count": 0,
            "skipped_count": 0,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "downloaded_assets": [],
            "download_index": 1,
            "download_anchor": None,
            "download_skip_assets": [],
            "history": [],
        }
    else:
        state.setdefault("remaining_prompts", prompts.copy())
        state.setdefault("completed_count", 0)
        state.setdefault("skipped_count", 0)
        state.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
        state.setdefault("downloaded_assets", [])
        state.setdefault("download_index", 1)
        state.setdefault("download_anchor", None)
        state.setdefault("download_skip_assets", [])
        state.setdefault("history", [])

    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


class TkLogHandler(logging.Handler):
    def __init__(self, app: "SoraAutoApp"):
        super().__init__()
        self.app = app

    def emit(self, record):
        msg = self.format(record)
        self.app.post_ui(lambda: self.app.append_log(msg))


class SoraAutoApp:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / "sora_config.json"

        self.config = load_or_create_config(self.cfg_path)
        self.prompt_sets = self._normalize_prompt_sets(self.config.get("prompt_sets", []))
        self.prompt_set_map = {item["id"]: item for item in self.prompt_sets}
        active_set = self.config.get("active_prompt_set")
        if active_set not in self.prompt_set_map:
            active_set = self.prompt_sets[0]["id"]
        self.state_lock = threading.RLock()
        self.state_path: Path = self._state_file_for_set(active_set)
        self.state = {}
        self.downloaded_assets: set[str] = set()
        self.download_skip_assets: set[str] = set()
        self.next_download_index = 1
        self.download_anchor: Optional[str] = None
        self.active_prompt_set_id: Optional[str] = None
        self._activate_prompt_set(active_set, initializing=True)

        self.driver: Optional[webdriver.Chrome] = None
        self.driver_lock = threading.RLock()
        self.stop_requested = threading.Event()
        self.force_run_event = threading.Event()
        self.paused = threading.Event()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.last_status = 0.0
        self.last_download_scan = 0.0
        self.download_stop_event = threading.Event()
        self.download_thread: Optional[threading.Thread] = None

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("900x720")
        self.root.configure(bg="#14121F")
        self.root.resizable(True, True)
        self.root.minsize(820, 640)

        self.next_run_ts: Optional[float] = None

        self._build_ui()
        self._setup_logging()
        self.refresh_summary()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _build_ui(self):
        self._apply_styles()

        header = tk.Frame(self.root, bg="#221F33")
        header.pack(fill="x")

        title = tk.Label(
            header,
            text="🌅  Sora2 Auto – Aurora Horizon",
            font=("Pretendard", 26, "bold"),
            fg="#F8F4FF",
            bg="#221F33",
        )
        title.pack(pady=(18, 6))

        subtitle = tk.Label(
            header,
            text="배경에서도 부드럽게 흐르는 감성 자동화",
            font=("Pretendard", 14),
            fg="#B8B2D6",
            bg="#221F33",
        )
        subtitle.pack(pady=(0, 16))

        body = tk.Frame(self.root, bg="#14121F")
        body.pack(fill="both", expand=True)

        interval_seconds = max(30, int(self.config.get("check_interval_seconds", 1500)))
        self.interval_var = tk.IntVar(value=interval_seconds)
        self.countdown_var = tk.StringVar(value="대기 시간 —")

        self.status_label = tk.Label(
            body,
            text="먼저 크롬을 자동으로 준비할게요… 잠시만 기다려 주세요 ✨",
            font=("Pretendard", 13),
            fg="#E7E3FF",
            bg="#14121F",
        )
        self.status_label.pack(pady=(30, 10))

        self.countdown_label = tk.Label(
            body,
            textvariable=self.countdown_var,
            font=("Pretendard", 18, "bold"),
            fg="#F5B3E0",
            bg="#14121F",
        )
        self.countdown_label.pack(pady=(0, 16))

        timer_frame = tk.Frame(body, bg="#14121F")
        timer_frame.pack(pady=(0, 18))

        timer_label = tk.Label(
            timer_frame,
            text="⏱️ 자동 간격",
            font=("Pretendard", 12, "bold"),
            fg="#DCD5FF",
            bg="#14121F",
        )
        timer_label.grid(row=0, column=0, padx=(0, 12))

        self.interval_spin = ttk.Spinbox(
            timer_frame,
            from_=30,
            to=10800,
            increment=30,
            width=8,
            textvariable=self.interval_var,
            justify="center",
            command=self._on_interval_spin,
        )
        self.interval_spin.grid(row=0, column=1)
        self.interval_spin.bind("<Return>", self._on_interval_spin_return)
        self.interval_spin.bind("<FocusOut>", self._on_interval_spin)

        timer_hint = tk.Label(
            timer_frame,
            text="초 단위 (30초~3시간)",
            font=("Pretendard", 10),
            fg="#AFA8D9",
            bg="#14121F",
        )
        timer_hint.grid(row=0, column=2, padx=(12, 0))

        buttons = tk.Frame(body, bg="#14121F")
        buttons.pack(pady=14, fill="x")

        for col in range(7):
            buttons.grid_columnconfigure(col, weight=1)

        self.start_btn = ttk.Button(buttons, text="🌠 스타트", command=self.on_start)
        self.start_btn.grid(row=0, column=0, padx=6, pady=4, sticky="ew")

        self.pause_btn = ttk.Button(buttons, text="⏸️ 일시정지", command=self.on_pause)
        self.pause_btn.grid(row=0, column=1, padx=6, pady=4, sticky="ew")

        self.resume_btn = ttk.Button(buttons, text="▶️ 다시재생", command=self.on_resume)
        self.resume_btn.grid(row=0, column=2, padx=6, pady=4, sticky="ew")

        self.now_btn = ttk.Button(buttons, text="⚡ 바로실행", command=self.on_force_run)
        self.now_btn.grid(row=0, column=3, padx=6, pady=4, sticky="ew")

        self.prev_btn = ttk.Button(buttons, text="⏮ 이전으로", command=self.on_prev)
        self.prev_btn.grid(row=0, column=4, padx=6, pady=4, sticky="ew")

        self.skip_btn = ttk.Button(buttons, text="🪽 건너뛰기", command=self.on_skip)
        self.skip_btn.grid(row=0, column=5, padx=6, pady=4, sticky="ew")

        self.stop_btn = ttk.Button(buttons, text="🛑 종료", command=self.on_stop)
        self.stop_btn.grid(row=0, column=6, padx=6, pady=4, sticky="ew")

        prompt_label = ttk.Label(buttons, text="📚 프롬프트 세트", style="InfoLabel.TLabel")
        prompt_label.grid(row=1, column=0, padx=6, pady=(10, 4), sticky="e")

        self.prompt_set_var = tk.StringVar(value=self.active_prompt_set_id)
        # rebuild display map using full labels (unique)
        self.prompt_label_map = {}
        display_values = []
        used = set()
        for idx, info in enumerate(self.prompt_sets, start=1):
            label = (info.get("label") or info.get("id") or f"세트 {idx}").strip()
            display = label if label not in used else f"{label} ({info['id']})"
            used.add(display)
            self.prompt_label_map[display] = info["id"]
            display_values.append(display)
            if info["id"] == self.active_prompt_set_id:
                self.prompt_set_var.set(display)

        self.prompt_set_combo = ttk.Combobox(
            buttons,
            values=display_values,
            state="readonly",
            textvariable=self.prompt_set_var,
        )
        if display_values and self.prompt_set_var.get() in display_values:
            self.prompt_set_combo.current(display_values.index(self.prompt_set_var.get()))
        self.prompt_set_combo.grid(row=1, column=1, columnspan=2, padx=6, pady=(10, 4), sticky="ew")
        self.prompt_set_combo.bind("<<ComboboxSelected>>", self.on_prompt_set_selected)

        self.reload_btn = ttk.Button(buttons, text="🔄 다시불러오기", command=self.on_reload_prompts)
        self.reload_btn.grid(row=1, column=3, padx=6, pady=(10, 4), sticky="ew")

        self.open_prompt_btn = ttk.Button(buttons, text="📄 열기", command=self.on_open_prompt_file)
        self.open_prompt_btn.grid(row=1, column=4, padx=6, pady=(10, 4), sticky="ew")

        self.rename_btn = ttk.Button(buttons, text="✏️ 세트 이름", command=self.on_rename_prompt_set)
        self.rename_btn.grid(row=1, column=5, padx=6, pady=(10, 4), sticky="ew")

        self.auto_download_var = tk.BooleanVar(value=bool(self.config.get("auto_download_enabled", False)))
        self.mark_download_btn = ttk.Button(
            buttons,
            text="🎯 여기서 다운로드 시작",
            command=self.on_mark_download_anchor,
        )
        self.mark_download_btn.grid(row=2, column=0, columnspan=3, padx=6, pady=(6, 10), sticky="ew")

        self.auto_download_toggle = ttk.Checkbutton(
            buttons,
            text="🎞 자동 다운로드",
            variable=self.auto_download_var,
            command=self.on_toggle_auto_download,
            style="TCheckbutton",
        )
        self.auto_download_toggle.grid(row=2, column=3, columnspan=3, padx=6, pady=(6, 10), sticky="ew")

        info_box = tk.Frame(body, bg="#1E1B2C")
        info_box.pack(padx=20, pady=16, fill="x")

        self.summary_label = tk.Label(
            info_box,
            text="",
            font=("Pretendard", 12),
            fg="#F6EEF8",
            bg="#1E1B2C",
            justify="left",
        )
        self.summary_label.pack(anchor="w", padx=20, pady=(18, 10))

        self.preview_label = tk.Label(
            info_box,
            text="✨ 다음 프롬프트 미리보기",
            font=("Pretendard", 11, "bold"),
            fg="#CFC1FF",
            bg="#1E1B2C",
        )
        self.preview_label.pack(anchor="w", padx=20)

        self.preview_box = tk.Label(
            info_box,
            text="",
            font=("Pretendard", 11),
            fg="#E7E3FF",
            bg="#251F34",
            wraplength=750,
            justify="left",
            padx=18,
            pady=12,
        )
        self.preview_box.pack(fill="x", padx=18, pady=(6, 18))

        log_frame = tk.Frame(body, bg="#14121F")
        log_frame.pack(padx=20, pady=(0, 16), fill="both", expand=True)

        log_label = tk.Label(
            log_frame,
            text="🌈 라이브 로그",
            font=("Pretendard", 12, "bold"),
            fg="#C7B8FF",
            bg="#14121F",
        )
        log_label.pack(anchor="w")

        self.log_text = ScrolledText(
            log_frame,
            width=100,
            height=10,
            font=("Consolas", 11),
            bg="#0B0614",
            fg="#FDF7FF",
            insertbackground="#FDF7FF",
            relief="flat",
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text.tag_configure("log", foreground="#FDF7FF")
        self.log_text.tag_configure("hint", foreground="#8D7FE5")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "✨ 라이브 로그가 여기 표시돼요!\n", "hint")
        self.log_text.configure(state="disabled")

        footer = tk.Label(
            body,
            text="Tip ✨ : Sora 전용 창은 프로그램이 알아서 관리해요. 다른 브라우저로 자유롭게 서핑해도 괜찮아요!",
            font=("Pretendard", 11),
            fg="#B4A9F6",
            bg="#14121F",
        )
        footer.pack(pady=(4, 20))

        self._set_countdown(None)

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TButton",
            font=("Pretendard", 11, "bold"),
            padding=(18, 10),
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
        style.configure(
            "TCheckbutton",
            font=("Pretendard", 11, "bold"),
            background="#14121F",
            foreground="#F7F4FF",
        )
        style.map(
            "TCheckbutton",
            background=[("active", "#2F2A54")],
            foreground=[("disabled", "#7F76B0")],
        )
        style.configure(
            "InfoLabel.TLabel",
            font=("Pretendard", 10, "bold"),
            background="#14121F",
            foreground="#CFC1FF",
        )

    # ------------------------------------------------------------------
    # Logging / status helpers
    # ------------------------------------------------------------------
    def _setup_logging(self):
        log_dir = self.base / self.config["log_dir"]
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"sora_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        handler_file = logging.FileHandler(log_path, encoding="utf-8")
        handler_ui = TkLogHandler(self)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler_file.setFormatter(formatter)
        handler_ui.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()
        root_logger.addHandler(handler_file)
        root_logger.addHandler(handler_ui)

        logging.info("%s 시작", APP_NAME)
        logging.info("로그 파일: %s", log_path)

    def update_status(self, message: str):
        self.post_ui(lambda: self.status_label.config(text=message))

    def append_log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n", "log")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def refresh_summary(self):
        with self.state_lock:
            completed = self.state.get("completed_count", 0)
            skipped = self.state.get("skipped_count", 0)
            remaining = len(self.state.get("remaining_prompts", []))
            downloads = len(self.downloaded_assets)
            next_idx = int(self.next_download_index)
            set_label = self.prompt_set_map.get(self.active_prompt_set_id, {}).get("label", self.active_prompt_set_id)
        summary = (
            f"📚 {set_label}  |  ✅ 완료 {completed}  |  🪽 스킵 {skipped}  |  🌱 남은 프롬프트 {remaining}  |  🎞 다운로드 {downloads} (다음: sora2auto_{next_idx})\n"
            f"🕒 마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.post_ui(lambda: self.summary_label.config(text=summary))
        with self.state_lock:
            next_prompt = self.state["remaining_prompts"][0] if self.state["remaining_prompts"] else "모든 프롬프트를 완주했어요!"
        self.post_ui(lambda: self.preview_box.config(text=next_prompt))

    # ------------------------------------------------------------------
    # Prompt set helpers
    # ------------------------------------------------------------------
    def _normalize_prompt_sets(self, raw_sets) -> list[dict]:
        fallback = DEFAULT_CONFIG.get("prompt_sets", [])
        normalized: list[dict] = []
        seen_ids: set[str] = set()
        for idx in range(5):
            default_entry = fallback[idx] if idx < len(fallback) else {
                "id": f"set{idx + 1}",
                "label": f"세트 {idx + 1}",
                "file": f"prompts_set{idx + 1}.txt",
            }
            entry = default_entry.copy()
            if isinstance(raw_sets, list) and idx < len(raw_sets) and isinstance(raw_sets[idx], dict):
                candidate = raw_sets[idx]
                if candidate.get("id"):
                    entry["id"] = str(candidate["id"]).strip()
                if candidate.get("label"):
                    entry["label"] = str(candidate["label"]).strip()
                if candidate.get("file"):
                    entry["file"] = str(candidate["file"]).strip()
            entry["id"] = entry.get("id") or f"set{idx + 1}"
            if not entry.get("label"):
                entry["label"] = f"세트 {idx + 1}"
            if not entry.get("file"):
                entry["file"] = f"prompts_set{idx + 1}.txt"
            base_id = entry["id"]
            counter = 1
            while entry["id"] in seen_ids:
                entry["id"] = f"{base_id}_{counter}"
                counter += 1
            seen_ids.add(entry["id"])
            normalized.append(entry)
        return normalized

    def _state_file_for_set(self, set_id: str) -> Path:
        return self.base / f"sora_state_{set_id}.json"

    def _prompt_file_path(self, set_id: str) -> Path:
        info = self.prompt_set_map.get(set_id)
        if not info:
            raise KeyError(f"Unknown prompt set: {set_id}")
        path = self.base / info.get("file", f"prompts_{set_id}.txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        return path

    def _activate_prompt_set(self, set_id: str, initializing: bool = False):
        if set_id not in self.prompt_set_map:
            raise KeyError(f"Unknown prompt set id: {set_id}")
        with self.state_lock:
            if self.active_prompt_set_id and not initializing and self.state:
                try:
                    self._save_state()
                except Exception:
                    logging.exception("프롬프트 세트 전환 중 상태 저장에 실패했습니다.")

            prompts_path = self._prompt_file_path(set_id)
            prompts = load_prompts(prompts_path, self.config["prompts_separator"])
            state_path = self._state_file_for_set(set_id)
            auto_resume = bool(self.config.get("auto_resume", True))
            state = load_or_init_state(state_path, prompts, auto_resume)

            self.state_path = state_path
            self.state = state
            self.downloaded_assets = set(state.get("downloaded_assets", []))
            self.download_skip_assets = set(state.get("download_skip_assets", []))
            self.next_download_index = int(state.get("download_index", 1))
            self.download_anchor = state.get("download_anchor")
            self.active_prompt_set_id = set_id

            self.config["active_prompt_set"] = set_id
            self.config["prompts_file"] = self.prompt_set_map[set_id].get("file")
            save_config(self.cfg_path, self.config)

        if not initializing:
            self.refresh_summary()
            self.update_status(f"📚 '{self.prompt_set_map[set_id]['label']}' 세트를 불러왔어요.")

    def post_ui(self, callback):
        if self.root.winfo_exists():
            self.root.after(0, callback)

    def _format_seconds_readable(self, seconds: int) -> str:
        seconds = max(0, int(seconds))
        minutes, secs = divmod(seconds, 60)
        if minutes and secs:
            return f"{minutes}분 {secs:02d}초"
        if minutes:
            return f"{minutes}분"
        return f"{secs}초"

    def _set_countdown(self, seconds: Optional[int], message: Optional[str] = None):
        if message is not None:
            text = message
        elif seconds is None:
            text = "대기 시간 —"
        else:
            seconds = max(0, int(seconds))
            minutes, secs = divmod(seconds, 60)
            if minutes:
                text = f"다음 자동 입력까지 {minutes:02d}:{secs:02d}"
            else:
                text = f"다음 자동 입력까지 {secs:02d}초"
        self.post_ui(lambda: self.countdown_var.set(text))

    def _current_remaining_seconds(self) -> Optional[int]:
        if self.next_run_ts is None:
            return None
        return max(0, int(self.next_run_ts - time.time()))

    def _get_interval_seconds(self) -> int:
        return max(30, int(self.config.get("check_interval_seconds", 1500)))

    def _apply_interval_change(self, seconds: int):
        seconds = max(30, min(10800, int(seconds)))
        self.interval_var.set(seconds)
        self.config["check_interval_seconds"] = seconds
        save_config(self.cfg_path, self.config)
        readable = self._format_seconds_readable(seconds)
        logging.info("자동 간격이 %s(%d초)로 설정되었습니다.", readable, seconds)
        self.update_status(f"⏱️ 자동 간격을 {readable}로 설정했어요.")
        if self.scheduler_thread and self.scheduler_thread.is_alive() and not self.stop_requested.is_set():
            self.next_run_ts = time.time() + seconds
            self._set_countdown(seconds)

    def _on_interval_spin(self, event=None):
        try:
            value = int(self.interval_var.get())
        except (ValueError, tk.TclError):
            value = self._get_interval_seconds()
        self._apply_interval_change(value)
        return None

    def _on_interval_spin_return(self, event):
        self._on_interval_spin()
        return "break"

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------
    def on_start(self):
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            messagebox.showinfo("이미 실행 중", "자동 입력이 이미 진행 중이에요 😊")
            return
        if not self.state["remaining_prompts"]:
            messagebox.showwarning("프롬프트 없음", "prompts.txt 에 내용을 작성해 주세요 ✍️")
            return
        self.stop_requested.clear()
        self.paused.clear()
        self.force_run_event.set()
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.update_status("🚀 자동화를 시작했어요. Sora 창을 준비 중입니다…")
        self.next_run_ts = time.time()
        self._set_countdown(0, message="🌟 첫 프롬프트를 준비 중이에요")

    def on_pause(self):
        self.paused.set()
        self.update_status("⏸️ 잠시 쉬는 중이에요.")
        self._set_countdown(None, message="⏸️ 일시정지 중")

    def on_resume(self):
        if not self.scheduler_thread or not self.scheduler_thread.is_alive():
            self.on_start()
            return
        self.paused.clear()
        self.force_run_event.set()
        self.update_status("▶️ 다시 리듬을 타봅시다!")
        remaining = self._current_remaining_seconds()
        if remaining is not None:
            self._set_countdown(remaining)

    def on_force_run(self):
        self.force_run_event.set()
        self.update_status("⚡ 요청하신 대로 지금 바로 다음 프롬프트를 보낼게요!")
        self.next_run_ts = time.time()
        self._set_countdown(0, message="⚡ 곧 바로 실행됩니다")

    def on_skip(self):
        with self.state_lock:
            if not self.state["remaining_prompts"]:
                return
            skipped = self.state["remaining_prompts"].pop(0)
            self.state["skipped_count"] += 1
            hist = self.state.get("history", [])
            hist.append({"p": skipped, "ok": False})
            self.state["history"] = hist[-200:]
            self._save_state()
        logging.info("프롬프트를 건너뛰었습니다: %s", skipped[:60].replace("\n", " "))
        self.refresh_summary()
        self.force_run_event.set()
        self.next_run_ts = time.time()
        self._set_countdown(0, message="🪽 새로운 프롬프트를 곧 실행할게요")

    def on_prev(self):
        with self.state_lock:
            hist = self.state.get("history", [])
            if not hist:
                return
            item = hist.pop()
            prompt = item.get("p", "")
            ok = bool(item.get("ok", False))
            if ok:
                self.state["completed_count"] = max(0, int(self.state.get("completed_count", 0)) - 1)
            else:
                self.state["skipped_count"] = max(0, int(self.state.get("skipped_count", 0)) - 1)
            if prompt:
                self.state.setdefault("remaining_prompts", [])
                self.state["remaining_prompts"].insert(0, prompt)
            self.state["history"] = hist
            self._save_state()
        logging.info("이전으로 되돌림: %s", (prompt or "").replace("\n", " ")[:80])
        self.refresh_summary()
        self.force_run_event.set()
        self.next_run_ts = time.time()
        self._set_countdown(0, message="⏮ 이전 프롬프트로 되돌렸어요")

    def on_reload_prompts(self):
        current_set = self.active_prompt_set_id
        prompts = load_prompts(self._prompt_file_path(current_set), self.config["prompts_separator"])
        with self.state_lock:
            used = set(self.state["remaining_prompts"])
            fresh = [p for p in prompts if p not in used]
            if fresh:
                self.state["remaining_prompts"].extend(fresh)
            elif prompts:
                self.state["remaining_prompts"] = prompts.copy()
            self._save_state()
        logging.info("프롬프트를 다시 읽어왔어요. 남은 개수: %d", len(self.state["remaining_prompts"]))
        self.refresh_summary()

    def on_prompt_set_selected(self, event=None):
        display = self.prompt_set_var.get()
        set_id = self.prompt_label_map.get(display)
        if not set_id or set_id == self.active_prompt_set_id:
            return
        try:
            self._activate_prompt_set(set_id)
        except Exception as exc:
            logging.exception("프롬프트 세트 전환 중 오류가 발생했습니다.")
            messagebox.showerror("세트 전환 실패", f"선택한 세트를 불러오지 못했습니다: {exc}")
            return
        for display, pid in self.prompt_label_map.items():
            if pid == set_id:
                self.prompt_set_var.set(display)
                try:
                    self.prompt_set_combo.set(display)
                except Exception:
                    pass
                break
        self.refresh_summary()
        self.force_run_event.set()

    def on_open_prompt_file(self):
        path = self._prompt_file_path(self.active_prompt_set_id)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            logging.info("프롬프트 파일을 열었습니다: %s", path)
        except Exception as exc:
            logging.exception("프롬프트 파일 열기에 실패했습니다.")
            messagebox.showerror("열기 실패", f"프롬프트 파일을 열지 못했습니다: {exc}")

    def _rebuild_prompt_set_combo(self):
        used = set()
        display_values = []
        self.prompt_label_map = {}
        for idx, info in enumerate(self.prompt_sets, start=1):
            label = (info.get("label") or info.get("id") or f"세트 {idx}").strip()
            display = label if label not in used else f"{label} ({info['id']})"
            used.add(display)
            self.prompt_label_map[display] = info["id"]
            display_values.append(display)
        try:
            self.prompt_set_combo.configure(values=display_values)
        except Exception:
            pass
        for display, sid in self.prompt_label_map.items():
            if sid == self.active_prompt_set_id:
                self.prompt_set_var.set(display)
                try:
                    self.prompt_set_combo.set(display)
                except Exception:
                    pass
                break

    def on_rename_prompt_set(self):
        display = (self.prompt_set_var.get() or "").strip()
        set_id = self.prompt_label_map.get(display) or self.active_prompt_set_id
        info = self.prompt_set_map.get(set_id, {})
        old = info.get("label", set_id)
        new = simpledialog.askstring(APP_NAME, "세트 이름을 입력해 주세요:", initialvalue=old, parent=self.root)
        if not new:
            return
        new = new.strip()
        if not new or new == old:
            return
        info["label"] = new
        for ent in self.prompt_sets:
            if ent.get("id") == set_id:
                ent["label"] = new
                break
        cfg_sets = list(self.config.get("prompt_sets", []))
        for ent in cfg_sets:
            try:
                if ent.get("id") == set_id:
                    ent["label"] = new
                    break
            except Exception:
                continue
        self.config["prompt_sets"] = cfg_sets
        save_config(self.cfg_path, self.config)
        self._rebuild_prompt_set_combo()
        self.refresh_summary()

    def on_toggle_auto_download(self):
        enabled = bool(self.auto_download_var.get())
        self.config["auto_download_enabled"] = enabled
        save_config(self.cfg_path, self.config)
        self.last_download_scan = 0.0
        status = "🎞 자동 다운로드를 켰어요. 새로운 영상이 있는지 살펴볼게요." if enabled else "🎞 자동 다운로드를 잠시 멈출게요."
        self.update_status(status)
        logging.info("자동 다운로드 %s", "활성화" if enabled else "비활성화")
        if enabled:
            self._start_download_worker()
        else:
            self._stop_download_worker()

    def on_mark_download_anchor(self):
        try:
            driver = self._get_driver()
        except Exception as exc:
            logging.error("다운로드 시작 지점을 설정하지 못했습니다: %s", exc)
            self.update_status("Chrome 창과 연결하지 못했어요. 다시 시도해 주세요.")
            return

        try:
            self._navigate_to_sora(driver)
        except Exception:
            pass

        cards = self._find_downloadable_cards(driver)
        if not cards:
            self.update_status("화면에서 다운로드 가능한 영상을 찾지 못했어요. Sora Drafts 목록이 보이도록 해주세요.")
            logging.warning("자동 다운로드 가능한 카드가 없습니다.")
            return

        if self._is_detail_view(driver):
            asset_id = self._extract_detail_asset_id(driver)
            if not asset_id:
                self.update_status("현재 영상 ID를 찾지 못했어요. 페이지를 새로고침하고 다시 시도해 주세요.")
                logging.warning("상세 화면에서 asset id 추출 실패")
                return
            with self.state_lock:
                self.download_anchor = asset_id
                self.download_skip_assets.clear()
                self._save_state()
            self.refresh_summary()
            self.last_download_scan = 0.0
            self.update_status("🎯 지금 열려 있는 영상부터 자동 다운로드를 시작할게요.")
            logging.info("상세 화면에서 자동 다운로드 시작 지점 설정: %s", asset_id)
            return

        hover_card = self._resolve_hover_card(driver)
        hover_asset = self._extract_asset_id(driver, hover_card) if hover_card else None

        card_infos: list[dict] = []
        for item in cards:
            asset_id = self._extract_asset_id(driver, item)
            if not asset_id:
                continue
            try:
                rect = driver.execute_script(
                    "const r = arguments[0].getBoundingClientRect(); return [r.top, r.bottom, r.height];",
                    item,
                )
            except Exception:
                rect = None
            card_infos.append({
                "element": item,
                "asset_id": asset_id,
                "rect": rect,
            })

        if not card_infos:
            self.update_status("카드 정보를 읽어오지 못했어요. 페이지를 새로고침한 뒤 다시 시도해 주세요.")
            logging.warning("자동 다운로드 카드 정보가 비어 있습니다.")
            return

        selected_info = None
        if hover_asset:
            for info in card_infos:
                if info["asset_id"] == hover_asset:
                    selected_info = info
                    break

        if selected_info is None:
            try:
                viewport_mid = float(driver.execute_script(
                    "return (window.innerHeight || document.documentElement.clientHeight || 1080) / 2;"
                ))
            except Exception:
                viewport_mid = 540.0

            best_info = None
            best_score = float("inf")
            for info in card_infos:
                rect = info.get("rect") or [None, None, None]
                top, bottom, height = rect if len(rect) == 3 else (None, None, None)
                if top is None or bottom is None:
                    score = best_score + 1000.0
                else:
                    mid = top + (height or (bottom - top)) / 2.0
                    score = abs(mid - viewport_mid)
                if best_info is None or score < best_score:
                    best_info = info
                    best_score = score
            selected_info = best_info or card_infos[0]

        selected_asset = selected_info["asset_id"]
        skip_assets: list[str] = []
        for info in card_infos:
            aid = info["asset_id"]
            if aid == selected_asset:
                break
            skip_assets.append(aid)

        for info in card_infos:
            aid = info["asset_id"]
            elem = info["element"]
            try:
                if aid in skip_assets:
                    driver.execute_script("arguments[0].setAttribute('data-auto-skip', '1');", elem)
                else:
                    driver.execute_script("arguments[0].removeAttribute('data-auto-skip');", elem)
                if aid == selected_asset:
                    driver.execute_script("arguments[0].removeAttribute('data-auto-downloaded');", elem)
            except Exception:
                continue

        with self.state_lock:
            self.download_anchor = selected_asset
            self.download_skip_assets = set(skip_assets)
            self.download_skip_assets.discard(selected_asset)
            self._save_state()

        self.refresh_summary()
        self.last_download_scan = 0.0
        self.update_status("🎯 화면 가운데 있는 카드부터 자동 다운로드를 이어갈게요.")
        logging.info("자동 다운로드 시작 지점 설정: %s (건너뛸 카드 %d개)", selected_asset, len(skip_assets))

    def on_stop(self):
        self.stop_requested.set()
        self.paused.clear()
        self.force_run_event.set()
        self.update_status("🛑 자동 입력을 멈추고 있어요…")
        self.next_run_ts = None
        self._set_countdown(None, message="🍂 정지 상태")
        self._stop_download_worker()

    # ------------------------------------------------------------------
    # Scheduler loop
    # ------------------------------------------------------------------
    def _scheduler_loop(self):
        next_run_ts = time.time()
        self.next_run_ts = next_run_ts
        self._set_countdown(0, message="✨ 첫 실행을 준비해요")
        status_every = max(5, int(self.config.get("status_update_seconds", 60)))
        while not self.stop_requested.is_set():
            with self.state_lock:
                remaining_prompts = len(self.state.get("remaining_prompts", []))
            if remaining_prompts == 0:
                logging.info("모든 프롬프트 작업이 끝났습니다.")
                self.update_status("🎉 모든 프롬프트를 완료했어요!")
                self._set_countdown(None, message="🎉 완료")
                self.next_run_ts = None
                try:
                    if self.state_path.exists():
                        self.state_path.unlink()
                except Exception:
                    pass
                return

            if self.paused.is_set():
                time.sleep(0.4)
                continue

            now = time.time()
            if self.force_run_event.is_set() or now >= next_run_ts:
                self.force_run_event.clear()
                self.next_run_ts = now
                self._set_countdown(None, message="✨ 프롬프트를 입력하는 중…")
                success = self._execute_cycle()
                if self.stop_requested.is_set():
                    break
                interval = self._get_interval_seconds() if success else 60
                next_run_ts = time.time() + interval
                self.next_run_ts = next_run_ts
                if success:
                    self._set_countdown(interval)
                else:
                    self._set_countdown(interval, message="⚠️ 재시도까지 잠시 대기 중…")
                self.last_status = 0
            else:
                if now - self.last_status >= status_every:
                    remaining_seconds = int(next_run_ts - now)
                    self.update_status(
                        f"⏳ 다음 프롬프트까지 {remaining_seconds}초 남았어요. 다른 창에서 서핑 중이어도 괜찮아요!"
                    )
                    self.last_status = now
                if self.config.get("auto_download_enabled", False):
                    interval = max(2, int(self.config.get("download_check_seconds", 5)))
                    if now - self.last_download_scan >= interval:
                        self.last_download_scan = now
                        try:
                            downloaded = self._attempt_auto_download()
                            if downloaded:
                                self.refresh_summary()
                        except Exception:
                            logging.exception("자동 다운로드 처리 중 오류가 발생했습니다.")
                if self.next_run_ts:
                    self._set_countdown(max(0, int(self.next_run_ts - now)))
                time.sleep(0.4)

        self.update_status("🍃 자동 입력이 종료되었습니다.")
        self._set_countdown(None, message="🍂 정지 상태")
        self.next_run_ts = None
        self._release_driver()

    def _execute_cycle(self) -> bool:
        batch = max(1, int(self.config.get("prompts_per_cycle", 1)))
        success_any = False
        for _ in range(batch):
            with self.state_lock:
                if not self.state["remaining_prompts"]:
                    break
                prompt = self.state["remaining_prompts"][0]
            if self.stop_requested.is_set() or self.paused.is_set():
                break
            ok = self._submit_prompt(prompt)
            with self.state_lock:
                if self.state["remaining_prompts"] and self.state["remaining_prompts"][0] == prompt:
                    self.state["remaining_prompts"].pop(0)
                if ok:
                    self.state["completed_count"] += 1
                else:
                    self.state["skipped_count"] += 1
                hist = self.state.get("history", [])
                hist.append({"p": prompt, "ok": bool(ok)})
                self.state["history"] = hist[-200:]
                self._save_state()
            self.refresh_summary()
            success_any = success_any or ok
            time.sleep(1)
        return success_any

    # ------------------------------------------------------------------
    # Chrome / Selenium helpers
    # ------------------------------------------------------------------
    def _ensure_chrome_ready(self) -> bool:
        port = int(self.config.get("chrome_devtools_port", 9222))
        if self._is_debug_port_alive(port):
            return True
        chrome_path = self._resolve_chrome_path()
        profile_dir = self.base / self.config.get("chrome_profile_dir", "chrome_profile_plus")
        profile_dir.mkdir(parents=True, exist_ok=True)

        flags = [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--profile-directory=CodexSora",
            "--no-first-run",
            "--disable-popup-blocking",
            "--disable-features=TranslateUI",
            "--start-maximized",
        ]
        try:
            subprocess.Popen(flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            logging.error("Chrome 실행에 실패했습니다: %s", exc)
            return False

        self.update_status("🌐 Chrome 창을 준비 중입니다…")
        for _ in range(30):
            if self._is_debug_port_alive(port):
                return True
            time.sleep(1)
        return self._is_debug_port_alive(port)

    def _is_debug_port_alive(self, port: int) -> bool:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1):
                return True
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
            return False

    def _resolve_chrome_path(self) -> str:
        override = self.config.get("chrome_executable", "").strip()
        candidates = []
        if override:
            candidates.append(Path(override))
        candidates.extend(
            [
                Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
                Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
                Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
            ]
        )
        for path in candidates:
            if path and path.exists():
                return str(path)
        raise FileNotFoundError("Chrome 실행 파일을 찾지 못했습니다. sora_config.json 의 chrome_executable 값을 수정해 주세요.")

    def _get_driver(self) -> webdriver.Chrome:
        with self.driver_lock:
            if self.driver:
                try:
                    self.driver.execute_script("return document.readyState;")
                    return self.driver
                except WebDriverException:
                    self.driver = None
            if not self._ensure_chrome_ready():
                raise RuntimeError("Chrome 디버그 세션을 준비하지 못했습니다.")
            options = ChromeOptions()
            options.add_experimental_option(
                "debuggerAddress",
                f"127.0.0.1:{int(self.config.get('chrome_devtools_port', 9222))}"
            )
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(2)
            try:
                download_dir = self._get_download_dir()
                self.driver.execute_cdp_cmd(
                    "Page.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": str(download_dir)},
                )
                logging.debug("Chrome 다운로드 디렉터리를 %s 로 설정했습니다.", download_dir)
            except Exception as exc:
                logging.warning("Chrome 다운로드 디렉터리 설정에 실패했습니다: %s", exc)
            return self.driver

    def _navigate_to_sora(self, driver: webdriver.Chrome):
        target_url = self.config.get("sora_url", "https://sora.chatgpt.com/drafts")
        try:
            if not driver.current_url.startswith("http") or "sora.chatgpt.com" not in driver.current_url:
                driver.get(target_url)
        except Exception:
            driver.get(target_url)

    def _wait_for_prompt_area(self, driver: webdriver.Chrome, timeout: int = 600):
        selectors = [
            "textarea",
            "div[contenteditable='true']",
            "div[role='textbox']",
        ]

        def finder(d):
            for selector in selectors:
                elements = d.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        if element.is_displayed() and element.size.get("height", 0) > 40:
                            return element
                    except Exception:
                        continue
            return False

        try:
            return WebDriverWait(driver, timeout, poll_frequency=1).until(finder)
        except Exception:
            return None

    def _fill_prompt(self, element, prompt: str):
        element.click()
        element.send_keys(Keys.CONTROL, "a")
        time.sleep(0.05)
        element.send_keys(Keys.BACKSPACE)
        time.sleep(0.05)
        lines = prompt.splitlines()
        for idx, line in enumerate(lines):
            if idx > 0:
                element.send_keys(Keys.SHIFT, Keys.ENTER)
                time.sleep(0.05)
            if line:
                element.send_keys(line)
                time.sleep(0.01)
        if not lines:
            element.send_keys(" ")
            time.sleep(0.05)

    def _press_submit(self, driver: webdriver.Chrome, element) -> bool:
        submitted = False
        try:
            element.send_keys(Keys.CONTROL, Keys.ENTER)
            time.sleep(1.0)
            submitted = True
        except Exception:
            pass

        try:
            element.send_keys(Keys.ENTER)
            time.sleep(1.0)
            submitted = True
        except Exception:
            pass

        buttons = driver.find_elements(By.CSS_SELECTOR, "button, [role='button']")
        keywords = [
            "Generate", "Create", "Submit", "Send", "Draft", "Make", "Render",
            "제출", "생성", "작성", "만들기", "보내기", "시작",
        ]
        for button in buttons:
            try:
                if not button.is_displayed():
                    continue
                label = (button.text or "").strip()
                aria = (button.get_attribute("aria-label") or "").strip()
                if any(key.lower() in label.lower() for key in keywords) or any(key.lower() in aria.lower() for key in keywords):
                    button.click()
                    time.sleep(0.4)
                    return True
            except Exception:
                continue

        selectors = list(self.config.get("submit_selectors", []))
        for selector in selectors:
            try:
                targets = driver.find_elements(By.CSS_SELECTOR, selector)
            except Exception:
                continue
            for target in targets:
                try:
                    if not target.is_displayed():
                        continue
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", target)
                    target.click()
                    time.sleep(0.6)
                    return True
                except Exception:
                    continue

        try:
            js_path = self.base / "click_submit_button.js"
            if js_path.exists():
                clicked = driver.execute_script(js_path.read_text(encoding="utf-8"))
                if clicked:
                    time.sleep(0.6)
                    return True
        except Exception:
            pass

        try:
            element.send_keys(Keys.TAB)
            time.sleep(0.1)
            element.send_keys(Keys.ENTER)
            time.sleep(0.4)
            submitted = True
        except Exception:
            pass
        return submitted

    def _submit_prompt(self, prompt: str) -> bool:
        try:
            driver = self._get_driver()
        except Exception as exc:
            logging.error("Chrome 연결에 실패했습니다: %s", exc)
            self.update_status("⚠️ Chrome 연결에 실패했습니다. 잠시 후 다시 시도할게요.")
            return False

        self.update_status("🌐 Sora Drafts와 연결 중…")
        self._navigate_to_sora(driver)

        area = self._wait_for_prompt_area(driver, timeout=120)
        if not area:
            self.update_status("🔐 로그인 화면 같아요. 브라우저에서 로그인 후 다시 시도 버튼을 눌러 주세요.")
            logging.warning("프롬프트 입력 영역을 찾지 못했습니다. 사용자의 로그인이 필요합니다.")
            self.paused.set()
            return False

        try:
            driver.execute_cdp_cmd("Page.bringToFront", {})
            logging.info("Sora 창을 앞으로 가져왔어요.")
        except Exception:
            logging.debug("Sora 창을 앞으로 가져오지 못했습니다.")
        try:
            driver.maximize_window()
        except Exception:
            pass

        logging.info("프롬프트 입력 준비: %s", prompt[:80].replace("\n", " "))
        self.update_status("📝 프롬프트를 입력하고 있어요…")
        try:
            self._fill_prompt(area, prompt)
            submitted = self._press_submit(driver, area)
            if submitted:
                logging.info("프롬프트 제출 명령을 보냈어요.")
                self.update_status("🌟 제출 완료! 다음 작품을 기다리는 중이에요.")
            else:
                logging.warning("프롬프트 제출 버튼을 찾지 못했습니다.")
                self.update_status("⚠️ 버튼을 찾지 못했어요. 잠시 후 다시 시도합니다.")
            return submitted
        except Exception as exc:
            logging.error("프롬프트 제출 중 오류: %s", exc)
            self.update_status("⚠️ 제출에 실패했습니다. 로그를 확인해 주세요.")
            return False
        finally:
            try:
                driver.minimize_window()
            except Exception:
                pass

    @staticmethod
    def _xpath_ci_contains(expr: str, keyword: str) -> str:
        safe = keyword.lower().replace("'", "\\'")
        return f"contains(translate({expr}, '{TRANSLATE_UPPER}', '{TRANSLATE_LOWER}'), '{safe}')"

    def _attempt_auto_download(self) -> int:
        try:
            driver = self._get_driver()
        except Exception as exc:
            logging.debug("자동 다운로드용 Chrome 세션 확보 실패: %s", exc)
            return 0

        try:
            self._navigate_to_sora(driver)
        except Exception:
            pass

        download_dir = self._get_download_dir()
        batch_limit = max(1, int(self.config.get("download_batch_limit", 10)))

        if self._is_detail_view(driver):
            downloads = 0
            processed = 0
            while processed < batch_limit and not self.stop_requested.is_set():
                outcome = self._download_detail_view(driver, download_dir)
                if outcome == "downloaded":
                    downloads += 1
                elif outcome == "retry":
                    time.sleep(0.5)
                    continue
                elif outcome == "skip":
                    pass
                else:
                    break
                processed += 1
            return downloads

        cards = self._find_downloadable_cards(driver)
        if not cards:
            logging.debug("다운로드할 영상 카드가 보이지 않습니다.")
            return 0

        anchor = self.download_anchor
        started = anchor is None
        processed = 0
        new_downloads = 0

        for card in cards:
            if self.stop_requested.is_set() or processed >= batch_limit:
                break
            asset_id = self._extract_asset_id(driver, card)
            if not asset_id:
                continue
            if (
                asset_id in self.download_skip_assets
                or card.get_attribute("data-auto-skip") == "1"
            ) and (anchor is None or asset_id != anchor):
                continue
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", card)
                time.sleep(0.15)
            except Exception:
                pass
            if not started:
                if asset_id == anchor:
                    started = True
                else:
                    continue
            with self.state_lock:
                already_done = asset_id in self.downloaded_assets
            if already_done or card.get_attribute("data-auto-downloaded") == "1":
                continue
            try:
                success = self._download_card(driver, card, asset_id, download_dir)
            except Exception:
                logging.exception("영상 자동 다운로드 중 오류 (asset: %s)", asset_id)
                success = False

            processed += 1
            if success:
                new_downloads += 1
            else:
                if asset_id == anchor:
                    logging.debug("선택한 앵커 카드 다운로드에 실패했습니다. 잠시 후 다시 시도할게요.")
                    break

        return new_downloads

    def _auto_download_loop(self):
        logging.info("자동 다운로드 워커 스레드를 시작합니다.")
        while not self.download_stop_event.is_set():
            if not self.config.get("auto_download_enabled", False):
                time.sleep(1.0)
                continue
            try:
                downloaded = self._attempt_auto_download()
                if downloaded:
                    logging.info("자동 다운로드로 %d개의 영상을 저장했습니다.", downloaded)
                else:
                    logging.debug("자동 다운로드 대상이 없습니다.")
            except Exception:
                logging.exception("자동 다운로드 루프에서 오류가 발생했습니다.")
            interval = max(2, int(self.config.get("download_check_seconds", 5)))
            for _ in range(interval * 10):
                if self.download_stop_event.is_set() or not self.config.get("auto_download_enabled", False):
                    break
                time.sleep(0.1)
        logging.info("자동 다운로드 워커 스레드를 종료합니다.")

    def _find_downloadable_cards(self, driver: webdriver.Chrome) -> list:
        script = """
        const seen = new Set();
        const results = [];
        document.querySelectorAll('video').forEach(video => {
            let holder = video.closest('[data-testid]');
            if (!holder) {
                let current = video.parentElement;
                while (current && current !== document.body) {
                    if (current.dataset && (current.dataset.assetId || current.dataset.draftId)) {
                        holder = current;
                        break;
                    }
                    if (current.hasAttribute && current.hasAttribute('data-testid')) {
                        holder = current;
                        break;
                    }
                    if (current.tagName && current.tagName.toLowerCase() === 'article') {
                        holder = current;
                        break;
                    }
                    current = current.parentElement;
                }
            }
            if (!holder) {
                holder = video.parentElement;
            }
            if (holder instanceof HTMLElement && !seen.has(holder)) {
                seen.add(holder);
                if (!holder.dataset || holder.dataset.autoDownloaded !== '1') {
                    results.push(holder);
                }
            }
        });
        return results;
        """
        try:
            elements = driver.execute_script(script) or []
        except Exception:
            elements = []

        cards = []
        for element in elements:
            try:
                if element.is_displayed():
                    cards.append(element)
            except Exception:
                continue
        return cards

    def _extract_asset_id(self, driver: webdriver.Chrome, card) -> str:
        if card is None:
            return ""
        attrs = [
            card.get_attribute("data-asset-id"),
            card.get_attribute("data-draft-id"),
            card.get_attribute("data-testid"),
            card.get_attribute("data-id"),
            card.get_attribute("id"),
        ]
        for value in attrs:
            if value:
                return value

        try:
            href = driver.execute_script(
                "const card = arguments[0]; const link = card.querySelector('a[href*=\"/drafts/\"]');"
                "return link ? link.getAttribute('href') : '';",
                card,
            )
        except Exception:
            href = ""
        if href:
            return href

        try:
            src = driver.execute_script(
                "const card = arguments[0];"
                "const source = card.querySelector('video source');"
                "if (source && source.src) return source.src;"
                "const video = card.querySelector('video');"
                "return video ? (video.currentSrc || video.src || '') : '';",
                card,
            )
        except Exception:
            src = ""
        if src:
            return src

        try:
            text = driver.execute_script(
                "return (arguments[0].innerText || arguments[0].textContent || '').trim();",
                card,
            )
        except Exception:
            text = ""
        if text:
            digest = hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()
            return f"text-{digest[:16]}"

        return f"asset-{int(time.time() * 1000)}"

    def _download_card(self, driver: webdriver.Chrome, card, asset_id: str, download_dir: Path) -> bool:
        logging.info("자동 다운로드 시도: %s", asset_id)
        snapshot = self._snapshot_downloads(download_dir)

        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", card)
        except Exception:
            pass
        time.sleep(0.2)
        try:
            ActionChains(driver).move_to_element(card).pause(0.1).perform()
        except Exception:
            pass

        more_button = self._find_more_button(driver, card)
        if not more_button:
            logging.debug("⋯ 버튼을 찾지 못했습니다 (asset: %s)", asset_id)
            return False

        try:
            more_button.click()
        except Exception as exc:
            logging.debug("⋯ 버튼 클릭 실패 (asset: %s, error: %s)", asset_id, exc)
            return False
        time.sleep(0.3)

        download_button = self._find_menu_option(driver, ["download video", "download", "다운로드"])
        if not download_button:
            logging.debug("다운로드 메뉴 항목을 찾지 못했습니다 (asset: %s)", asset_id)
            self._send_escape(driver)
            return False

        try:
            download_button.click()
        except Exception as exc:
            logging.debug("다운로드 메뉴 클릭 실패 (asset: %s, error: %s)", asset_id, exc)
            self._send_escape(driver)
            return False

        time.sleep(0.5)

        confirm_button = self._find_menu_option(driver, ["save", "download", "저장", "다운로드"])
        if confirm_button:
            try:
                confirm_button.click()
                time.sleep(0.4)
            except Exception as exc:
                logging.debug("다운로드 확인 버튼 클릭 실패 (asset: %s, error: %s)", asset_id, exc)

        wait_seconds = max(15, int(self.config.get("download_wait_seconds", 180)))
        downloaded_file = self._wait_for_download_file(download_dir, snapshot, wait_seconds)
        self._send_escape(driver)

        if not downloaded_file:
            logging.warning("다운로드 파일을 확인하지 못했습니다 (asset: %s)", asset_id)
            return False

        final_path = self._finalize_download_file(download_dir, downloaded_file)

        with self.state_lock:
            self.downloaded_assets.add(asset_id)
            self.download_skip_assets.discard(asset_id)
            if self.download_anchor == asset_id:
                self.download_anchor = None
            self._save_state()

        try:
            driver.execute_script("arguments[0].setAttribute('data-auto-downloaded', '1');", card)
        except Exception:
            pass
        try:
            driver.execute_script("arguments[0].removeAttribute('data-auto-skip');", card)
        except Exception:
            pass

        self._scroll_to_next_card(driver, card)

        logging.info("다운로드 완료: %s -> %s", asset_id, final_path.name if final_path else downloaded_file.name)
        return True

    def _find_more_button(self, driver: webdriver.Chrome, card):
        keywords = ["more", "ellipsis", "options", "menu"]
        strategies = [
            (By.CSS_SELECTOR, "button[data-testid*='more']"),
            (By.CSS_SELECTOR, "button[data-testid*='More']"),
            (By.CSS_SELECTOR, "button[aria-haspopup='menu']"),
        ]
        for keyword in keywords:
            strategies.append((By.XPATH, f".//button[{self._xpath_ci_contains('@aria-label', keyword)}]"))
            strategies.append((By.XPATH, f".//button[{self._xpath_ci_contains('@title', keyword)}]"))
            strategies.append((By.XPATH, f".//button[{self._xpath_ci_contains('normalize-space(.)', keyword)}]"))

        button = self._find_visible_within(card, strategies)
        if button:
            return button

        try:
            result = driver.execute_script(
                "const card = arguments[0];"
                "const keywords = arguments[1].map(k => k.toLowerCase());"
                "const buttons = card.querySelectorAll('button');"
                "const isVisible = el => !!(el && el.offsetParent !== null);"
                "for (const btn of buttons) {"
                "  if (!isVisible(btn)) continue;"
                "  const text = (btn.innerText || btn.textContent || '').trim().toLowerCase();"
                "  const aria = (btn.getAttribute('aria-label') || '').trim().toLowerCase();"
                "  const dataTest = (btn.getAttribute('data-testid') || '').trim().toLowerCase();"
                "  if (keywords.some(key => (text && text.includes(key)) || (aria && aria.includes(key)) || (dataTest && dataTest.includes(key)))) {"
                "    return btn;"
                "  }"
                "  const svgTitle = btn.querySelector('svg title');"
                "  if (svgTitle) {"
                "    const title = svgTitle.textContent.trim().toLowerCase();"
                "    if (keywords.some(key => title.includes(key))) {"
                "      return btn;"
                "    }"
                "  }"
                "}"
                "return null;",
                card,
                keywords,
            )
            if result:
                return result
        except Exception:
            pass

        return None

    def _is_detail_view(self, driver: webdriver.Chrome) -> bool:
        try:
            if driver.find_elements(By.XPATH, "//button[normalize-space(.)='Post']"):
                return True
        except Exception:
            pass
        url = driver.current_url or ""
        return "/drafts/" in url

    def _extract_detail_asset_id(self, driver: webdriver.Chrome) -> str:
        url = driver.current_url or ""
        candidates: list[str] = []

        if url:
            parsed = urlparse(url)
            path = parsed.path or ""
            if "/drafts/" in path:
                segment = path.split("/drafts/", 1)[1].strip("/")
                if segment:
                    candidates.append(segment)
            query = parse_qs(parsed.query or "")
            for key in ("id", "draft", "draft_id", "draftId", "asset", "asset_id"):
                if key in query and query[key]:
                    candidates.append(query[key][0])
            if parsed.fragment:
                frag = parsed.fragment
                if "/drafts/" in frag:
                    segment = frag.split("/drafts/", 1)[1].strip("/")
                    if segment:
                        candidates.append(segment)

        script = """
        const result = [];
        const push = v => { if (v && typeof v === 'string') result.push(v); };
        const selectors = [
          '[data-asset-id]',
          '[data-draft-id]',
          'a[href*="/drafts/"]',
          'button[data-asset-id]'
        ];
        for (const sel of selectors) {
          document.querySelectorAll(sel).forEach(el => {
            if (el.dataset) {
              if (el.dataset.assetId) push(el.dataset.assetId);
              if (el.dataset.draftId) push(el.dataset.draftId);
            }
            const href = el.getAttribute('href');
            if (href) push(href);
          });
        }
        const video = document.querySelector('video');
        if (video) {
          if (video.dataset) {
            if (video.dataset.assetId) push(video.dataset.assetId);
            if (video.dataset.draftId) push(video.dataset.draftId);
          }
          const src = video.currentSrc || video.src || '';
          if (src) push(src);
          const source = video.querySelector('source');
          if (source && source.src) push(source.src);
        }
        return result;
        """
        try:
            js_candidates = driver.execute_script(script) or []
            if isinstance(js_candidates, list):
                candidates.extend(str(item) for item in js_candidates if item)
        except Exception:
            pass

        for raw in candidates:
            normalized = self._normalize_asset_id(raw)
            if normalized:
                return normalized
        return ""

    def _normalize_asset_id(self, value: str) -> str:
        if not value:
            return ""
        value = unquote(value).strip()
        if not value:
            return ""

        if "/drafts/" in value:
            value = value.split("/drafts/", 1)[1]
        if "https://" in value or "http://" in value:
            parsed = urlparse(value)
            name = Path(parsed.path or "").name
            if name:
                name_only = name.split(".")[0]
                if name_only:
                    return name_only
            hashed = hashlib.sha1(value.encode("utf-8", "ignore")).hexdigest()
            return f"url-{hashed[:16]}"

        value = value.split("?", 1)[0]
        value = value.split("#", 1)[0]
        value = value.strip("/")
        if value:
            return value
        return ""

    def _download_detail_view(self, driver: webdriver.Chrome, download_dir: Path) -> str:
        asset_id = self._extract_detail_asset_id(driver)
        if not asset_id:
            logging.warning("상세 화면에서 영상 ID를 찾지 못했습니다.")
            return "stop"

        logging.debug("상세 화면 다운로드 준비: %s", asset_id)

        with self.state_lock:
            anchor = self.download_anchor

        if anchor and asset_id != anchor:
            logging.debug("설정한 시작 지점(%s)에 아직 도달하지 않았습니다. 현재: %s", anchor, asset_id)
            moved = self._go_to_next_detail(driver, asset_id)
            return "skip" if moved else "stop"

        with self.state_lock:
            if asset_id in self.downloaded_assets:
                logging.debug("이미 다운로드한 상세 영상입니다: %s", asset_id)
                moved = self._go_to_next_detail(driver, asset_id)
                return "skip" if moved else "stop"

        snapshot = self._snapshot_downloads(download_dir)

        try:
            menu_button = self._find_detail_menu_button(driver)
        except Exception:
            menu_button = None
        if not menu_button:
            logging.warning("상세 화면에서 ⋯ 메뉴 버튼을 찾지 못했습니다.")
            self._go_to_next_detail(driver, asset_id)
            return "retry"

        logging.debug("상세 화면 ⋯ 메뉴 버튼을 찾았습니다.")

        try:
            menu_button.click()
        except Exception as exc:
            logging.debug("상세 화면 ⋯ 버튼 클릭 실패: %s", exc)
            return "retry"
        time.sleep(0.3)

        download_button = self._find_menu_option(driver, ["download", "다운로드"])
        if not download_button:
            logging.warning("상세 화면에서 다운로드 메뉴를 찾지 못했습니다.")
            self._send_escape(driver)
            return "retry"

        logging.debug("상세 화면 다운로드 메뉴를 찾았습니다.")

        try:
            download_button.click()
        except Exception as exc:
            logging.debug("상세 화면 다운로드 메뉴 클릭 실패: %s", exc)
            self._send_escape(driver)
            return "retry"

        time.sleep(0.4)

        confirm_button = self._find_menu_option(driver, ["save", "download", "저장", "다운로드"])
        if confirm_button:
            try:
                confirm_button.click()
                time.sleep(0.4)
            except Exception as exc:
                logging.debug("상세 화면 다운로드 확인 버튼 클릭 실패: %s", exc)

        logging.debug("상세 화면 파일 저장 대기 중…")

        wait_seconds = max(15, int(self.config.get("download_wait_seconds", 180)))
        downloaded_file = self._wait_for_download_file(download_dir, snapshot, wait_seconds)
        self._send_escape(driver)

        if not downloaded_file:
            logging.warning("상세 화면 다운로드 파일을 확인하지 못했습니다 (asset: %s)", asset_id)
            return "retry"

        final_path = self._finalize_download_file(download_dir, downloaded_file)

        with self.state_lock:
            self.downloaded_assets.add(asset_id)
            if self.download_anchor == asset_id:
                self.download_anchor = None
            self._save_state()

        logging.info("상세 화면 다운로드 완료: %s -> %s", asset_id, final_path.name if final_path else downloaded_file.name)

        self._go_to_next_detail(driver, asset_id)
        return "downloaded"

    def _find_detail_menu_button(self, driver: webdriver.Chrome):
        script = """
        const prefers = [
          "button[aria-haspopup='menu']",
          "button[aria-label*='More']",
          "button[aria-label*='Options']",
          "button[aria-label*='Actions']",
          "button[title*='More']"
        ];
        const isVisible = (el) => el && el.offsetParent !== null;
        for (const sel of prefers) {
          const buttons = document.querySelectorAll(sel);
          for (const btn of buttons) {
            if (isVisible(btn)) return btn;
          }
        }
        const ellipsis = ['...', '…', '⋮', '⋯'];
        const candidates = Array.from(document.querySelectorAll('button')).filter(btn => {
          if (!isVisible(btn)) return false;
          const textRaw = (btn.innerText || '').trim();
          const ariaRaw = (btn.getAttribute('aria-label') || '').trim();
          const text = textRaw.toLowerCase();
          const aria = ariaRaw.toLowerCase();
          if (ellipsis.includes(textRaw) || ellipsis.includes(ariaRaw)) return true;
          if (ellipsis.some(sym => textRaw.includes(sym) || ariaRaw.includes(sym))) return true;
          if (text.includes('more')) return true;
          if (aria.includes('more')) return true;
          const svg = btn.querySelector('svg');
          if (svg) {
            const title = (svg.getAttribute('aria-label') || '').toLowerCase();
            if (title.includes('more')) return true;
          }
          return false;
        });
        return candidates.length ? candidates[0] : null;
        """
        try:
            return driver.execute_script(script)
        except Exception:
            return None

    def _go_to_next_detail(self, driver: webdriver.Chrome, current_asset: str) -> bool:
        for attempt in range(5):
            try:
                driver.execute_script(
                    "const distance = (window.innerHeight || 800) * 0.6;"
                    "window.scrollBy({top: -distance, behavior: 'instant'});"
                )
            except Exception:
                pass
            try:
                driver.execute_script(
                    "window.dispatchEvent(new WheelEvent('wheel', {deltaY: -120, bubbles: true, cancelable: true}));"
                )
            except Exception:
                pass
            time.sleep(0.8)
            new_asset = self._extract_detail_asset_id(driver)
            if new_asset and new_asset != current_asset:
                logging.debug("상세 화면 다음 영상으로 이동: %s -> %s", current_asset, new_asset)
                return True
        logging.debug("상세 화면에서 다음 영상을 찾지 못했습니다 (현재: %s)", current_asset)
        return False

    def _find_menu_option(self, driver: webdriver.Chrome, keywords: list[str]):
        if not keywords:
            return None
        strategies = []
        for keyword in keywords:
            if not keyword:
                continue
            strategies.extend(
                [
                    (By.XPATH, f"//button[{self._xpath_ci_contains('@aria-label', keyword)}]"),
                    (By.XPATH, f"//button[{self._xpath_ci_contains('normalize-space(.)', keyword)}]"),
                    (By.XPATH, f"//div[@role='menuitem'][{self._xpath_ci_contains('normalize-space(.)', keyword)}]"),
                    (By.XPATH, f"//a[@role='menuitem'][{self._xpath_ci_contains('normalize-space(.)', keyword)}]"),
                ]
            )
        return self._find_visible_global(driver, strategies)

    def _find_visible_within(self, root, strategies):
        if root is None:
            return None
        for by, value in strategies:
            try:
                elements = root.find_elements(by, value)
            except Exception:
                continue
            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    continue
        return None

    def _find_visible_global(self, driver, strategies):
        if not driver:
            return None
        for by, value in strategies:
            try:
                elements = driver.find_elements(by, value)
            except Exception:
                continue
            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    continue
        return None

    def _resolve_hover_card(self, driver: webdriver.Chrome):
        script = """
        const locate = (node) => {
            if (!node) return null;
            if (node.closest) {
                const direct = node.closest('[data-testid]');
                if (direct) return direct;
                const dataset = node.closest('[data-asset-id], [data-draft-id]');
                if (dataset) return dataset;
                const article = node.closest('article');
                if (article) return article;
            }
            let current = node.parentElement;
            while (current && current !== document.body) {
                if (current.dataset && (current.dataset.assetId || current.dataset.draftId)) {
                    return current;
                }
                if (current.hasAttribute && current.hasAttribute('data-testid')) {
                    return current;
                }
                if (current.tagName && current.tagName.toLowerCase() === 'article') {
                    return current;
                }
                current = current.parentElement;
            }
            return null;
        };

        const hovered = Array.from(document.querySelectorAll(':hover')).filter(el => el instanceof HTMLElement);
        for (let i = hovered.length - 1; i >= 0; i--) {
            const card = locate(hovered[i]);
            if (card) return card;
        }

        if (document.activeElement instanceof HTMLElement) {
            const activeCard = locate(document.activeElement);
            if (activeCard) return activeCard;
        }

        const fromPoint = (x, y) => {
            const el = document.elementFromPoint(x, y);
            if (!el) return null;
            return locate(el);
        };

        const width = window.innerWidth || 1200;
        const height = window.innerHeight || 800;
        const points = [
            [width / 2, height * 0.45],
            [width / 2, height * 0.35],
            [width / 2, height * 0.55],
            [width / 2, height * 0.25],
            [width / 2, height * 0.65]
        ];
        for (const [x, y] of points) {
            const card = fromPoint(x, y);
            if (card) return card;
        }

        const videos = Array.from(document.querySelectorAll('video'));
        const seen = new Set();
        const cards = [];
        for (const video of videos) {
            const card = locate(video);
            if (card && !seen.has(card)) {
                seen.add(card);
                cards.push(card);
            }
        }

        const isVisible = (card) => {
            if (!(card instanceof HTMLElement)) return false;
            const rect = card.getBoundingClientRect();
            const margin = Math.min(120, (window.innerHeight || 800) * 0.2);
            return rect.bottom > margin && rect.top < (window.innerHeight || 800) - margin;
        };

        for (const card of cards) {
            if (isVisible(card)) return card;
        }

        return cards.length ? cards[0] : null;
        """
        try:
            return driver.execute_script(script)
        except Exception:
            return None

    def _snapshot_downloads(self, download_dir: Path) -> dict[str, float]:
        snapshot: dict[str, float] = {}
        if not download_dir.exists():
            return snapshot
        for entry in download_dir.iterdir():
            if entry.is_file():
                try:
                    snapshot[entry.name] = entry.stat().st_mtime
                except FileNotFoundError:
                    continue
        return snapshot

    def _wait_for_download_file(self, download_dir: Path, before: dict[str, float], timeout: int) -> Optional[Path]:
        end_ts = time.time() + timeout
        newest_completed: Optional[Path] = None
        while time.time() < end_ts:
            try:
                entries = list(download_dir.iterdir())
            except FileNotFoundError:
                return None
            for entry in entries:
                if not entry.is_file():
                    continue
                name = entry.name
                if name.endswith((".crdownload", ".tmp", ".partial", ".download")):
                    try:
                        base = entry.with_suffix("")
                    except ValueError:
                        base = entry
                    if base.exists() and base.is_file():
                        newest_completed = base
                        return newest_completed
                    continue
                previous = before.get(name)
                try:
                    mtime = entry.stat().st_mtime
                except FileNotFoundError:
                    continue
                if previous is None or mtime > previous + 0.1:
                    newest_completed = entry
                    return newest_completed
            time.sleep(0.5)
        return newest_completed

    def _send_escape(self, driver: Optional[webdriver.Chrome] = None):
        driver = driver or self.driver
        if not driver:
            return
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        except Exception:
            pass

    def _finalize_download_file(self, download_dir: Path, file_path: Path) -> Path:
        ext = file_path.suffix
        if not ext:
            ext = ".mp4"
        elif not ext.startswith("."):
            ext = f".{ext}"
        with self.state_lock:
            index = int(self.next_download_index)
            self.next_download_index = index + 1
        target = self._build_download_target(download_dir, index, ext)
        try:
            file_path.rename(target)
            logging.debug("다운로드 파일 이름을 %s 로 바꿨어요.", target.name)
            return target
        except Exception as exc:
            logging.warning("다운로드 파일 이름 변경 실패 (%s): %s", file_path.name, exc)
            with self.state_lock:
                self.next_download_index = max(1, self.next_download_index - 1)
            return file_path

    def _build_download_target(self, directory: Path, index: int, ext: str) -> Path:
        base = f"sora2auto_{index}"
        candidate = directory / f"{base}{ext}"
        suffix = 1
        while candidate.exists():
            candidate = directory / f"{base}_{suffix}{ext}"
            suffix += 1
        return candidate

    def _scroll_to_next_card(self, driver: webdriver.Chrome, card):
        script = """
        const card = arguments[0];
        if (!card) return;
        const locate = (node) => {
            if (!node) return null;
            const holder = node.closest && (node.closest('[data-testid]') || node.closest('[data-asset-id], [data-draft-id]') || node.closest('article'));
            return holder || null;
        };
        const videos = Array.from(document.querySelectorAll('video'));
        let index = -1;
        const currentVideo = card.querySelector && card.querySelector('video');
        if (currentVideo) {
            index = videos.indexOf(currentVideo);
        }
        for (let i = index + 1; i < videos.length; i++) {
            const nextCard = locate(videos[i]);
            if (nextCard) {
                nextCard.scrollIntoView({behavior: 'smooth', block: 'center'});
                break;
            }
        }
        """
        try:
            driver.execute_script(script, card)
        except Exception:
            pass

    def _save_state(self):
        self.state["downloaded_assets"] = sorted(self.downloaded_assets)
        self.state["download_index"] = int(self.next_download_index)
        self.state["download_anchor"] = self.download_anchor
        self.state["download_skip_assets"] = sorted(self.download_skip_assets)
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _start_download_worker(self):
        if self.download_thread and self.download_thread.is_alive():
            return
        self.download_stop_event.clear()
        self.download_thread = threading.Thread(target=self._auto_download_loop, daemon=True)
        self.download_thread.start()

    def _stop_download_worker(self):
        self.download_stop_event.set()
        thread = self.download_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
        self.download_thread = None

    def _get_download_dir(self) -> Path:
        folder = self.config.get("download_dir", "downloads")
        path = (self.base / folder).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _release_driver(self):
        with self.driver_lock:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        if messagebox.askokcancel("종료", "창을 닫으면 자동 입력이 멈춰요. 정말 종료할까요?"):
            self.on_stop()
            self._release_driver()
            self.root.destroy()


def main():
    try:
        app = SoraAutoApp()
    except Exception as exc:
        messagebox.showerror("치명적 오류", f"프로그램 시작에 실패했습니다: {exc}")
        raise
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"치명적 오류: {e}")
        sys.exit(1)
