@echo off
chcp 65001 >nul
cd /d %~dp0

echo ========================================================
echo [Flow Veo] Install 'pynput' for Hotkey Detection
echo ========================================================
echo.
echo Installing 'pynput' to allow detecting 'Enter' key
echo for coordinate capture mode.
echo.

set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

echo Using Python: %PYCMD%
echo.

%PYCMD% -m pip install --upgrade pip
%PYCMD% -m pip install pyautogui pyperclip opencv-python pillow pynput

echo.
echo ========================================================
echo [OK] Ready to capture coordinates with Enter key!
echo Run '2_Auto_Program_Start.bat' now.
echo ========================================================
pause
