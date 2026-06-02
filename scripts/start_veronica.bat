@echo off
title Veronica — Start Assistant
setlocal EnableExtensions
pushd "%~dp0\.."
set "PYTHON_CMD=py -3"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"
%PYTHON_CMD% -m veronica --gui --reminders --speak
set RESULT=%ERRORLEVEL%
popd
exit /b %RESULT%
