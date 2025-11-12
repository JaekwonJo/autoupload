@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0
set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"
rem Optional: ensure Tk paths (adjust if needed)
set "TCL_LIBRARY=%USERPROFILE%\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
set "TK_LIBRARY=%USERPROFILE%\AppData\Local\Programs\Python\Python313\tcl\tk8.6"
echo [Hailuo Minimal] Starting...
%PYCMD% -u hailuo_auto.py
echo Finished.
pause
endlocal

