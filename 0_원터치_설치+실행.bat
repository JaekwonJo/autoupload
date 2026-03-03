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
for %%I in ("%LOCALAPPDATA%") do set "LOCALAPPDATA_NORM=%%~fI"
if not defined LOCALAPPDATA_NORM set "LOCALAPPDATA_NORM=%ROOT%"
set "RUNTIME_DIR=%LOCALAPPDATA_NORM%\Autoupload\runtime"
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

)

echo [3/6] 내장 Python site 설정 확인 중...
call :ENSURE_PTH
if errorlevel 1 goto :FAIL_PTH

echo [4/6] pip 준비 확인 중...
call :RUN_PIP --version >nul 2>&1
if errorlevel 1 (
    echo pip 설치 중...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%'"
    if errorlevel 1 goto :FAIL_GETPIP
    "%PY_EXE%" "%GETPIP%" --no-warn-script-location
    if errorlevel 1 goto :FAIL_PIP_INSTALL
    call :ENSURE_PTH
    if errorlevel 1 goto :FAIL_PTH
    call :RUN_PIP --version >nul 2>&1
    if errorlevel 1 goto :FAIL_PIP_INSTALL
)

echo [5/6] 필수 라이브러리 설치/업데이트 중...
call :RUN_PIP install --upgrade pip
if errorlevel 1 goto :FAIL_LIB
call :RUN_PIP install -r requirements.txt
if errorlevel 1 goto :FAIL_LIB

echo [6/6] Playwright Chromium 설치 확인 중...
"%PY_EXE%" -m playwright install chromium
if errorlevel 1 goto :FAIL_BROWSER

echo.
echo [OK] 준비 완료. 프로그램을 실행합니다.
echo.

python -c "import tkinter,playwright,pystray,PIL" >nul 2>&1
if not errorlevel 1 (
    start "" pythonw -m flow.flow_auto_v2
    goto :LAUNCH_OK
)

if exist "%PY_EXE%" (
    "%PY_EXE%" -c "import tkinter" >nul 2>&1
    if errorlevel 1 goto :FAIL_NO_TK
    if exist "%PYW_EXE%" (
        start "" "%PYW_EXE%" -m flow.flow_auto_v2
    ) else (
        start "" "%PY_EXE%" -m flow.flow_auto_v2
    )
    goto :LAUNCH_OK
)

goto :FAIL_LAUNCH

:LAUNCH_OK

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

:FAIL_PTH_MISSING
echo.
echo [ERROR] python*._pth 파일을 찾지 못했습니다.
echo 내장 Python 압축 해제 상태를 확인해주세요.
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

:FAIL_NO_TK
echo.
echo [ERROR] 내장 Python에 tkinter가 없어 GUI를 실행할 수 없습니다.
echo [INFO] 이 PC에서는 일반 Python(권장)으로 실행해주세요.
echo [INFO] 실행 파일: 2_오토_프로그램_실행.bat
echo.
pause
exit /b 1

:FAIL_LAUNCH
echo.
echo [ERROR] 실행 엔진을 찾지 못했습니다.
echo [INFO] 2_오토_프로그램_실행.bat 로 실행해보세요.
echo.
pause
exit /b 1

:ENSURE_PTH
set "PTH_FILE="
for /f "delims=" %%f in ('dir /b /a:-d "%PY_HOME%\python*._pth" 2^>nul') do (
    if not defined PTH_FILE set "PTH_FILE=%PY_HOME%\%%f"
)
if not defined PTH_FILE exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p='%PTH_FILE%'; $lines=Get-Content $p; " ^
  "$root='%ROOT%'; " ^
  "$hasSitePackages=($lines -match '^[ ]*Lib\\site-packages[ ]*$').Length -gt 0; " ^
  "if(-not $hasSitePackages){$lines += 'Lib\\site-packages'}; " ^
  "if(-not ($lines -contains $root)){$lines += $root}; " ^
  "$lines=$lines | ForEach-Object { if($_ -match '^[ ]*#?[ ]*import site[ ]*$'){ 'import site' } else { $_ } }; " ^
  "Set-Content -Path $p -Value $lines -Encoding ASCII"
if errorlevel 1 exit /b 1
exit /b 0

:RUN_PIP
"%PY_EXE%" -m pip %*
if not errorlevel 1 exit /b 0
if exist "%PIP_EXE%" (
    "%PIP_EXE%" %*
    exit /b %errorlevel%
)
exit /b 1
