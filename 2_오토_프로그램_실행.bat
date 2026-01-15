@echo off
cd /d "%~dp0"

:: 가상환경 활성화 (있으면)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: [완료] 검은 창 없이 조용히 실행 (pythonw 사용)
start "" pythonw flow\flow_auto.py

exit