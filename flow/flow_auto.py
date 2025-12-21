import json
import os
import time
import random
import threading
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

# [비전 봇 핵심 모듈]
import pyautogui
import pyperclip

# [알림창 클래스 추가]
class CountdownAlert:
    def __init__(self, master, seconds=30):
        self.root = tk.Toplevel(master)
        self.root.title("봇 출동 알림")
        self.root.overrideredirect(True) # 테두리 없음
        self.root.attributes("-topmost", True) # 항상 위에
        self.root.attributes("-alpha", 0.9) # 약간 투명
        self.root.configure(bg="#282A36")
        
        # 위치 설정 (화면 우측 하단 기본)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 300, 80
        x = sw - w - 20
        y = sh - h - 100
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        # 드래그 이동 기능
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        
        # UI
        frame = tk.Frame(self.root, bg="#282A36", highlightbackground="#BD93F9", highlightthickness=2)
        frame.pack(fill="both", expand=True)
        
        self.lbl_title = tk.Label(frame, text="👻 비전 봇 출동 준비!", font=("Malgun Gothic", 11, "bold"), bg="#282A36", fg="#FF79C6")
        self.lbl_title.pack(pady=(10, 2))
        
        self.lbl_time = tk.Label(frame, text=f"{seconds}초 전", font=("Malgun Gothic", 16, "bold"), bg="#282A36", fg="#50FA7B")
        self.lbl_time.pack(pady=(0, 10))
        
        self.x = 0
        self.y = 0

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
        self.lbl_time.config(text=f"{int(seconds)}초 전")
        if seconds <= 5:
            self.lbl_time.config(fg="#FF5555") # 5초 전부터 빨간색 경고

    def close(self):
        try:
            self.root.destroy()
        except: pass

# --- 설정 ---
APP_NAME = "Flow Veo Vision Bot"
CONFIG_FILE = "flow_config.json"
DEFAULT_CONFIG = {
    "prompts_file": "flow_prompts.txt",
    "prompts_separator": "|||",
    "interval_seconds": 60,
    "input_coords": {"x": 0, "y": 0},
    "submit_coords": {"x": 0, "y": 0},
    "prompt_slots": []
}

