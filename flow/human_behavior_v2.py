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

CONFIG_FILE = "human_config_v2.json"

QWERTY_NEIGHBORS = {
    '1': '2q', '2': '13qw', '3': '24we', '4': '35er', '5': '46rt', '6': '57ty', '7': '68yu', '8': '79ui', '9': '80io', '0': '9-op',
    'q': '12wa', 'w': 'qeas23', 'e': 'wrsd34', 'r': 'etdf45', 't': 'ryfg56', 'y': 'tugh67', 'u': 'yihj78', 'i': 'uojk89', 'o': 'ipkl90', 'p': 'ol0-',
    'a': 'qwsz', 's': 'qweadz', 'd': 'wersfc', 'f': 'ertdgv', 'g': 'rtyfhb', 'h': 'tyugjn', 'j': 'yuihkm', 'k': 'uiojlm', 'l': 'opk',
    'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhjm', 'm': 'njk'
}

class HumanActor:
    def __init__(self):
        pyautogui.FAILSAFE = True
        self.base_path = Path(__file__).resolve().parent
        self.config_path = self.base_path / CONFIG_FILE
        self.cfg = {} 
        self.current_persona_name = "Initializing..."
        self.session_start_time = time.time()
        self.randomize_persona() 
        self.current_batch_size = random.randint(15, 30)
        self.processed_count = 0

    def _get_random_batch_size(self):
        return random.randint(15, 30)

    def load_config(self):
        return {}
    def save_config(self, new_config):
        pass

    def randomize_persona(self):
        """[CORE] 인격 생성: 안전 제일 모드"""
        seed_id = random.randint(1000, 9999)
        self.current_persona_name = f"Modern Human V9 #{seed_id}"
        
        self.current_mood = random.choice(["Energetic", "Calm", "Tired", "Meticulous"])
        
        base_speed = random.uniform(0.8, 1.2) 
        if self.current_mood == "Energetic": base_speed *= 1.2
        if self.current_mood == "Tired": base_speed *= 0.8

        self.cfg = {
            "speed_multiplier": base_speed,
            "overshoot_rate": 0.2,
            "micro_correction_rate": 0.4,
            "hesitation_before_click": 0.6,
            "double_click_mistake": 0.0, 
            "typo_rate": random.uniform(0.03, 0.05),
            "caps_lock_mistake": 0.02,
            "breathing_pause_rate": 0.3,
            "window_focus_switch_rate": 0.15,
            "random_scroll_rate": 0.3,
            "mouse_wiggle_rate": 0.2,
            "aimless_drag_rate": 0.15,
            "empty_click_rate": 0.0,
            "tab_switch_rate": 0.1,
            "mouse_leave_rate": 0.0,
            "enter_submit_rate": random.uniform(0.2, 0.8),
            "gaze_simulation": 0.0,
            
            # --- Schedule (User Request: 3~5 mins) ---
            "bio_break_interval": random.randint(15, 30),
            "long_break_duration": (180, 300), 
        }

    def get_fatigue_factor(self):
        elapsed_min = (time.time() - self.session_start_time) / 60.0
        if elapsed_min > 30:
            factor = min(0.2, (elapsed_min - 30) * 0.005)
            return 1.0 - factor
        return 1.0

    def check_schedule(self):
        return True, "24/7 풀가동 중 🔥"

    def take_bio_break(self, status_callback=None):
        """[Feature] 휴식 타이머 기능 추가"""
        min_sec, max_sec = self.cfg["long_break_duration"]
        duration = random.randint(min_sec, max_sec)
        
        # 구석으로 치워두기
        if random.random() < 0.15:
            scr_w, scr_h = pyautogui.size()
            self.move_to(scr_w - 10, scr_h - 10, overshoot=False)
            
        print(f"☕ [Bio-Rhythm] Taking a long break for {duration}s...")
        
        # [SAFETY] 키보드 초기화
        pyautogui.keyUp('ctrl'); pyautogui.keyUp('shift'); pyautogui.keyUp('alt')
        
        # [TIMER] 1초씩 카운트다운하며 UI 업데이트
        for i in range(duration, 0, -1):
            if status_callback:
                mins, secs = divmod(i, 60)
                status_callback(f"☕ 휴식 중... ({mins:02d}:{secs:02d} 남음)")
            time.sleep(1)
            
        return duration

    def _clamp(self, x, y):
        """[CRITICAL SAFETY] 화면 좌표 강제 보정 (FailSafe 방지)"""
        w, h = pyautogui.size()
        safe_x = max(10, min(x, w - 10))
        safe_y = max(10, min(y, h - 10))
        return safe_x, safe_y

    def _fitts_law_duration(self, x1, y1, x2, y2):
        distance = math.hypot(x2 - x1, y2 - y1)
        index_of_difficulty = math.log2(distance / 50.0 + 1)
        speed_factor = self.cfg["speed_multiplier"] * self.get_fatigue_factor()
        a = 0.15 / speed_factor
        b = 0.10 / speed_factor
        duration = a + b * index_of_difficulty
        duration *= random.uniform(0.9, 1.1)
        return max(0.15, min(duration, 2.0))

    def move_to(self, tx, ty, overshoot=True, wild_approach=False):
        sx, sy = pyautogui.position()
        tx, ty = self._clamp(tx, ty)
        
        duration = self._fitts_law_duration(sx, sy, tx, ty)
        
        if overshoot and random.random() < self.cfg["overshoot_rate"]:
            over_dist = random.randint(10, 30)
            angle = math.atan2(ty - sy, tx - sx)
            ox = tx + math.cos(angle) * over_dist
            oy = ty + math.sin(angle) * over_dist
            ox, oy = self._clamp(ox, oy)
            
            self._move_bezier(sx, sy, ox, oy, duration)
            time.sleep(random.uniform(0.05, 0.15))
            self._move_bezier(ox, oy, tx, ty, duration * 0.3)
        else:
            self._move_bezier(sx, sy, tx, ty, duration)

        if random.random() < self.cfg["hesitation_before_click"]:
            self._micro_hesitate(tx, ty)

    def _move_bezier(self, x1, y1, x2, y2, duration):
        x1, y1 = self._clamp(x1, y1)
        x2, y2 = self._clamp(x2, y2)
        
        dist = math.hypot(x2-x1, y2-y1)
        distortion = max(20, dist * 0.15)
        
        cp1x = x1 + (x2-x1)*0.3 + random.uniform(-distortion, distortion)
        cp1y = y1 + (y2-y1)*0.3 + random.uniform(-distortion, distortion)
        cp2x = x1 + (x2-x1)*0.7 + random.uniform(-distortion, distortion)
        cp2y = y1 + (y2-y1)*0.7 + random.uniform(-distortion, distortion)
        
        steps = max(20, int(duration * 100))
        path = []
        for i in range(steps+1):
            t = i / steps
            ease_t = t * t * (3 - 2 * t) 
            bx = (1-ease_t)**3*x1 + 3*(1-ease_t)**2*ease_t*cp1x + 3*(1-ease_t)*ease_t**2*cp2x + ease_t**3*x2
            by = (1-ease_t)**3*y1 + 3*(1-ease_t)**2*ease_t*cp1y + 3*(1-ease_t)*ease_t**2*cp2y + ease_t**3*y2
            bx, by = self._clamp(bx, by)
            path.append((bx, by))
            
        for px, py in path:
            pyautogui.moveTo(px, py)
            time.sleep(duration/steps)

    def _micro_hesitate(self, x, y):
        mode = random.choice(["pause", "shake"])
        if mode == "pause":
            time.sleep(random.uniform(0.1, 0.4))
        elif mode == "shake":
            for _ in range(2):
                pyautogui.moveRel(random.randint(-1, 1), random.randint(-1, 1))
                time.sleep(0.05)

    def smart_click(self):
        time.sleep(random.uniform(0.05, 0.1))
        pyautogui.click()
        time.sleep(0.1)

    def _ensure_english_mode_clipboard(self):
        try:
            if not IMM32: return
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd: return
            himc = IMM32.ImmGetContext(hwnd)
            if not himc: return
            if IMM32.ImmGetOpenStatus(himc):
                pyautogui.press('hangul')
                time.sleep(0.2)
            IMM32.ImmReleaseContext(hwnd, himc)
        except: pass

    def type_text(self, text, input_area=None, speed_callback=None):
        self._ensure_english_mode_clipboard()
        
        # [FIX] 변수 누락 방지
        fatigue = self.get_fatigue_factor()
        key_latency = {'q': 0.02, 'p': 0.03, 'z': 0.03, 'm': 0.02, 'space': 0.04}
        
        pyautogui.keyUp('shift'); pyautogui.keyUp('ctrl'); pyautogui.keyUp('alt')
        text = text.replace('\n', ' ')

        for i, char in enumerate(text):
            if i % random.randint(10, 20) == 0 and random.random() < self.cfg["breathing_pause_rate"]:
                time.sleep(random.uniform(0.1, 0.3))

            current_typo_rate = self.cfg["typo_rate"] * (2.0 if fatigue < 0.9 else 1.0)
            if char not in [' '] and random.random() < current_typo_rate:
                self._handle_typo(char)

            if char.isupper() and random.random() < self.cfg["caps_lock_mistake"]:
                pyautogui.press(char.lower())
                time.sleep(0.3)
                pyautogui.press('backspace')

            base_delay = random.uniform(0.03, 0.07) / fatigue
            base_delay += key_latency.get(char.lower(), 0.0)

            if speed_callback:
                speed_callback(round(1.0/base_delay, 1))

            if char == ' ':
                pyautogui.keyUp('shift')
                time.sleep(0.02)
                pyautogui.press('space')
                base_delay += 0.05
                
            elif char.isupper() or char in '!@#$%^&*()_+{}|:"<>?~':
                pyautogui.keyDown('shift')
                time.sleep(0.02)
                if char.isupper(): pyautogui.press(char.lower())
                else: pyautogui.press(char)
                time.sleep(0.02)
                pyautogui.keyUp('shift')
                time.sleep(0.03)
                
            else:
                pyautogui.press(char)

            self._jitter_mouse_during_typing()
            time.sleep(base_delay)

    def _jitter_mouse_during_typing(self):
        if random.random() > 0.1: return 
        x_offset = random.randint(-2, 2)
        y_offset = random.randint(-2, 2)
        pyautogui.moveRel(x_offset, y_offset, duration=0.1)

    def _handle_typo(self, target_char):
        if target_char.lower() in QWERTY_NEIGHBORS:
            wrong = random.choice(QWERTY_NEIGHBORS[target_char.lower()])
            if target_char.isupper(): wrong = wrong.upper()
        else:
            wrong = chr(ord(target_char) + 1)
            
        pyautogui.write(wrong)
        time.sleep(random.uniform(0.3, 0.8)) 
        pyautogui.press('backspace')
        time.sleep(random.uniform(0.1, 0.2))

    def random_behavior_routine(self):
        actions = []
        if random.random() < self.cfg["window_focus_switch_rate"]: actions.append("focus_switch")
        if random.random() < self.cfg["random_scroll_rate"]: actions.append("scroll")
        if random.random() < self.cfg["aimless_drag_rate"]: actions.append("drag")
        if random.random() < self.cfg["mouse_leave_rate"]: actions.append("mouse_leave")
        
        if not actions: return

        action = random.choice(actions)
        
        if action == "focus_switch":
            pyautogui.hotkey('alt', 'tab')
            time.sleep(random.uniform(0.5, 1.5))
            pyautogui.hotkey('alt', 'tab')
            time.sleep(0.5)
            
        elif action == "scroll":
            scrolls = random.randint(2, 5)
            for _ in range(scrolls):
                pyautogui.scroll(random.choice([200, -200]))
                time.sleep(random.uniform(0.2, 0.5))
                
        elif action == "drag":
            pyautogui.dragRel(random.randint(50, 150), 0, duration=0.3, button='left')
            time.sleep(0.2)
            pyautogui.click() 
            
        elif action == "mouse_leave":
            w, h = pyautogui.size()
            pyautogui.moveTo(w - 10, h/2) 
            time.sleep(random.uniform(2.0, 5.0))

    def simulate_focus_loss(self):
        pass

    def shake_mouse(self):
        if random.random() > self.cfg.get("mouse_wiggle_rate", 0.0): return
        for _ in range(random.randint(3, 7)):
            pyautogui.moveRel(random.randint(-3, 3), random.randint(-3, 3))
            time.sleep(0.05)

    def highlight_text_habit(self):
        self.random_behavior_routine() 

    def hesitate_on_submit(self, tx, ty):
        pass
    def confused_scroll(self):
        pass
    
    def simulate_gaze(self):
        if random.random() < 0.3: 
            pyautogui.scroll(300) 
            time.sleep(random.uniform(1.0, 3.0)) 
            pyautogui.scroll(-300) 

    def subconscious_drag(self):
        pyautogui.dragRel(100, 0, 0.3, button='left')
        time.sleep(0.1)
        pyautogui.click() 

    def click_empty_space(self):
        pass 

    def read_prompt_pause(self, text):
        dur = random.uniform(2.0, 8.0)
        print(f"📖 [Human] Reading prompt... ({dur:.1f}s)")
        start = time.time()
        while time.time() - start < dur:
            if random.random() < 0.3:
                self.shake_mouse()
            time.sleep(0.5)

    def aimless_drag(self):
        x, y = pyautogui.position()
        tx, ty = self._clamp(x + random.randint(100, 300), y + random.randint(100, 300))
        self._move_bezier(x, y, tx, ty, 0.5)

    def idle_action(self, area):
        if random.random() > 0.2: return
        action = random.choice(["wiggle", "scroll", "rest"])
        try:
            if action == "wiggle":
                tx = random.randint(area['x1'], area['x2'])
                ty = random.randint(area['y1'], area['y2'])
                self.move_to(tx, ty, overshoot=False)
            elif action == "scroll":
                pyautogui.scroll(random.randint(-200, 200))
            elif action == "rest":
                time.sleep(2.0)
        except: pass
