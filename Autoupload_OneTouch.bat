@echo off
setlocal
cd /d "%~dp0"

start "" /b wscript.exe "%~dp0Flow_Start.vbs"
exit /b 0
