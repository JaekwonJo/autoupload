import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk, filedialog, simpledialog
from tkinter.scrolledtext import ScrolledText

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# ------------------------------------------------------------------------------
# 🎨 CONFIG & CONSTANTS
# ------------------------------------------------------------------------------
APP_NAME = "Flow Studio Ultimate v9.0 (Final Fix)"

C_BG = "#121212"
C_PANEL = "#1e1e2e"
C_TEXT = "#e0e0e0"
C_ACCENT = "#bb9af7"
C_GREEN = "#73daca"
C_RED = "#f7768e"
C_WARN = "#e0af68"
C_BTN_TXT = "#1a1b26"
C_HIGHLIGHT = "#f7768e"
C_SLOT_BG = "#292e42"
C_SLOT_ACTIVE = "#7aa2f7"

DEFAULT_FLOW_URL = "https://labs.google/fx/ko/tools/flow"

DEFAULT_CONFIG = {
    "prompts_file": "flow_prompts.txt",
    "prompts_separator": "|||",
    "check_interval_seconds": 180,
    "flow_project_url": "",
    "chrome_profile_dir": "../flow/flow_chrome_profile",
    "chrome_devtools_port": 9555,
    "chrome_executable": "",
    "download_dir": "",
    "input_selectors": [],
    "submit_selectors": [],
    "dl_icon_selectors": [],
    "dl_file_selectors": [],
    "auto_screenshot": True,
    "slot_names": [f"Slot {i+1}" for i in range(10)]
}

# ------------------------------------------------------------------------------
# 🕹️ CAPTURE SCRIPT
# ------------------------------------------------------------------------------
JS_CAPTURE_TOOL = """
(function() {
    if (window.__cap_active) return;
    window.__cap_active = true;
    window.__cap_result = null;

    const style = document.createElement('style');
    style.id = '__cap_style';
    style.textContent = `
        .__cap_hover, .__cap_hover * { 
            outline: 4px solid #f7768e !important; 
            box-shadow: 0 0 10px #f7768e !important;
            cursor: crosshair !important; 
        }
        .__cap_overlay { 
            position: fixed; top: 0; left: 0; padding: 10px 20px; 
            background: #f7768e; color: white; font-size: 16px; 
            z-index: 2147483647; font-family: sans-serif; font-weight: bold; 
            border-bottom-right-radius: 8px; pointer-events: none; 
        }
    `;
    document.head.appendChild(style);

    const overlay = document.createElement('div');
    overlay.className = '__cap_overlay';
    overlay.textContent = '🎯 TARGET MODE: Hover & Enter (Menus Clickable)';
    document.body.appendChild(overlay);

    let lastEl = null;

    function getSelector(el) {
        if (!el) return '';
        if (el.id) return '#' + CSS.escape(el.id);
        
        const attrs = ['data-testid', 'aria-label', 'name', 'role', 'type', 'placeholder'];
        for (let a of attrs) {
            if (el.hasAttribute(a)) {
                return el.tagName.toLowerCase() + '[' + a + '="' + CSS.escape(el.getAttribute(a)) + '"]';
            }
        }
        
        let path = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let sel = el.tagName.toLowerCase();
            if (el.className && typeof el.className === 'string') {
                const classes = el.className.trim().split(/\s+/).filter(c => !c.startsWith('__cap'));
                if (classes.length > 0) sel += '.' + classes.map(CSS.escape).join('.');
            }
            if (el.id) {
                sel = '#' + CSS.escape(el.id);
                path.unshift(sel);
                break;
            }
            let sib = el, nth = 1;
            while (sib = sib.previousElementSibling) {
                if (sib.tagName.toLowerCase() === sel.split('.')[0]) nth++;
            }
            if (nth > 1) sel += ':nth-of-type(' + nth + ')';
            path.unshift(sel);
            el = el.parentNode;
        }
        return path.join(' > ');
    }

    function handler(e) {
        if (e.type === 'click' || e.type === 'mousedown' || e.type === 'mouseup') return;
        e.preventDefault();
        e.stopPropagation();

        if (e.type === 'mouseover') {
            if (lastEl) lastEl.classList.remove('__cap_hover');
            e.target.classList.add('__cap_hover');
            lastEl = e.target;
        }
        else if (e.type === 'keydown') {
            if (e.key === 'Enter' && lastEl) {
                window.__cap_result = getSelector(lastEl);
                cleanup();
            } else if (e.key === 'Escape') {
                window.__cap_result = 'CANCELLED';
                cleanup();
            }
        }
    }

    function cleanup() {
        ['mouseover', 'keydown'].forEach(ev => window.removeEventListener(ev, handler, true));
        if (lastEl) lastEl.classList.remove('__cap_hover');
        const s = document.getElementById('__cap_style');
        if (s) s.remove();
        overlay.remove();
        window.__cap_active = false;
    }

    ['mouseover', 'keydown'].forEach(ev => window.addEventListener(ev, handler, true));
})();
"""

