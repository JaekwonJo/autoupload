@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================================
echo        ☁️ GitHub 자동 업로드 (Auto Push) ☁️
echo ========================================================
echo.

:: 1. 변경 사항 확인
echo [1/3] 변경된 파일을 찾고 있습니다...
git add .

:: 2. 커밋 (현재 시간으로 메시지 작성)
echo [2/3] 변경 사항을 포장(Commit) 중입니다...
set "TIMESTAMP=%DATE% %TIME%"
git commit -m "Auto Backup: %TIMESTAMP%"

:: 3. 푸시 (업로드)
echo [3/3] GitHub로 업로드(Push) 중입니다...
git push origin main

echo.
echo ========================================================
if %ERRORLEVEL% == 0 (
    echo    ✅ 업로드 성공! 마음 편히 쉬세요. 
) else (
    echo    ❌ 업로드 실패! 인터넷 연결을 확인해주세요.
)
echo ========================================================
echo.
pause