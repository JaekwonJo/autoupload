# Flow Veo 자동화 봇 (Playwright Sync 전환판)

Playwright(Sync API) 기반으로 동작하는 자동화 앱입니다.
기존 프롬프트 순환/예약 시작/이어달리기/로그 창 기능을 유지하면서,
브라우저 내부에서 사람처럼 보이는 마우스/타이핑 행동을 수행합니다.

## 핵심 변경점
- OS 자동화 제거: `pyautogui`, `keyboard`, `mouse` 사용 안 함
- Playwright 전용 동작: `page.mouse`, `page.keyboard`만 사용
- ghost-cursor 연동: `python-ghost-cursor` 경로 기반 마우스 이동
- 행동 패턴 강화:
  - 베지어 마우스 이동 + 가속/감속 + 미세 지터 + 가끔 멈칫
  - 클릭/타이핑 랜덤 딜레이(0.3~2초)
  - 생각 시간 랜덤 pause(2~15초)
  - 세션 중 랜덤 행동으로 반복 패턴 완화
- 로그 강화:
  - UI 로그 창
  - 파일 로그: `logs/action_trace_YYYYMMDD_HHMMSS.log`
  - 세션 리포트: `logs/session_report_YYYYMMDD_HHMMSS.json`

## 설치 방법
1. `1_필수라이브러리_설치.bat` 실행
2. 내부적으로 아래를 자동 수행
   - `pip install -r requirements.txt`
   - `python -m playwright install chromium`

## 실행 방법
- 일반 실행: `2_오토_프로그램_실행.bat`
- 무음 실행: `Flow_Start.vbs`
- 디버깅 실행: `5_디버깅_모드.bat`

## 첫 설정(중요)
앱 왼쪽 설정에서 아래 3개를 반드시 입력하세요.
1. 시작 URL
2. 입력창 CSS Selector
3. 제출 버튼 CSS Selector

앱에서 아래 버튼으로 자동 도움도 가능합니다.
- `🔍 Selector 자동 찾기`: 현재 페이지에서 후보 selector 자동 탐색
- `🧪 Selector 테스트`: 지금 입력된 selector가 실제로 보이는지 검사
- `홈 화면이면 '새 프로젝트' 자동 클릭`: 홈 URL일 때 편집 화면으로 자동 진입 시도
- `새 프로젝트 버튼 selector(선택)`: 자동 탐색이 안 될 때 직접 지정 가능

예시(사이트마다 다름):
- 입력창: `textarea, [contenteditable='true']`
- 제출 버튼: `button[type='submit']`

## 프롬프트 파일
- 기본 파일: `flow/flow_prompts.txt`
- 구분자: `|||`
- 슬롯(여러 문서) 기능, 이어달리기 기능 계속 사용 가능

## 주의
- 셀렉터가 사이트 구조와 다르면 입력/제출이 실패할 수 있습니다.
- 실패 시 `5_디버깅_모드.bat`로 실행 후 로그를 확인하세요.
