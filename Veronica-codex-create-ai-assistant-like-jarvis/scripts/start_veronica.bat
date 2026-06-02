@echo off
title Veronica — AI Assistant
setlocal EnableExtensions

call "C:\Users\admin\Downloads\Veronica-codex-create-ai-assistant-like-jarvis\.venv\Scripts\activate.bat"

pushd "C:\Users\admin\Downloads\Veronica-codex-create-ai-assistant-like-jarvis\Veronica-codex-create-ai-assistant-like-jarvis"

set "PYTHON_CMD=C:\Users\admin\Downloads\Veronica-codex-create-ai-assistant-like-jarvis\.venv\Scripts\python.exe"

echo.
echo  Starting Veronica AI Server...
echo.

REM Start Veronica in background (alag process)
start "Veronica Server" %PYTHON_CMD% -m veronica --speak --mobile

REM Server boot hone ka wait
echo  Waiting for server to start...
timeout /t 6 /nobreak >nul

REM Chrome mein Desktop UI open karo
echo  Opening Veronica Desktop UI...
start "" "C:\Users\admin\AppData\Local\Google\Chrome\Application\chrome.exe" --app="http://127.0.0.1:5000/desktop" --window-size=1400,900

echo  Veronica is ONLINE!
echo  Press any key to stop server...
pause >nul

REM Veronica band karo
taskkill /f /fi "WINDOWTITLE eq Veronica Server" >nul 2>&1
taskkill /f /im python.exe >nul 2>&1

popd
exit /b 0
