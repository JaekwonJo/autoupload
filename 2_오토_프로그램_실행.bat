@echo off
cd /d "%~dp0"

:: 가상환경 활성화 (있으면)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: [V2] 좀비 프로세스 회피용 새 파일 실행
start "" pythonw flow\flow_auto_v2.py

exit