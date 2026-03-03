@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo [Autoupload] Installer Build - 2026-03-04 Ver.02
echo ========================================================
echo.

set "ISS=installer\FlowVeo_20260303_Ver01.iss"
set "ISCC="

where iscc >nul 2>&1
if %errorlevel% equ 0 (
    set "ISCC=iscc"
)

if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)

if not defined ISCC (
    echo [ERROR] Inno Setup 6(ISCC.exe)를 찾지 못했습니다.
    echo 아래 링크에서 설치 후 다시 실행하세요.
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

if not exist "%ISS%" (
    echo [ERROR] 스크립트 파일이 없습니다: %ISS%
    echo.
    pause
    exit /b 1
)

echo [INFO] ISCC 경로: %ISCC%
echo [INFO] 빌드 스크립트: %ISS%
echo.

"%ISCC%" "%ISS%"
if errorlevel 1 (
    echo.
    echo [ERROR] 설치파일 빌드 실패
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] 빌드 완료
echo 출력 폴더: ..\dist (Autoupload_20260304_Ver02_Setup.exe)
echo.
pause
exit /b 0
