@echo off
chcp 65001 >nul
cd /d %~dp0

echo ========================================================
echo [Flow Veo] Login Helper
echo ========================================================
echo.
echo 1. Close ALL Chrome windows first!
echo 2. Press any key to open 'Real Chrome'.
echo 3. Log in to Google/Flow in the new window.
echo 4. KEEP THE CHROME WINDOW OPEN!
echo 5. Run 'Flow_Start.bat' (or Flow_Run.bat).
echo.
echo ========================================================
pause

set "CHROME_EXE="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if "%CHROME_EXE%"=="" (
  echo Chrome not found! Please install Chrome.
  pause
  exit /b
)

rem Open Chrome in Debug Mode (Port 9555) with the Human Profile
start "" "%CHROME_EXE%" --remote-debugging-port=9555 --user-data-dir="%~dp0flow\flow_human_profile" "https://labs.google/fx/ko/tools/flow"

echo.
echo Chrome opened! Please login, then run the Auto program.
echo.
pause