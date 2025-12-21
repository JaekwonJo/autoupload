@echo off
chcp 65001 >nul
cd /d %~dp0

:: 진짜 파이썬 주소 지정
set "REAL_PYTHON=C:\Users\jaekw\AppData\Local\Programs\Python\Python311\python.exe"

echo =================================================
echo      Flow Studio 필수 도구 설치 도우미 🛠️
echo      (진짜 파이썬 위치: %REAL_PYTHON%)
echo =================================================
echo.

if not exist "%REAL_PYTHON%" (
    echo [오류] 지정된 경로에 파이썬이 없습니다.
    echo 경로: %REAL_PYTHON%
    pause
    exit /b
)

echo [1/1] 필요한 부품(Selenium)을 진짜 파이썬에 설치합니다...
echo 잠시만 기다려주세요...
echo.
"%REAL_PYTHON%" -m pip install selenium webdriver_manager

echo.
echo =================================================
echo      ✨ 설치가 모두 완료되었습니다! ✨
echo =================================================
echo.
echo 이제 이 창을 끄고 [Flow_Start.bat]를 실행하시면 됩니다.
echo.
pause