@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0
set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

rem Optional: set Tk paths for Tkinter (same as Sora launcher)
set "_TCL=%USERPROFILE%\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
set "_TK=%USERPROFILE%\AppData\Local\Programs\Python\Python313\tcl\tk8.6"
if exist "%_TCL%" set "TCL_LIBRARY=%_TCL%"
if exist "%_TK%" set "TK_LIBRARY=%_TK%"

echo [Flow Veo3.1 Auto] Checking Python...
%PYCMD% --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed. Please install Python 3 and run this again.
  pause
  exit /b 1
)

echo [Flow Veo3.1 Auto] Starting...
%PYCMD% -u flow\flow_auto.py
set ERR=%ERRORLEVEL%
echo Finished. (exit code %ERR%)
echo If there was a problem, please check flow\logs\flow_run_*.log or flow_crash_*.log.
pause
endlocal
