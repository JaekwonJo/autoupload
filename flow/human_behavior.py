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
CONFIG_FILE = "human_config.json"

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
        # 마우스를 화면 구석(주로 왼쪽 위)으로 휙 던지면 프로그램이 즉시 멈춥니다.
        pyautogui.FAILSAFE = True
        self.base_path = Path(__file__).resolve().parent
        self.config_path = self.base_path / CONFIG_FILE
        
        self.cfg = {} # 현재 설정값 (매번 바뀜)
        self.current_persona_name = "Initializing..."
        
        # 시작하자마자 완전 무작위 스탯 생성
        self.randomize_persona()
        
        self.current_batch_size = random.randint(self.cfg["batch_min"], self.cfg["batch_max"])
        self.processed_count = 0
        self.session_start_time = time.time()

    def load_config(self):
        # 더 이상 파일에서 로드하지 않음 (항상 랜덤)
        return {}

    def save_config(self, new_config):
        # 저장 기능 차단 (패턴 고착화 방지)
        print("💾 [Human] Save Disabled (Random Chaos Mode Active)")
        pass

    def randomize_persona(self):
        """[CORE] 인격 프리셋 삭제 -> 완전 무작위(Pure Chaos) 스탯 생성"""
        
        # 이름도 매번 바뀝니다 (구분용)
        seed_id = random.randint(1000, 9999)
        self.current_persona_name = f"Pure Random #{seed_id}"
        
        # [True Random Logic] 모든 수치를 독립적으로 주사위 굴리기
        # 연관성 없음. 그냥 다 랜덤.
        self.cfg = {
            # --- 속도 & 기본 ---
            "speed_multiplier": random.uniform(0.3, 2.5), # 더 넓은 범위
            "fitts_law_enabled": 1.0, 
            
            # --- 이동 특성 ---
            "hesitation_rate": random.uniform(0.0, 0.8),      # 가다가 멈칫거릴 확률
            "overshoot_rate": random.uniform(0.0, 0.5),       # 목표 지나칠 확률
            "micro_correction_rate": random.uniform(0.0, 0.8), # 이동 중 떨림 강도
            
            # --- 실수 & 오타 ---
            "typo_rate": random.uniform(0.02, 0.25),          # 오타 확률 대폭 증가
            "double_click_mistake": random.uniform(0.0, 0.1), # 더블클릭 실수
            "empty_click_rate": random.uniform(0.0, 0.3),     # 허공 클릭 확률
            "caret_check_rate": random.uniform(0.005, 0.04),  # [NEW] 커서 이동 검토 확률

            # --- [NEW] 11가지 인간미 기능 확률표 ---
            "enter_submit_rate": random.uniform(0.2, 0.8),    # 엔터로 제출할 확률
            "mouse_shake_rate": random.uniform(0.1, 0.5),     # 마우스 흔들기 확률
            "drag_habit_rate": random.uniform(0.1, 0.6),      # 글씨 드래그 습관
            "hesitation_on_submit": random.uniform(0.2, 0.7), # 제출 전 망설임
            "focus_loss_rate": random.uniform(0.0, 0.15),     # 딴짓하다 창 포커스 잃음
            "confused_scroll_rate": random.uniform(0.1, 0.4), # 스크롤 왔다갔다

            # --- 딴짓 & 환경 ---
            "distraction_rate": random.uniform(0.1, 0.7),     # 딴짓(창전환 등) 확률
            "drag_rate": random.uniform(0.0, 0.5),            # 의미없는 드래그
            "mouse_leave_rate": random.uniform(0.0, 0.2),     # 마우스 가출 확률
            "gaze_simulation": random.uniform(0.0, 0.5),      # 스크롤 확인 확률
            
            # --- 미세 디테일 ---
            "click_hesitation_rate": random.uniform(0.0, 0.8), # 클릭 전 빙글빙글
            "breathing_rate": random.uniform(0.0, 0.4),        # 숨 고르기
            "fatigue_factor": random.uniform(0.0, 0.2),        # 피로도 누적 속도
            
            # --- 스케줄 ---
            "batch_min": 3,
            "batch_max": random.randint(5, 12),
            "break_min_sec": random.randint(30, 300),
            "break_max_sec": random.randint(300, 1200),
            
            "work_start_hour": 0,
            "work_end_hour": 24,
            "weekend_skip_rate": random.uniform(0.0, 0.8)
        }
        
        # 기분 팩터 초기화 (이미 cfg에 반영되었으므로 1.0으로 고정)
        self.mood_time_factor = 1.0
        self.mood_typo_factor = 1.0
        self.current_mood = random.choice(["Hasty", "Relaxed", "Tired", "Normal", "Hyper", "Sluggish"])
        
        print(f"\n🎲 [Chaos Engine] Generated New Stats: {self.current_persona_name}")
        print(f"   (Speed: {self.cfg['speed_multiplier']:.2f}, Typo: {self.cfg['typo_rate']:.2f}, Distraction: {self.cfg['distraction_rate']:.2f})\n")

    def get_fatigue_multiplier(self):
        # [Feature 10] 피로도 시스템: 시간이 지날수록 점점 느려짐
        elapsed_hours = (time.time() - self.session_start_time) / 3600.0
        # 피로하면 속도가 최대 50%까지 느려짐
        fatigue = min(0.5, elapsed_hours * self.cfg.get("fatigue_factor", 0.1))
        return 1.0 + fatigue

    def get_effective_speed(self):
        return self.cfg["speed_multiplier"] * self.get_fatigue_multiplier()

    def update_batch_size(self):
        """배치가 끝날 때마다 인격도 새로고침"""
        self.randomize_persona() 
        self.current_batch_size = random.randint(self.cfg["batch_min"], self.cfg["batch_max"])
        self.processed_count = 0
        return self.current_batch_size

    def check_schedule(self):
        now = datetime.now()
        start = self.cfg["work_start_hour"] + random.uniform(-0.5, 0.5)
        end = self.cfg["work_end_hour"] + random.uniform(-0.5, 0.5)
        
        current_hour = now.hour + now.minute / 60.0
        if not (start <= current_hour <= end):
            return False, f"💤 수면 시간 ({int(start)}~{int(end)}시)"
        if now.weekday() >= 5 and random.random() < self.cfg["weekend_skip_rate"]:
            return False, "🎮 주말 휴식"
        return True, "활동 가능"

    # --- Actions ---

    def move_to(self, target_x, target_y, overshoot=True):
        """
        [Advanced Human Movement]
        직선 이동 금지! 베지에 곡선과 가속도 물리 엔진 적용.
        """
        start_x, start_y = pyautogui.position()
        
        # 기본 속도보다 훨씬 빠르게 설정 (답답함 해소)
        base_speed = self.get_effective_speed() * random.uniform(0.5, 0.8) # 숫자가 작을수록 빠름
        
        dist = math.hypot(target_x - start_x, target_y - start_y)
        
        # 거리에 따른 가변 시간 (너무 느리지 않게 상한선 둠)
        # 가까우면 순식간에, 멀어도 1초 안팎으로 휙!
        min_dur = 0.15
        max_dur = 1.2
        duration = (dist / 1800.0) * base_speed
        duration = max(min_dur, min(duration, max_dur))
        
        # [Chaos] 가끔 미친듯이 빠르게 움직임 (휙!)
        if random.random() < 0.2:
            duration *= 0.5

        # Overshoot (지나쳤다 돌아오기)
        if overshoot and random.random() < self.cfg["overshoot_rate"]:
            # 목표 지점을 살짝 지나치는 가짜 목표 설정
            over_dist = random.randint(20, 80)
            angle = math.atan2(target_y - start_y, target_x - start_x)
            over_x = target_x + math.cos(angle) * over_dist
            over_y = target_y + math.sin(angle) * over_dist
            
            # 1차 이동 (휙!)
            self._move_human_curve(start_x, start_y, over_x, over_y, duration)
            
            # 복귀 (쓱~)
            time.sleep(random.uniform(0.05, 0.15))
            self._move_human_curve(over_x, over_y, target_x, target_y, duration * 0.3)
        else:
            # 그냥 이동
            self._move_human_curve(start_x, start_y, target_x, target_y, duration)
            
        # Click hesitation (도착 후 미세 떨림)
        if random.random() < self.cfg["click_hesitation_rate"]:
            self.micro_hesitate_on_target()

    def _move_human_curve(self, x1, y1, x2, y2, duration):
        """
        [Physics Engine]
        단순 베지에가 아니라, 2~3개의 제어점을 무작위로 생성하여
        S자 곡선, C자 곡선 등 예측 불가능한 궤적을 그림.
        """
        # 제어점(Control Points) 생성 - 시작과 끝 사이 어딘가에 랜덤하게 뿌림
        # 직선 경로에서 수직으로 얼마나 벗어날지(Variance) 결정
        dist = math.hypot(x2-x1, y2-y1)
        variance = max(50, dist * 0.3)
        
        # 시작점 제어 (출발할 때 튀는 방향)
        cp1_x = x1 + (x2-x1)*0.3 + random.uniform(-variance, variance)
        cp1_y = y1 + (y2-y1)*0.3 + random.uniform(-variance, variance)
        
        # 도착점 제어 (들어갈 때 꺾이는 방향)
        cp2_x = x1 + (x2-x1)*0.7 + random.uniform(-variance, variance)
        cp2_y = y1 + (y2-y1)*0.7 + random.uniform(-variance, variance)
        
        # 단계 수: 부드러움을 위해 충분히 확보하되, 너무 많으면 느려짐
        steps = max(20, int(duration * 120)) 
        
        # 가속도 곡선 (Ease-Out or Ease-In-Out)
        # t가 0~1로 갈 때, 실제 진행률(progress)을 비선형으로 만듦
        # random.choice로 성격 결정
        curve_type = random.choice(["easeOut", "easeInOut", "snappy"])
        
        path = []
        for i in range(steps + 1):
            t = i / steps
            
            # 가속도 적용
            if curve_type == "easeOut":
                p = 1 - (1 - t) ** 3  # 처음에 빠르고 끝에 느려짐
            elif curve_type == "easeInOut":
                p = t * t * (3 - 2 * t) # 부드러운 출발과 도착
            else: # snappy
                p = 1 - (1 - t) ** 5 # 아주 빠르게 휙 가서 멈춤
            
            # 3차 베지에 공식
            bx = (1-p)**3*x1 + 3*(1-p)**2*p*cp1_x + 3*(1-p)*p**2*cp2_x + p**3*x2
            by = (1-p)**3*y1 + 3*(1-p)**2*p*cp1_y + 3*(1-p)*p**2*cp2_y + p**3*y2
            
            # [Noise] 가는 길에 손떨림 추가
            if self.cfg["micro_correction_rate"] > 0:
                shake = random.uniform(-2, 2)
                bx += shake
                by += shake
            
            path.append((bx, by))

        # 실제 이동 실행 (pyautogui.moveTo는 너무 느리므로, 잘게 쪼개서 0초 딜레이로 이동)
        # 루프 내 sleep으로 전체 시간 제어
        step_delay = duration / steps
        
        for px, py in path:
            pyautogui.moveTo(px, py)
            # 윈도우sleep 정밀도 한계 극복을 위해 busy wait 또는 최소값
            # 너무 짧으면 sleep 무시됨 -> 누적 오차 생김
            # 여기서는 단순하게 처리하되, 'snappy'하면 중간 생략도 가능
            if step_delay > 0.001:
                time.sleep(step_delay)

    def micro_hesitate_on_target(self):
        dur = random.uniform(0.1, 0.3)
        st = time.time()
        cx, cy = pyautogui.position()
        while time.time() - st < dur:
            pyautogui.moveTo(cx + random.randint(-2,2), cy + random.randint(-2,2))
            time.sleep(0.05)

    def smart_click(self):
        if random.random() < self.cfg["double_click_mistake"]:
            pyautogui.click()
            time.sleep(0.08)
            pyautogui.click()
            print("🖱️ [Mistake] Double Click")
        else:
            pyautogui.click()

    # def _ensure_english_mode(self):
    #     """
    #     [지능형 한/영 감지 센서] - 사용자 요청으로 비활성화 (수동 확인 권장)
    #     """
    #     pass

    # -------------------------------------------------------------------------
    # [Extreme Human Typing Engine V2 - Rhythm & Safe Return]
    # -------------------------------------------------------------------------
    def type_text(self, text, input_area=None):
        """
        [업그레이드된 타이핑 엔진]
        - 리듬감 추가: 갑자기 빨라지거나(Burst), 멍때리는(Pause) 패턴 적용
        - 안전한 커서 복귀: 검토 모드 후 글자가 꼬이지 않도록 3중 안전장치 적용
        """
        # [Manual] 사용자가 직접 알림창 보고 영어로 바꿉니다! (자동 기능 OFF)
        # self._ensure_english_mode()

        base_speed = self.get_effective_speed()
        
        # [Rhythm] 타이핑 리듬 상태 변수
        burst_mode = False
        burst_remaining = 0
        
        # 시작할 때 대문자 실수 (5% 확률)
        if random.random() < 0.05 and text: 
             text = text[0].swapcase() + text[1:]

        i = 0
        while i < len(text):
            char = text[i]
            
            # --- 1. 리듬 엔진 (속도 조절) ---
            # 버스트 모드 진입/해제 결정
            if not burst_mode and random.random() < 0.05: # 5% 확률로 급발진
                burst_mode = True
                burst_remaining = random.randint(5, 15)
                # print("🔥 Burst Mode On!")
            
            if burst_mode:
                # 엄청 빠름 (0.01 ~ 0.05초)
                current_delay = random.uniform(0.01, 0.05) * base_speed
                burst_remaining -= 1
                if burst_remaining <= 0:
                    burst_mode = False
            else:
                # 평소 속도 (0.05 ~ 0.25초) - 꽤 불규칙하게
                current_delay = random.uniform(0.05, 0.25) * base_speed
                
                # 가끔 멍때리기 (Thinking Pause)
                if random.random() < 0.03: # 3% 확률로 멈칫
                    pause_time = random.uniform(0.5, 1.5)
                    # print(f"💭 Thinking... ({pause_time:.1f}s)")
                    time.sleep(pause_time)

            # --- 2. 오타 시뮬레이션 (줄바꿈/공백 아닐때만) ---
            if char not in ['\n', ' '] and random.random() < self.cfg["typo_rate"]:
                self._handle_typo(char, base_speed, input_area)

            # --- 3. [Critical Fix] 안전한 검토(Caret Navigation) 모드 ---
            # 글자가 꽤 쌓였을 때(i > 10) 가끔 뒤를 돌아봄
            if i > 10 and not burst_mode and random.random() < self.cfg.get("caret_check_rate", 0.02):
                # 타이핑 잠시 중단하고 검토
                self._simulate_caret_navigation_safe(base_speed)
            
            # --- 4. 실제 키 입력 ---
            if char == '\n':
                print("⌨️ [Human] Shift+Enter (Line Break)")
                # 줄바꿈은 조금 천천히 신중하게
                time.sleep(random.uniform(0.1, 0.3))
                pyautogui.hotkey('shift', 'enter')
                time.sleep(random.uniform(0.1, 0.3))
            else:
                pyautogui.write(char)
            
            # 5. 후처리 (띄어쓰기 후 조금 쉬기 등)
            if char == ' ':
                current_delay += random.uniform(0.05, 0.1) # 단어 사이 미세 휴식
            
            # 6. 마우스 불안증 (타이핑 중 마우스 건드리기)
            # [CRITICAL FIX] 마우스가 흔들리다가 실수로 '클릭'을 해버리면 커서가 엉뚱한 곳으로 튄다!
            # 마우스 액션 후에는 무조건 커서 위치를 재정렬해야 함.
            clicked = self._jitter_mouse_during_typing(input_area)
            
            if clicked:
                # 마우스가 클릭을 했다면, 커서가 이동했을 수 있음.
                # 다음 글자 쓰기 전에 무조건 맨 뒤로 복귀!
                # print("🖱️ [Human] Mouse clicked! restoring cursor...")
                time.sleep(0.05)
                pyautogui.hotkey('ctrl', 'end')
                time.sleep(0.05)
            
            time.sleep(current_delay)
            i += 1

    def _simulate_caret_navigation_safe(self, speed):
        """
        [Human Behavior] - 안전 제일 버전
        커서를 뒤로 옮겨서 척만 하고, 다시 돌아올 때는 '무조건 맨 끝'으로 강제 이동.
        """
        # 1. 뒤로 이동 (Left Arrow)
        steps_back = random.randint(2, 8) # 너무 많이 가지 않음 (안전 위해)
        
        # 톡, 톡, 톡 끊어서 이동 (사람처럼)
        for _ in range(steps_back):
            pyautogui.press('left')
            time.sleep(random.uniform(0.05, 0.15) * speed)
            
        # 2. 고민하는 척 (Pause)
        time.sleep(random.uniform(0.3, 0.8) * speed)
        
        # 3. [CRITICAL] 원위치 복귀 (3중 안전 장치)
        # 절대 꼬이지 않게 '끝'으로 가는 모든 키를 다 동원합니다.
        
        # (A) 일단 End 키 (줄의 끝으로)
        pyautogui.press('end')
        time.sleep(0.05)
        
        # (B) 아래 방향키 (혹시 윗줄로 갔을까봐)
        pyautogui.press('down') 
        time.sleep(0.05)
        
        # (C) Ctrl + End (문서의 진짜 끝으로)
        # 꾹 누르는 느낌을 주기 위해 keyDown/keyUp 사용 권장이나 hotkey에 interval 추가
        pyautogui.hotkey('ctrl', 'end', interval=0.1)
        
        # (D) 확실히 도착했는지 0.1초 대기
        time.sleep(0.15)

    def _get_dynamic_typing_delay(self, base_speed):
        # (이 함수는 이제 type_text 내부 로직으로 대체되었으나 호환성을 위해 남김)
        return random.uniform(0.05, 0.2) * base_speed

    def _handle_typo(self, target_char, speed, input_area):
        """
        오타 시나리오 연출
        1. 옆의 키를 누름
        2. 인지하고 멈칫
        3. 백스페이스
        4. 가끔은 오타를 여러 개 내고 다 지움
        """
        # Get neighbor key
        neighbor = self._get_neighbor_key(target_char)
        
        # Multiple typos scenario (Rage typo)
        typo_count = 1
        if random.random() < 0.2:
            typo_count = random.randint(2, 4)
            
        # Type wrong keys
        for _ in range(typo_count):
            wrong_char = neighbor if _ == 0 else self._get_neighbor_key(neighbor)
            pyautogui.write(wrong_char)
            self._jitter_mouse_during_typing(input_area)
            time.sleep(random.uniform(0.05, 0.15) * speed)
        
        # Realization pause
        time.sleep(random.uniform(0.2, 0.6) * speed)
        
        # Correction (Backspace)
        for _ in range(typo_count):
            pyautogui.press('backspace')
            time.sleep(random.uniform(0.08, 0.15) * speed)
            
        # Relief pause
        if random.random() < 0.5:
            self._jitter_mouse_during_typing(input_area) # Nervous mouse check
            time.sleep(random.uniform(0.1, 0.3) * speed)

    def _get_neighbor_key(self, char):
        lower_char = char.lower()
        if lower_char in QWERTY_NEIGHBORS:
            candidates = QWERTY_NEIGHBORS[lower_char]
            return random.choice(candidates)
        # Fallback: random ascii or just the char itself
        return char

    def _jitter_mouse_during_typing(self, input_area):
        """
        타이핑 중에 마우스를 가만히 두지 않고 입력창 내부에서 빙빙 돌리거나 떤다.
        input_area: {x1, y1, x2, y2}
        Returns: True if clicked, False otherwise
        """
        if random.random() > 0.4: return False # 너무 자주는 정신사나움
        
        current_x, current_y = pyautogui.position()
        
        # Target Generation
        if input_area:
            # 입력창 내에서 랜덤 이동
            tx = random.randint(input_area['x1'], input_area['x2'])
            ty = random.randint(input_area['y1'], input_area['y2'])
            
            # 가끔은 입력창 근처 외부로 나갔다 들어옴 (User error simulation)
            if random.random() < 0.1:
                tx += random.randint(-50, 50)
                ty += random.randint(-50, 50)
        else:
            # 영역 모르면 현재 위치 주변에서 떨림
            tx = current_x + random.randint(-30, 30)
            ty = current_y + random.randint(-30, 30)

        # Move logic (Small movements, not full moves)
        # Just nudge towards target
        dx = (tx - current_x) * 0.2
        dy = (ty - current_y) * 0.2
        
        pyautogui.moveRel(dx, dy, duration=random.uniform(0.05, 0.1))
        
        # Very rare random click inside box (Refocusing)
        if input_area and random.random() < 0.05:
            # Ensure strictly inside before clicking
            cx, cy = pyautogui.position()
            if (input_area['x1'] < cx < input_area['x2']) and \
               (input_area['y1'] < cy < input_area['y2']):
                pyautogui.click()
                return True # 클릭했음!
        
        return False
                
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # [NEW] 11 Human Behaviors Implementation
    # -------------------------------------------------------------------------

    def shake_mouse(self):
        """[Feature 3] 마우스 어디갔지? (흔들기)"""
        if random.random() > self.cfg.get("mouse_shake_rate", 0.0): return
        print("👋 [Human] Shaking mouse")
        x, y = pyautogui.position()
        for _ in range(random.randint(3, 6)):
            dx = random.randint(-20, 20)
            dy = random.randint(-20, 20)
            pyautogui.moveRel(dx, dy, duration=0.05)

    def highlight_text_habit(self):
        """[Feature 1] 읽으면서 습관적으로 드래그"""
        if random.random() > self.cfg.get("drag_habit_rate", 0.0): return
        print("🖱️ [Human] Highlight text habit")
        pyautogui.dragRel(random.randint(-100, 100), 0, duration=0.3, button='left')
        time.sleep(random.uniform(0.2, 0.5))
        pyautogui.click() # 해제

    def hesitate_on_submit(self, target_x, target_y):
        """[Feature 4] 버튼 누르기 전 망설임"""
        if random.random() > self.cfg.get("hesitation_on_submit", 0.0): return
        print("🤔 [Human] Hesitating...")
        # 1. Approach
        self.move_to(target_x, target_y)
        # 2. Move away slightly (Doubt)
        x, y = pyautogui.position()
        pyautogui.moveTo(x + random.randint(-50, 50), y + random.randint(-50, 50), duration=0.3)
        time.sleep(random.uniform(0.5, 1.0))
        # 3. Come back
        self.move_to(target_x, target_y, overshoot=False)

    def simulate_focus_loss(self):
        """[Feature 8] 딴짓하다가 창 포커스 잃음"""
        if random.random() > self.cfg.get("focus_loss_rate", 0.0): return
        print("🪟 [Human] Focus Lost")
        # 현재 위치 저장
        ox, oy = pyautogui.position()
        # 화면 밖(작업표시줄 근처 등)으로 이동해서 클릭
        scr_w, scr_h = pyautogui.size()
        pyautogui.moveTo(scr_w/2, scr_h - 10, duration=0.5)
        pyautogui.click()
        time.sleep(random.uniform(1.0, 3.0)) # 멍때림
        # 다시 돌아오기 (원래 위치 근처)
        self.move_to(ox, oy, overshoot=False)
        pyautogui.click() # 포커스 회복

    def confused_scroll(self):
        """[Feature 9] 스크롤 왔다갔다 (위치 못찾음)"""
        if random.random() > self.cfg.get("confused_scroll_rate", 0.0): return
        print("📜 [Human] Confused scrolling")
        # 확 내렸다가
        pyautogui.scroll(-random.randint(300, 700))
        time.sleep(random.uniform(0.5, 1.0))
        # "어? 너무 갔네" 하고 다시 올림
        pyautogui.scroll(random.randint(100, 400))

    def simulate_gaze(self):
        print("👀 [Human] Gaze Check")
        pyautogui.scroll(random.choice([100, 200, -100]))
        time.sleep(random.uniform(0.5, 1.5))
        pyautogui.scroll(random.choice([-100, -200, 100]))

    def subconscious_drag(self):
        if random.random() < self.cfg["drag_rate"]:
            pyautogui.dragRel(random.randint(50, 150), 0, duration=0.4, button='left')
            time.sleep(0.5)
            pyautogui.click() # Release selection often by clicking

    def click_empty_space(self):
        """[Feature 5] 허공 클릭"""
        x, y = pyautogui.position()
        self.move_to(x+random.randint(-100,100), y+random.randint(-100,100), overshoot=False)
        pyautogui.click()

    def take_bio_break(self):
        dur = random.randint(self.cfg["break_min_sec"], self.cfg["break_max_sec"])
        if random.random() < self.cfg["mouse_leave_rate"]:
            scr_w, _ = pyautogui.size()
            self.move_to(scr_w-5, 500, overshoot=False)
        print(f"☕ [Human] Break: {dur}s")
        time.sleep(dur)
        return dur

    def random_behavior_routine(self):
        """[Feature 2 Included] 딴짓 루틴"""
        if random.random() > self.cfg["distraction_rate"]: return
        r = random.random()
        if r < 0.2: 
            # Tab 쳤다가 돌아오기
            pyautogui.press('tab')
            time.sleep(0.5)
            pyautogui.hotkey('shift', 'tab')
        elif r < 0.4:
            pyautogui.hotkey('alt','tab'); time.sleep(random.uniform(0.5, 2.0)); pyautogui.hotkey('alt','tab')
        elif r < 0.6:
            self.confused_scroll()
        else:
            self.shake_mouse()

    def read_prompt_pause(self, text):
        # Reading speed simulation
        base_wpm = 200
        speed = self.cfg.get("speed_multiplier", 1.0)
        # speed is delay multiplier (lower=faster), so wpm should be inverse
        wpm = base_wpm / speed
        words = len(text.split()) if text else 0
        dur = max(0.5, words / (wpm / 60.0))
        time.sleep(dur)

    def aimless_drag(self):
        # Just moving mouse around after work
        x, y = pyautogui.position()
        dx = random.randint(-100, 100)
        dy = random.randint(-100, 100)
        
        # Circle movement roughly
        self._move_human_curve(x, y, x+dx, y+dy, random.uniform(0.5, 1.0))