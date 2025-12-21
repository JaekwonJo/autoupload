@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0

echo [YouTube Bot] Starting...

rem 1. Python Check
set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

%PYCMD% --version >nul 2>&1
if errorlevel 1 (
  echo Python not found! Please install Python.
  pause
  exit /b 1
)

rem 2. Install Deps (Quick Check)
rem We assume they are installed from previous setup, but a quick check won't hurt.
rem Suppress output to keep it clean.
%PYCMD% -c "import selenium" >nul 2>&1
if errorlevel 1 (
  echo Installing requirements...
  %PYCMD% -m pip install selenium webdriver-manager
)

rem 3. Launch GUI (Hidden Console)
rem Using pythonw if available, or start /w
if exist "%~dp0heart_bot.py" (
    start "" pythonw heart_bot.py
) else (
    echo heart_bot.py not found!
    pause
)

exit