@echo off
setlocal

set TAG=%1
if "%TAG%"=="" set TAG=v0.2.0

python tools/build_release_bundle.py
if not "%ERRORLEVEL%"=="0" exit /b %ERRORLEVEL%

git tag %TAG%
if not "%ERRORLEVEL%"=="0" exit /b %ERRORLEVEL%

git push origin %TAG%
if not "%ERRORLEVEL%"=="0" exit /b %ERRORLEVEL%

gh release create %TAG% dist/demo_case_ctf10.zip dist/report.sample.html dist/evidence.sample.zip dist/release_manifest.json ^
  --title "GenieGuard %TAG%" ^
  --notes "GenieGuard release bundle (v0.2 contract): fixed demo case + sample report + evidence + manifest."

if not "%ERRORLEVEL%"=="0" exit /b %ERRORLEVEL%

echo [GenieGuard] Release created: %TAG%
endlocal
