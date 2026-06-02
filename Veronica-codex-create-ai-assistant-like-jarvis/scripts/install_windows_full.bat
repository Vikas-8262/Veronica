@echo off
title Veronica — Full Optional Installer
color 0A
setlocal EnableExtensions

echo.
echo  ╔═══════════════════════════════════════════╗
echo  ║       Veronica — Full Optional Installer  ║
echo  ╚═══════════════════════════════════════════╝
echo.

pushd "%~dp0\.."
set "PYTHON_CMD=py -3"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"

echo  [1/4] pip upgrade...
%PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 goto install_failed

echo  [2/4] Veronica optional Python packages...
%PYTHON_CMD% -m pip install -r requirements-all.txt
if errorlevel 1 goto install_failed

echo  [3/4] Verifying Veronica imports...
%PYTHON_CMD% -m py_compile veronica\__main__.py veronica\assistant.py
if errorlevel 1 goto install_failed

echo  [4/4] Done.
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  EXTRA SETUP (manual karna hoga):
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  1. OCR ke liye Tesseract install karo:
echo     https://github.com/UB-Mannheim/tesseract/wiki
echo     Optional: set TESSERACT_CMD to tesseract.exe path.
echo.
echo  2. News ke liye free API key lo:
echo     https://newsapi.org
echo     set NEWS_API_KEY=your-key
echo.
echo  3. Weather/WhatsApp optional config:
echo     set WEATHER_API_KEY=your-openweather-key
echo     set WHATSAPP_NUMBER=+910000000000
echo.
echo  4. Face recognition security:
echo     Agar face-recognition install fail ho, CMake + Visual Studio Build Tools install karo.
echo.
echo  5. Windows startup shortcut:
echo     scripts\add_to_startup.bat
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  ╔═══════════════════════════════════════════╗
echo  ║   Done! Ab README.md padho                ║
echo  ║   Phir: python -m veronica                ║
echo  ╚═══════════════════════════════════════════╝
echo.
popd
pause
exit /b 0

:install_failed
echo.
echo  Install mein problem aayi. Upar ka error check karo.
echo  Tip: CMake/Build Tools ke bina face-recognition fail ho sakta hai.
echo.
popd
pause
exit /b 1
