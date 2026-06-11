@echo off
title Dabeeo Super Intelligence

rem Move to this script's folder (project root) so paths work on double-click.
cd /d "%~dp0"

rem Use Claude Code CLI (Max subscription) auth -- clear any stale API key.
set "ANTHROPIC_API_KEY="

echo ============================================================
echo   Dabeeo Super Intelligence - Proposal Generator
echo ============================================================
echo   Browser will open http://localhost:8501 shortly.
echo   To stop: press Ctrl+C in this window or close it.
echo ============================================================
echo.

python -m streamlit run webapp\app.py

echo.
echo [Web app stopped. You can close this window.]
pause
