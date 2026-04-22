@echo off
echo Starting ProposalAI...

:: ── Check .env exists ─────────────────────────────────────────────────────────
if not exist "%~dp0backend\.env" (
    echo ERROR: backend\.env file not found.
    echo Copy backend\.env and fill in your API keys before running.
    pause
    exit /b 1
)

:: ── Backend ──────────────────────────────────────────────────────────────────
echo [1/4] Setting up Python virtual environment...
cd "%~dp0backend"
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/4] Installing backend dependencies...
pip install -r requirements.txt --quiet

echo [3/4] Running migrations...
python manage.py migrate --run-syncdb

echo [4/4] Starting Django + Celery...
start "Django Server" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && python manage.py runserver"
start "Celery Worker" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && celery -A config worker --loglevel=info --pool=solo"

cd ..

:: ── Frontend ─────────────────────────────────────────────────────────────────
echo [5/5] Starting React frontend...
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    npm install
)
start "React Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

cd ..

echo.
echo ✓ All services started in separate windows.
echo.
echo   Frontend  →  http://localhost:5173
echo   Backend   →  http://localhost:8000/api/
echo   Admin     →  http://localhost:8000/admin/
echo.
pause
