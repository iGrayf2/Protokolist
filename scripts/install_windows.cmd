@echo off
setlocal
cd /d "%~dp0\.."

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or 3.12 and enable PATH.
  pause
  exit /b 1
)

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 goto error
)

echo Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto error

echo Installing dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Install complete.
pause
exit /b 0

:error
echo.
echo Install failed.
pause
exit /b 1
