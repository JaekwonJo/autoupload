@echo off
cd /d %~dp0

:: Set Python Path explicitly
set "REAL_PYTHON=C:\Users\jaekw\AppData\Local\Programs\Python\Python311\python.exe"

echo =================================================
echo      Flow Studio Ultimate (v4.0) Launcher
echo =================================================
echo.

if not exist "%REAL_PYTHON%" (
    echo [ERROR] Python executable not found at:
    echo %REAL_PYTHON%
    pause
    exit /b
)

echo [1/2] Launching Flow Studio...
echo.
"%REAL_PYTHON%" flow_main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The program closed with an error.
    echo Please check the messages above.
    pause
)

echo.
echo [2/2] Closed.
pause
