@echo off
cd /d %~dp0

rem 1. 간단하게 pyw 실행 (윈도우용 파이썬 런처 - 콘솔 없음)
start "" pyw -3 flow\flow_auto.py

rem 2. 만약 pyw가 없으면 그냥 pythonw로 실행 시도
if errorlevel 1 start "" pythonw flow\flow_auto.py

exit