class FlowVisionApp:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / CONFIG_FILE
        self.cfg = self.load_config()
        
        self.running = False
        self.prompts = []
        self.index = 0
        self.t_next = None
        self.alert_window = None # 알림창 인스턴스
        
        # UI 초기화
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("600x650")
        self.root.configure(bg="#1E1E2E")
        
        # 아이콘 (있으면)
        try:
            icon_path = self.base.parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except: pass

        self._build_ui()
        self._ensure_prompt_slots()
        self.on_reload() # 프롬프트 로드
        
        # 타이머 루프 시작
        self.root.after(1000, self._tick)

    def load_config(self):
        if not self.cfg_path.exists():
            return DEFAULT_CONFIG.copy()
        try:
            return json.loads(self.cfg_path.read_text(encoding="utf-8"))
        except:
            return DEFAULT_CONFIG.copy()

    def save_config(self):
        self.cfg_path.write_text(json.dumps(self.cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    def _ensure_prompt_slots(self):
        if not self.cfg.get("prompt_slots"):
            self.cfg["prompt_slots"] = [{"name": "기본", "file": "flow_prompts.txt"}]
            self.save_config()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", font=("Malgun Gothic", 10), padding=6, background="#3E3E5E", foreground="white")
        style.map("TButton", background=[('active', '#5E5E7E')])
        style.configure("Accent.TButton", background="#FF79C6", foreground="black", font=("Malgun Gothic", 10, "bold"))
        
        # 상단: 타이틀 & 설명
        top = tk.Frame(self.root, bg="#1E1E2E")
        top.pack(fill="x", padx=20, pady=15)
        tk.Label(top, text="🌙 Flow 비전 봇 (탐지 불가)", font=("Malgun Gothic", 16, "bold"), fg="#BD93F9", bg="#1E1E2E").pack(anchor="w")
        tk.Label(top, text="Selenium을 쓰지 않고, 순수 마우스/키보드 제어로 구글을 속입니다.", font=("Malgun Gothic", 9), fg="#6272A4", bg="#1E1E2E").pack(anchor="w")

        # 좌표 설정 영역
        coord_frame = tk.LabelFrame(self.root, text=" 1. 좌표 설정 (필수!) ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=10, pady=10)
        coord_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(coord_frame, text="버튼을 누르고 5초 안에 마우스를 해당 위치로 옮기세요!", bg="#1E1E2E", fg="#FFB86C").pack(pady=(0,5))
        
        btn_box = tk.Frame(coord_frame, bg="#1E1E2E")
        btn_box.pack(fill="x")
        
        self.btn_set_input = ttk.Button(btn_box, text="📍 입력창 위치 잡기 (5초 대기)", command=lambda: self.start_capture("input"))
        self.btn_set_input.pack(side="left", expand=True, fill="x", padx=2)
        
        self.btn_set_submit = ttk.Button(btn_box, text="📍 생성 버튼 위치 잡기 (5초 대기)", command=lambda: self.start_capture("submit"))
        self.btn_set_submit.pack(side="left", expand=True, fill="x", padx=2)
        
        self.lbl_coords = tk.Label(coord_frame, text=self._get_coord_text(), bg="#1E1E2E", fg="#8BE9FD")
        self.lbl_coords.pack(pady=5)

        # 실행 제어 영역
        run_frame = tk.LabelFrame(self.root, text=" 2. 실행 제어 ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=10, pady=10)
        run_frame.pack(fill="x", padx=20, pady=10)
        
        ctrl_box = tk.Frame(run_frame, bg="#1E1E2E")
        ctrl_box.pack(fill="x")
        
        tk.Label(ctrl_box, text="간격(초):", bg="#1E1E2E", fg="white").pack(side="left")
        self.entry_interval = tk.Entry(ctrl_box, width=5)
        self.entry_interval.insert(0, str(self.cfg.get("interval_seconds", 60)))
        self.entry_interval.pack(side="left", padx=5)
        
        self.btn_start = ttk.Button(ctrl_box, text="🌙 조용히 시작", style="Accent.TButton", command=self.on_start)
        self.btn_start.pack(side="left", padx=10, fill="x", expand=True)
        
        self.btn_stop = ttk.Button(ctrl_box, text="🛑 멈추기", command=self.on_stop, state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True)

        self.lbl_status = tk.Label(run_frame, text="대기 중...", bg="#1E1E2E", fg="#50FA7B", font=("Malgun Gothic", 10))
        self.lbl_status.pack(pady=5)

        # 프롬프트 표시 영역
        tk.Label(self.root, text="현재 프롬프트 미리보기:", bg="#1E1E2E", fg="white").pack(anchor="w", padx=20)
        self.text_preview = ScrolledText(self.root, height=10, bg="#282A36", fg="#F8F8F2", insertbackground="white")
        self.text_preview.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _get_coord_text(self):
        ix = self.cfg.get('input_coords', {}).get('x', 0)
        iy = self.cfg.get('input_coords', {}).get('y', 0)
        sx = self.cfg.get('submit_coords', {}).get('x', 0)
        sy = self.cfg.get('submit_coords', {}).get('y', 0)
        return f"현재 설정: 입력창({ix}, {iy}) / 버튼({sx}, {sy})"

    def start_capture(self, kind):
        def countdown():
            for i in range(5, 0, -1):
                self.lbl_coords.config(text=f"⏳ {i}초 뒤 좌표를 저장합니다! 마우스를 위치시키세요!", fg="#FF5555")
                self.root.update()
                time.sleep(1)
            
            x, y = pyautogui.position()
            if kind == "input":
                self.cfg["input_coords"] = {"x": x, "y": y}
            else:
                self.cfg["submit_coords"] = {"x": x, "y": y}
            
            self.save_config()
            self.lbl_coords.config(text=self._get_coord_text(), fg="#8BE9FD")
            messagebox.showinfo("성공", f"좌표 저장 완료!\n({x}, {y})")
            
        threading.Thread(target=countdown, daemon=True).start()

    def on_reload(self):
        try:
            path = self.base / self.cfg["prompts_file"]
            raw = path.read_text(encoding="utf-8")
            sep = self.cfg.get("prompts_separator", "|||")
            self.prompts = [p.strip() for p in raw.split(sep) if p.strip()]
            self.text_preview.delete("1.0", "end")
            if self.prompts:
                self.text_preview.insert("1.0", self.prompts[0])
                self.lbl_status.config(text=f"프롬프트 로드 완료 ({len(self.prompts)}개)")
            else:
                self.text_preview.insert("1.0", "(프롬프트 파일이 비어있습니다)")
        except Exception as e:
            self.lbl_status.config(text=f"로드 실패: {e}")

    def on_start(self):
        # 좌표 확인
        ix = self.cfg.get('input_coords', {}).get('x', 0)
        sx = self.cfg.get('submit_coords', {}).get('x', 0)
        
        if ix == 0 or sx == 0:
            messagebox.showwarning("주의", "먼저 '좌표 설정'을 해주세요!\n입력창과 생성 버튼 위치를 알려줘야 합니다.")
            return
            
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.entry_interval.config(state="disabled")
        
        # 첫 실행 즉시 시작
        self.t_next = time.time()
        self.lbl_status.config(text="🚀 자동화 시작!", fg="#50FA7B")

    def on_stop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.entry_interval.config(state="normal")
        self.lbl_status.config(text="⏹ 멈춤", fg="#FF5555")
        
        # 알림창 닫기
        if self.alert_window:
            self.alert_window.close()
            self.alert_window = None

    def _tick(self):
        if self.running and self.t_next:
            remain = self.t_next - time.time()
            
            # [알림창 로직] 30초 전부터 카운트다운
            if 0 < remain <= 30:
                if self.alert_window is None:
                    self.alert_window = CountdownAlert(self.root, remain)
                else:
                    self.alert_window.update_time(remain)
            
            if remain <= 0:
                # 작업 시작 전 알림창 닫기
                if self.alert_window:
                    self.alert_window.close()
                    self.alert_window = None
                    
                self._run_task()
                # 다음 시간 설정 (랜덤 변동 추가)
                try:
                    base = int(self.entry_interval.get())
                except: base = 60
                variation = random.randint(-5, 30)
                interval = max(10, base + variation)
                self.t_next = time.time() + interval
            else:
                self.lbl_status.config(text=f"다음 작업까지 {int(remain)}초...", fg="#F1FA8C")
        
        self.root.after(1000, self._tick)

    def _run_task(self):
        if not self.prompts or self.index >= len(self.prompts):
            self.running = False
            self.lbl_status.config(text="🎉 모든 작업 완료!", fg="#BD93F9")
            messagebox.showinfo("완료", "모든 프롬프트를 처리했습니다.")
            self.on_stop()
            return

        prompt = self.prompts[self.index]
        self.text_preview.delete("1.0", "end")
        self.text_preview.insert("1.0", f"[진행 중: {self.index+1}/{len(self.prompts)}]\n{prompt}")
        
        ix = self.cfg["input_coords"]["x"]
        iy = self.cfg["input_coords"]["y"]
        sx = self.cfg["submit_coords"]["x"]
        sy = self.cfg["submit_coords"]["y"]
        
        try:
            # 1. 입력창 클릭
            self.lbl_status.config(text="🖱️ 입력창 이동 중...", fg="white")
            self._human_move(ix, iy)
            pyautogui.click()
            time.sleep(random.uniform(0.5, 1.0))
            
            # 2. 내용 지우기 (Ctrl+A -> Backspace)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("backspace")
            time.sleep(0.2)
            
            # 3. 입력 (사람처럼)
            self.lbl_status.config(text="✍️ 입력 중...", fg="white")
            pyperclip.copy(prompt)
            time.sleep(0.2)
            
            # a 눌렀다 지우기 (키보드 이벤트 발생)
            pyautogui.press('a')
            time.sleep(0.1)
            pyautogui.press('backspace')
            time.sleep(0.2)
            
            pyautogui.hotkey("ctrl", "v")
            time.sleep(random.uniform(0.8, 1.5))
            
            # 4. 버튼 클릭
            self.lbl_status.config(text="🖱️ 생성 버튼 누르러 가는 중...", fg="white")
            self._human_move(sx, sy)
            pyautogui.click()
            
            self.lbl_status.config(text="✅ 제출 완료! 대기 모드 진입", fg="#50FA7B")
            self.index += 1
            
        except Exception as e:
            self.lbl_status.config(text=f"오류 발생: {e}")
            self.running = False
            self.on_stop()

    def _human_move(self, x, y):
        """사람처럼 마우스 이동 (곡선 + 속도 변화)"""
        start_x, start_y = pyautogui.position()
        duration = random.uniform(0.5, 1.0)
        # 중간에 튀는 점 하나 생성
        mid_x = start_x + (x - start_x) * random.uniform(0.3, 0.7) + random.randint(-50, 50)
        mid_y = start_y + (y - start_y) * random.uniform(0.3, 0.7) + random.randint(-50, 50)
        
        # pyautogui.moveTo는 tween을 지원 (easeOutQuad 등)
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeOutQuad)

if __name__ == "__main__":
    FlowVisionApp().root.mainloop()