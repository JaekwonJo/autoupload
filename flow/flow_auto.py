import json
import os
import time
import random
import threading
import math
from pathlib import Path
from datetime import datetime
import ctypes

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

# [비전 봇 핵심 모듈]
import pyautogui
import pyperclip

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
    "interval_seconds": 60,
    "input_coords": {"x": 0, "y": 0},
    "submit_coords": {"x": 0, "y": 0},
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
        w, h = 300, 80
        x = sw - w - 20
        y = sh - h - 100
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        
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
            self.lbl_time.config(fg="#FF5555")

    def close(self):
        try:
            self.root.destroy()
        except: pass

# [좌표 캡처 오버레이]
class CaptureOverlay:
    def __init__(self, master, on_capture, kind_text):
        self.on_capture = on_capture
        self.root = tk.Toplevel(master)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.3)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black", cursor="crosshair")
        
        self.label = tk.Label(self.root, text=f"{kind_text} 위치에서 [클릭] 또는 [Enter]", 
                              bg="#FF79C6", fg="black", font=("Malgun Gothic", 12, "bold"))
        self.label.place(x=0, y=0)
        
        self.root.bind("<Motion>", self.on_move)
        self.root.bind("<Button-1>", self.on_click)
        self.root.bind("<Return>", self.on_click)
        self.root.bind("<Escape>", self.close)

    def on_move(self, event):
        self.label.place(x=event.x + 20, y=event.y + 20)
        self.label.config(text=f"X:{event.x}, Y:{event.y}\n(클릭하여 저장)")

    def on_click(self, event):
        x, y = event.x, event.y
        self.root.destroy()
        self.on_capture(x, y)

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
        
        # [휴식 시스템]
        self.task_count = 0
        self.next_break_threshold = random.randint(5, 12) # 5~12회마다 긴 휴식
        
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("800x800")
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
        ix = self.cfg.get('input_coords', {}).get('x', 0)
        sx = self.cfg.get('submit_coords', {}).get('x', 0)
        if ix == 0 or sx == 0:
            messagebox.showwarning("주의", "좌표 설정을 먼저 해주세요!")
            return
            
        self._prevent_sleep()
        
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.entry_interval.config(state="disabled")
        self.t_next = time.time()
        self.lbl_status.config(text="🚀 자동화 시작!", fg="#50FA7B")
        
        # 시작할 때 휴식 카운터 초기화
        self.task_count = 0
        self.next_break_threshold = random.randint(5, 12)

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
        coord_frame = tk.LabelFrame(main, text=" 1. 좌표 설정 ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=10, pady=5)
        coord_frame.pack(fill="x", padx=20, pady=5)
        
        btn_box = tk.Frame(coord_frame, bg="#1E1E2E")
        btn_box.pack(fill="x")
        ttk.Button(btn_box, text="📍 입력창 위치", command=lambda: self.start_capture("input")).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_box, text="📍 생성 버튼 위치", command=lambda: self.start_capture("submit")).pack(side="left", expand=True, fill="x", padx=2)
        self.lbl_coords = tk.Label(coord_frame, text=self._get_coord_text(), bg="#1E1E2E", fg="#8BE9FD")
        self.lbl_coords.pack(pady=2)

        # 3. 실행 제어
        run_frame = tk.LabelFrame(main, text=" 2. 실행 제어 ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=10, pady=5)
        run_frame.pack(fill="x", padx=20, pady=5)
        
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

    def _get_coord_text(self):
        ix = self.cfg.get('input_coords', {}).get('x', 0)
        iy = self.cfg.get('input_coords', {}).get('y', 0)
        sx = self.cfg.get('submit_coords', {}).get('x', 0)
        sy = self.cfg.get('submit_coords', {}).get('y', 0)
        return f"현재 설정: 입력창({ix}, {iy}) / 버튼({sx}, {sy})"

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
        kind_text = "입력창" if kind == "input" else "생성 버튼"
        def on_captured(x, y):
            if kind == "input":
                self.cfg["input_coords"] = {"x": x, "y": y}
            else:
                self.cfg["submit_coords"] = {"x": x, "y": y}
            self.save_config()
            self.lbl_coords.config(text=self._get_coord_text(), fg="#8BE9FD")
            messagebox.showinfo("성공", f"{kind_text} 좌표 저장 완료!\n({x}, {y})")
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
                self._run_task()
                
                # 다음 시간 설정 (랜덤)
                var = random.randint(-min(30, base//5), min(30, base//5))
                if base < 30: var = random.randint(-5, 10)
                interval = max(10, base + var)
                self.t_next = time.time() + interval
                self.log(f"🎲 다음 간격: {interval}초 (랜덤)")
        else:
            self.lbl_eta.config(text="-")
        
        self.root.after(1000, self._tick)

    def _run_task(self):
        if not self.prompts or self.index >= len(self.prompts):
            self.running = False
            self.lbl_status.config(text="🎉 모든 작업 완료!", fg="#BD93F9")
            self.log("작업 완료")
            messagebox.showinfo("완료", "모든 프롬프트를 처리했습니다.")
            self.on_stop()
            return

        # [NEW] 생체 리듬 휴식 (Bio-Break)
        self.task_count += 1
        if self.task_count >= self.next_break_threshold:
            self._take_bio_break()
            # 휴식 후 카운터 리셋
            self.task_count = 0
            self.next_break_threshold = random.randint(5, 12)
            # 휴식 끝났으니 바로 재개
            return

        self._show()
        prompt = self.prompts[self.index]
        self.log(f"▶ 진행: {self.index+1}/{len(self.prompts)}")
        
        ix = self.cfg["input_coords"]["x"]
        iy = self.cfg["input_coords"]["y"]
        sx = self.cfg["submit_coords"]["x"]
        sy = self.cfg["submit_coords"]["y"]
        
        try:
            # 0. 의미 없는 긁기 & 딴짓 (25% 확률)
            if random.random() < 0.25:
                self.lbl_status.config(text="🤔 생각하는 중... (딴짓)", fg="#FFB86C")
                self._random_aimless_action()

            # 1. 입력창 이동 (베지에 곡선 & 오버슈트 적용)
            self.lbl_status.config(text="🖱️ 입력창 이동...", fg="white")
            self._human_move_advanced(ix, iy, overshoot=True)
            time.sleep(random.uniform(0.1, 0.3))
            pyautogui.click() # 클릭도 살짝 딜레이 후

            # 2. 지우기 (기존 내용)
            time.sleep(random.uniform(0.2, 0.5))
            pyautogui.hotkey("ctrl", "a")
            time.sleep(random.uniform(0.1, 0.3))
            pyautogui.press("backspace")
            time.sleep(random.uniform(0.2, 0.5))
            
            # 3. 입력 (오타 포함)
            self.lbl_status.config(text="✍️ 입력 중...", fg="white")
            
            # 혹시 모를 앞글자 씹힘 방지용 더미 클릭/대기
            if random.random() < 0.2:
                pyautogui.press('shift')
                time.sleep(0.1)

            # [NEW] 오타 포함 타이핑
            self._human_type_advanced(prompt)
            
            time.sleep(random.uniform(0.8, 1.5))
            
            # 4. 버튼 클릭 (베지에 곡선 & 오버슈트)
            self.lbl_status.config(text="🖱️ 버튼 클릭...", fg="white")
            self._human_move_advanced(sx, sy, overshoot=True)
            time.sleep(random.uniform(0.1, 0.3))
            pyautogui.click()
            
            self.log(f"✅ 제출 완료")
            
            # 5. 제출 후 가만히 있지 않고 마우스를 살짝 치움 (30% 확률)
            if random.random() < 0.3:
                time.sleep(0.5)
                self._human_move_advanced(sx + random.randint(100, 300), sy + random.randint(-100, 100))

        except Exception as e:
            self.log(f"❌ 오류: {e}")
            self.running = False
            self.on_stop()
        
        finally:
            self.index += 1

    # [NEW] 생체 리듬 휴식
    def _take_bio_break(self):
        # 3분 ~ 10분 (초 단위)
        break_time = random.randint(180, 600)
        finish_at = time.time() + break_time
        
        self.log(f"☕ [휴식] {break_time}초 동안 멍 때리기 (인간 흉내)")
        
        while time.time() < finish_at:
            if not self.running: break
            remain = int(finish_at - time.time())
            self.lbl_status.config(text=f"☕ 휴식 중... {remain}초 남음", fg="#FF5555")
            
            # 휴식 중에도 가끔 마우스 툭 건드림 (절전 방지 느낌)
            if random.random() < 0.05:
                x, y = pyautogui.position()
                pyautogui.moveTo(x + random.randint(-5, 5), y + random.randint(-5, 5), duration=0.2)
            
            self.root.update()
            time.sleep(1)
        
        self.log("☕ 휴식 끝! 다시 일하러 갑니다.")
        # 휴식이 끝났으니 이번 턴 작업을 수행하도록 설정 (재귀 호출 대신 플래그 처리해도 되지만, 여기선 Tick이 다음을 부르므로 이번 작업은 Skip됨.
        # 즉, 휴식 타임 = 이번 프롬프트 건너뛰기가 아니라, 이번 시간(Tick)을 휴식으로 쓴 것.
        # 프롬프트 인덱스는 증가시키지 않았으므로 다음 Tick에 다시 시도하게 됨.

    # [NEW] 의미 없는 딴짓
    def _random_aimless_action(self):
        action = random.choice(["scroll", "select_text", "wiggle", "pause"])
        if action == "scroll":
            # 스크롤 살짝
            pyautogui.scroll(random.randint(-200, 200))
            time.sleep(random.uniform(0.5, 1.0))
        elif action == "select_text":
            # 아무데나 드래그하는 척
            x, y = pyautogui.position()
            pyautogui.dragRel(random.randint(-50, 50), 0, duration=0.5, button='left')
            time.sleep(0.3)
            pyautogui.click() # 선택 해제
        elif action == "wiggle":
            x, y = pyautogui.position()
            self._human_move_advanced(x + random.randint(-30, 30), y + random.randint(-30, 30))
        elif action == "pause":
            time.sleep(random.uniform(1.5, 3.5))

    # [NEW] 베지에 곡선 & 오버슈트 이동
    def _human_move_advanced(self, target_x, target_y, overshoot=False):
        start_x, start_y = pyautogui.position()
        
        # 오버슈트: 목표 지점을 살짝 지나쳤다가 돌아옴
        if overshoot and random.random() < 0.2: # 20% 확률
            overshoot_x = target_x + random.randint(-20, 20)
            overshoot_y = target_y + random.randint(-20, 20)
            
            # 1. 오버슈트 지점까지 이동
            self._move_bezier(start_x, start_y, overshoot_x, overshoot_y)
            time.sleep(random.uniform(0.05, 0.15))
            
            # 2. 다시 정확한 지점으로 이동
            self._move_bezier(overshoot_x, overshoot_y, target_x, target_y, duration_base=0.3)
        else:
            # 그냥 이동
            self._move_bezier(start_x, start_y, target_x, target_y)

        # 도착 후 미세 조정 (Jitter)
        if random.random() < 0.5:
            jitter_x = random.randint(-2, 2)
            jitter_y = random.randint(-2, 2)
            pyautogui.moveRel(jitter_x, jitter_y, duration=0.1)

    def _move_bezier(self, x1, y1, x2, y2, duration_base=None):
        # 제어점 생성 (직선 경로에서 랜덤하게 벗어난 점)
        dist = math.hypot(x2 - x1, y2 - y1)
        if duration_base is None:
            duration = random.uniform(0.5, 1.2) + (dist / 2000) # 거리에 비례해 시간 추가
        else:
            duration = duration_base

        # 제어점 2개 생성 (3차 베지에)
        ctrl1_x = x1 + (x2 - x1) * 0.33 + random.randint(-100, 100)
        ctrl1_y = y1 + (y2 - y1) * 0.33 + random.randint(-100, 100)
        ctrl2_x = x1 + (x2 - x1) * 0.66 + random.randint(-100, 100)
        ctrl2_y = y1 + (y2 - y1) * 0.66 + random.randint(-100, 100)

        # 경로 따라 이동
        steps = int(duration * 60) # 60 FPS
        if steps < 5: steps = 5
        
        for i in range(steps + 1):
            t = i / steps
            # Ease-in-out 효과 (t를 변형)
            t_eased = t * t * (3 - 2 * t) 
            
            # 3차 베지에 공식
            bx = (1-t_eased)**3 * x1 + \
                 3 * (1-t_eased)**2 * t_eased * ctrl1_x + \
                 3 * (1-t_eased) * t_eased**2 * ctrl2_x + \
                 t_eased**3 * x2
            
            by = (1-t_eased)**3 * y1 + \
                 3 * (1-t_eased)**2 * t_eased * ctrl1_y + \
                 3 * (1-t_eased) * t_eased**2 * ctrl2_y + \
                 t_eased**3 * y2
                 
            pyautogui.moveTo(bx, by)
            # 루프 내 sleep은 최소화 (moveTo 자체가 시간이 걸릴 수 있지만 duration=0으로 호출하므로 즉시 이동)
            # 하지만 너무 빠르면 안되므로 아주 짧게 대기
            time.sleep(duration / steps)

    # [NEW] 오타 시뮬레이션 타이핑
    def _human_type_advanced(self, text):
        for char in text:
            # 1. 3% 확률로 오타 발생
            if random.random() < 0.03:
                wrong_char = chr(ord(char) + 1) # 대충 다음 아스키코드
                pyautogui.write(wrong_char)
                time.sleep(random.uniform(0.1, 0.4))
                
                # 아차차! 지우기
                pyautogui.press("backspace")
                time.sleep(random.uniform(0.1, 0.3))

            # 2. 타이핑 (한글은 복붙, 영어는 타이핑)
            if 32 <= ord(char) <= 126: 
                pyautogui.write(char)
            else:
                pyperclip.copy(char)
                time.sleep(0.01)
                pyautogui.hotkey("ctrl", "v")
            
            # 3. 타이핑 간격 랜덤 (리듬감)
            time.sleep(random.uniform(0.03, 0.15))

if __name__ == "__main__":
    FlowVisionApp().root.mainloop()