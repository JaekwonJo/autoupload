import json
import os
import time
import random
import threading
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

# [비전 봇 핵심 모듈]
import pyautogui
import pyperclip

# --- 설정 ---
APP_NAME = "Flow Veo Vision Bot (Full)"
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

# [좌표 캡처 오버레이 클래스]
class CaptureOverlay:
    def __init__(self, master, on_capture, kind_text):
        self.on_capture = on_capture
        self.root = tk.Toplevel(master)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.3) # 반투명 배경
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black", cursor="crosshair")
        
        # 안내 라벨 (마우스 따라다님)
        self.label = tk.Label(self.root, text=f"{kind_text} 위치에서 [클릭] 또는 [Enter]", 
                              bg="#FF79C6", fg="black", font=("Malgun Gothic", 12, "bold"))
        self.label.place(x=0, y=0)
        
        # 이벤트 바인딩
        self.root.bind("<Motion>", self.on_move)
        self.root.bind("<Button-1>", self.on_click) # 클릭으로 저장
        self.root.bind("<Return>", self.on_click)   # 엔터로 저장
        self.root.bind("<Escape>", self.close)      # ESC 취소

    def on_move(self, event):
        self.label.place(x=event.x + 20, y=event.y + 20)
        self.label.config(text=f"X:{event.x}, Y:{event.y}\n(클릭하여 저장)")

    def on_click(self, event):
        x, y = event.x, event.y
        self.root.destroy()
        self.on_capture(x, y)

    def close(self, event=None):
        self.root.destroy()

# [알림창 클래스]
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
            self.lbl_time.config(fg="#FF5555")

    def close(self):
        try:
            self.root.destroy()
        except: pass

