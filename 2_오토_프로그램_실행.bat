@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0
set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

rem Optional: set Tk paths for Tkinter (same as Sora launcher)
rem set "_TCL=%USERPROFILE%\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
rem set "_TK=%USERPROFILE%\AppData\Local\Programs\Python\Python313\tcl\tk8.6"
rem if exist "%_TCL%" set "TCL_LIBRARY=%_TCL%"
rem if exist "%_TK%" set "TK_LIBRARY=%_TK%"

echo [Flow Veo3.1 Auto] Checking Python...
%PYCMD% --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed. Please install Python 3 and run this again.
  pause
  exit /b 1
)

echo [Flow Veo3.1 Auto] Starting process...
rem Run directly to show errors
%PYCMD% flow\flow_auto.py

echo.
echo Program exited.
pause
exit
endlocal
