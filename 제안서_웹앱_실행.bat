@echo off
chcp 65001 >nul
title Dabeeo Super Intelligence

rem 이 .bat 가 있는 폴더(프로젝트 루트)로 이동 — 더블클릭해도 경로 맞음
cd /d "%~dp0"

rem 구독(claude CLI) 인증을 쓰도록 소진된 API 키 환경변수 제거
set "ANTHROPIC_API_KEY="

echo ============================================================
echo   Dabeeo Super Intelligence - 제안서 생성 웹앱
echo ============================================================
echo   브라우저가 자동으로 http://localhost:8501 을 엽니다.
echo   종료하려면 이 창에서 Ctrl+C 를 누르거나 창을 닫으세요.
echo ============================================================
echo.

python -m streamlit run webapp\app.py

echo.
echo [웹앱이 종료되었습니다. 창을 닫아도 됩니다.]
pause
