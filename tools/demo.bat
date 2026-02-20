@echo off
setlocal

set ROOT=artifacts\demo_latest
if not exist "%ROOT%" mkdir "%ROOT%"
set RUN=%ROOT%\run_%RANDOM%_%RANDOM%

python run_demo.py --demo-case ctf10 --max-attempts 2 --out "%RUN%" --fail-on-soft-fail
set RC=%ERRORLEVEL%

if not "%RC%"=="0" (
  echo [GenieGuard] Gate failed. Exit code=%RC%
  exit /b %RC%
)

echo %RUN% > "%ROOT%\LATEST_RUN.txt"
start "" "%RUN%\report.html" >nul 2>nul
echo [GenieGuard] Demo completed: %RUN%\report.html
endlocal
