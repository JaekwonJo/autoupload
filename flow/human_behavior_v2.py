import math
import random
import time
from datetime import datetime
from typing import Callable, Optional, Tuple

try:
    from playwright.sync_api import Error as PlaywrightError
except Exception:  # pragma: no cover
    PlaywrightError = Exception
try:
    # ghost-cursor Python 포트 (요구사항 반영)
    from python_ghost_cursor import path as ghost_cursor_path
except Exception:  # pragma: no cover
    ghost_cursor_path = None


QWERTY_NEIGHBORS = {
    "1": "2q", "2": "13qw", "3": "24we", "4": "35er", "5": "46rt", "6": "57ty", "7": "68yu", "8": "79ui", "9": "80io", "0": "9-op",
    "q": "12wa", "w": "qeas23", "e": "wrsd34", "r": "etdf45", "t": "ryfg56", "y": "tugh67", "u": "yihj78", "i": "uojk89", "o": "ipkl90", "p": "ol0-",
    "a": "qwsz", "s": "qweadz", "d": "wersfc", "f": "ertdgv", "g": "rtyfhb", "h": "tyugjn", "j": "yuihkm", "k": "uiojlm", "l": "opk",
    "z": "asx", "x": "zsdc", "c": "xdfv", "v": "cfgb", "b": "vghn", "n": "bhjm", "m": "njk",
}


