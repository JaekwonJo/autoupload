@echo off
chcp 65001 >nul
cd /d %~dp0

echo ========================================================
echo [Flow Veo] Upgrade to Pure Vision Bot (No Selenium)
echo ========================================================
echo.
echo Installing Computer Vision tools (OpenCV, Pillow)...
echo This will allow the bot to "see" your screen.
echo.

set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

echo Using Python: %PYCMD%
echo.

%PYCMD% -m pip install --upgrade pip
%PYCMD% -m pip install pyautogui pyperclip opencv-python pillow

echo.
echo ========================================================
echo [OK] Vision Bot Ready!
echo You can now run 'Flow_Start.bat'.
echo ========================================================
pause