@echo off
setlocal
cd /d %~dp0

rem 1. Python 3 위치 찾기 (py 런처 사용)
for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%i"

rem 2. python.exe -> pythonw.exe 로 변경 (콘솔 없는 버전)
set "PYTHONW_EXE=%PYTHON_EXE:python.exe=pythonw.exe%"

rem 3. 프로그램 실행 (검은 화면 없이)
if exist "%PYTHONW_EXE%" (
    start "" "%PYTHONW_EXE%" flow\flow_auto.py
) else (
    rem pythonw가 없으면 그냥 python으로 실행 (혹시 모르니)
    start "" "%PYTHON_EXE%" flow\flow_auto.py
)

exit
