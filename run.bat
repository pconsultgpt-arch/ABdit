@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    py -3 -m venv .venv
    if errorlevel 1 (
        python -m venv .venv
    )
)

call .venv\Scripts\activate.bat

pip install -q -r requirements.txt

python -m app.seed
if errorlevel 1 goto :end

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

:end
endlocal
