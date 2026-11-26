@echo off
cd /d "%~dp0"
echo Opening CS-IRCFS Management in your browser...
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000/'"
if exist "%~dp0backend\.local-ai\manifest.json" (
    PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-local.ps1" -Demo -LocalAI
) else (
    PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-local.ps1" -Demo
)
pause
