@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0

rem Pick Python launcher if available (fallback to python)
set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

rem Only set Tk paths if they actually exist (avoid breaking Tk)
set "_TCL=%USERPROFILE%\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
set "_TK=%USERPROFILE%\AppData\Local\Programs\Python\Python313\tcl\tk8.6"
if exist "%_TCL%" (
  set "TCL_LIBRARY=%_TCL%"
)
if exist "%_TK%" (
  set "TK_LIBRARY=%_TK%"
)

echo [Hailuo Minimal] Checking Python...
%PYCMD% --version >nul 2>&1
if errorlevel 1 (
  echo Python이 설치되어 있지 않아요. https://www.python.org/ 에서 설치 후 다시 실행해 주세요.
  pause
  exit /b 1
)

echo Starting...
%PYCMD% -u hailuo_auto.py
set ERR=%ERRORLEVEL%
echo Finished. (exit code %ERR%)
echo 로그는 프로젝트\logs\hailuo_run_*.log 또는 hailuo_crash_*.log 를 확인하세요.
pause
endlocal

