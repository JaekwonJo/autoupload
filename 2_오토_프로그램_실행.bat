@echo off
CHCP 65001 > nul
cd /d "%~dp0"

REM --- 가상환경 활성화 (안전 모드) ---
if exist ".venv_wsl/Scripts/activate.bat" (
    call .venv_wsl/Scripts/activate.bat
) else if exist ".venv/Scripts/activate.bat" (
    call .venv/Scripts/activate.bat
)

REM --- 오토 프로그램 실행 ---
REM 검정색 창을 완전히 숨기려면 'Flow_Start.vbs'를 실행하세요.
REM 이 배치 파일은 디버깅용으로 남겨둡니다.

echo [INFO] 프로그램을 시작합니다...
echo [INFO] 이 창을 닫아도 프로그램은 종료되지 않습니다.
echo [INFO] (프로그램 종료는 GUI에서 '중지'를 누르세요)

start "" wscript.exe "%~dp0Flow_Start.vbs"

exit