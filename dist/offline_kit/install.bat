@echo off
chcp 65001 > nul
echo ============================================
echo  AI 관광 추천 서비스 - 오프라인 설치
echo ============================================
echo.
python -m pip install --no-index --find-links=wheels flask
if errorlevel 1 goto fail
echo.
echo 설치가 끝났습니다.
echo 이제 프로젝트 폴더에서 아래 두 줄을 실행하세요.
echo.
echo   python scripts/init_db.py
echo   python app.py
echo.
pause
exit /b 0

:fail
echo.
echo 설치에 실패했습니다. 선생님께 알려 주세요.
pause
exit /b 1