class FlowVisionApp:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / CONFIG_FILE
        self.cfg = self.load_config()
        
        self.running = False
        self.prompts = []
        self.index = 0
        self.t_next = None
        self.alert_window = None
        
        # UI 초기화
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("650x750")
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
            # 10개 채우기
            for i in range(2, 11):
                self.cfg["prompt_slots"].append({"name": f"슬롯 {i}", "file": f"flow_prompts_slot{i}.txt"})
            self.save_config()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", font=("Malgun Gothic", 10), padding=6, background="#3E3E5E", foreground="white")
        style.map("TButton", background=[('active', '#5E5E7E')])
        style.configure("Accent.TButton", background="#FF79C6", foreground="black", font=("Malgun Gothic", 10, "bold"))
        
        # 메인 컨테이너
        main = tk.Frame(self.root, bg="#1E1E2E")
        main.pack(fill="both", expand=True)

        # 1. 상단: 타이틀
        top = tk.Frame(main, bg="#1E1E2E")
        top.pack(fill="x", padx=20, pady=10)
        tk.Label(top, text="🌙 Flow 비전 봇 (Full Ver)", font=("Malgun Gothic", 14, "bold"), fg="#BD93F9", bg="#1E1E2E").pack(side="left")
        
        # 2. 좌표 설정
        coord_frame = tk.LabelFrame(main, text=" 1. 좌표 설정 ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=10, pady=5)
        coord_frame.pack(fill="x", padx=20, pady=5)
        
        btn_box = tk.Frame(coord_frame, bg="#1E1E2E")
        btn_box.pack(fill="x")
        ttk.Button(btn_box, text="📍 입력창 위치 (5초)", command=lambda: self.start_capture("input")).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_box, text="📍 생성 버튼 위치 (5초)", command=lambda: self.start_capture("submit")).pack(side="left", expand=True, fill="x", padx=2)
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
        
        self.lbl_status = tk.Label(run_frame, text="대기 중...", bg="#1E1E2E", fg="#50FA7B", font=("Malgun Gothic", 11, "bold"))
        self.lbl_status.pack(pady=2)
        
        # [ETA 라벨 추가]
        self.lbl_eta = tk.Label(run_frame, text="-", bg="#1E1E2E", fg="#FF79C6", font=("Malgun Gothic", 9))
        self.lbl_eta.pack(pady=(0, 5))

        # 4. 프롬프트 관리 (풀옵션 복구)
        prompt_frame = tk.LabelFrame(main, text=" 3. 프롬프트 관리 ", font=("Malgun Gothic", 10, "bold"), bg="#1E1E2E", fg="#F8F8F2", padx=10, pady=5)
        prompt_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 툴바 1: 슬롯, 파일 열기, 저장
        toolbar1 = tk.Frame(prompt_frame, bg="#1E1E2E")
        toolbar1.pack(fill="x", pady=(0, 5))
        
        self.slot_var = tk.StringVar()
        slots = [s["name"] for s in self.cfg["prompt_slots"]]
        self.combo_slots = ttk.Combobox(toolbar1, textvariable=self.slot_var, values=slots, state="readonly", width=15)
        self.combo_slots.pack(side="left", padx=2)
        self.combo_slots.bind("<<ComboboxSelected>>", self.on_slot_change)
        
        # [이름 변경 버튼 추가]
        ttk.Button(toolbar1, text="✏️ 이름", width=6, command=self.on_rename_slot).pack(side="left", padx=2)
        
        current_idx = self.cfg.get("active_prompt_slot", 0)
        if 0 <= current_idx < len(slots):
            self.combo_slots.current(current_idx)
            
        ttk.Button(toolbar1, text="📄 파일 열기", command=self.on_open_prompts).pack(side="left", padx=2)
        ttk.Button(toolbar1, text="💾 저장", command=self.on_save_prompts).pack(side="right", padx=2)
        ttk.Button(toolbar1, text="🔄 새로고침", command=self.on_reload).pack(side="right", padx=2)

        # 툴바 2: 네비게이션
        toolbar2 = tk.Frame(prompt_frame, bg="#1E1E2E")
        toolbar2.pack(fill="x", pady=(0, 5))
        
        ttk.Button(toolbar2, text="⏮ 처음", width=6, command=self.on_first).pack(side="left", padx=2)
        ttk.Button(toolbar2, text="◀ 이전", width=6, command=self.on_prev).pack(side="left", padx=2)
        
        self.lbl_pos = tk.Label(toolbar2, text="0 / 0", bg="#1E1E2E", fg="white", width=15, font=("Consolas", 10, "bold"))
        self.lbl_pos.pack(side="left", padx=5)
        
        ttk.Button(toolbar2, text="다음 ▶", width=6, command=self.on_next).pack(side="left", padx=2)
        ttk.Button(toolbar2, text="끝 ⏭", width=6, command=self.on_last).pack(side="left", padx=2)

        # 에디터
        self.text_preview = ScrolledText(prompt_frame, height=10, bg="#282A36", fg="#F8F8F2", insertbackground="white", font=("Consolas", 10))
        self.text_preview.pack(fill="both", expand=True)

    def _get_coord_text(self):
        ix = self.cfg.get('input_coords', {}).get('x', 0)
        iy = self.cfg.get('input_coords', {}).get('y', 0)
        sx = self.cfg.get('submit_coords', {}).get('x', 0)
        sy = self.cfg.get('submit_coords', {}).get('y', 0)
        return f"현재 설정: 입력창({ix}, {iy}) / 버튼({sx}, {sy})"

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

        # 오버레이 실행 (화면 전체를 덮는 투명 레이어)
        CaptureOverlay(self.root, on_captured, kind_text)

    def on_rename_slot(self):
        idx = self.combo_slots.current()
        if idx < 0:
            return
        
        current_name = self.cfg["prompt_slots"][idx]["name"]
        new_name = simpledialog.askstring("이름 변경", "새 슬롯 이름을 입력하세요:", initialvalue=current_name)
        
        if new_name:
            self.cfg["prompt_slots"][idx]["name"] = new_name
            self.save_config()
            
            # 콤보박스 목록 갱신
            slots = [s["name"] for s in self.cfg["prompt_slots"]]
            self.combo_slots["values"] = slots
            self.combo_slots.current(idx)
            self.slot_var.set(new_name)
            
            messagebox.showinfo("성공", f"'{new_name}'(으)로 변경 완료!")

    def on_slot_change(self, event=None):
        idx = self.combo_slots.current()
        if idx >= 0:
            self.cfg["active_prompt_slot"] = idx
            slot = self.cfg["prompt_slots"][idx]
            self.cfg["prompts_file"] = slot["file"]
            self.save_config()
            self.on_reload()

    def on_open_prompts(self):
        try:
            path = self.base / self.cfg["prompts_file"]
            if not path.exists():
                path.write_text("", encoding="utf-8")
            os.startfile(path)
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
            if not path.exists():
                path.write_text("", encoding="utf-8")
            
            raw = path.read_text(encoding="utf-8")
            sep = self.cfg.get("prompts_separator", "|||")
            self.prompts = [p.strip() for p in raw.split(sep) if p.strip()]
            
            # 인덱스 범위 체크
            if self.index >= len(self.prompts):
                self.index = 0
            
            self._show()
            self.lbl_status.config(text=f"프롬프트 로드 완료: 총 {len(self.prompts)}개", fg="#8BE9FD")
        except Exception as e:
            self.lbl_status.config(text=f"로드 실패: {e}", fg="#FF5555")

    def _show(self):
        self.text_preview.delete("1.0", "end")
        if self.prompts and 0 <= self.index < len(self.prompts):
            self.text_preview.insert("1.0", self.prompts[self.index])
            self.lbl_pos.config(text=f"{self.index + 1} / {len(self.prompts)}")
        else:
            self.text_preview.insert("1.0", "(프롬프트 없음)")
            self.lbl_pos.config(text="0 / 0")

    def on_first(self):
        self.index = 0
        self._show()

    def on_prev(self):
        if self.index > 0:
            self.index -= 1
            self._show()

    def on_next(self):
        if self.prompts and self.index < len(self.prompts) - 1:
            self.index += 1
            self._show()

    def on_last(self):
        if self.prompts:
            self.index = len(self.prompts) - 1
            self._show()

    def on_start(self):
        ix = self.cfg.get('input_coords', {}).get('x', 0)
        sx = self.cfg.get('submit_coords', {}).get('x', 0)
        
        if ix == 0 or sx == 0:
            messagebox.showwarning("주의", "먼저 '좌표 설정'을 해주세요!\n입력창과 생성 버튼 위치를 알려줘야 합니다.")
            return
            
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.entry_interval.config(state="disabled")
        
        self.t_next = time.time()
        self.lbl_status.config(text="🚀 자동화 시작!", fg="#50FA7B")

    def on_stop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        # [수정] 멈췄을 때 간격 수정 가능하도록 잠금 해제
        self.entry_interval.config(state="normal")
        self.lbl_status.config(text="⏹ 멈춤 (설정 변경 가능)", fg="#FF5555")
        
        if self.alert_window:
            self.alert_window.close()
            self.alert_window = None

    def _tick(self):
        if self.running and self.t_next:
            remain = self.t_next - time.time()
            
            # 1. 다음 작업 카운트다운 표시
            if remain > 0:
                self.lbl_status.config(text=f"⏳ 다음 작업까지 {int(remain)}초...", fg="#F1FA8C")
            else:
                self.lbl_status.config(text="🚀 작업 시작!", fg="#50FA7B")

            # 2. 전체 완료 예상 시간(ETA) 계산
            try:
                base_interval = int(self.entry_interval.get())
            except: base_interval = 60
            
            remain_count = len(self.prompts) - self.index
            total_remain_sec = remain_count * base_interval + max(0, int(remain))
            
            # 현재 시각 + 남은 초 = 완료 예정 시각
            finish_time = datetime.fromtimestamp(time.time() + total_remain_sec)
            finish_str = finish_time.strftime("%p %I:%M")
            
            # 남은 시간 (분)
            remain_min = total_remain_sec // 60
            
            self.lbl_eta.config(text=f"📅 예상 완료: {finish_str} (약 {remain_min}분 남음)")

            # [알림창 로직] 30초 전부터 카운트다운
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
                
                # [다음 시간 설정 - 랜덤 변동 강화]
                # ±20% 범위 내에서 랜덤 변동 (최소 5초 ~ 최대 30초 변동폭 제한)
                variation = random.randint(-min(30, base_interval//5), min(30, base_interval//5))
                if base_interval < 30:
                    variation = random.randint(-5, 10)
                    
                interval = max(10, base_interval + variation)
                
                self.t_next = time.time() + interval
                self.log(f"🎲 다음 작업은 {interval}초 뒤에 시작합니다")
        else:
            self.lbl_status.config(text="대기 중...", fg="#50FA7B")
            self.lbl_eta.config(text="-")
        
        self.root.after(1000, self._tick)

    def _run_task(self):
        if not self.prompts or self.index >= len(self.prompts):
            self.running = False
            self.lbl_status.config(text="🎉 모든 작업 완료!", fg="#BD93F9")
            messagebox.showinfo("완료", "모든 프롬프트를 처리했습니다.")
            self.on_stop()
            return

        self._show() # 현재 진행 중인 프롬프트 표시
        prompt = self.prompts[self.index]
        
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
            
            self.lbl_status.config(text=f"✅ {self.index+1}번 제출 완료! 대기 중...", fg="#50FA7B")
            self.index += 1
            
        except Exception as e:
            self.lbl_status.config(text=f"오류 발생: {e}")
            self.running = False
            self.on_stop()

    def _human_move(self, x, y):
        start_x, start_y = pyautogui.position()
        duration = random.uniform(0.5, 1.0)
        mid_x = start_x + (x - start_x) * random.uniform(0.3, 0.7) + random.randint(-50, 50)
        mid_y = start_y + (y - start_y) * random.uniform(0.3, 0.7) + random.randint(-50, 50)
        pyautogui.moveTo(mid_x, mid_y, duration=duration/2, tween=pyautogui.easeOutQuad)
        pyautogui.moveTo(x, y, duration=duration/2, tween=pyautogui.easeInQuad)

if __name__ == "__main__":
    FlowVisionApp().root.mainloop()
