import json
import os
import subprocess
import time
import re
import random
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

APP_NAME = "YouTube 시청자 소통 봇 (Pro)"
DEFAULT_STUDIO_URL = "https://studio.youtube.com/"
CONFIG_FILE = "heart_config.json"

DEFAULT_CONFIG = {
    "chrome_profile_dir": "heart_chrome_profile",
    "chrome_devtools_port": 9556,
    "min_delay": 10.0,
    "max_delay": 15.0,
    "scroll_step": 600
}

class YouTubeManagerBot:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.cfg_path = self.base / CONFIG_FILE
        self.cfg = self.load_config()

        self.driver: webdriver.Chrome | None = None
        self.running = False
        self.reply_data = {} 
        self.last_scroll_height = 0
        self.scroll_stuck_count = 0
        
        # --- UI 초기화 ---
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1100x850")
        self.root.configure(bg="#F8F9FA")
        
        # 아이콘 설정 (있으면)
        try:
            icon_path = self.base.parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except: pass

        self._build_ui()
        self.log(f"{APP_NAME} 준비 완료. 환영합니다!")

    def load_config(self):
        if not self.cfg_path.exists():
            return DEFAULT_CONFIG.copy()
        try:
            return json.loads(self.cfg_path.read_text(encoding="utf-8"))
        except:
            return DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            self.cfg["min_delay"] = float(self.entry_min.get())
            self.cfg["max_delay"] = float(self.entry_max.get())
        except:
            pass
        self.cfg_path.write_text(json.dumps(self.cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", font=("Malgun Gothic", 10), padding=6)
        style.configure("Accent.TButton", background="#FA5252", foreground="white", font=("Malgun Gothic", 11, "bold"))
        style.map("Accent.TButton", background=[('active', '#E03131')])
        style.configure("TLabel", background="#F8F9FA", font=("Malgun Gothic", 10))
        style.configure("TCheckbutton", background="#F8F9FA", font=("Malgun Gothic", 10))

        paned = tk.PanedWindow(self.root, orient="horizontal", bg="#F8F9FA", sashwidth=6)
        paned.pack(fill="both", expand=True, padx=15, pady=15)

        left_frame = tk.Frame(paned, bg="#F8F9FA")
        right_frame = tk.Frame(paned, bg="#F8F9FA")
        paned.add(left_frame, minsize=420)
        paned.add(right_frame, minsize=500)

        # === [좌측] 제어 패널 ===
        tk.Label(left_frame, text="💜 시청자 소통 센터", font=("Malgun Gothic", 18, "bold"), fg="#495057", bg="#F8F9FA").pack(anchor="w", pady=(0, 5))
        tk.Label(left_frame, text="유튜브 스튜디오 댓글 자동 관리", font=("Malgun Gothic", 10), fg="#868E96", bg="#F8F9FA").pack(anchor="w", pady=(0, 20))

        # 1. 연결
        step1_frame = tk.LabelFrame(left_frame, text=" 1. 스튜디오 연결 ", font=("Malgun Gothic", 10, "bold"), bg="#F8F9FA", fg="#228BE6", padx=10, pady=10)
        step1_frame.pack(fill="x", pady=5)
        ttk.Button(step1_frame, text="🌐 크롬 브라우저 열기 (로그인 필요)", command=self.open_chrome).pack(fill="x")

        # 2. 설정
        step2_frame = tk.LabelFrame(left_frame, text=" 2. 인간적인 딜레이 설정 (봇 탐지 방지) ", font=("Malgun Gothic", 10, "bold"), bg="#F8F9FA", fg="#228BE6", padx=10, pady=10)
        step2_frame.pack(fill="x", pady=15)
        
        delay_inner = tk.Frame(step2_frame, bg="#F8F9FA")
        delay_inner.pack(fill="x")
        tk.Label(delay_inner, text="답글 작성 후").pack(side="left")
        self.entry_min = tk.Entry(delay_inner, width=5, justify="center")
        self.entry_min.pack(side="left", padx=5)
        self.entry_min.insert(0, str(self.cfg.get("min_delay", 10.0)))
        tk.Label(delay_inner, text="초 ~").pack(side="left")
        self.entry_max = tk.Entry(delay_inner, width=5, justify="center")
        self.entry_max.pack(side="left", padx=5)
        self.entry_max.insert(0, str(self.cfg.get("max_delay", 15.0)))
        tk.Label(delay_inner, text="초 랜덤 휴식").pack(side="left")

        # 타이머
        self.timer_label = tk.Label(step2_frame, text="대기 중...", fg="#ADB5BD", font=("Malgun Gothic", 9))
        self.timer_label.pack(anchor="w", pady=(5, 0))
        self.progress = ttk.Progressbar(step2_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=2)

        # 3. 실행
        step3_frame = tk.LabelFrame(left_frame, text=" 3. 작업 시작 ", font=("Malgun Gothic", 10, "bold"), bg="#F8F9FA", fg="#228BE6", padx=10, pady=10)
        step3_frame.pack(fill="x", pady=5)
        
        self.var_heart_like = tk.BooleanVar(value=True)
        self.var_reply = tk.BooleanVar(value=True)
        
        chk_inner = tk.Frame(step3_frame, bg="#F8F9FA")
        chk_inner.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(chk_inner, text="하트+좋아요 찍기", variable=self.var_heart_like).pack(side="left", padx=(0, 15))
        ttk.Checkbutton(chk_inner, text="준비된 답글 달기", variable=self.var_reply).pack(side="left")

        self.btn_start = ttk.Button(step3_frame, text="▶ 작업 시작 (START)", style="Accent.TButton", command=self.start_loop)
        self.btn_start.pack(fill="x", pady=2)
        self.btn_stop = ttk.Button(step3_frame, text="⏹ 작업 중단 (STOP)", command=self.stop_loop)
        self.btn_stop.pack(fill="x", pady=2)

        # 로그창
        tk.Label(left_frame, text="진행 로그:", font=("Malgun Gothic", 9, "bold")).pack(anchor="w", pady=(15, 2))
        self.log_text = scrolledtext.ScrolledText(left_frame, height=10, state="disabled", font=("Consolas", 9), bg="#F1F3F5")
        self.log_text.pack(fill="both", expand=True)


        # === [우측] 대본 에디터 ===
        right_top = tk.Frame(right_frame, bg="#F8F9FA")
        right_top.pack(fill="x", pady=(0, 5))
        tk.Label(right_top, text="📝 답글 매칭 대본", font=("Malgun Gothic", 12, "bold"), fg="#495057", bg="#F8F9FA").pack(side="left")
        ttk.Button(right_top, text="📂 파일 불러오기", command=self.load_reply_file).pack(side="right")

        self.editor_text = scrolledtext.ScrolledText(right_frame, font=("Malgun Gothic", 10), undo=True)
        self.editor_text.pack(fill="both", expand=True, padx=2, pady=2)

        # 사용자 요청 예시 텍스트 설정
        default_script = """1. 역사 팩트 체크형 📜
 @야무진-x8j (29분 전): 크리스마스 자체가 예수님의 탄생일이 아닙니다. 태양신의 탄생일이었던 동지제를 변질시킨거죠.

↳ 답글 (똑똑즈 TtokTtokz): 오! 역시 우리 채널 시청자분들은 지식 수준이 상당하시네요! 🕵️‍♂️ 말씀하신 대로 크리스마스의 기원에는 로마의 '동지제' 같은 다양한 역사적 배경이 섞여 있죠. 똑똑즈는 그 위에 **'자본주의'**라는 강력한 양념이 어떻게 뿌려졌는지를 다뤄봤는데, 기원까지 짚어주시니 영상이 더 풍성해지는 기분입니다! 지식 나눔 감사합니다! 🎓✨

2. 자본주의를 깨달은 고등학생 🎒
 @Ihate-schoolsomuch (2시간 전): 자본주의를 맛본 고등학생 입장이되니 크리스마스에 선물 주는 문화도 사기극이라 확신함. 근데 아이들 입장에서는 돈 쓰기 싫은 부모들의 변명으로 들릴뿐.

↳ 답글 (똑똑즈 TtokTtokz): 와... 고등학생인데 벌써 자본주의의 민낯을 보셨군요! 🐯 장난감 회사의 전략을 간파하다니, 미래의 워런 버핏이 여기 있었네요. 😂 맞아요, "이거 다 상술이야!"라고만 하면 동심 파괴처럼 들릴 수 있죠. 그래서 우리는 **'상술인 건 알지만, 그 안에서 현명하게 행복을 찾는 법'**을 배우는 거랍니다! (시험 공부 화이팅이에요! 📖🔥)

3. 피드백 감사형 (자막 위치 수정) 🙏
 @김정우-s7y8v (4시간 전): 자막 위로 올려주셨군요 감사합니다 다음편부터 적용 된다 하셨는데 앞으로 더욱 열심히 보러 오겠습니다.

↳ 답글 (똑똑즈 TtokTtokz): 정우님! 🐯✨ 소중한 의견 주신 덕분에 저희 채널이 한 단계 더 업그레이드될 수 있었습니다! 시청자분들이 편하게 보시는 게 저희에겐 0순위거든요. 🫡 약속드린 대로 다음 편부터는 훨씬 보기 편한 자막으로 찾아뵙겠습니다! 앞으로도 '출석 체크' 잊지 마세요! 충성!
"""
        self.editor_text.insert("1.0", default_script)

        btn_parse = ttk.Button(right_frame, text="✅ 위 내용 분석하여 적용하기 (Analyze)", command=self.parse_editor_content)
        btn_parse.pack(fill="x", pady=10)

        self.lbl_status = tk.Label(right_frame, text="준비된 답글: 0개", bg="#F8F9FA", fg="#E03131", font=("Malgun Gothic", 12, "bold"))
        self.lbl_status.pack(pady=(0, 10))

    # --- 기능 로직 ---

    def log(self, msg):
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{ts}] {msg}\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        except: pass

    def load_reply_file(self):
        filename = filedialog.askopenfilename(title="파일 열기", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filename:
            try:
                content = Path(filename).read_text(encoding="utf-8")
                self.editor_text.delete("1.0", "end")
                self.editor_text.insert("1.0", content)
                self.parse_editor_content()
                self.log(f"파일 로드 완료: {Path(filename).name}")
            except Exception as e:
                messagebox.showerror("오류", f"파일 읽기 실패: {e}")

    def parse_editor_content(self):
        """
        사용자가 제공한 형식을 파싱합니다.
        형식 특징: 번호로 블록 구분, @아이디 라인, ↳ 답글 라인
        """
        text = self.editor_text.get("1.0", "end")
        
        # 결과를 저장할 딕셔너리
        parsed_data = {}
        
        # 1. 텍스트를 줄 단위로 분리
        lines = text.splitlines()
        
        current_user_id = None
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # A. 사용자 아이디 찾기 (@로 시작하거나 포함된 라인)
            # 예: "@야무진-x8j (29분 전): ..." -> @야무진-x8j 추출
            if "@" in line and "답글" not in line:
                # 정규식으로 @아이디 부분만 추출 (공백, 괄호 전까지)
                match = re.search(r"(@[\w\-]+)", line)
                if match:
                    current_user_id = match.group(1)
                    # print(f"Found User: {current_user_id}")
                    continue
            
            # B. 답글 내용 찾기 (↳ 답글 ... : ...)
            # 예: "↳ 답글 (똑똑즈 TtokTtokz): 내용..."
            if (line.startswith("↳") or "답글" in line) and current_user_id:
                # 콜론(:) 뒤의 내용이 진짜 답글 내용
                parts = line.split(":", 1)
                if len(parts) > 1:
                    reply_content = parts[1].strip()
                    if reply_content:
                        parsed_data[current_user_id] = reply_content
                        # print(f"Mapped {current_user_id} -> {reply_content[:10]}...")
                        # 매칭 후 아이디 초기화 (다음 블록을 위해)
                        # current_user_id = None 
                        # (단, 한 아이디에 여러 줄일 수도 있으니 초기화는 신중히. 여기선 1:1 매핑 가정)
        
        self.reply_data = parsed_data
        count = len(self.reply_data)
        self.lbl_status.config(text=f"준비된 답글: {count}개")
        
        if count > 0:
            self.log(f"✅ 대본 분석 성공! 총 {count}명의 타겟을 찾았습니다.")
            # 검증용 로그
            first_user = list(parsed_data.keys())[0]
            self.log(f"   (예: {first_user} 님에게 답글 준비됨)")
        else:
            self.log("⚠️ 분석된 데이터가 없습니다. 형식을 확인해주세요.")
            messagebox.showwarning("분석 실패", "형식에 맞는 데이터(아이디(@), 답글)를 찾지 못했습니다.")

    def open_chrome(self):
        # ... (기존과 동일한 크롬 실행 로직) ...
        port = self.cfg["chrome_devtools_port"]
        try:
            # 이미 켜진 크롬에 연결 시도
            opts = ChromeOptions()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            svc = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=svc, options=opts)
            self.log("♻️ 실행 중인 크롬에 연결되었습니다.")
            return
        except:
            pass
        
        self.log("새 크롬 창을 시작합니다...")
        try:
            profile_path = self.base / self.cfg["chrome_profile_dir"]
            profile_path.mkdir(exist_ok=True)
            
            # Windows Chrome 경로 탐색
            candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe")
            ]
            chrome_exe = next((c for c in candidates if os.path.exists(c)), None)
            
            if not chrome_exe:
                messagebox.showerror("오류", "크롬 브라우저를 찾을 수 없습니다.")
                return

            cmd = [
                chrome_exe,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile_path}",
                "--no-first-run",
                "--disable-popup-blocking",
                DEFAULT_STUDIO_URL
            ]
            # subprocess.Popen(cmd) # 콘솔창 뜨는 문제 방지
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            time.sleep(3)
            
            opts = ChromeOptions()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            svc = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=svc, options=opts)
            self.log("✅ 크롬 실행 및 연결 성공!")
            
        except Exception as e:
            self.log(f"크롬 실행 실패: {e}")
            messagebox.showerror("실패", str(e))

    def _start_countdown(self, duration, callback):
        if not self.running: return
        start_ts = time.time()
        
        def update_timer():
            if not self.running: return
            elapsed = time.time() - start_ts
            remain = duration - elapsed
            
            if remain <= 0:
                self.progress['value'] = 0
                self.timer_label.config(text="휴식 끝! 다시 작업합니다.", fg="#228BE6")
                callback()
            else:
                pct = (remain / duration) * 100
                self.progress['value'] = pct
                self.timer_label.config(text=f"⏳ 봇 탐지 회피 중... {remain:.1f}초 남음", fg="#E03131")
                self.root.after(100, update_timer)
        
        update_timer()

    def start_loop(self):
        if not self.driver:
            messagebox.showwarning("주의", "먼저 '크롬 브라우저 열기'를 눌러주세요.")
            return
        
        self.parse_editor_content() # 시작 전 다시 파싱
        if self.var_reply.get() and not self.reply_data:
            if not messagebox.askyesno("확인", "준비된 답글이 없습니다. 하트/좋아요만 하시겠습니까?"):
                return

        self.save_config()
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.scroll_stuck_count = 0
        self.last_scroll_height = 0
        
        self.log("▶ 자동화 작업을 시작합니다.")
        self.root.after(100, self._process_comments)

    def stop_loop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.log("⏹ 작업이 사용자에 의해 중단되었습니다.")
        self.timer_label.config(text="중지됨")

    def _process_comments(self):
        if not self.running: return
        
        try:
            # JS로 현재 화면의 댓글 요소 분석 및 행동 결정
            # (Python에서 요소를 하나하나 찾으면 느리고 StaleElement 에러가 잦음)
            
            js_code = """
            return (function(replyData, doHeartLike, doReply) {
                // Shadow DOM 내부 탐색 헬퍼
                function getAllComments(root) {
                    let comments = [];
                    // ytcp-comment-thread 요소 찾기
                    let threads = root.querySelectorAll('ytcp-comment-thread');
                    threads.forEach(t => comments.push(t));
                    
                    // 재귀적으로 ShadowRoot 탐색
                    let walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, null, false);
                    while(walker.nextNode()) {
                        let node = walker.currentNode;
                        if(node.shadowRoot) {
                            comments = comments.concat(getAllComments(node.shadowRoot));
                        }
                    }
                    return comments;
                }

                let threads = getAllComments(document.body);
                
                for (let thread of threads) {
                    // 화면에 보이는지 체크 (대략적으로)
                    if (thread.offsetParent === null) continue;

                    // 작성자 이름 찾기 (#author-text > span.name 혹은 #author-text 자체)
                    let authorEl = thread.querySelector('#author-text .name') || thread.querySelector('#author-text');
                    let authorName = authorEl ? authorEl.textContent.trim() : "";
                    
                    // 작성자 아이디(핸들) 찾기 - 보통 텍스트에 포함됨
                    // 정확한 매칭을 위해 replyData의 키가 authorName에 포함되는지 확인
                    let targetKey = null;
                    if (doReply) {
                        for (let key in replyData) {
                            // key: @username
                            if (authorName.includes(key)) {
                                targetKey = key;
                                break;
                            }
                        }
                    }

                    // --- 1. 하트/좋아요 로직 ---
                    if (doHeartLike) {
                        let likeBtn = thread.querySelector('#like-button');
                        let heartBtn = thread.querySelector('#heart-button');
                        
                        // 이미 봇이 처리했는지 체크 (Attribute 이용)
                        if (likeBtn && !likeBtn.hasAttribute('data-bot-done')) {
                            let pressed = likeBtn.getAttribute('aria-pressed') === 'true';
                            if (!pressed) {
                                likeBtn.scrollIntoView({block: 'center'});
                                likeBtn.click();
                                likeBtn.setAttribute('data-bot-done', 'true');
                                return {type: 'like', name: authorName};
                            }
                            likeBtn.setAttribute('data-bot-done', 'true'); // 이미 눌려있어도 마킹
                        }
                        
                        if (heartBtn && !heartBtn.hasAttribute('data-bot-done')) {
                            let pressed = heartBtn.getAttribute('aria-pressed') === 'true';
                            // 'unhearted' 클래스 혹은 pressed 속성 확인
                            if (!pressed) {
                                heartBtn.scrollIntoView({block: 'center'});
                                heartBtn.click();
                                heartBtn.setAttribute('data-bot-done', 'true');
                                return {type: 'heart', name: authorName};
                            }
                            heartBtn.setAttribute('data-bot-done', 'true');
                        }
                    }

                    // --- 2. 답글 로직 ---
                    if (doReply && targetKey) {
                        // 이미 답글 달았는지 체크
                        if (thread.hasAttribute('data-bot-replied')) continue;
                        
                        // 내가 이미 단 답글이 있는지 확인 (reply-dialog 내부 등)
                        // 하지만 DOM 구조상 복잡하므로, 일단 'data-bot-replied' 속성으로 제어하고,
                        // 화면상에 '답글' 버튼이 있는지 확인
                        
                        let replyBtn = thread.querySelector('#reply-button');
                        let inputArea = thread.querySelector('#contenteditable-root'); // 입력창
                        
                        // 입력창이 없고 답글버튼이 있으면 -> 답글 버튼 클릭
                        if (!inputArea && replyBtn) {
                            replyBtn.scrollIntoView({block: 'center'});
                            replyBtn.click();
                            return {type: 'open_reply_box'};
                        }
                        
                        // 입력창이 있으면 -> 텍스트 입력 준비
                        if (inputArea) {
                            inputArea.focus();
                            thread.setAttribute('data-bot-replied', 'true'); // 처리 완료 표시
                            return {
                                type: 'write_reply', 
                                name: authorName, 
                                content: replyData[targetKey],
                                key: targetKey
                            };
                        }
                    }
                }
                
                // 아무 작업도 안 했다면 -> 스크롤 정보 반환
                return {
                    type: 'scroll', 
                    h: document.documentElement.scrollHeight, 
                    y: window.scrollY
                };

            })(arguments[0], arguments[1], arguments[2]);
            """
            
            # JS 실행
            reply_json_obj = self.reply_data
            result = self.driver.execute_script(js_code, reply_json_obj, self.var_heart_like.get(), self.var_reply.get())
            
            action_type = result.get('type')
            
            if action_type == 'like':
                self.log(f"👍 좋아요: {result.get('name')}")
                self.root.after(200, self._process_comments) # 딜레이 짧게
                
            elif action_type == 'heart':
                self.log(f"❤️ 하트: {result.get('name')}")
                self.root.after(200, self._process_comments)
                
            elif action_type == 'open_reply_box':
                # 답글 창 열리는 애니메이션 대기
                self.root.after(1000, self._process_comments)
                
            elif action_type == 'write_reply':
                target_user = result.get('name')
                content = result.get('content')
                self.log(f"📝 {target_user}님께 답글 작성 시작...")
                
                # 클립보드 복사 -> 붙여넣기 (가장 안정적)
                self.root.clipboard_clear()
                self.root.clipboard_append(content)
                self.root.update()
                
                # Ctrl + V
                ac = ActionChains(self.driver)
                ac.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                time.sleep(1.0) # 붙여넣기 대기
                
                # Ctrl + Enter (전송)
                ac.key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(Keys.CONTROL).perform()
                
                self.log(f"✅ 답글 전송 완료!")
                
                # ★ 중요: 랜덤 딜레이 (10~15초)
                delay = random.uniform(self.cfg["min_delay"], self.cfg["max_delay"])
                self.log(f"☕ 자연스러움을 위해 {delay:.1f}초 쉽니다...")
                self._start_countdown(delay, self._process_comments)
                
            elif action_type == 'scroll':
                # 스크롤 내리기
                current_h = result.get('h')
                if current_h == self.last_scroll_height:
                    self.scroll_stuck_count += 1
                else:
                    self.scroll_stuck_count = 0
                    self.last_scroll_height = current_h
                
                if self.scroll_stuck_count >= 5: # 5번 이상 변화 없으면 끝
                    self.log("🏁 더 이상 댓글이 없습니다. 작업 완료!")
                    self.stop_loop()
                    messagebox.showinfo("완료", "모든 댓글 확인 완료!")
                    return

                self.log("⬇️ 스크롤 내리는 중...")
                self.driver.execute_script(f"window.scrollBy(0, {self.cfg['scroll_step']});")
                self.root.after(1500, self._process_comments)

        except Exception as e:
            self.log(f"❌ 오류 발생: {e}")
            # 오류 나도 멈추지 않고 잠시 후 재시도
            self.root.after(3000, self._process_comments)

if __name__ == "__main__":
    YouTubeManagerBot().root.mainloop()