@echo off
chcp 65001 > nul
cd /d %~dp0
echo.
echo [INFO] 필수 라이브러리 설치를 시도합니다...
echo.

rem 1. 'python' 명령어로 시도
python --version > nul 2>&1
if %errorlevel% equ 0 (
    echo [확인] 'python' 명령어가 작동합니다. 설치를 진행합니다.
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    goto :SUCCESS
)

rem 2. 'py' (윈도우 런처) 명령어로 시도
py --version > nul 2>&1
if %errorlevel% equ 0 (
    echo [확인] 'py' 런처가 감지되었습니다. 설치를 진행합니다.
    py -m pip install --upgrade pip
    py -m pip install -r requirements.txt
    goto :SUCCESS
)

rem 3. 실패 시 안내
echo.
echo [❌ 오류 발생] 파이썬을 찾을 수 없습니다!
echo.
echo ========================================================
echo  [해결 방법]
echo  1. 파이썬(Python)이 설치되어 있는지 확인해주세요.
echo  2. 설치했다면, 혹시 설치 화면 맨 아래에 있는
echo     "[ v ] Add Python to PATH" 체크박스를 체크하셨나요?
echo.
echo     -> 이걸 안 하면 윈도우가 파이썬을 못 찾습니다.
echo     -> 파이썬을 삭제 후 다시 설치하면서 꼭 '체크'해주세요!
echo ========================================================
echo.
pause
exit /b

:SUCCESS
echo.
echo [✅ 성공] 모든 라이브러리 설치가 완료되었습니다!
echo 이제 '2_오토_프로그램_실행.bat'을 실행하시면 됩니다.
echo.
pause