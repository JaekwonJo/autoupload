@echo off
cd /d %~dp0

:: Set Python Path explicitly
set "REAL_PYTHON=C:\Users\jaekw\AppData\Local\Programs\Python\Python311\python.exe"

echo =================================================
echo      Flow Studio Setup Helper
echo      (Using: %REAL_PYTHON%)
echo =================================================
echo.

if not exist "%REAL_PYTHON%" (
    echo [ERROR] Python executable not found at:
    echo %REAL_PYTHON%
    pause
    exit /b
)

echo [1/2] Upgrading pip...
"%REAL_PYTHON%" -m pip install --upgrade pip

echo.
echo [2/2] Installing Selenium & WebDriver Manager...
"%REAL_PYTHON%" -m pip install selenium webdriver_manager

echo.
echo =================================================
echo      Setup Completed Successfully!
echo =================================================
echo.
echo You can close this window and run [Flow_Start.bat].
echo.
pause
