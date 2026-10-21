@echo off
chcp 65001 >nul
title TikTok Auto Commenter Bot

python -m pip install -r requirements.txt
echo.
python main.py
pause
