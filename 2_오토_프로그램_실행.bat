@echo off
cd /d "%~dp0"

echo ========================================================
echo      🧟‍♂️ [좀비 프로세스 청소 중...] 🧟‍♂️
echo   기존에 켜져 있던 봇들을 강제로 종료합니다.
echo ========================================================
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
echo 청소 완료! 깨끗한 상태에서 시작합니다. ✨
echo.

:: 가상환경 활성화 (있으면)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: [V2] 새로운 붙여넣기 전용 봇 실행
echo 🚀 Flow Veo Vision Bot (V2) 시작!
start "" pythonw flow\flow_auto_v2.py

exit