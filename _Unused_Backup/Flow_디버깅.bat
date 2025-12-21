@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0

echo ========================================================
echo [Flow Veo] Debug Mode
echo ========================================================
echo.
echo Checking Python environment...

set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

echo Using Python: %PYCMD%
%PYCMD% --version

echo.
echo Running flow_auto.py in debug mode...
echo (If an error occurs, it will stay on screen)
echo.

%PYCMD% flow\flow_auto.py

echo.
echo ========================================================
echo Program exited. Check the error message above!
echo ========================================================
pause