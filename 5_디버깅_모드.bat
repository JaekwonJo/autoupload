@echo off
echo ========================================================
echo [GEMINI] EMERGENCY DEBUG MODE (ASCII ONLY)
echo ========================================================
echo.
echo 1. Checking Python Version...
python --version
echo.
echo 2. Starting Flow Vision Bot...
echo (If the window closes, read the ERROR message below!)
echo --------------------------------------------------------
echo.

python flow/flow_auto_v2.py

echo.
echo --------------------------------------------------------
echo [STOP] Program finished.
echo If you see an error message above (Traceback...), please copy it.
echo ========================================================
pause