@echo off
setlocal
cd /d "%~dp0"

echo.
echo [INFO] Installing required libraries...
echo.

set "PY_CMD="
where python >nul 2>&1
if %errorlevel% equ 0 set "PY_CMD=python"

if not defined PY_CMD (
    where py >nul 2>&1
    if %errorlevel% equ 0 set "PY_CMD=py"
)

if not defined PY_CMD (
    echo [ERROR] Python command not found.
    echo Please install Python and enable "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [INFO] Using command: %PY_CMD%
%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 goto :FAIL

%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :FAIL

%PY_CMD% -m playwright install chromium
if errorlevel 1 goto :FAIL

echo.
echo [OK] Library installation finished.
echo Run "2_오토_프로그램_실행.bat" next.
echo.
pause
exit /b 0

:FAIL
echo.
echo [ERROR] Installation failed. Check the message above.
echo.
pause
exit /b 1
