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
        self.language_mode = "en" # 기본값: 영어 전용
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
        self.current_persona_name = f"인간 지능 V9 #{seed_id}"
        
        moods_ko = {"Energetic": "활기참", "Calm": "차분함", "Tired": "피곤함", "Meticulous": "꼼꼼함"}
        raw_mood = random.choice(list(moods_ko.keys()))
        self.current_mood = moods_ko[raw_mood]
        
        base_speed = random.uniform(0.8, 1.2) 
        if raw_mood == "Energetic": base_speed *= 1.2
        if raw_mood == "Tired": base_speed *= 0.8

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
        
        self.active_traits = []
        if self.cfg["typo_rate"] > 0.04: self.active_traits.append("⌨️ 가끔 오타 발생 및 수정")
        if self.cfg["hesitation_before_click"] > 0.5: self.active_traits.append("🖱️ 클릭 전 신중하게 고민")
        if self.cfg["mouse_wiggle_rate"] > 0.1: self.active_traits.append("🌊 마우스 커서 자연스러운 흔들림")
        if self.cfg["breathing_pause_rate"] > 0.2: self.active_traits.append("🤔 입력 도중 생각하며 멈춤")
        if self.cfg["overshoot_rate"] > 0.1: self.active_traits.append("🎯 목표 지점 살짝 지나쳤다 복귀")
        if self.cfg["random_scroll_rate"] > 0.2: self.active_traits.append("📜 가끔 무의미한 스크롤")
        if self.cfg["window_focus_switch_rate"] > 0.1: self.active_traits.append("👀 다른 창 기웃거리기 (딴짓)")
        if raw_mood == "Energetic": self.active_traits.append("⚡ 빠른 반응 속도")
        elif raw_mood == "Tired": self.active_traits.append("💤 반응 속도 다소 느림")

    def get_active_traits(self):
        return self.active_traits

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
            
        print(f"☕ [바이오 리듬] 휴식 중... ({duration}초)")
        
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
        # [NEW] 한글+영어 모드 대응: 한글이 포함된 경우 클립보드 붙여넣기 사용
        if hasattr(self, 'language_mode') and self.language_mode == "ko_en" and any(ord(c) > 127 for c in text):
            pyperclip.copy(text)
            time.sleep(random.uniform(0.5, 1.0))
            pyautogui.hotkey('ctrl', 'v')
            # 붙여넣기 후 텍스트 길이에 비례해 인간적인 대기 시간 추가
            typing_time = len(text) * 0.05 * (1.0 / self.cfg.get("speed_multiplier", 1.0))
            time.sleep(min(typing_time, 5.0))
            return

        self._ensure_english_mode_clipboard()
        
        fatigue = self.get_fatigue_factor()
        key_latency = {'q': 0.02, 'p': 0.03, 'z': 0.03, 'm': 0.02, 'space': 0.04}
        
        # [SAFETY] 시작 전 모든 키 해제
        pyautogui.keyUp('shift'); pyautogui.keyUp('ctrl'); pyautogui.keyUp('alt')
        
        # [CRITICAL] 텍스트 입력 루프
        for i, char in enumerate(text):
            # 중간에 잠깐 생각하며 멈춤 (클릭 절대 금지)
            if i % random.randint(10, 20) == 0 and random.random() < self.cfg["breathing_pause_rate"]:
                time.sleep(random.uniform(0.1, 0.3))

            current_typo_rate = self.cfg["typo_rate"] * (2.0 if fatigue < 0.9 else 1.0)
            
            # 오타 발생 로직 (공백, 줄바꿈 제외)
            if char not in [' ', '\n'] and random.random() < current_typo_rate:
                self._handle_typo(char)

            # CapsLock 실수 시뮬레이션
            if char.isupper() and random.random() < self.cfg["caps_lock_mistake"]:
                pyautogui.press(char.lower())
                time.sleep(0.3)
                pyautogui.press('backspace')

            base_delay = random.uniform(0.03, 0.07) / fatigue
            base_delay += key_latency.get(char.lower(), 0.0)

            if speed_callback:
                speed_callback(round(1.0/max(base_delay, 0.01), 1))

            # [STRICT RULE 1] Shift+Space 금지 (한영전환 방지)
            if char == ' ':
                pyautogui.keyUp('shift') # 반드시 Shift 떼기
                time.sleep(0.01)
                pyautogui.press('space')
                base_delay += 0.03
                
            # [STRICT RULE 3] 줄바꿈은 무조건 Shift+Enter
            elif char == '\n':
                pyautogui.keyDown('shift')
                time.sleep(0.02)
                pyautogui.press('enter')
                time.sleep(0.02)
                pyautogui.keyUp('shift')
                base_delay += 0.1
                
            # 특수문자 및 대문자 처리
            elif char.isupper() or char in '!@#$%^&*()_+{}|:"<>?~':
                pyautogui.keyDown('shift')
                time.sleep(0.02)
                if char.isupper(): pyautogui.press(char.lower())
                else: pyautogui.press(char)
                time.sleep(0.02)
                pyautogui.keyUp('shift')
                time.sleep(0.02)
                
            else:
                pyautogui.press(char)

            # [STRICT RULE 2] 마우스 흔들기만 허용 (클릭 금지)
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
            # [STRICT] 클릭 금지 - 드래그 대신 마우스만 쓱 움직임
            pyautogui.moveRel(random.randint(50, 150), 0, duration=0.3)
            time.sleep(0.2)
            
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
        # [STRICT] 클릭 금지 - 드래그 제스처만 취함 (버튼 클릭 X)
        pyautogui.moveRel(100, 0, duration=0.3)
        time.sleep(0.1) 

    def click_empty_space(self):
        pass 

    def read_prompt_pause(self, text):
        dur = random.uniform(2.0, 8.0)
        print(f"📖 [인간화] 프롬프트 읽는 중... ({dur:.1f}초)")
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
