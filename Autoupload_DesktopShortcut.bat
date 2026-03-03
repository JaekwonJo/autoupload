@echo off
setlocal
cd /d "%~dp0"

set "ICON=%CD%\icon.ico"
set "TARGET=%CD%\Autoupload_OneTouch.bat"

echo [INFO] Creating desktop shortcut: Autoupload.lnk
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$ws=New-Object -ComObject WScript.Shell;$desk=[Environment]::GetFolderPath('Desktop');$lnk=$ws.CreateShortcut((Join-Path $desk 'Autoupload.lnk'));$lnk.TargetPath='%TARGET%';$lnk.WorkingDirectory='%CD%';if(Test-Path '%ICON%'){$lnk.IconLocation='%ICON%'};$lnk.Description='Autoupload launcher';$lnk.Save()"

if errorlevel 1 (
  echo [ERROR] Failed to create desktop shortcut.
) else (
  echo [OK] Desktop shortcut created: Autoupload.lnk
)

echo.
pause
