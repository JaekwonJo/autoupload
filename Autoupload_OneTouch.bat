@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BOOTSTRAP="
for %%F in ("%~dp00_*.bat") do (
  if /I not "%%~nxF"=="Autoupload_실행.bat" if /I not "%%~nxF"=="Autoupload_OneTouch.bat" (
    set "BOOTSTRAP=%%~fF"
    goto :FOUND
  )
)

echo [ERROR] 0_*.bat launcher not found.
echo.
pause
exit /b 1

:FOUND
echo [INFO] Launching: %BOOTSTRAP%
call "%BOOTSTRAP%"
echo.
pause
