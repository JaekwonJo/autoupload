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

APP_NAME = "YouTube 만능 관리 봇 (Final Fix)"
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
        
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1000x850")
        self.root.configure(bg="#F3F0FF") 

        self._build_ui()
        self.log(f"{APP_NAME} 준비 완료 (Shadow DOM V4) 💜")

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
        style.configure("TButton", font=("Pretendard", 10), padding=6)
        style.configure("Accent.TButton", background="#845EF7", foreground="white", font=("Pretendard", 11, "bold"))
        style.map("Accent.TButton", background=[('active', '#7048E8')])

        paned = tk.PanedWindow(self.root, orient="horizontal", bg="#F3F0FF")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = tk.Frame(paned, bg="#F3F0FF")
        right_frame = tk.Frame(paned, bg="#F3F0FF")
        paned.add(left_frame, minsize=400)
        paned.add(right_frame, minsize=500)

        # --- 왼쪽: 컨트롤 패널 ---
        tk.Label(left_frame, text="💜 유튜브 만능 관리 봇", font=("Pretendard", 18, "bold"), bg="#F3F0FF", fg="#5F3DC4").pack(pady=(10, 5))
        tk.Label(left_frame, text="하트/좋아요 픽스 + 답글 기능 강화", font=("Pretendard", 10), bg="#F3F0FF", fg="#777").pack(pady=(0, 20))

        # 1. 크롬 열기
        ttk.Button(left_frame, text="🌐 1. 스튜디오 열기 (로그인)", command=self.open_chrome).pack(fill="x", pady=5)
        
        # 2. 휴식 간격 설정
        tk.Label(left_frame, text="⏱️ 2. 답글 딜레이 설정", font=("Pretendard", 12, "bold"), bg="#F3F0FF", fg="#555").pack(anchor="w", pady=(15, 5))
        
        delay_frame = tk.Frame(left_frame, bg="#F3F0FF")
        delay_frame.pack(fill="x", pady=5)
        
        tk.Label(delay_frame, text="최소", bg="#F3F0FF").pack(side="left")
        self.entry_min = tk.Entry(delay_frame, width=5, justify="center")
        self.entry_min.pack(side="left", padx=5)
        self.entry_min.insert(0, str(self.cfg.get("min_delay", 10.0)))
        
        tk.Label(delay_frame, text="초 ~ 최대", bg="#F3F0FF").pack(side="left")
        self.entry_max = tk.Entry(delay_frame, width=5, justify="center")
        self.entry_max.pack(side="left", padx=5)
        self.entry_max.insert(0, str(self.cfg.get("max_delay", 15.0)))
        tk.Label(delay_frame, text="초 (랜덤)", bg="#F3F0FF").pack(side="left")

        # 타이머 UI
        tk.Label(left_frame, text="⏳ 실시간 휴식 타이머", font=("Pretendard", 10, "bold"), bg="#F3F0FF", fg="#7950F2").pack(anchor="w", pady=(10, 2))
        self.timer_label = tk.Label(left_frame, text="대기 중...", bg="#F3F0FF", fg="#555")
        self.timer_label.pack(anchor="w", padx=5)
        
        self.progress = ttk.Progressbar(left_frame, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(fill="x", pady=5)

        # 3. 옵션 및 시작
        tk.Label(left_frame, text="🚀 3. 실행 옵션", font=("Pretendard", 12, "bold"), bg="#F3F0FF", fg="#555").pack(anchor="w", pady=(15, 5))
        
        self.var_heart_like = tk.BooleanVar(value=True)
        self.var_reply = tk.BooleanVar(value=True)
        
        chk_frame = tk.Frame(left_frame, bg="#F3F0FF")
        chk_frame.pack(fill="x", pady=5)
        tk.Checkbutton(chk_frame, text="하트+좋아요 찍기", variable=self.var_heart_like, bg="#F3F0FF", font=("Pretendard", 11)).pack(side="left", padx=5)
        tk.Checkbutton(chk_frame, text="답글 달기", variable=self.var_reply, bg="#F3F0FF", font=("Pretendard", 11)).pack(side="left", padx=5)

        self.btn_start = ttk.Button(left_frame, text="▶ 작업 시작", style="Accent.TButton", command=self.start_loop)
        self.btn_start.pack(fill="x", pady=(10, 5))
        
        self.btn_stop = ttk.Button(left_frame, text="⏹ 멈추기", command=self.stop_loop)
        self.btn_stop.pack(fill="x", pady=2)

        # 로그
        tk.Label(left_frame, text="로그", bg="#F3F0FF", fg="#555", font=("Pretendard", 10, "bold")).pack(anchor="w", pady=(20, 5))
        self.log_text = scrolledtext.ScrolledText(left_frame, height=12, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # --- 오른쪽: 답글 에디터 ---
        tk.Label(right_frame, text="📝 답글 대본 입력", font=("Pretendard", 12, "bold"), bg="#F3F0FF", fg="#555").pack(pady=(10, 5))
        tk.Label(right_frame, text="1. @아이디 (설명)\n[답글 복사] 내용...", bg="#F3F0FF", fg="#777", justify="left").pack(pady=(0, 5))
        
        self.editor_text = scrolledtext.ScrolledText(right_frame, font=("Malgun Gothic", 10))
        self.editor_text.pack(fill="both", expand=True, padx=5)
        
        # 기본 예시 텍스트
        example_text = """
1. @영림하-j6h (전세사기 피해 언급)
답글: 맞습니다. 피해자분들의 눈물을 생각하면 정말 가만히 있을 수가 없죠.. 😢

2. @리시앙에게진심인 (집의 본질)
[답글 복사] 명언입니다. 집은 '사는(Live) 곳'이지 투기판의 '칩'이 아니니까요. 🔥
"""
        self.editor_text.insert("1.0", example_text)

        btn_apply = ttk.Button(right_frame, text="✅ 이 내용으로 적용하기 (Parsing)", command=self.parse_editor_content)
        btn_apply.pack(fill="x", padx=5, pady=5)
        
        self.lbl_status = tk.Label(right_frame, text="준비된 답글: 0명", bg="#F3F0FF", fg="#E03131", font=("Pretendard", 11, "bold"))
        self.lbl_status.pack(pady=5)

    def log(self, msg):
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            text = f"[{ts}] {msg}\n"
            self.log_text.config(state="normal")
            self.log_text.insert("end", text)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        except:
            pass
    
    def _start_countdown(self, duration, callback):
        if not self.running: return
        start_time = time.time()
        end_time = start_time + duration
        
        def update():
            if not self.running: return
            now = time.time()
            remain = end_time - now
            if remain <= 0:
                self.progress['value'] = 0
                self.timer_label.config(text="휴식 끝! 다시 일합니다.", fg="#555")
                callback()
            else:
                percent = (remain / duration) * 100
                self.progress['value'] = percent
                self.timer_label.config(text=f"휴식 중... {remain:.1f}초 남음", fg="#E03131")
                self.root.after(50, update)
        update()

    def load_reply_file(self):
        filename = filedialog.askopenfilename(title="답글 텍스트 파일 열기", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            content = ""
            encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-16']
            for enc in encodings:
                try:
                    content = Path(filename).read_text(encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content:
                self.editor_text.delete("1.0", "end")
                self.editor_text.insert("1.0", content)
                self.parse_editor_content()
                self.log(f"파일 불러옴: {Path(filename).name}")
            else:
                messagebox.showerror("오류", "파일을 읽을 수 없습니다. (인코딩 문제)")

    def parse_editor_content(self):
        content = self.editor_text.get("1.0", "end")
        new_data = {}
        lines = content.splitlines()
        current_id = None
        
        for line in lines:
            line = line.strip()
            line = line.replace('\u200b', '').replace('\ufeff', '')
            if not line: continue
            
            # 관대한 아이디 찾기
            if "@" in line and not line.startswith("답글") and not line.startswith("[답글"):
                match = re.search(r"(@[^ \(\)\t\n]+)", line)
                if match:
                    current_id = match.group(1).strip()
                    continue
            
            # 다양한 답글 형식 인식
            reply_match = re.match(r"^(\[답글 복사\]|\[답글\]|답글:?)\s*(.*)", line)
            
            if reply_match and current_id:
                reply_msg = reply_match.group(2).strip()
                if reply_msg:
                    new_data[current_id] = reply_msg
        
        self.reply_data = new_data
        count = len(self.reply_data)
        self.lbl_status.config(text=f"준비된 답글: {count}명")
        
        if count > 0:
            sample = list(self.reply_data.items())[0]
            self.log(f"✅ 대본 분석 완료! 총 {count}명의 답글 준비.")
            self.log(f"   (예시: {sample[0]} -> {sample[1][:10]}...)")
        else:
            self.log("⚠️ 인식된 답글이 없습니다.")

    def open_chrome(self):
        port = self.cfg["chrome_devtools_port"]
        
        try:
            opts = ChromeOptions()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            svc = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=svc, options=opts)
            self.log("♻️ 이미 실행 중인 크롬을 찾았습니다! 연결 성공.")
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except: pass
            return
        except Exception:
            pass

        self.log("새 크롬 창을 실행합니다...")
        try:
            profile = self.base / self.cfg["chrome_profile_dir"]
            profile.mkdir(exist_ok=True)
            
            chrome_candidates = [
                Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe"
            ]
            chrome_exe = None
            for p in chrome_candidates:
                if p.exists():
                    chrome_exe = str(p)
                    break
            
            if not chrome_exe:
                messagebox.showerror("오류", "크롬을 찾을 수 없습니다.")
                return

            cmd = [
                chrome_exe,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--disable-popup-blocking",
                DEFAULT_STUDIO_URL
            ]
            subprocess.Popen(cmd)
            time.sleep(2)
            
            opts = ChromeOptions()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            svc = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=svc, options=opts)
            self.log("크롬 연결 성공!")
            
        except Exception as e:
            self.log(f"크롬 연결 실패: {e}")
            messagebox.showerror("오류", f"크롬 연결 실패:\n{e}")

    def start_loop(self):
        if not self.driver:
            self.log("먼저 크롬을 열어주세요.")
            return
        
        if self.var_reply.get() and not self.reply_data:
            if not messagebox.askyesno("확인", "준비된 답글 데이터가 없습니다.\n답글 없이 진행할까요?"):
                return

        self.save_config()
        # 스크롤 초기화
        self.scroll_stuck_count = 0
        self.last_scroll_height = 0

        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.log("💜 자동화 시작! (화면 분석 중...)")
        
        self.root.after(100, self._process_comments)

    def stop_loop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.log("⏹ 작업 중단")
        self.timer_label.config(text="중지됨", fg="#555")
        self.progress['value'] = 0

    def _get_random_delay(self):
        try:
            mn = float(self.entry_min.get())
            mx = float(self.entry_max.get())
            if mn < 0: mn = 0
            if mx < mn: mx = mn
        except:
            mn, mx = 10.0, 15.0
        return random.uniform(mn, mx)

    def _process_comments(self):
        if not self.running:
            return

        try:
            reply_json = json.dumps(self.reply_data, ensure_ascii=False)
            do_heart_like = "true" if self.var_heart_like.get() else "false"
            do_reply = "true" if self.var_reply.get() else "false"
            
            js_script = f"""
            return (function(replyData, doHeartLike, doReply) {{
                function queryShadowRoot(root) {{
                    let boxes = [];
                    let threads = root.querySelectorAll('ytcp-comment-thread');
                    threads.forEach(t => boxes.push(t));
                    let allNodes = root.querySelectorAll('*');
                    allNodes.forEach(node => {{
                        if (node.shadowRoot) {{
                            boxes = boxes.concat(queryShadowRoot(node.shadowRoot));
                        }}
                    }});
                    return boxes;
                }}

                let threads = queryShadowRoot(document.body);
                
                for (let thread of threads) {{
                    if (thread.offsetParent === null) continue;

                    let authorEl = thread.querySelector('#author-text');
                    let authorText = authorEl ? authorEl.innerText.trim() : "";
                    
                    let targetHandle = null;
                    if (doReply) {{
                        for (let handle in replyData) {{
                            if (authorText.includes(handle)) {{
                                targetHandle = handle;
                                break;
                            }}
                        }}
                    }}

                    // 1. 하트 & 좋아요 (강화된 로직)
                    if (doHeartLike) {{
                        // 아이콘 버튼들 찾기 (ytcp-icon-button)
                        // 좋아요: #like-button, 하트: #heart-button
                        let likeBtn = thread.querySelector('#like-button');
                        let heartBtn = thread.querySelector('#heart-button');

                        // 좋아요: aria-pressed 체크 (true면 이미 눌림)
                        // data-bot-clicked가 없어야 함
                        if (likeBtn && !likeBtn.hasAttribute('data-bot-clicked')) {{
                            if (likeBtn.getAttribute('aria-pressed') !== 'true') {{
                                likeBtn.scrollIntoView({{block: 'center', inline: 'center'}});
                                likeBtn.click();
                                likeBtn.setAttribute('data-bot-clicked', 'true');
                                return {{action: 'like'}};
                            }} else {{
                                // 이미 눌려있으면 패스 마킹 (다시 안 보게)
                                likeBtn.setAttribute('data-bot-clicked', 'true');
                            }}
                        }}

                        // 하트: aria-pressed 체크
                        if (heartBtn && !heartBtn.hasAttribute('data-bot-clicked')) {{
                            if (heartBtn.getAttribute('aria-pressed') !== 'true') {{
                                heartBtn.scrollIntoView({{block: 'center', inline: 'center'}});
                                heartBtn.click();
                                heartBtn.setAttribute('data-bot-clicked', 'true');
                                return {{action: 'heart'}};
                            }} else {{
                                heartBtn.setAttribute('data-bot-clicked', 'true');
                            }}
                        }}
                    }}

                    // 2. 답글
                    if (doReply && targetHandle) {{
                        if (thread.hasAttribute('data-bot-replied')) continue;
                        
                        let replyBtn = thread.querySelector('#reply-button');
                        let inputArea = thread.querySelector('#contenteditable-root');
                        
                        // 답글 창이 안 열려있으면 열기
                        if (!inputArea && replyBtn) {{
                            replyBtn.scrollIntoView({{block: 'center', inline: 'center'}});
                            replyBtn.click();
                            return {{action: 'open_reply'}};
                        }}
                        
                        // 열려있으면 입력
                        if (inputArea) {{
                            inputArea.focus();
                            thread.setAttribute('data-bot-replied', 'true');
                            return {{
                                action: 'type_reply',
                                text: replyData[targetHandle],
                                handle: targetHandle
                            }}; 
                        }}
                    }}
                }}
                
                // 현재 보이는 화면에서 할 일이 없음 -> 스크롤 정보 리턴
                return {{
                    action: 'none', 
                    scrollHeight: document.documentElement.scrollHeight,
                    scrollY: window.scrollY
                }};
            }})({reply_json}, {do_heart_like}, {do_reply});
            """
            
            result = self.driver.execute_script(js_script)
            action = result.get('action')
            
            if action == 'like':
                self.log("👍 좋아요 클릭!")
                self.root.after(100, self._process_comments) # 딜레이 없이 바로 다음
                
            elif action == 'heart':
                self.log("❤️ 하트 클릭!")
                self.root.after(100, self._process_comments)
                
            elif action == 'open_reply':
                # 답글 창 열릴 때까지 약간 대기
                self.root.after(800, self._process_comments)
                
            elif action == 'type_reply':
                text = result.get('text')
                handle = result.get('handle')
                self.log(f"📝 {handle}님에게 답글 작성 중...")
                
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                    self.root.update()
                    
                    ac = ActionChains(self.driver)
                    ac.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    time.sleep(1.0) # 타이핑 확인 딜레이
                    ac.key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(Keys.CONTROL).perform()
                    
                    self.log(f"✅ 답글 전송 완료!")
                    
                    # 답글 후 휴식
                    delay = self._get_random_delay()
                    self.log(f"   ☕ 답글 작성 후 휴식... ({delay:.1f}초)")
                    self._start_countdown(delay, self._process_comments)
                    
                except Exception as e:
                    self.log(f"답글 작성 실패: {e}")
                    self.root.after(100, self._process_comments)
                
            else:
                # 할 일 없음 -> 스크롤 내리기
                if self.running:
                    current_h = result.get('scrollHeight', 0)
                    
                    # 스크롤 종료 체크
                    if current_h == self.last_scroll_height:
                        self.scroll_stuck_count += 1
                    else:
                        self.scroll_stuck_count = 0
                        self.last_scroll_height = current_h
                    
                    # 3번 이상 높이 변화가 없으면 종료
                    if self.scroll_stuck_count >= 3:
                        self.log("🏁 모든 댓글을 확인했습니다. (스크롤 끝)")
                        self.stop_loop()
                        messagebox.showinfo("완료", "모든 작업이 끝났습니다!")
                        return

                    self.log("더 찾으러 내려갑니다... ⬇️")
                    self.driver.execute_script(f"window.scrollBy(0, {self.cfg.get('scroll_step', 600)});")
                    
                    # 로딩 대기
                    self.root.after(2000, self._process_comments)

        except Exception as e:
            self.log(f"오류: {e}")
            self.running = False
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")

if __name__ == "__main__":
    YouTubeManagerBot().root.mainloop()