@echo off
cd /d %~dp0
echo [INFO] 필수 라이브러리를 설치합니다...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] 설치 중 오류가 발생했습니다. 파이썬이 설치되어 있는지 확인해주세요.
) else (
    echo [SUCCESS] 모든 설치가 완료되었습니다! 이제 '2_오토_프로그램_실행.bat'을 실행하세요.
)
pause
