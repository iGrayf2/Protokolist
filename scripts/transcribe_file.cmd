@echo off
setlocal
cd /d "%~dp0\.."

if "%~1"=="" (
  echo Drag and drop an audio file onto this script.
  pause
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Run scripts\install_windows.cmd first.
  pause
  exit /b 1
)

set PYTHONPATH=%CD%\src
.venv\Scripts\python.exe -m protokolist.cli "%~1" --model small --language ru --output-dir output
pause