# ------------------------------------------------------------------------------
# 🛠️ HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def load_config(path):
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg: cfg[k] = v
        return cfg
    except:
        return DEFAULT_CONFIG.copy()

def save_config(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def now_str():
    return datetime.now().strftime("%H:%M:%S")

# ------------------------------------------------------------------------------
# 🧠 MAIN APPLICATION
# ------------------------------------------------------------------------------
class FlowApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1300x950") # Increased height
        self.root.configure(bg=C_BG)
        
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / "flow_config.json"
        self.cfg = load_config(self.cfg_path)
        
        self.shot_dir = self.base / "screenshots"
        self.shot_dir.mkdir(exist_ok=True)
        
        self.slot_dir = self.base / "flow_slots"
        self.slot_dir.mkdir(exist_ok=True)

        self.prompts = []
        self.current_idx = 0
        self.running = False
        self.next_run_time = 0
        self.driver = None
        self.start_time = None
        self.cnt_success = 0
        self.cnt_fail = 0
        self.current_slot_id = -1

        self.setup_styles()
        self.setup_layout()
        
        self.log("시스템 준비 완료. 슬롯을 선택해주세요.")
        self.check_connection_loop()
        self.root.after(500, self.tick)

    def setup_styles(self):
        s = ttk.Style()
        s.theme_use('clam')
        s.configure("TFrame", background=C_BG)
        s.configure("Panel.TFrame", background=C_PANEL, relief="flat")
        s.configure("TButton", font=("Malgun Gothic", 10, "bold"), borderwidth=0)
        
        s.configure("Action.TButton", background=C_ACCENT, foreground=C_BTN_TXT)
        s.map("Action.TButton", background=[('active', '#9d7cd8')])
        s.configure("Start.TButton", background=C_GREEN, foreground=C_BTN_TXT, font=("Malgun Gothic", 12, "bold"))
        s.map("Start.TButton", background=[('active', '#41a6b5')])
        s.configure("Stop.TButton", background=C_RED, foreground=C_BTN_TXT, font=("Malgun Gothic", 12, "bold"))
        s.map("Stop.TButton", background=[('active', '#db4b4b')])
        s.configure("Target.TButton", background="#ff9e64", foreground=C_BTN_TXT, font=("Malgun Gothic", 9, "bold"))
        s.map("Target.TButton", background=[('active', '#ffb380')])
        s.configure("Settings.TButton", background="#414868", foreground="#c0caf5", font=("Malgun Gothic", 10))
        s.configure("Download.TButton", background="#7dcfff", foreground=C_BTN_TXT, font=("Malgun Gothic", 10, "bold"))
        s.configure("TCheckbutton", background=C_PANEL, foreground=C_TEXT, font=("Malgun Gothic", 10))
        
        s.configure("Slot.TButton", background=C_SLOT_BG, foreground="white", font=("Malgun Gothic", 9))
        s.map("Slot.TButton", background=[('active', '#3b4261'), ('pressed', C_SLOT_ACTIVE)])
        s.configure("SlotActive.TButton", background=C_SLOT_ACTIVE, foreground="black", font=("Malgun Gothic", 9, "bold"))

    def setup_layout(self):
        # Left Panel
        left_panel = ttk.Frame(self.root, style="Panel.TFrame", width=340)
        left_panel.pack(side="left", fill="y", padx=10, pady=10)
        
        tk.Label(left_panel, text="FLOW STUDIO", font=("Impact", 28), bg=C_PANEL, fg=C_ACCENT).pack(pady=(30, 5))
        tk.Label(left_panel, text="Ultimate Automation v9.0", font=("Arial", 10), bg=C_PANEL, fg="gray").pack(pady=(0, 20))
        
        tk.Label(left_panel, text="⏳ 다음 작업까지", font=("Malgun Gothic", 11), bg=C_PANEL, fg=C_TEXT).pack()
        self.lbl_next = tk.Label(left_panel, text="--:--", font=("Consolas", 40, "bold"), bg=C_PANEL, fg=C_GREEN)
        self.lbl_next.pack(pady=5)
        
        tk.Label(left_panel, text="🏁 전체 완료까지", font=("Malgun Gothic", 11), bg=C_PANEL, fg=C_TEXT).pack(pady=(15, 0))
        self.lbl_total = tk.Label(left_panel, text="--:--:--", font=("Consolas", 22), bg=C_PANEL, fg=C_WARN)
        self.lbl_total.pack(pady=5)
        
        # Control Box
        ctrl_box = tk.Frame(left_panel, bg=C_PANEL)
        ctrl_box.pack(fill="x", padx=20, pady=15)
        tk.Label(ctrl_box, text="간격(초):", bg=C_PANEL, fg=C_TEXT).pack(anchor="w")
        self.var_interval = tk.IntVar(value=self.cfg.get("check_interval_seconds", 180))
        ttk.Spinbox(ctrl_box, from_=10, to=9999, textvariable=self.var_interval).pack(fill="x", pady=(0, 10))
        self.btn_start = ttk.Button(ctrl_box, text="▶ 자동 시작", style="Start.TButton", command=self.start_auto)
        self.btn_start.pack(fill="x", pady=5)
        self.btn_stop = ttk.Button(ctrl_box, text="⏹ 정지", style="Stop.TButton", command=self.stop_auto, state="disabled")
        self.btn_stop.pack(fill="x", pady=5)
        ttk.Button(ctrl_box, text="⚡ 1회 즉시 실행", style="Action.TButton", command=self.run_once).pack(fill="x", pady=(10, 0))

        # Download Box
        dl_box = tk.LabelFrame(left_panel, text=" 📥 수확(Download) ", bg=C_PANEL, fg="#7dcfff", font=("Malgun Gothic", 10, "bold"))
        dl_box.pack(fill="x", padx=20, pady=15)
        ttk.Button(dl_box, text="📥 자동 수확 시작", style="Download.TButton", command=self.start_harvest).pack(fill="x", padx=10, pady=10)

        # Target Box
        target_box = tk.LabelFrame(left_panel, text=" 🎯 타겟 설정 ", bg=C_PANEL, fg=C_HIGHLIGHT, font=("Malgun Gothic", 10, "bold"))
        target_box.pack(fill="x", padx=20, pady=5)
        f_tgt = tk.Frame(target_box, bg=C_PANEL)
        f_tgt.pack(fill="x", padx=5, pady=5)
        ttk.Button(f_tgt, text="⌨️ 입력", style="Target.TButton", command=self.capture_input).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(f_tgt, text="🖱️ 전송", style="Target.TButton", command=self.capture_submit).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ttk.Button(f_tgt, text="📥 1차", style="Target.TButton", command=self.capture_dl_icon).grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(f_tgt, text="📀 2차", style="Target.TButton", command=self.capture_dl_file).grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        f_tgt.grid_columnconfigure(0, weight=1); f_tgt.grid_columnconfigure(1, weight=1)

        # Right Panel
        right_panel = tk.Frame(self.root, bg=C_BG)
        right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Slots
        slot_frame = tk.LabelFrame(right_panel, text=" 📁 프롬프트 퀵 슬롯 (클릭하여 메모장 열기) ", bg=C_BG, fg=C_TEXT, font=("Malgun Gothic", 11, "bold"))
        slot_frame.pack(fill="x", pady=(0, 10))
        self.slot_btns = []
        grid_f = tk.Frame(slot_frame, bg=C_BG)
        grid_f.pack(fill="x", padx=10, pady=10)
        for i in range(10):
            f = tk.Frame(grid_f, bg=C_BG)
            f.grid(row=i//5, column=i%5, padx=5, pady=5, sticky="ew")
            grid_f.grid_columnconfigure(i%5, weight=1)
            name = self.cfg["slot_names"][i]
            btn = ttk.Button(f, text=name, style="Slot.TButton", command=lambda x=i: self.on_click_slot(x))
            btn.pack(side="left", fill="x", expand=True)
            ren_btn = tk.Button(f, text="✏️", bg="#3b4261", fg="white", bd=0, font=("Arial", 10, "bold"), width=3, cursor="hand2",
                                activebackground="#7aa2f7", activeforeground="black",
                                command=lambda x=i: self.rename_slot(x))
            ren_btn.pack(side="right", padx=(3, 0))
            self.slot_btns.append(btn)

        # Top Buttons
        btn_bar = tk.Frame(right_panel, bg=C_BG)
        btn_bar.pack(fill="x", pady=(5, 10))
        
        # BIG FLOW BUTTON
        ttk.Button(btn_bar, text="🌐 Flow 사이트 열기", style="Download.TButton", command=self.open_site).pack(side="left", padx=5)
        ttk.Button(btn_bar, text="⚙️ 설정", style="Settings.TButton", command=self.open_settings).pack(side="left", padx=5)
        ttk.Button(btn_bar, text="💾 목록 저장", style="Action.TButton", command=self.on_save_as).pack(side="left", padx=5)

        # List
        self.list_frame = tk.Frame(right_panel, bg=C_PANEL)
        self.list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(self.list_frame, bg="#252535", fg="#ffffff", font=("Malgun Gothic", 11),
                                  selectbackground=C_ACCENT, selectforeground="black",
                                  relief="flat", borderwidth=0, highlightthickness=0)
        self.listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        sb = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=sb.set)
        
        # Editor & Logs
        tk.Label(right_panel, text="✏️ 편집", font=("Malgun Gothic", 10), bg=C_BG, fg="gray").pack(anchor="w", pady=(5, 0))
        self.editor = ScrolledText(right_panel, height=4, bg="#252535", fg="white", insertbackground="white", font=("Consolas", 10))
        self.editor.pack(fill="x")
        ttk.Button(right_panel, text="✅ 수정 적용", style="Action.TButton", command=self.on_apply_edit).pack(anchor="e", pady=5)
        
        tk.Label(right_panel, text="📟 시스템 로그", font=("Malgun Gothic", 10), bg=C_BG, fg="gray").pack(anchor="w", pady=(5, 0))
        self.log_box = ScrolledText(right_panel, height=6, bg="black", fg="#00ff00", font=("Consolas", 9), state="disabled")
        self.log_box.pack(fill="x")
        
        # Status Bar
        self.status_bar = tk.Label(right_panel, text="🔴 크롬 연결 안됨", bg="#330000", fg="white", font=("Malgun Gothic", 10, "bold"), height=2)
        self.status_bar.pack(fill="x", pady=(5, 0))

    def run(self): self.root.mainloop()

    # --------------------------------------------------------------------------
    # LOGIC
    # --------------------------------------------------------------------------
    def check_connection_loop(self):
        try:
            if self.driver and self.driver.title:
                self.status_bar.config(text="🟢 크롬 연결됨", bg="#003300")
            else:
                self.status_bar.config(text="🔴 크롬 연결 안됨", bg="#330000")
        except:
            self.status_bar.config(text="🔴 크롬 연결 안됨", bg="#330000")
        self.root.after(2000, self.check_connection_loop)

    def on_click_slot(self, slot_idx):
        self.log(f"📂 슬롯 {slot_idx+1}번 선택됨.")
        slot_file = self.slot_dir / f"slot_{slot_idx+1}.txt"
        if not slot_file.exists(): slot_file.write_text("", encoding="utf-8")
        self.log("📝 메모장을 엽니다...")
        try: subprocess.run(["notepad.exe", str(slot_file)])
        except: pass
        try:
            text = slot_file.read_text(encoding="utf-8")
            sep = self.cfg.get("prompts_separator", "|||")
            self.prompts = [p.strip() for p in text.split(sep) if p.strip()]
            self.current_idx = 0; self.current_slot_id = slot_idx
            self.refresh_list(); self.update_slot_buttons()
            self.log(f"✅ 슬롯 {slot_idx+1} 로드 완료: {len(self.prompts)}개")
        except Exception as e: self.log(f"오류: {e}")

    def rename_slot(self, slot_idx):
        old = self.cfg["slot_names"][slot_idx]
        new = simpledialog.askstring("이름 변경", "새 이름:", initialvalue=old)
        if new:
            self.cfg["slot_names"][slot_idx] = new
            save_config(self.cfg_path, self.cfg)
            self.slot_btns[slot_idx].config(text=new)

    def update_slot_buttons(self):
        for i, btn in enumerate(self.slot_btns):
            if i == self.current_slot_id: btn.configure(style="SlotActive.TButton")
            else: btn.configure(style="Slot.TButton")

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, p in enumerate(self.prompts):
            icon = "✅" if i < self.current_idx else ("👉" if i == self.current_idx else "⬜")
            self.listbox.insert(tk.END, f"{icon} [{i+1:02d}] {p[:50]}...")
        if self.prompts: self.listbox.see(self.current_idx)

    def ensure_driver(self):
        try:
            if self.driver: self.driver.title; return True
        except: pass
        try: self.driver = self.launch_chrome(); return True
        except Exception as e: 
            self.log(f"❌ 크롬 실행 실패: {e}")
            messagebox.showerror("크롬 오류", f"크롬을 열 수 없습니다.\n오류: {e}")
            return False

    def run_capture_tool(self, mode):
        if not self.ensure_driver(): return
        d = self.driver
        try:
            if "flow" not in d.current_url: d.get(self.cfg.get("flow_project_url", DEFAULT_FLOW_URL)); time.sleep(2)
        except: d.get(self.cfg.get("flow_project_url", DEFAULT_FLOW_URL)); time.sleep(2)
        d.execute_script(JS_CAPTURE_TOOL)
        messagebox.showinfo("지정 모드", "마우스 올리고 ENTER!\n(취소: Esc)")
        start = time.time(); found = None
        while time.time() - start < 60:
            try:
                res = d.execute_script("return window.__cap_result;")
                if res:
                    if res == "CANCELLED": return
                    found = res; break
            except: pass
            time.sleep(0.5); self.root.update()
        if found:
            key = {"input":"input_selectors","submit":"submit_selectors","dl_icon":"dl_icon_selectors","dl_file":"dl_file_selectors"}.get(mode)
            lst = self.cfg.get(key, [])
            if found not in lst: lst.insert(0, found)
            self.cfg[key] = lst; save_config(self.cfg_path, self.cfg)
            messagebox.showinfo("성공", f"저장됨!\n{found}")

    def capture_input(self): self.run_capture_tool("input")
    def capture_submit(self): self.run_capture_tool("submit")
    def capture_dl_icon(self): self.run_capture_tool("dl_icon")
    def capture_dl_file(self): self.run_capture_tool("dl_file")

    def start_auto(self):
        if not self.prompts: messagebox.showwarning("없음", "슬롯을 먼저 선택하세요."); return
        self.log("🚀 자동 시작 중...")
        # FORCE CHECK DRIVER
        if not self.ensure_driver(): return
        
        self.running = True; self.start_time = datetime.now()
        self.cnt_success = 0; self.cnt_fail = 0
        self.btn_start.config(state="disabled"); self.btn_stop.config(state="normal")
        self.run_task_step()

    def stop_auto(self, finished=False):
        self.running = False
        self.btn_start.config(state="normal"); self.btn_stop.config(state="disabled")
        self.lbl_next.config(text="중지", fg="gray"); self.lbl_total.config(text="--:--:--")
        if finished: self.show_summary()
        else: self.log("⏹ 중지됨")

    def show_summary(self):
        dur = str(datetime.now() - self.start_time).split('.')[0]
        msg = f"완료!\n시간: {dur}\n성공: {self.cnt_success}\n실패: {self.cnt_fail}"
        self.log(msg); messagebox.showinfo("완료", msg)

    def run_once(self):
        if self.current_idx < len(self.prompts): self.run_task_step(single_mode=True)

    def run_task_step(self, single_mode=False):
        if self.current_idx >= len(self.prompts):
            self.log("🎉 끝!"); 
            if not single_mode: self.stop_auto(finished=True)
            return
        self.log(f"▶ #{self.current_idx+1} 실행...")
        if self.do_selenium_action(self.prompts[self.current_idx]):
            self.cnt_success += 1; self.log("✅ 성공"); self.current_idx += 1; self.refresh_list()
        else:
            self.cnt_fail += 1; self.log("❌ 실패 (스킵)")
        if not single_mode and self.running:
            iv = self.var_interval.get()
            self.next_run_time = time.time() + iv
            self.log(f"⏳ {iv}초 대기...")

    def tick(self):
        if self.running and self.next_run_time > 0:
            rem = int(self.next_run_time - time.time())
            if rem <= 0: self.next_run_time = 0; self.run_task_step()
            else:
                m, s = divmod(rem, 60)
                self.lbl_next.config(text=f"{m:02d}:{s:02d}", fg=C_GREEN)
                left = len(self.prompts) - self.current_idx
                tot = (left * self.var_interval.get()) + rem - self.var_interval.get()
                th, tr = divmod(max(0, tot), 3600); tm, ts = divmod(tr, 60)
                self.lbl_total.config(text=f"{th:02d}:{tm:02d}:{ts:02d}", fg=C_WARN)
        self.root.after(1000, self.tick)

    def do_selenium_action(self, text):
        try:
            if not self.driver: self.driver = self.launch_chrome()
            d = self.driver
            url = self.cfg.get("flow_project_url", DEFAULT_FLOW_URL)
            try:
                if url not in d.current_url: d.get(url); time.sleep(3)
            except: d.get(url); time.sleep(3)
            
            self.log("...입력창")
            el = None
            if self.cfg.get("input_selectors"):
                for s in self.cfg["input_selectors"]:
                    try:
                        el = d.find_element(By.CSS_SELECTOR, s)
                        if el.is_displayed(): break
                    except: pass
            if not el:
                el = WebDriverWait(d, 10).until(lambda x: x.find_element(By.CSS_SELECTOR, "textarea, div[contenteditable='true']"))
            
            el.click(); time.sleep(0.5)
            el.send_keys(Keys.CONTROL, "a"); el.send_keys(Keys.BACKSPACE)
            self.root.clipboard_clear(); self.root.clipboard_append(text); self.root.update()
            time.sleep(0.5); el.send_keys(Keys.CONTROL, "v"); time.sleep(1)
            
            self.log("...전송")
            sub = None
            if self.cfg.get("submit_selectors"):
                for s in self.cfg["submit_selectors"]:
                    try:
                        sub = d.find_element(By.CSS_SELECTOR, s)
                        if sub.is_displayed(): sub.click(); break
                    except: pass
            if not sub: el.send_keys(Keys.ENTER)
            time.sleep(2)
            if self.cfg.get("auto_screenshot", True):
                ts = datetime.now().strftime("%y%m%d_%H%M%S")
                fname = f"{ts}_Prompt_{self.current_idx+1}.png"
                s_path = self.shot_dir / fname
                d.save_screenshot(str(s_path))
                self.log(f"📸 스크린샷: {fname}")
            return True
        except Exception as e:
            self.log(f"오류: {e}"); 
            if self.driver: 
                try: self.driver.quit()
                except: pass
                self.driver = None
            return False

    def start_harvest(self):
        self.log("📥 수확 시작..."); 
        if not self.ensure_driver(): return
        d = self.driver
        s_icon = self.cfg.get("dl_icon_selectors", [])[0] if self.cfg.get("dl_icon_selectors") else None
        s_file = self.cfg.get("dl_file_selectors", [])[0] if self.cfg.get("dl_file_selectors") else None
        if not s_icon or not s_file: messagebox.showwarning("경고", "타겟 지정 필요"); return
        
        count = 0
        try:
            icons = d.find_elements(By.CSS_SELECTOR, s_icon)
            self.log(f"🔍 {len(icons)}개 발견")
            for i, icon in enumerate(icons):
                try:
                    d.execute_script("arguments[0].scrollIntoView({block: 'center'});", icon)
                    time.sleep(0.5); icon.click(); time.sleep(0.5)
                    btn = WebDriverWait(d, 3).until(lambda x: x.find_element(By.CSS_SELECTOR, s_file))
                    if btn.is_displayed(): btn.click(); self.log(f"✅ #{i+1} 다운"); count += 1; time.sleep(1)
                except Exception as ex: self.log(f"❌ #{i+1} 실패: {ex}")
            messagebox.showinfo("완료", f"수확 끝. {count}개")
        except Exception as e: self.log(f"수확 오류: {e}")

    def open_settings(self):
        win = tk.Toplevel(self.root); win.title("설정"); win.geometry("500x500"); win.configure(bg=C_PANEL)
        tk.Label(win, text="설정", font=("bold", 14), bg=C_PANEL, fg=C_TEXT).pack(pady=10)
        f = tk.Frame(win, bg=C_PANEL); f.pack(padx=20, fill="x")
        def row(l, k, r):
            tk.Label(f, text=l, bg=C_PANEL, fg=C_TEXT).grid(row=r, column=0, sticky="w", pady=5)
            e = tk.Entry(f, width=40); e.insert(0, str(self.cfg.get(k, ""))); e.grid(row=r, column=1)
            return e
        e_u = row("URL:", "flow_project_url", 0); e_i = row("간격:", "check_interval_seconds", 1)
        e_p = row("프로필:", "chrome_profile_dir", 2); e_d = row("포트:", "chrome_devtools_port", 3)
        
        tk.Label(f, text="다운로드:", bg=C_PANEL, fg=C_TEXT).grid(row=4, column=0)
        e_dl = tk.Entry(f, width=30); e_dl.insert(0, self.cfg.get("download_dir", "")); e_dl.grid(row=4, column=1)
        ttk.Button(f, text="찾기", command=lambda: [e_dl.delete(0,tk.END), e_dl.insert(0,filedialog.askdirectory())]).grid(row=4, column=2)
        
        v_s = tk.BooleanVar(value=self.cfg.get("auto_screenshot", True))
        ttk.Checkbutton(f, text="자동 스크린샷", variable=v_s).grid(row=5, columnspan=3, pady=10)
        
        def save():
            self.cfg.update({
                "flow_project_url": e_u.get().strip(), "check_interval_seconds": int(e_i.get()),
                "chrome_profile_dir": e_p.get().strip(), "chrome_devtools_port": int(e_d.get()),
                "download_dir": e_dl.get().strip(), "auto_screenshot": v_s.get()
            })
            save_config(self.cfg_path, self.cfg); self.var_interval.set(self.cfg["check_interval_seconds"])
            messagebox.showinfo("완료", "저장됨"); win.destroy()
        ttk.Button(win, text="저장", command=save).pack(pady=20)

    def on_save_as(self):
        f = filedialog.asksaveasfilename(initialfile=f"{datetime.now().strftime('%y%m%d')}_MyPrompts.txt")
        if f:
            t = f"\n\n{self.cfg.get('prompts_separator', '|||')}\n\n".join(self.prompts)
            Path(f).write_text(t, encoding="utf-8"); messagebox.showinfo("완료", "저장됨")

    def on_open(self):
        f = filedialog.askopenfilename()
        if f: self.load_prompts_from_file(Path(f))

    def on_select(self, e):
        if self.listbox.curselection():
            self.editor.delete("1.0", tk.END); self.editor.insert("1.0", self.prompts[self.listbox.curselection()[0]])

    def on_apply_edit(self):
        if self.listbox.curselection():
            self.prompts[self.listbox.curselection()[0]] = self.editor.get("1.0", tk.END).strip(); self.refresh_list()

    def log(self, msg):
        t = f"[{now_str()}] {msg}\n"
        self.log_box.configure(state="normal"); self.log_box.insert("end", t); self.log_box.see("end"); self.log_box.configure(state="disabled"); print(t.strip())

    def open_site(self):
        if self.ensure_driver(): self.driver.get(self.cfg.get("flow_project_url", DEFAULT_FLOW_URL))

    def launch_chrome(self):
        exe = self.cfg.get("chrome_executable", "")
        if not exe or not os.path.exists(exe):
            for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")]:
                if os.path.exists(p): exe = p; break
        port = self.cfg.get("chrome_devtools_port", 9555)
        prof = Path(self.cfg.get("chrome_profile_dir", "../flow/flow_chrome_profile")).resolve()
        subprocess.Popen([exe, f"--remote-debugging-port={port}", f"--user-data-dir={prof}", "--no-first-run", "--profile-directory=FlowVeo", "--start-maximized"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        opts = ChromeOptions(); opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        dl = self.cfg.get("download_dir", "")
        if dl: opts.add_experimental_option("prefs", {"download.default_directory": str(Path(dl).resolve()), "download.prompt_for_download": False})
        svc = ChromeService(ChromeDriverManager().install())
        d = webdriver.Chrome(service=svc, options=opts); d.implicitly_wait(5)
        return d

if __name__ == "__main__": FlowApp().run()
