@echo off
title Veronica — Add to Startup
setlocal
pushd "%~dp0\.."
python -m veronica --add-startup --startup-name Veronica --startup-args --gui --reminders
set RESULT=%ERRORLEVEL%
popd
if %RESULT% EQU 0 (
    echo Veronica ab Windows startup mein add ho gaya!
    echo Har baar laptop on hone par automatically chalega.
) else (
    echo Startup shortcut banane mein problem aayi. Upar ka error check karo.
)
pause
exit /b %RESULT%
