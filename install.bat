@echo off
rem STALKER 2 AI Modding Toolkit: starts the interactive installer. It only copies skill folders.
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 install.py %*
  goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python install.py %*
  goto end
)
echo Python 3 was not found on this PC.
echo Install it from python.org (tick "Add python.exe to PATH"), then run install.bat again.
echo Or ask your AI agent to follow AGENTS.md in this folder, or copy folders from skills by hand (see START_HERE.md).
:end
echo.
pause
