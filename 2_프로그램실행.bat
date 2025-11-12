@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0
set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"
set "TCL_LIBRARY=C:\Users\jaekw\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
set "TK_LIBRARY=C:\Users\jaekw\AppData\Local\Programs\Python\Python313\tcl\tk8.6"
echo [Sora2 Auto] Starting...
%PYCMD% -u sora_auto.py
echo Finished.
pause
endlocal
