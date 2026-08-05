@echo off
title PyFlow Server Runner
color 0A
set PYTHONPATH=.
set PYTHONIOENCODING=utf-8

echo ===================================================
echo   🚀 PyFlow Server Start Up
echo   Running on: http://127.0.0.1:8000
echo ===================================================
echo.

python run.py

echo.
echo Server has stopped.
pause
