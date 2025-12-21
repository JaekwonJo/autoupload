@echo off
rem 파이썬으로 아이콘 생성 스크립트 실행
set "PYCMD=python"
where py >nul 2>&1 && set "PYCMD=py -3"

%PYCMD% make_icon.py

if exist icon.ico (
    echo Icon created successfully!
    del make_icon.py
    del %0
) else (
    echo Failed to create icon.
    pause
)
