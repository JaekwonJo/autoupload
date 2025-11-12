@echo off
setlocal
rem Use UTF-8 for readable output on Korean systems
chcp 65001 >nul
echo [Sora2 Auto] Installing required packages...

rem Prefer Python launcher if available
set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

%PYCMD% --version >nul 2>&1
if errorlevel 1 (
  echo Python not found. Please install from https://www.python.org/ and rerun.
  pause
  exit /b 1
)

rem 1) Bootstrap pip if missing
echo Checking pip...
%PYCMD% -m pip --version >nul 2>&1
if errorlevel 1 (
  echo Bootstrapping pip with ensurepip...
  %PYCMD% -m ensurepip --upgrade >nul 2>&1
  if errorlevel 1 (
    %PYCMD% -m ensurepip --default-pip >nul 2>&1
  )
)

rem 2) Upgrade pip and install deps
%PYCMD% -m pip install --upgrade pip
%PYCMD% -m pip install --upgrade selenium webdriver-manager
echo Done. You can now run the program.
pause
endlocal
