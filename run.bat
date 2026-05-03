@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" goto :activate

echo Creating virtual environment...
py -3 -m venv .venv 2>nul
if exist ".venv\Scripts\activate.bat" goto :activate

python -m venv .venv 2>nul
if exist ".venv\Scripts\activate.bat" goto :activate

echo.
echo ERROR: Could not create a Python virtual environment.
echo Install Python 3.11 or newer from https://www.python.org/downloads/
echo and make sure "Add Python to PATH" is checked during install.
echo Then re-run run.bat.
echo.
exit /b 1

:activate
call ".venv\Scripts\activate.bat"

pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed.
    exit /b 1
)

python -m app.seed
if errorlevel 1 (
    echo ERROR: seed step failed.
    exit /b 1
)

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

endlocal
