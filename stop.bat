@echo off
title PyMVC Server Stopper
color 0C

echo ===================================================
echo   🛑 Stopping PyMVC Server on Port 8000
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
