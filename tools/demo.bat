@echo off
setlocal

set OUT=artifacts\demo_latest
if exist "%OUT%" rd /s /q "%OUT%"

python run_demo.py --seed-count 50 --max-attempts 2 --out "%OUT%" --open --fail-on-soft-fail
set RC=%ERRORLEVEL%

if not "%RC%"=="0" (
  echo [GenieGuard] Gate failed. Exit code=%RC%
  exit /b %RC%
)

echo [GenieGuard] Demo completed: %OUT%\report.html
endlocal
