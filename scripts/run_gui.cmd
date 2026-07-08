@echo off
setlocal
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Run scripts\install_windows.cmd first.
  pause
  exit /b 1
)

set PYTHONPATH=%CD%\src
.venv\Scripts\python.exe run.py
if errorlevel 1 (
  echo.
  echo Application failed.
  pause
)
