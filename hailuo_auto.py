import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


APP_NAME = "Hailuo 자동 – 타이머 내비게이터"

DEFAULT_CONFIG = {
    "prompts_file": "hailuo_prompts.txt",
    "prompts_separator": "|||",
    "check_interval_seconds": 1200,
    "hailuo_url": "https://hailuoai.video/create/text-to-video",
    "chrome_profile_dir": "hailuo_chrome_profile",
    "chrome_executable": "",
    "submit_selectors": [],
    "reset_selectors": [],
    "auto_download_enabled": False,
    "download_dir": "downloads",
    "download_selectors": [],
    "download_wait_seconds": 180,
    "download_index": 1
}


def load_or_create_config(path: Path) -> dict:
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def save_config(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prompts(prompts_path: Path, sep: str) -> list[str]:
    if not prompts_path.exists():
        prompts_path.write_text("", encoding="utf-8")
        return []
    raw = prompts_path.read_text(encoding="utf-8")
    return [p.strip() for p in raw.split(sep) if p.strip()]


class App:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / "hailuo_config.json"
        self.cfg = load_or_create_config(self.cfg_path)

        self.prompts = load_prompts(self.base / self.cfg["prompts_file"], self.cfg["prompts_separator"])
        self.index = 0
        self.running = False
        self.t_next: float | None = None

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("880x600")
        self.root.configure(bg="#14121F")

        self.interval_var = tk.IntVar(value=max(30, min(3600, int(self.cfg.get("check_interval_seconds", 1200)))))
        self.status_var = tk.StringVar(value="대기 중…")

        # selenium state
        self.driver = None
        self.driver_ready = False

        # logging
        self.log_dir = self.base / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / f"hailuo_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.log_file = open(self.log_path, "a", encoding="utf-8")

        self._build_ui()
        self.log(f"{APP_NAME} 시작 – 로그 파일: {self.log_path}")
        self._tick()

    def _build_ui(self):
        top = tk.Frame(self.root, bg="#14121F")
        top.pack(fill="x", padx=12, pady=10)

        ttk.Button(top, text="📄 프롬프트 열기", command=self.on_open).grid(row=0, column=0, padx=6)
        ttk.Button(top, text="🔄 다시불러오기", command=self.on_reload).grid(row=0, column=1, padx=6)
        ttk.Button(top, text="⏮ 이전", command=self.on_prev).grid(row=0, column=2, padx=6)
        ttk.Button(top, text="⏭ 다음", command=self.on_next).grid(row=0, column=3, padx=6)
        ttk.Button(top, text="🌐 Hailuo 열기", command=self.on_open_site).grid(row=0, column=4, padx=(18,6))

        ttk.Button(top, text="🎯 제출 버튼 지정", command=self.on_capture_submit).grid(row=0, column=5, padx=6)
        ttk.Button(top, text="🧹 초기화 버튼 지정", command=self.on_capture_reset).grid(row=0, column=6, padx=6)

        tk.Label(top, text="⏱ 간격(초)", fg="#E7E3FF", bg="#14121F").grid(row=0, column=7, padx=(18,6))
        sp = ttk.Spinbox(top, from_=30, to=3600, increment=30, textvariable=self.interval_var, width=8, justify="center", command=self._on_interval)
        sp.grid(row=0, column=8, padx=6)
        sp.bind("<Return>", lambda e: self._on_interval())

        # Bottom controls (moves big buttons here)
        bottom = tk.Frame(self.root, bg="#14121F")
        bottom.pack(fill="x", padx=12, pady=(2,10))
        ttk.Button(bottom, text="🌠 시작", command=self.on_start).grid(row=0, column=0, padx=6)
        ttk.Button(bottom, text="⚡ 지금 제출", command=self.on_now).grid(row=0, column=1, padx=6)
        ttk.Button(bottom, text="🛑 정지", command=self.on_stop).grid(row=0, column=2, padx=6)
        # download controls
        self.auto_dl_var = tk.BooleanVar(value=bool(self.cfg.get("auto_download_enabled", False)))
        ttk.Checkbutton(bottom, text="🎞 자동 다운로드", variable=self.auto_dl_var, command=self.on_toggle_auto_download).grid(row=0, column=3, padx=(18,6))
        ttk.Button(bottom, text="💾 다운로드 버튼 지정", command=self.on_capture_download).grid(row=0, column=4, padx=6)
        ttk.Button(bottom, text="📁 다운로드 폴더", command=self.on_pick_download_dir).grid(row=0, column=5, padx=6)
        self.auto_next_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bottom, text="⏭ 자동 다음 이동", variable=self.auto_next_var).grid(row=0, column=6, padx=(18,6))

        info = tk.Frame(self.root, bg="#14121F")
        info.pack(fill="x", padx=12)
        self.pos_label = tk.Label(info, text="0 / 0", fg="#B8B2D6", bg="#14121F")
        self.pos_label.pack(side="left")
        self.countdown_label = tk.Label(info, textvariable=self.status_var, fg="#B8B2D6", bg="#14121F")
        self.countdown_label.pack(side="right")

        self.text = ScrolledText(self.root, wrap="word", bg="#0B0614", fg="#FDF7FF", insertbackground="#FDF7FF", font=("Consolas", 12))
        self.text.pack(fill="both", expand=True, padx=12, pady=8)
        self.text.configure(state="disabled")

        self._show()

        # Live log area
        log_frame = tk.Frame(self.root, bg="#14121F")
        log_frame.pack(fill="both", expand=False, padx=12, pady=(0, 10))
        tk.Label(log_frame, text="🌈 라이브 로그", fg="#C7B8FF", bg="#14121F").pack(anchor="w")
        self.log_text = ScrolledText(log_frame, height=10, bg="#0B0614", fg="#FDF7FF", insertbackground="#FDF7FF", relief="flat", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    # -------------- logging helpers --------------
    def log(self, message: str):
        line = f"{datetime.now().strftime('%H:%M:%S')} | {message}"
        try:
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

    def _on_interval(self):
        v = max(30, min(3600, int(self.interval_var.get() or 1200)))
        self.interval_var.set(v)
        self.cfg["check_interval_seconds"] = v
        save_config(self.cfg_path, self.cfg)
        self.status_var.set(f"간격 {v}초 저장")
        if self.running:
            self.t_next = time.time() + v

    def on_open(self):
        p = self.base / self.cfg["prompts_file"]
        try:
            if os.name == "nt":
                os.startfile(str(p))  # type: ignore
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"프롬프트 파일을 열 수 없습니다: {exc}")

    def on_reload(self):
        cur = self.prompts[self.index] if self.prompts and 0 <= self.index < len(self.prompts) else None
        self.prompts = load_prompts(self.base / self.cfg["prompts_file"], self.cfg["prompts_separator"])
        if not self.prompts:
            self.index = 0
        else:
            if cur in self.prompts:
                self.index = self.prompts.index(cur)
            else:
                self.index = min(self.index, len(self.prompts) - 1)
        self._show()
        self.status_var.set("프롬프트 다시불러옴")
        self.log(f"프롬프트 로드: 총 {len(self.prompts)}개")

    def on_prev(self):
        if not self.prompts:
            return
        if self.index > 0:
            self.index -= 1
            self._show()
            if self.running:
                self.t_next = time.time() + int(self.interval_var.get())
            self.log(f"이전으로 이동: {self.index+1}/{len(self.prompts)}")

    def on_next(self):
        if not self.prompts:
            return
        if self.index < len(self.prompts) - 1:
            self.index += 1
            self._show()
            if self.running:
                self.t_next = time.time() + int(self.interval_var.get())
            self.log(f"다음으로 이동: {self.index+1}/{len(self.prompts)}")

    def on_open_site(self):
        try:
            d = self._get_driver()
        except Exception as exc:
            self.status_var.set("Chrome 연결 실패")
            self.log(f"Chrome 연결 실패: {exc}")
            messagebox.showerror(APP_NAME, f"Chrome 연결 실패: {exc}")
            return
        try:
            self._navigate(d)
            self.status_var.set("Hailuo 페이지 열림")
            self.log("Hailuo 페이지 열기 완료")
        except Exception as exc:
            self.status_var.set("페이지 이동 실패")
            self.log(f"페이지 이동 실패: {exc}")

    def on_start(self):
        if not self.prompts:
            messagebox.showwarning(APP_NAME, "프롬프트가 비어 있습니다.")
            return
        self.running = True
        # 즉시 1회 제출하고 타이머 시작
        ok = self._auto_submit_current()
        self.t_next = time.time() + int(self.interval_var.get())
        self.status_var.set("자동 진행 중… (방금 1회 제출 완료)" if ok else "자동 진행 중… (방금 1회 제출 실패)")
        self.log("자동 제출 시작 – 즉시 1회 실행 완료" if ok else "자동 제출 시작 – 즉시 1회 실행 실패")
        if ok and self.auto_next_var.get():
            if self.index < len(self.prompts) - 1:
                self.index += 1
                self._show()

    def on_stop(self):
        self.running = False
        self.t_next = None
        self.status_var.set("정지됨")
        self.log("정지됨")

    def on_now(self):
        ok = self._auto_submit_current()
        self.status_var.set("즉시 제출 완료" if ok else "즉시 제출 실패")
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
        self.text.configure(state="disabled")

    def _tick(self):
        if self.running and self.t_next:
            remain = int(self.t_next - time.time())
            if remain <= 0:
                # Perform auto submit on current prompt; do not auto-advance index.
                ok = self._auto_submit_current()
                self.t_next = time.time() + int(self.interval_var.get())
                if ok and self.auto_next_var.get():
                    if self.index < len(self.prompts) - 1:
                        self.index += 1
                        self._show()
                    else:
                        self.on_stop()
                        self.status_var.set("모든 프롬프트 완료")
                        self.log("모든 프롬프트 완료 – 자동 진행 종료")
                        return
                self.status_var.set("자동 제출 완료" if ok else "자동 제출 실패")
            else:
                self.status_var.set(f"다음까지 {remain}초")
        self.root.after(200, self._tick)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.mainloop()

    # ---------------- Automation helpers ----------------
    def _resolve_chrome_path(self) -> str:
        override = str(self.cfg.get("chrome_executable", "")).strip()
        candidates = []
        if override:
            candidates.append(Path(override))
        candidates += [
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
        ]
        for p in candidates:
            if p and p.exists():
                return str(p)
        raise FileNotFoundError("Chrome 실행 파일을 찾지 못했습니다. hailuo_config.json 의 chrome_executable 값을 확인하세요.")

    def _is_debug_port_alive(self, port: int) -> bool:
        import urllib.request, urllib.error
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1):
                return True
        except Exception:
            return False

    def _ensure_chrome_ready(self, port: int) -> bool:
        if self._is_debug_port_alive(port):
            self.log(f"Chrome 디버그 포트 {port} 감지됨")
            return True
        chrome = self._resolve_chrome_path()
        profile = self.base / self.cfg.get("chrome_profile_dir", "hailuo_chrome_profile")
        profile.mkdir(parents=True, exist_ok=True)
        flags = [
            chrome,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--profile-directory=HailuoMinimal",
            "--no-first-run",
            "--disable-popup-blocking",
            "--disable-features=TranslateUI",
            "--start-maximized",
        ]
        try:
            self.log("Chrome 실행 시도")
            subprocess.Popen(flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            self.log("Chrome 실행 실패")
            return False
        for _ in range(30):
            if self._is_debug_port_alive(port):
                self.log("Chrome 준비 완료")
                return True
            time.sleep(1)
        ok = self._is_debug_port_alive(port)
        self.log("Chrome 준비 실패" if not ok else "Chrome 준비 완료(재확인)")
        return ok

    def _get_driver(self):
        if self.driver and self.driver_ready:
            try:
                self.driver.execute_script("return document.readyState;")
                return self.driver
            except Exception:
                self.driver = None
                self.driver_ready = False
        port = 9333
        if not self._ensure_chrome_ready(port):
            self.log("Chrome 디버그 세션 시작 실패")
            raise RuntimeError("Chrome 디버그 세션을 시작하지 못했습니다.")
        options = ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(2)
        self.driver_ready = True
        self.log("Chrome 세션 연결 완료")
        return self.driver

    def _navigate(self, d):
        url = self.cfg.get("hailuo_url", "https://hailuoai.video/create/text-to-video")
        try:
            if "hailuoai.video" not in (d.current_url or ""):
                d.get(url)
        except Exception:
            d.get(url)

    def _wait_input(self, d, timeout=60):
        sels = ["textarea", "div[contenteditable='true']", "div[role='textbox']"]
        def finder(_d):
            for s in sels:
                els = _d.find_elements(By.CSS_SELECTOR, s)
                for el in els:
                    try:
                        if el.is_displayed() and el.size.get("height", 0) >= 30:
                            return el
                    except Exception:
                        continue
            return False
        try:
            return WebDriverWait(d, timeout, poll_frequency=1).until(finder)
        except Exception:
            return None

    def _press_reset(self, d, el):
        for sel in list(self.cfg.get("reset_selectors", [])):
            try:
                for b in d.find_elements(By.CSS_SELECTOR, sel):
                    if b.is_displayed() and b.is_enabled():
                        try:
                            b.click(); return True
                        except Exception:
                            try: d.execute_script("arguments[0].click();", b); return True
                            except Exception: pass
            except Exception:
                continue
        # fallback clear
        try:
            el.click(); el.send_keys(Keys.CONTROL, "a"); time.sleep(0.05); el.send_keys(Keys.BACKSPACE); time.sleep(0.05)
            return True
        except Exception:
            return False

    def _sanitize_bmp(self, s: str) -> str:
        # Remove non-BMP characters (e.g., some emoji) to avoid ChromeDriver errors
        return "".join(ch for ch in s if ord(ch) <= 0xFFFF)

    def _fill_via_keys(self, d, el, text: str):
        # Strictly use keyboard input so counters (0/2000) update correctly
        text = self._sanitize_bmp(text)
        try:
            el.click()
            el.send_keys(Keys.CONTROL, "a")
            time.sleep(0.05)
            el.send_keys(Keys.BACKSPACE)
            time.sleep(0.05)
            lines = text.splitlines()
            for idx, line in enumerate(lines):
                if idx > 0:
                    try:
                        el.send_keys(Keys.SHIFT, Keys.ENTER)
                    except Exception:
                        el.send_keys(Keys.ENTER)
                    time.sleep(0.02)
                if line:
                    el.send_keys(line)
                    time.sleep(0.01)
            if not lines:
                el.send_keys(" ")
                time.sleep(0.02)
            # Nudge input to ensure framework updates (optional)
            try:
                el.send_keys(" ")
                el.send_keys(Keys.BACKSPACE)
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _press_submit(self, d, el):
        for sel in list(self.cfg.get("submit_selectors", [])):
            try:
                for b in d.find_elements(By.CSS_SELECTOR, sel):
                    if b.is_displayed() and b.is_enabled():
                        try:
                            b.click(); return True
                        except Exception:
                            try: d.execute_script("arguments[0].click();", b); return True
                            except Exception: pass
            except Exception:
                continue
        # fallback keyboard
        for seq in [(Keys.CONTROL, Keys.ENTER), (Keys.ENTER,)]:
            try:
                el.send_keys(*seq); time.sleep(0.6); return True
            except Exception:
                continue
        return False

    def _auto_submit_current(self):
        if not self.prompts:
            return False
        try:
            d = self._get_driver()
        except Exception as exc:
            self.status_var.set(f"Chrome 오류: {exc}")
            return False
        self._navigate(d)
        el = self._wait_input(d, timeout=60)
        if not el:
            self.status_var.set("입력창 미발견")
            self.log("입력창을 찾지 못했습니다")
            return False
        # reset before input
        self.log("초기화 시도")
        self._press_reset(d, el)
        text = self.prompts[self.index]
        ok_fill = self._fill_via_keys(d, el, text)
        if not ok_fill:
            self.status_var.set("입력 실패")
            self.log("입력 실패")
            return False
        self.log(f"입력 완료({len(text)}자), 제출 시도")
        ok_submit = self._press_submit(d, el)
        self.log("제출 성공" if ok_submit else "제출 실패")
        # Auto-download if enabled
        if ok_submit and bool(self.cfg.get("auto_download_enabled", False)):
            try:
                self._attempt_download()
            except Exception as exc:
                self.log(f"자동 다운로드 중 오류: {exc}")
        return ok_submit

    # -------------- download helpers --------------
    def _get_download_dir(self) -> Path:
        d = Path(self.cfg.get("download_dir", str(self.base / "downloads")))
        d.mkdir(parents=True, exist_ok=True)
        return d

    def on_pick_download_dir(self):
        cur = str(self._get_download_dir())
        try:
            chosen = filedialog.askdirectory(initialdir=cur, title="다운로드 폴더 선택")
        except Exception:
            chosen = None
        if not chosen:
            return
        self.cfg["download_dir"] = chosen
        save_config(self.cfg_path, self.cfg)
        self.status_var.set(f"다운로드 폴더: {chosen}")
        self.log(f"다운로드 폴더 선택: {chosen}")

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
                    if p.is_file() and not str(p).endswith('.crdownload') and p.name not in before:
                        return p
            except Exception:
                pass
            time.sleep(0.5)
        return None

    def _finalize_download(self, p: Path) -> Path:
        try:
            idx = int(self.cfg.get("download_index", 1))
            self.cfg["download_index"] = idx + 1
            save_config(self.cfg_path, self.cfg)
            ext = p.suffix or ".bin"
            target = p.with_name(f"hailuo_{idx}{ext}")
            try:
                if target.exists():
                    target.unlink()
            except Exception:
                pass
            p.rename(target)
            return target
        except Exception:
            return p

    def _attempt_download(self) -> bool:
        sels = list(self.cfg.get("download_selectors", []))
        if not sels:
            return False
        try:
            d = self._get_driver()
        except Exception as exc:
            self.log(f"Chrome 연결 실패(다운로드): {exc}")
            return False
        self._navigate(d)
        dl_dir = self._get_download_dir()
        snap = self._snapshot_files(dl_dir)
        clicked = False
        for sel in sels:
            try:
                for b in d.find_elements(By.CSS_SELECTOR, sel):
                    if b.is_displayed() and b.is_enabled():
                        try:
                            b.click(); clicked = True; break
                        except Exception:
                            try: d.execute_script("arguments[0].click();", b); clicked = True; break
                            except Exception: pass
                if clicked: break
            except Exception:
                continue
        if not clicked:
            self.log("다운로드 버튼을 찾지 못했습니다")
            return False
        wait = max(5, int(self.cfg.get("download_wait_seconds", 180)))
        newf = self._wait_new_file(dl_dir, snap, wait)
        if not newf:
            self.log("다운로드 파일 감지 실패")
            return False
        final = self._finalize_download(newf)
        self.log(f"다운로드 완료: {final.name}")
        # wheel up to next
        delta = int(self.cfg.get("wheel_scroll_delta", 800))
        js = """
        (function(){
          var delta = arguments[0] || 800;
          try {
            var el = document.scrollingElement || document.documentElement || document.body;
            el.scrollBy({top: -delta, left: 0, behavior: 'instant'});
            var evt = new WheelEvent('wheel', {deltaY: -delta, bubbles: true});
            (document.elementFromPoint(window.innerWidth/2, 20) || el).dispatchEvent(evt);
          } catch (e) {}
          try { window.scrollBy(0, -delta); } catch (e) {}
        })();
        """
        try:
            d.execute_script(js, delta)
        except Exception:
            pass
        return True

    def on_toggle_auto_download(self):
        enabled = bool(self.auto_dl_var.get())
        self.cfg["auto_download_enabled"] = enabled
        save_config(self.cfg_path, self.cfg)
        self.status_var.set("자동 다운로드 켬" if enabled else "자동 다운로드 끔")
        self.log("자동 다운로드 켬" if enabled else "자동 다운로드 끔")

    # -------------- capture selectors --------------
    def on_capture_submit(self):
        self._capture_button(kind="submit")

    def on_capture_reset(self):
        self._capture_button(kind="reset")

    def on_capture_download(self):
        self._capture_button(kind="download")

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
          if (window.__cap && window.__cap.active) return;
          function cssEscape(s){ return (window.CSS&&CSS.escape)?CSS.escape(s):s.replace(/([#.;,:+*~'>"\[\]\(\) ])/g,'\\$1'); }
          function uniqueSelector(el){
            if(!el) return '';
            const attrs=['data-testid','aria-label','data-id','id','name','type'];
            for(const a of attrs){ try{ const v=el.getAttribute(a); if(v){ if(a==='id') return '#'+cssEscape(v); return el.tagName.toLowerCase()+'['+a+'="'+String(v).replace(/"/g,'\\"')+'"]'; } }catch(e){} }
            const parts=[]; let n=el, depth=0; while(n&&n.nodeType===1&&n!==document.body&&depth<6){ let p=n.tagName.toLowerCase(); const cls=(n.className||'').trim().split(/\s+/).filter(Boolean); if(cls.length&&cls.join('').length<40){ p+='.'+cls.map(cssEscape).join('.'); } else { let i=1,s=n; while((s=s.previousElementSibling)!=null){ if(s.tagName===n.tagName) i++; } p+=':nth-of-type('+i+')'; } parts.unshift(p); if(n.id){ parts.unshift('#'+cssEscape(n.id)); break;} n=n.parentElement; depth++; } return parts.join(' > ');
          }
          const style=document.createElement('style'); style.textContent='.__cap_mark{outline:2px solid #ff3b3b!important;cursor: crosshair!important;}'; document.documentElement.appendChild(style);
          const state={active:true,done:false,cancel:false,sel:'',prev:null,cleanup(){
            ['mouseover','mouseout','click','mousedown','mouseup','pointerdown','pointerup','keydown'].forEach(ev=>document.removeEventListener(ev,handler,true));
            try{style.remove();}catch(e){}
            try{ if(state.prev) state.prev.classList.remove('__cap_mark'); }catch(e){}
            state.active=false;
          }};
          function handler(e){
            if(e.type==='mouseover'){
              try{ if(state.prev) state.prev.classList.remove('__cap_mark'); state.prev=e.target; e.target.classList.add('__cap_mark'); }catch(err){}
              return;
            }
            if(e.type==='mouseout'){
              try{ e.target.classList.remove('__cap_mark'); }catch(err){}
              return;
            }
            if(e.type==='keydown'){
              if(e.key==='Escape'){ e.preventDefault(); e.stopPropagation(); state.cancel=true; state.done=true; state.cleanup(); window.__cap=state; return; }
              if(e.key==='Enter' || e.key.toLowerCase()==='s'){
                e.preventDefault(); e.stopPropagation();
                const t=state.prev; state.sel=uniqueSelector(t); state.done=true; state.cleanup(); window.__cap=state; return;
              }
              return;
            }
            // Block real clicks from reaching page scripts while capturing
            if(e.type==='click' || e.type==='mousedown' || e.type==='mouseup' || e.type==='pointerdown' || e.type==='pointerup'){
              e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
              return;
            }
          }
          ['mouseover','mouseout','click','mousedown','mouseup','pointerdown','pointerup','keydown'].forEach(ev=>document.addEventListener(ev,handler,true));
          window.__cap=state;
        })();
        """
        try:
            d.execute_script(js)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"캡쳐 스크립트 실패: {exc}")
            return
        self.status_var.set("원하는 버튼 위로 마우스 이동 후 Enter (Esc 취소)")
        start = time.time(); picked = None
        while time.time() - start < 60:
            try:
                res = d.execute_script("return window.__cap && window.__cap.done ? {sel: window.__cap.sel, cancel: window.__cap.cancel} : null;")
            except Exception:
                res = None
            if res:
                if res.get('cancel'):
                    self.status_var.set("지정 취소됨"); return
                picked = (res.get('sel') or '').strip(); break
            time.sleep(0.1)
        if not picked:
            self.status_var.set("시간 초과")
            return
        if kind == 'submit':
            key = 'submit_selectors'
        elif kind == 'reset':
            key = 'reset_selectors'
        elif kind == 'download':
            key = 'download_selectors'
        else:
            key = kind
        cur = list(self.cfg.get(key, []))
        self.cfg[key] = [picked] + [s for s in cur if s != picked]
        save_config(self.cfg_path, self.cfg)
        label = '제출' if key=='submit_selectors' else ('초기화' if key=='reset_selectors' else '다운로드')
        self.status_var.set(f"{label} 버튼 지정: {picked}")


if __name__ == "__main__":
    App().run()
