@echo off
setlocal
cd /d "%~dp0"

if exist "Autoupload_OneTouch.bat" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell;$desk=[Environment]::GetFolderPath('Desktop');$lnk=$ws.CreateShortcut((Join-Path $desk 'Autoupload.lnk'));$lnk.TargetPath=(Join-Path '%cd%' 'Autoupload_OneTouch.bat');$lnk.WorkingDirectory='%cd%';if(Test-Path '%cd%\\icon.ico'){$lnk.IconLocation=(Join-Path '%cd%' 'icon.ico')};$lnk.Description='Autoupload launcher';$lnk.Save()"
  if errorlevel 1 (
    echo [ERROR] Failed to create desktop shortcut.
  ) else (
    echo [OK] Desktop shortcut created: Autoupload.lnk
  )
  echo.
  pause
) else (
  call "%~dp0Autoupload_DesktopShortcut.bat"
)
