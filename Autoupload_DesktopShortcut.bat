@echo off
setlocal
cd /d "%~dp0"

set "ICON=%CD%\icon.ico"

echo [INFO] Creating desktop shortcut: Autoupload.lnk
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';$base=(Get-Location).Path;$launcher=Get-ChildItem -LiteralPath $base -Filter 'Autoupload_*.bat' | Where-Object { $_.Name -ne 'Autoupload_DesktopShortcut.bat' } | Select-Object -First 1;if(-not $launcher){throw 'Launcher bat not found.'};$ws=New-Object -ComObject WScript.Shell;$desk=[Environment]::GetFolderPath('Desktop');$lnk=$ws.CreateShortcut((Join-Path $desk 'Autoupload.lnk'));$lnk.TargetPath=$launcher.FullName;$lnk.WorkingDirectory=$base;if(Test-Path '%ICON%'){$lnk.IconLocation='%ICON%'};$lnk.Description='Autoupload launcher';$lnk.Save()"

if errorlevel 1 (
  echo [ERROR] Failed to create desktop shortcut.
) else (
  echo [OK] Desktop shortcut created: Autoupload.lnk
)

echo.
pause
