@echo off
setlocal enabledelayedexpansion

:: Change directory to the repository root
cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Locate Python executable (.venv or system)
if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

:: If command-line arguments are provided, pass them directly to Python
if not "%~1"=="" (
    "%PY_CMD%" scripts\add_button.py %*
    exit /b %ERRORLEVEL%
)

:: Interactive mode: Python prompts for label, role, emoji, style, and row
"%PY_CMD%" scripts\add_button.py --interactive

:END
echo.
pause
