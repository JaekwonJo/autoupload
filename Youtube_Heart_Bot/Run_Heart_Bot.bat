@echo off
setlocal
cd /d "%~dp0"

echo [YouTube Heart Bot] Finding correct Python...

REM Check standard install locations first to avoid broken C:\Python313
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe" (
    set "PYCMD=%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe"
    goto :FOUND
)

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PYCMD=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    goto :FOUND
)

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
    set "PYCMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
    goto :FOUND
)

REM Fallback to system command if explicit paths fail
set "PYCMD=python"

:FOUND
echo Using Python: "%PYCMD%"

echo [YouTube Heart Bot] Installing requirements...
"%PYCMD%" -m pip install selenium webdriver-manager

echo.
echo [YouTube Heart Bot] Starting...
"%PYCMD%" heart_bot.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred.
    pause
)
pause
endlocal