class HumanActor:
    """
    Playwright 전용 인간형 인터랙션 엔진.
    - OS 레벨 자동화(마우스/키보드 훅) 없이 page.mouse / page.keyboard 만 사용
    - 베지어 이동 + 가속/감속 + 지터 + 멈칫 + 랜덤 딜레이
    """

    def __init__(
        self,
        action_logger: Optional[Callable[[str], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.page = None
        self.language_mode = "en"
        self.session_start_time = time.time()
        self.action_logger = action_logger
        self.status_callback = status_callback
        self.current_persona_name = "Initializing..."
        self.current_mood = "Calm"
        self.mouse_x = 960.0
        self.mouse_y = 540.0
        self._viewport_cache = (1920, 1080)

        self.randomize_persona()
        self.current_batch_size = self._get_random_batch_size()
        self.processed_count = 0

    def set_page(self, page):
        self.page = page
        w, h = self._viewport()
        self.mouse_x = w / 2
        self.mouse_y = h / 2
        self._log_action(f"브라우저 페이지 연결됨 (viewport={w}x{h})")

    def _log_action(self, message: str):
        if self.action_logger:
            ts = datetime.now().strftime("%H:%M:%S")
            self.action_logger(f"[{ts}] {message}")

    def _status(self, text: str):
        if self.status_callback:
            self.status_callback(text)

    def _get_random_batch_size(self):
        return random.randint(15, 30)

    def update_batch_size(self):
        self.current_batch_size = self._get_random_batch_size()

    def randomize_persona(self):
        seed_id = random.randint(1000, 9999)
        self.current_persona_name = f"인간 지능 PW #{seed_id}"

        moods_ko = {"Energetic": "활기참", "Calm": "차분함", "Tired": "피곤함", "Meticulous": "꼼꼼함"}
        raw_mood = random.choice(list(moods_ko.keys()))
        self.current_mood = moods_ko[raw_mood]

        base_speed = random.uniform(0.8, 1.2)
        if raw_mood == "Energetic":
            base_speed *= 1.2
        if raw_mood == "Tired":
            base_speed *= 0.8

        self.cfg = {
            "speed_multiplier": base_speed,
            "overshoot_rate": random.uniform(0.1, 0.3),
            "micro_correction_rate": random.uniform(0.25, 0.5),
            "hesitation_before_click": random.uniform(0.35, 0.75),
            "double_click_mistake": 0.0,
            "typo_rate": random.uniform(0.02, 0.06),
            "caps_lock_mistake": random.uniform(0.01, 0.03),
            "breathing_pause_rate": random.uniform(0.2, 0.45),
            "window_focus_switch_rate": random.uniform(0.05, 0.2),
            "random_scroll_rate": random.uniform(0.15, 0.35),
            "mouse_wiggle_rate": random.uniform(0.15, 0.3),
            "aimless_drag_rate": random.uniform(0.08, 0.2),
            "empty_click_rate": 0.0,
            "tab_switch_rate": 0.0,
            "mouse_leave_rate": 0.0,
            "enter_submit_rate": random.uniform(0.25, 0.75),
            "gaze_simulation": random.uniform(0.1, 0.3),
            "bio_break_interval": random.randint(15, 30),
            "long_break_duration": (180, 300),
        }

        traits = []
        if self.cfg["typo_rate"] > 0.04:
            traits.append("⌨️ 가끔 오타 발생 및 수정")
        if self.cfg["hesitation_before_click"] > 0.5:
            traits.append("🖱️ 클릭 전 신중하게 고민")
        if self.cfg["mouse_wiggle_rate"] > 0.2:
            traits.append("🌊 마우스 커서 자연스러운 흔들림")
        if self.cfg["breathing_pause_rate"] > 0.3:
            traits.append("🤔 입력 도중 생각하며 멈춤")
        if self.cfg["overshoot_rate"] > 0.2:
            traits.append("🎯 목표 지점 살짝 지나쳤다 복귀")
        if self.cfg["random_scroll_rate"] > 0.25:
            traits.append("📜 가끔 무의미한 스크롤")
        if raw_mood == "Energetic":
            traits.append("⚡ 빠른 반응 속도")
        elif raw_mood == "Tired":
            traits.append("💤 반응 속도 다소 느림")
        self.active_traits = traits

    def get_active_traits(self):
        return self.active_traits

    def get_fatigue_factor(self):
        elapsed_min = (time.time() - self.session_start_time) / 60.0
        if elapsed_min > 30:
            factor = min(0.2, (elapsed_min - 30) * 0.005)
            return 1.0 - factor
        return 1.0

    def check_schedule(self):
        return True, "24/7 풀가동 중"

    def take_bio_break(self, status_callback=None):
        min_sec, max_sec = self.cfg["long_break_duration"]
        duration = random.randint(min_sec, max_sec)
        self._log_action(f"바이오 브레이크 시작 ({duration}초)")

        cb = status_callback or self.status_callback
        for i in range(duration, 0, -1):
            if cb:
                mins, secs = divmod(i, 60)
                cb(f"☕ 휴식 중... ({mins:02d}:{secs:02d} 남음)")
            time.sleep(1)

        self._log_action("바이오 브레이크 종료")
        return duration

    def _viewport(self) -> Tuple[int, int]:
        if self.page is None:
            return self._viewport_cache

        try:
            vp = self.page.viewport_size
            if vp and vp.get("width") and vp.get("height"):
                self._viewport_cache = (int(vp["width"]), int(vp["height"]))
                return self._viewport_cache
        except Exception:
            pass

        try:
            width, height = self.page.evaluate("() => [window.innerWidth, window.innerHeight]")
            self._viewport_cache = (int(width), int(height))
            return self._viewport_cache
        except Exception:
            return self._viewport_cache

    def _clamp(self, x: float, y: float) -> Tuple[float, float]:
        w, h = self._viewport()
        safe_x = max(2.0, min(float(x), float(w - 2)))
        safe_y = max(2.0, min(float(y), float(h - 2)))
        return safe_x, safe_y

    def _fitts_law_duration(self, x1: float, y1: float, x2: float, y2: float) -> float:
        distance = math.hypot(x2 - x1, y2 - y1)
        index_of_difficulty = math.log2(distance / 50.0 + 1.0)
        speed_factor = self.cfg["speed_multiplier"] * self.get_fatigue_factor()
        a = 0.18 / max(speed_factor, 0.2)
        b = 0.12 / max(speed_factor, 0.2)
        duration = a + b * index_of_difficulty
        duration *= random.uniform(0.85, 1.2)
        return max(0.25, min(duration, 3.0))

    @staticmethod
    def _ease_in_out(t: float) -> float:
        # 부드러운 가속/감속 (S-curve)
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _bezier_point(p0, p1, p2, p3, t: float):
        one_t = 1.0 - t
        return (
            one_t ** 3 * p0[0] + 3 * one_t ** 2 * t * p1[0] + 3 * one_t * t ** 2 * p2[0] + t ** 3 * p3[0],
            one_t ** 3 * p0[1] + 3 * one_t ** 2 * t * p1[1] + 3 * one_t * t ** 2 * p2[1] + t ** 3 * p3[1],
        )

    def _move_bezier(self, x1: float, y1: float, x2: float, y2: float, duration: float):
        if self.page is None:
            return

        x1, y1 = self._clamp(x1, y1)
        x2, y2 = self._clamp(x2, y2)
        points = []
        # 1) ghost-cursor 경로를 우선 사용
        if ghost_cursor_path is not None:
            try:
                route = ghost_cursor_path({"x": x1, "y": y1}, {"x": x2, "y": y2})
                if route and len(route) >= 2:
                    for p in route:
                        points.append((float(p["x"]), float(p["y"])))
                    self._log_action(f"ghost-cursor 경로 사용 (포인트 {len(points)}개)")
            except Exception as e:
                self._log_action(f"ghost-cursor 경로 생성 실패(베지어 폴백): {e}")

        # 2) ghost-cursor 실패 시 기존 베지어 폴백
        if not points:
            dist = math.hypot(x2 - x1, y2 - y1)
            distortion = max(12.0, dist * random.uniform(0.12, 0.22))

            cp1 = (
                x1 + (x2 - x1) * random.uniform(0.2, 0.4) + random.uniform(-distortion, distortion),
                y1 + (y2 - y1) * random.uniform(0.2, 0.4) + random.uniform(-distortion, distortion),
            )
            cp2 = (
                x1 + (x2 - x1) * random.uniform(0.6, 0.8) + random.uniform(-distortion, distortion),
                y1 + (y2 - y1) * random.uniform(0.6, 0.8) + random.uniform(-distortion, distortion),
            )

            steps = max(20, int(duration * random.randint(70, 130)))
            for i in range(1, steps + 1):
                t = i / steps
                eased_t = self._ease_in_out(t)
                px, py = self._bezier_point((x1, y1), cp1, cp2, (x2, y2), eased_t)
                points.append((px, py))

        steps = max(1, len(points))
        for i, (px, py) in enumerate(points, start=1):
            # ghost-cursor 포인트에도 easing 기반 시간 분배를 추가
            t = i / steps
            _ = self._ease_in_out(t)

            # 미세 jitter: 너무 튀지 않게 1~2px 수준
            if random.random() < 0.35:
                px += random.uniform(-1.2, 1.2)
                py += random.uniform(-1.2, 1.2)

            px, py = self._clamp(px, py)
            self.page.mouse.move(px, py)

            # 가끔 멈칫
            if random.random() < 0.03:
                time.sleep(random.uniform(0.05, 0.35))

            base = duration / steps
            time.sleep(base * random.uniform(0.6, 1.6))

        self.mouse_x, self.mouse_y = x2, y2

    def _micro_hesitate(self):
        mode = random.choice(["pause", "shake"])
        if mode == "pause":
            time.sleep(random.uniform(0.08, 0.35))
            return
        if self.page is None:
            return
        for _ in range(random.randint(1, 3)):
            self.mouse_x, self.mouse_y = self._clamp(
                self.mouse_x + random.uniform(-2.0, 2.0),
                self.mouse_y + random.uniform(-2.0, 2.0),
            )
            self.page.mouse.move(self.mouse_x, self.mouse_y)
            time.sleep(random.uniform(0.03, 0.08))

    def random_action_delay(self, reason: str = "행동 딜레이", min_sec: float = 0.3, max_sec: float = 2.0) -> float:
        delay = random.uniform(min_sec, max_sec)
        self._log_action(f"{reason}: {delay:.2f}초 대기")
        time.sleep(delay)
        return delay

    def think_pause(self, reason: str = "생각 중", min_sec: float = 2.0, max_sec: float = 15.0) -> float:
        pause = random.uniform(min_sec, max_sec)
        self._log_action(f"{reason}: {pause:.2f}초")
        self._status(f"🤔 {reason} ({pause:.1f}초)")
        time.sleep(pause)
        return pause

    def move_to(self, tx: float, ty: float, overshoot: bool = True, wild_approach: bool = False):
        if self.page is None:
            return

        tx, ty = self._clamp(tx, ty)
        sx, sy = self.mouse_x, self.mouse_y
        duration = self._fitts_law_duration(sx, sy, tx, ty)

        if wild_approach:
            duration *= random.uniform(1.1, 1.6)

        # 목표를 살짝 지나쳤다가 복귀하는 패턴
        if overshoot and random.random() < self.cfg.get("overshoot_rate", 0.2):
            over_dist = random.uniform(8.0, 30.0)
            angle = math.atan2(ty - sy, tx - sx)
            ox = tx + math.cos(angle) * over_dist
            oy = ty + math.sin(angle) * over_dist
            ox, oy = self._clamp(ox, oy)
            self._move_bezier(sx, sy, ox, oy, duration)
            time.sleep(random.uniform(0.05, 0.18))
            self._move_bezier(ox, oy, tx, ty, duration * random.uniform(0.2, 0.5))
        else:
            self._move_bezier(sx, sy, tx, ty, duration)

        if random.random() < self.cfg.get("hesitation_before_click", 0.5):
            self._micro_hesitate()

    def move_to_locator(self, locator, label: str = "대상"):
        if self.page is None:
            raise RuntimeError("Playwright page가 연결되지 않았습니다.")

        box = locator.bounding_box()
        if not box:
            raise RuntimeError(f"{label} 요소 위치를 찾지 못했습니다.")

        tx = box["x"] + box["width"] / 2.0 + random.uniform(-3.0, 3.0)
        ty = box["y"] + box["height"] / 2.0 + random.uniform(-2.0, 2.0)
        self._log_action(f"마우스 이동 -> {label} ({tx:.1f}, {ty:.1f})")
        self.move_to(tx, ty, overshoot=True)

    def smart_click(self, label: str = "클릭", button: str = "left"):
        if self.page is None:
            return

        self.random_action_delay(f"{label} 전 딜레이")
        down_hold = random.uniform(0.04, 0.22)
        self.page.mouse.down(button=button)
        time.sleep(down_hold)
        self.page.mouse.up(button=button)
        self._log_action(f"{label} 실행 (hold={down_hold:.2f}s)")
        self.random_action_delay(f"{label} 후 딜레이", min_sec=0.3, max_sec=1.0)

    def clear_input_field(self, locator, label: str = "입력창"):
        self.move_to_locator(locator, label=label)
        self.smart_click(label=f"{label} 포커스")
        self.page.keyboard.press("Control+A")
        self.random_action_delay("전체선택 후 딜레이", 0.3, 0.8)
        self.page.keyboard.press("Backspace")
        self._log_action(f"{label} 내용 초기화")

    def _jitter_mouse_during_typing(self):
        if self.page is None:
            return
        if random.random() > 0.18:
            return

        self.mouse_x, self.mouse_y = self._clamp(
            self.mouse_x + random.uniform(-2.0, 2.0),
            self.mouse_y + random.uniform(-2.0, 2.0),
        )
        self.page.mouse.move(self.mouse_x, self.mouse_y)
        time.sleep(random.uniform(0.03, 0.08))

    def _handle_typo(self, target_char: str):
        if target_char.lower() in QWERTY_NEIGHBORS:
            wrong = random.choice(QWERTY_NEIGHBORS[target_char.lower()])
            if target_char.isupper():
                wrong = wrong.upper()
        else:
            wrong = target_char

        self.page.keyboard.type(wrong)
        self.random_action_delay("오타 후 멈칫", 0.3, 1.0)
        self.page.keyboard.press("Backspace")
        self.random_action_delay("오타 수정 후 딜레이", 0.3, 0.7)
        self._log_action(f"오타 시뮬레이션: '{wrong}' -> 백스페이스")

    def type_text(self, text: str, input_locator=None, speed_callback=None, mode: str = "typing"):
        if self.page is None:
            raise RuntimeError("Playwright page가 연결되지 않았습니다.")

        if input_locator is not None:
            self.move_to_locator(input_locator, "입력창")
            self.smart_click("입력창 클릭")

        chosen_mode = mode
        if mode == "mixed":
            chosen_mode = random.choice(["typing", "paste"])

        self._log_action(f"텍스트 입력 시작 (mode={chosen_mode}, len={len(text)})")

        if chosen_mode == "paste":
            self.random_action_delay("붙여넣기 전 딜레이")
            self.page.keyboard.insert_text(text)
            self.random_action_delay("붙여넣기 후 딜레이")
            self._log_action("붙여넣기 완료")
            return

        fatigue = self.get_fatigue_factor()
        typo_rate = self.cfg.get("typo_rate", 0.03)

        for idx, ch in enumerate(text):
            if idx > 0 and idx % random.randint(8, 20) == 0 and random.random() < self.cfg.get("breathing_pause_rate", 0.25):
                self.think_pause("문장 입력 중 생각", 2.0, 6.0)

            current_typo_rate = typo_rate * (1.8 if fatigue < 0.9 else 1.0)
            if ch not in [" ", "\n"] and random.random() < current_typo_rate:
                self._handle_typo(ch)

            if ch == "\n":
                self.page.keyboard.press("Shift+Enter")
            else:
                self.page.keyboard.type(ch)

            # 요구사항: 타이핑 랜덤 딜레이 0.3~2.0초
            delay = random.uniform(0.3, 2.0)
            if speed_callback:
                speed_callback(round(1.0 / max(delay, 0.01), 2))

            self._jitter_mouse_during_typing()
            time.sleep(delay)

        self._log_action("타이핑 완료")

    def random_behavior_routine(self):
        if self.page is None:
            return

        actions = []
        if random.random() < self.cfg.get("random_scroll_rate", 0.2):
            actions.append("scroll")
        if random.random() < self.cfg.get("mouse_wiggle_rate", 0.2):
            actions.append("wiggle")
        if random.random() < self.cfg.get("aimless_drag_rate", 0.1):
            actions.append("move")

        if not actions:
            return

        action = random.choice(actions)
        if action == "scroll":
            amount = random.choice([-600, -300, -150, 150, 300, 600])
            self.page.mouse.wheel(0, amount)
            self._log_action(f"랜덤 스크롤 ({amount})")
            self.random_action_delay("스크롤 후 대기", 0.3, 1.2)
        elif action == "wiggle":
            self._micro_hesitate()
            self._log_action("랜덤 커서 흔들기")
        else:
            w, h = self._viewport()
            tx = random.uniform(w * 0.2, w * 0.8)
            ty = random.uniform(h * 0.2, h * 0.8)
            self.move_to(tx, ty, overshoot=True, wild_approach=True)
            self._log_action("랜덤 커서 이동")

    def shake_mouse(self):
        self._micro_hesitate()

    def read_prompt_pause(self, text):
        # 요구사항: 생각 시간 2~15초 랜덤
        self.think_pause("프롬프트 검토", 2.0, 15.0)

    def idle_action(self, _area=None):
        self.random_behavior_routine()

    def simulate_focus_loss(self):
        self.think_pause("잠깐 다른 생각", 2.0, 8.0)

    def highlight_text_habit(self):
        self.random_behavior_routine()

    def hesitate_on_submit(self, _tx=None, _ty=None):
        self.think_pause("제출 전 망설임", 2.0, 8.0)

    def confused_scroll(self):
        if self.page is None:
            return
        amount = random.choice([-400, -200, 200, 400])
        self.page.mouse.wheel(0, amount)
        self.random_action_delay("스크롤 후 멈칫", 0.3, 1.2)

    def simulate_gaze(self):
        self.random_behavior_routine()

    def subconscious_drag(self):
        self.random_behavior_routine()

    def click_empty_space(self):
        if self.page is None:
            return
        w, h = self._viewport()
        tx = random.uniform(w * 0.1, w * 0.9)
        ty = random.uniform(h * 0.1, h * 0.9)
        self.move_to(tx, ty, overshoot=True)
        self.smart_click("빈 공간 클릭")

    def ensure_locator_visible(self, locator, label: str = "요소"):
        try:
            locator.first.scroll_into_view_if_needed(timeout=5000)
        except PlaywrightError as e:
            raise RuntimeError(f"{label} 스크롤 실패: {e}") from e
