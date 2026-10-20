@echo off
chcp 65001 >nul
title TikTok Auto Commenter Bot
echo ========================================================
echo        Starting TikTok Auto Commenter Bot...
echo ========================================================
echo.

python -m pip install -r requirements.txt
echo.
python main.py
pause
