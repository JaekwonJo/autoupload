import time
import random
import math
import json
import os
import pyautogui
import pyperclip
import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

# [윈도우 한/영 상태 확인용 상수]
IMM32 = None
try:
    IMM32 = ctypes.windll.imm32
except: pass

# [NEW] 설정 파일 상수 복구
CONFIG_FILE = "human_config_v2.json"

# QWERTY Neighbor Map for Realistic Typos
QWERTY_NEIGHBORS = {
    '1': '2q', '2': '13qw', '3': '24we', '4': '35er', '5': '46rt', '6': '57ty', '7': '68yu', '8': '79ui', '9': '80io', '0': '9-op',
    'q': '12wa', 'w': 'qeas23', 'e': 'wrsd34', 'r': 'etdf45', 't': 'ryfg56', 'y': 'tugh67', 'u': 'yihj78', 'i': 'uojk89', 'o': 'ipkl90', 'p': 'ol0-',
    'a': 'qwsz', 's': 'qweadz', 'd': 'wersfc', 'f': 'ertdgv', 'g': 'rtyfhb', 'h': 'tyugjn', 'j': 'yuihkm', 'k': 'uiojlm', 'l': 'opk',
    'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhjm', 'm': 'njk'
}

class HumanActor:
    def __init__(self):
        # [CRITICAL] 긴급 정지 활성화! 
        pyautogui.FAILSAFE = True
        self.base_path = Path(__file__).resolve().parent
        self.config_path = self.base_path / CONFIG_FILE
        
        self.cfg = {} # 현재 설정값
        self.current_persona_name = "Initializing..."
        self.randomize_persona()
        
        self.current_batch_size = random.randint(self.cfg["batch_min"], self.cfg["batch_max"])
        self.processed_count = 0
        self.session_start_time = time.time()

    def load_config(self):
        return {}

    def save_config(self, new_config):
        print("💾 [Human] Save Disabled (Random Chaos Mode Active)")
        pass

    def randomize_persona(self):
        """[CORE] 인격 완전 무작위 생성"""
        seed_id = random.randint(1000, 9999)
        self.current_persona_name = f"Pure Random #{seed_id}"
        
        self.cfg = {
            "speed_multiplier": random.uniform(0.3, 2.5),
            "fitts_law_enabled": 1.0, 
            "hesitation_rate": random.uniform(0.0, 0.8),
            "overshoot_rate": random.uniform(0.0, 0.5),
            "micro_correction_rate": random.uniform(0.0, 0.8),
            "typo_rate": random.uniform(0.02, 0.25),
            "double_click_mistake": random.uniform(0.0, 0.1),
            "empty_click_rate": random.uniform(0.0, 0.3),
            "caret_check_rate": random.uniform(0.005, 0.04),
            "enter_submit_rate": random.uniform(0.2, 0.8),
            "mouse_shake_rate": random.uniform(0.1, 0.5),
            "drag_habit_rate": random.uniform(0.1, 0.6),
            "hesitation_on_submit": random.uniform(0.2, 0.7),
            "focus_loss_rate": random.uniform(0.0, 0.15),
            "confused_scroll_rate": random.uniform(0.1, 0.4),
            "distraction_rate": random.uniform(0.1, 0.7),
            "drag_rate": random.uniform(0.0, 0.5),
            "mouse_leave_rate": random.uniform(0.0, 0.2),
            "gaze_simulation": random.uniform(0.0, 0.5),
            "click_hesitation_rate": random.uniform(0.0, 0.8),
            "breathing_rate": random.uniform(0.0, 0.4),
            "fatigue_factor": random.uniform(0.0, 0.2),
            
            # --- 스케줄 ---
            "batch_min": 3,
            "batch_max": random.randint(5, 12),
            "break_min_sec": random.randint(30, 300),
            "break_max_sec": random.randint(300, 1200),
            "work_start_hour": 0,
            "work_end_hour": 24,
            "weekend_skip_rate": 0.0
        }
        
        self.mood_time_factor = 1.0
        self.mood_typo_factor = 1.0
        self.current_mood = random.choice(["Hasty", "Relaxed", "Tired", "Normal", "Hyper", "Sluggish"])
        print(f"\n🎲 [Chaos Engine] Generated New Stats: {self.current_persona_name}")

    def get_fatigue_multiplier(self):
        elapsed_hours = (time.time() - self.session_start_time) / 3600.0
        fatigue = min(0.5, elapsed_hours * self.cfg.get("fatigue_factor", 0.1))
        return 1.0 + fatigue

    def get_effective_speed(self):
        return self.cfg["speed_multiplier"] * self.get_fatigue_multiplier()

    def update_batch_size(self):
        self.randomize_persona() 
        self.current_batch_size = random.randint(self.cfg["batch_min"], self.cfg["batch_max"])
        self.processed_count = 0
        return self.current_batch_size

    def check_schedule(self):
        return True, "활동 가능"

    # --- Actions ---
    
    def _clamp_screen_coordinates(self, x, y, margin=10):
        """[Safety] 좌표가 화면 밖이나 FailSafe 구석으로 가지 않도록 보정"""
        screen_w, screen_h = pyautogui.size()
        
        # 화면 밖으로 나가지 않도록 제한 (최소 margin, 최대 화면-margin)
        safe_x = max(margin, min(x, screen_w - margin))
        safe_y = max(margin, min(y, screen_h - margin))
        
        return safe_x, safe_y

    def move_to(self, target_x, target_y, overshoot=True, wild_approach=False):
        # [Safety] 목표 좌표 보정
        target_x, target_y = self._clamp_screen_coordinates(target_x, target_y)
        
        start_x, start_y = pyautogui.position()
        base_speed = self.get_effective_speed() * random.uniform(0.5, 0.8)
        dist = math.hypot(target_x - start_x, target_y - start_y)
        min_dur = 0.15
        max_dur = 1.2
        duration = (dist / 1800.0) * base_speed
        duration = max(min_dur, min(duration, max_dur))
        
        if random.random() < 0.2: duration *= 0.5

        if overshoot and random.random() < self.cfg["overshoot_rate"]:
            over_dist = random.randint(20, 80)
            angle = math.atan2(target_y - start_y, target_x - start_x)
            y_constraint = 0.2
            if wild_approach: y_constraint = 1.0
            over_x = target_x + math.cos(angle) * over_dist
            over_y = target_y + (math.sin(angle) * over_dist * y_constraint)
            # 중간 경유지도 보정
            over_x, over_y = self._clamp_screen_coordinates(over_x, over_y)
            
            self._move_human_curve(start_x, start_y, over_x, over_y, duration, wild=wild_approach)
            time.sleep(random.uniform(0.1, 0.2))
            self._move_human_curve(over_x, over_y, target_x, target_y, duration * 0.3, wild=wild_approach)
        else:
            self._move_human_curve(start_x, start_y, target_x, target_y, duration, wild=wild_approach)
            
        if random.random() < self.cfg["click_hesitation_rate"]:
            self.micro_hesitate_on_target()

    def _move_human_curve(self, x1, y1, x2, y2, duration, wild=False):
        # [Safety] 시작/끝점 재확인
        x1, y1 = self._clamp_screen_coordinates(x1, y1)
        x2, y2 = self._clamp_screen_coordinates(x2, y2)
        
        dist = math.hypot(x2-x1, y2-y1)
        variance_factor = 0.5 if wild else 0.1
        variance = max(50, dist * variance_factor)
        cp1_x = x1 + (x2-x1)*0.3 + random.uniform(-variance, variance)
        cp1_y = y1 + (y2-y1)*0.3 + random.uniform(-variance, variance)
        cp2_x = x1 + (x2-x1)*0.7 + random.uniform(-variance, variance)
        cp2_y = y1 + (y2-y1)*0.7 + random.uniform(-variance, variance)
        steps = max(20, int(duration * 120)) 
        curve_type = random.choice(["easeOut", "easeInOut", "snappy"])
        path = []
        for i in range(steps + 1):
            t = i / steps
            if curve_type == "easeOut": p = 1 - (1 - t) ** 3
            elif curve_type == "easeInOut": p = t * t * (3 - 2 * t)
            else: p = 1 - (1 - t) ** 5
            bx = (1-p)**3*x1 + 3*(1-p)**2*p*cp1_x + 3*(1-p)*p**2*cp2_x + p**3*x2
            by = (1-p)**3*y1 + 3*(1-p)**2*p*cp1_y + 3*(1-p)*p**2*cp2_y + p**3*y2
            if self.cfg["micro_correction_rate"] > 0:
                bx += random.uniform(-2, 2); by += random.uniform(-0.5, 0.5)
            
            # [Safety] 경로상 모든 포인트 보정
            bx, by = self._clamp_screen_coordinates(bx, by)
            path.append((bx, by))
            
        step_delay = duration / steps
        for px, py in path:
            pyautogui.moveTo(px, py)
            if step_delay > 0.001: time.sleep(step_delay)

    def micro_hesitate_on_target(self):
        dur = random.uniform(0.1, 0.3)
        st = time.time(); cx, cy = pyautogui.position()
        while time.time() - st < dur:
            pyautogui.moveTo(cx + random.randint(-2,2), cy + random.randint(-1, 1))
            time.sleep(0.05)

    def smart_click(self):
        time.sleep(0.1) 
        if random.random() < self.cfg["double_click_mistake"]:
            pyautogui.click(); time.sleep(0.1); pyautogui.click()
        else: pyautogui.click()
        time.sleep(0.1)

    def _force_cursor_to_end_aggressive(self):
        time.sleep(0.5)
        with pyautogui.hold('ctrl'):
            time.sleep(0.2); pyautogui.press('end'); time.sleep(0.2)
        time.sleep(0.5); pyautogui.hotkey('ctrl', 'end'); time.sleep(1.0)

    def _ensure_english_mode_clipboard(self):
        """
        [IME] 현재 입력기가 한글 상태인지 확인하고, 한글이면 한영키를 눌러 영문으로 전환
        """
        try:
            if not IMM32: return
            
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd: return
            
            himc = IMM32.ImmGetContext(hwnd)
            if not himc: return
            
            # IME Open Status: 0=English(Closed), Non-zero=Korean(Open) usually
            is_open = IMM32.ImmGetOpenStatus(himc)
            
            if is_open:
                print("🇰🇷 [IME] 한글 감지! -> 영문 전환 (한영키)")
                pyautogui.press('hangul')
                time.sleep(0.2)
            
            IMM32.ImmReleaseContext(hwnd, himc)
            
        except Exception as e:
            print(f"⚠️ [IME Check Error] {e}")

    # -------------------------------------------------------------------------
    # [Extreme Human Typing Engine V3 - Paste Mode ONLY]
    # -------------------------------------------------------------------------
    def type_text(self, text, input_area=None, speed_callback=None):
        """
        [Speed & Safety Update]
        - 속도: 파도타기 (Wave) 알고리즘 적용 (빨랐다 느렸다 자연스럽게)
        - 안전: Shift+Space (한영전환) 절대 방지 + 시작 전 상태 초기화
        - 시각화: speed_callback을 통해 실시간 속도 전달
        """
        # [CRITICAL] 1. 시작 전 영어가 맞는지 확인 (최초 1회만)
        self._ensure_english_mode_clipboard()
        
        # [CRITICAL] 2. 잔여 키 상태 초기화 (Shift 눌림 방지)
        pyautogui.keyUp('shift')
        pyautogui.keyUp('ctrl')
        pyautogui.keyUp('alt')

        # [Flow Engine] 속도 흐름 제어 변수
        # time_offset: 사인파의 위상 (랜덤 시작)
        time_offset = random.uniform(0, 100)
        
        i = 0
        while i < len(text):
            char = text[i]
            
            # --- 1. Flow 기반 속도 계산 (사인파 + 노이즈) ---
            # 사인파로 기본 템포가 물결침 (주기 10~20글자)
            # 값 범위: -1.0 ~ 1.0
            flow_val = math.sin(i * 0.3 + time_offset) 
            
            # 기본 딜레이: 0.01 ~ 0.04 (평균 0.025)
            # flow가 높을수록(1.0) -> delay 작음(빠름)
            # flow가 낮을수록(-1.0) -> delay 큼(느림)
            base_delay = 0.025 - (flow_val * 0.015) 
            
            # 랜덤 노이즈 추가 (±0.005)
            noise = random.uniform(-0.005, 0.005)
            current_delay = max(0.005, base_delay + noise)

            # --- 2. 특수 상황 딜레이 ---
            # 단어 끝(공백)에서 잠깐 생각 (확률적)
            if char == ' ' and random.random() < 0.2:
                current_delay += random.uniform(0.05, 0.15)
                
            # 아주 가끔 멍때리기 (0.5초)
            if random.random() < 0.005: 
                time.sleep(random.uniform(0.3, 0.6))

            # --- 3. 오타 시뮬레이션 ---
            if char not in ['\n', ' '] and random.random() < (self.cfg["typo_rate"] * 0.3):
                self._handle_typo(char, 0.5, input_area)
            
            # --- 4. UI 시각화 콜백 ---
            if speed_callback:
                # 딜레이가 0.01이면 속도 100배? (기준 3.0 대비 표현)
                # 대략 0.03초 = 1배속(30WPM) 가정 시 역산
                # 시각적으로 1.0 ~ 10.0 사이로 매핑
                # delay 0.005 -> x 10.0
                # delay 0.05 -> x 1.0
                visual_speed = min(10.0, max(0.5, 0.05 / current_delay))
                speed_callback(round(visual_speed, 1))

            # --- 5. 실제 키 입력 (안전 모드 강화) ---
            if char == '\n':
                time.sleep(0.1)
                pyautogui.keyDown('shift')
                time.sleep(0.05)
                pyautogui.press('enter')
                time.sleep(0.05)
                pyautogui.keyUp('shift')
                time.sleep(0.1)
                # [Safety] 혹시 모를 잔여 상태 제거
                pyautogui.keyUp('shift')
                
            elif char == ' ':
                # [CRITICAL] Shift+Space 절대 방지 (이중 해제)
                pyautogui.keyUp('shift') 
                pyautogui.keyUp('shift')
                time.sleep(0.01)
                pyautogui.press('space') # write 대신 press 사용
                current_delay += 0.02
                
            else:
                pyautogui.write(char)

            if random.random() < 0.05:
                self._jitter_mouse_during_typing(input_area)
            
            time.sleep(current_delay)
            i += 1

    def _jitter_mouse_during_typing(self, input_area):
        if random.random() > 0.4: return False
        current_x, current_y = pyautogui.position()
        if input_area:
            tx = random.randint(input_area['x1'], input_area['x2'])
            ty = random.randint(input_area['y1'], input_area['y2'])
        else:
            tx = current_x + random.randint(-30, 30); ty = current_y + random.randint(-30, 30)
        dx = (tx - current_x) * 0.2; dy = (ty - current_y) * 0.2
        pyautogui.moveRel(dx, dy, duration=random.uniform(0.1, 0.2))
        return False

    def idle_action(self, area):
        if random.random() > 0.1: return
        pyautogui.failSafeCheck()
        action = random.choice(["move", "scroll", "sleep", "move", "sleep"])
        try:
            if action == "move":
                tx = random.randint(area['x1'], area['x2']); ty = random.randint(area['y1'], area['y2'])
                self.move_to(tx, ty, overshoot=False)
            elif action == "scroll":
                pyautogui.scroll(random.randint(-100, 100))
            elif action == "sleep":
                sleep_time = random.uniform(0.5, 2.0); steps = int(sleep_time / 0.1)
                for _ in range(steps):
                    time.sleep(0.1); pyautogui.failSafeCheck()
        except pyautogui.FailSafeException:
            print("🚨 [AFK] 긴급 정지 감지! (FailSafe)"); raise
        except Exception as e:
            print(f"👻 [AFK] Error: {e}")

    def random_behavior_routine(self):
        if random.random() > self.cfg["distraction_rate"]: return
        r = random.random()
        if r < 0.2: 
            pyautogui.press('tab'); time.sleep(0.5); pyautogui.hotkey('shift', 'tab')
        elif r < 0.4:
            pyautogui.hotkey('alt','tab'); time.sleep(random.uniform(0.5, 2.0)); pyautogui.hotkey('alt','tab')
        elif r < 0.6: self.confused_scroll()
        else: self.shake_mouse()

    def shake_mouse(self):
        if random.random() > self.cfg.get("mouse_shake_rate", 0.0): return
        for _ in range(random.randint(3, 6)):
            pyautogui.moveRel(random.randint(-20, 20), random.randint(-5, 5), duration=0.05)

    def highlight_text_habit(self):
        if random.random() > self.cfg.get("drag_habit_rate", 0.0): return
        pyautogui.dragRel(random.randint(-100, 100), 0, duration=0.3, button='left')
        time.sleep(random.uniform(0.2, 0.5)); pyautogui.click() 

    def hesitate_on_submit(self, target_x, target_y):
        if random.random() > self.cfg.get("hesitation_on_submit", 0.0): return
        self.move_to(target_x, target_y)
        x, y = pyautogui.position()
        pyautogui.moveTo(x + random.randint(-50, 50), y + random.randint(-10, 10), duration=0.3)
        time.sleep(random.uniform(0.5, 1.0)); self.move_to(target_x, target_y, overshoot=False)

    def simulate_focus_loss(self):
        if random.random() > self.cfg.get("focus_loss_rate", 0.0): return
        ox, oy = pyautogui.position(); scr_w, scr_h = pyautogui.size()
        # [Safety] 하단 10px -> 20px 로 여유 확보
        pyautogui.moveTo(scr_w/2, scr_h - 20, duration=0.5); pyautogui.click()
        time.sleep(random.uniform(1.0, 3.0)); self.move_to(ox, oy, overshoot=False); pyautogui.click()

    def confused_scroll(self):
        if random.random() > self.cfg.get("confused_scroll_rate", 0.0): return
        pyautogui.scroll(-random.randint(300, 700)); time.sleep(random.uniform(0.5, 1.0)); pyautogui.scroll(random.randint(100, 400))

    def simulate_gaze(self):
        pyautogui.scroll(random.choice([100, 200, -100])); time.sleep(random.uniform(0.5, 1.5)); pyautogui.scroll(random.choice([-100, -200, 100]))

    def subconscious_drag(self):
        if random.random() < self.cfg["drag_rate"]:
            pyautogui.dragRel(random.randint(50, 150), 0, duration=0.4, button='left')
            time.sleep(0.5); pyautogui.click() 

    def click_empty_space(self):
        x, y = pyautogui.position()
        tx, ty = self._clamp_screen_coordinates(x+random.randint(-100,100), y+random.randint(-20,20))
        self.move_to(tx, ty, overshoot=False)

    def take_bio_break(self):
        dur = random.randint(self.cfg["break_min_sec"], self.cfg["break_max_sec"])
        if random.random() < self.cfg["mouse_leave_rate"]:
            scr_w, _ = pyautogui.size(); self.move_to(scr_w-5, 500, overshoot=False)
        print(f"☕ [Human] Break: {dur}s"); time.sleep(dur); return dur

    def read_prompt_pause(self, text):
        base_wpm = 200; speed = self.cfg.get("speed_multiplier", 1.0); wpm = base_wpm / speed
        words = len(text.split()) if text else 0; dur = max(0.5, words / (wpm / 60.0))
        time.sleep(dur)

    def aimless_drag(self):
        x, y = pyautogui.position()
        tx, ty = self._clamp_screen_coordinates(x+random.randint(-100, 100), y+random.randint(-20, 20))
        self._move_human_curve(x, y, tx, ty, random.uniform(0.5, 1.0))

    def _handle_typo(self, target_char, speed, input_area):
        """[Typos] 실제 사람처럼 인접 키를 잘못 누르고 수정"""
        # 1. 오타 발생 (인접 키 찾기)
        if target_char.lower() in QWERTY_NEIGHBORS:
            candidates = QWERTY_NEIGHBORS[target_char.lower()]
            wrong_char = random.choice(candidates)
            if target_char.isupper(): wrong_char = wrong_char.upper()
        else:
            wrong_char = chr(ord(target_char) + random.randint(-1, 1))

        pyautogui.write(wrong_char)
        time.sleep(random.uniform(0.1, 0.3) * speed)

        # 2. 인지 반응 속도 (바로 지울지, 좀 더 치다 지울지)
        if random.random() < 0.7:
            # 즉시 인지
            pyautogui.press('backspace')
        else:
            # 늦은 인지 (1~2글자 더 치고 지움)
            dummy_chars = random.randint(1, 2)
            for _ in range(dummy_chars):
                pyautogui.write(random.choice(['a', 'e', 'i', 'o', 'u']))
                time.sleep(0.1)
            for _ in range(dummy_chars + 1):
                pyautogui.press('backspace')
                time.sleep(0.1)
        
        time.sleep(random.uniform(0.1, 0.2) * speed)

    def _simulate_caret_navigation_safe(self, speed):
        """[Review] 가끔 커서를 뒤로 보내서 확인하는 척 함"""
        if random.random() > 0.5: return
        
        steps = random.randint(2, 5)
        for _ in range(steps):
            pyautogui.press('left')
            time.sleep(random.uniform(0.05, 0.15) * speed)
        
        time.sleep(random.uniform(0.3, 0.8))
        
        for _ in range(steps):
            pyautogui.press('right')
            time.sleep(random.uniform(0.05, 0.15) * speed)