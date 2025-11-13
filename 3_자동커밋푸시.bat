@echo off
setlocal ENABLEDELAYEDEXPANSION

REM 빠른 커밋 + 푸시 도우미
REM 사용법: 3_자동커밋푸시.bat [커밋메시지]

cd /d "%~dp0"

set MSG=%*
if "%MSG%"=="" (
  set /p MSG=커밋 메시지를 적어주세요 (엔터=자동문구): 
)
if "%MSG%"=="" (
  for /f "tokens=1-5 delims=/:. " %%a in ("%date% %time%") do set MSG=auto commit %%a-%%b-%%c_%%d%%e
)

echo [git add]
git add -A

echo [git commit]
git commit -m "%MSG%"
if errorlevel 1 (
  echo 변경 사항이 없어 커밋할 것이 없어요.^^
)

echo [git push]
git push

echo.
echo 완료! 창을 닫아도 됩니다.
pause
