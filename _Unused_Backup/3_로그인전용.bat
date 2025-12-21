@echo off
chcp 65001 >nul
cd /d %~dp0

echo [Flow Veo Auto] 로그인 전용 크롬을 실행합니다.
echo.
echo ========================================================
echo 1. 지금 뜨는 크롬 창에서 구글 로그인을 완료하세요.
echo    (이 창은 자동화 기능이 없어서 로그인이 잘 됩니다!)
echo.
echo 2. Flow 사이트에도 로그인이 되어 있는지 확인하세요.
echo.
echo 3. 확인 끝났으면 창을 닫아주세요. (X 버튼)
echo.
echo 4. 그 다음 'Flow_실행.bat'을 실행하면 됩니다.
echo ========================================================
echo.

set "PROFILE_DIR=flow\flow_human_profile"
if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

rem 크롬 찾기
set "CHROME_EXE="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if "%CHROME_EXE%"=="" (
  echo 크롬이 설치된 위치를 찾을 수 없습니다.
  pause
  exit /b
)

rem 순정 모드로 실행 (디버깅 포트 제거 -> 로그인 차단 우회)
"%CHROME_EXE%" --user-data-dir="%~dp0flow\flow_human_profile" --profile-directory="Default" --no-first-run --start-maximized "https://labs.google/fx/ko/tools/flow"

echo.
echo 크롬이 종료되었습니다. 이제 'Flow_실행.bat'을 실행하세요.
pause
