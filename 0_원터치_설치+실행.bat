@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

title Flow Veo - 원터치 설치+실행

echo ========================================================
echo [Flow Veo] 원터치 설치+실행
echo ========================================================
echo.

set "ROOT=%cd%"
set "RUNTIME_DIR=%ROOT%\runtime"
set "PY_HOME=%RUNTIME_DIR%\python-embed"
set "PY_EXE=%PY_HOME%\python.exe"
set "PYW_EXE=%PY_HOME%\pythonw.exe"
set "PIP_EXE=%PY_HOME%\Scripts\pip.exe"
set "GETPIP=%RUNTIME_DIR%\get-pip.py"
set "PY_VER=3.11.9"
set "PY_ZIP=python-%PY_VER%-embed-amd64.zip"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/%PY_ZIP%"

if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"

if not exist "%PY_EXE%" (
    echo [1/6] 내장 Python 다운로드 중...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%RUNTIME_DIR%\%PY_ZIP%'"
    if errorlevel 1 goto :FAIL_DOWNLOAD_PY

    echo [2/6] 내장 Python 압축 해제 중...
    if exist "%PY_HOME%" rmdir /s /q "%PY_HOME%"
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "Expand-Archive -Path '%RUNTIME_DIR%\%PY_ZIP%' -DestinationPath '%PY_HOME%' -Force"
    if errorlevel 1 goto :FAIL_EXTRACT_PY

    del /q "%RUNTIME_DIR%\%PY_ZIP%" >nul 2>&1

    echo [3/6] 내장 Python site 설정 중...
    set "PTH_FILE="
    for %%f in ("%PY_HOME%\python*._pth") do (
        if not defined PTH_FILE set "PTH_FILE=%%~ff"
    )
    if defined PTH_FILE (
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
          "$p='%PTH_FILE%'; $lines=Get-Content $p; " ^
          "$hasSitePackages=($lines -match '^[ ]*Lib\\site-packages[ ]*$').Length -gt 0; " ^
          "if(-not $hasSitePackages){$lines += 'Lib\\site-packages'}; " ^
          "$lines=$lines | ForEach-Object { if($_ -match '^[ ]*#?[ ]*import site[ ]*$'){ 'import site' } else { $_ } }; " ^
          "Set-Content -Path $p -Value $lines -Encoding ASCII"
        if errorlevel 1 goto :FAIL_PTH
    )
)

echo [4/6] pip 준비 확인 중...
"%PY_EXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip 설치 중...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%'"
    if errorlevel 1 goto :FAIL_GETPIP
    "%PY_EXE%" "%GETPIP%" --no-warn-script-location
    if errorlevel 1 goto :FAIL_PIP_INSTALL
)

echo [5/6] 필수 라이브러리 설치/업데이트 중...
"%PY_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :FAIL_LIB
"%PY_EXE%" -m pip install -r requirements.txt
if errorlevel 1 goto :FAIL_LIB

echo [6/6] Playwright Chromium 설치 확인 중...
"%PY_EXE%" -m playwright install chromium
if errorlevel 1 goto :FAIL_BROWSER

echo.
echo [OK] 준비 완료. 프로그램을 실행합니다.
echo.

if exist "%PYW_EXE%" (
    start "" "%PYW_EXE%" -m flow.flow_auto_v2
) else (
    start "" "%PY_EXE%" -m flow.flow_auto_v2
)

echo [INFO] 실행 명령 전달 완료.
echo.
pause
exit /b 0

:FAIL_DOWNLOAD_PY
echo.
echo [ERROR] 내장 Python 다운로드 실패
echo 네트워크 연결 또는 보안 프로그램을 확인해주세요.
echo.
pause
exit /b 1

:FAIL_EXTRACT_PY
echo.
echo [ERROR] 내장 Python 압축 해제 실패
echo.
pause
exit /b 1

:FAIL_PTH
echo.
echo [ERROR] 내장 Python 설정(pth) 실패
echo.
pause
exit /b 1

:FAIL_GETPIP
echo.
echo [ERROR] get-pip.py 다운로드 실패
echo.
pause
exit /b 1

:FAIL_PIP_INSTALL
echo.
echo [ERROR] pip 설치 실패
echo.
pause
exit /b 1

:FAIL_LIB
echo.
echo [ERROR] 필수 라이브러리 설치 실패
echo requirements.txt 및 네트워크 상태를 확인해주세요.
echo.
pause
exit /b 1

:FAIL_BROWSER
echo.
echo [ERROR] Playwright Chromium 설치 실패
echo.
pause
exit /b 1
