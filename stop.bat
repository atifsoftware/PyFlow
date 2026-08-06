@echo off
chcp 65001 > nul
title PyFlow Server Stopper
color 0C
set PYTHONPATH=.
set PYTHONIOENCODING=utf-8

echo ===================================================
echo   🛑 Stopping PyFlow Server on Port 8000
echo ===================================================
echo.

:: ৮০০০ পোর্টে রানিং প্রসেস আইডি (PID) খুজে বের করে কিল করা
set found=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r /c:":8000 *LISTENING"') do (
    echo Process running on port 8000 found. PID: %%a
    taskkill /f /pid %%a
    set found=1
)

if %found%==1 (
    echo.
    echo ✅ Server stopped successfully!
) else (
    echo ⚠️  Port 8000-এ কোনো প্রসেস চলতে দেখা যায়নি।
)

echo.
pause
