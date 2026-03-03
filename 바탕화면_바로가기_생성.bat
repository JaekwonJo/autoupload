@echo off
setlocal
cd /d "%~dp0"

if exist "Autoupload_DesktopShortcut.bat" (
  call "Autoupload_DesktopShortcut.bat"
) else (
  echo [ERROR] Missing file: Autoupload_DesktopShortcut.bat
  echo.
  pause
)
