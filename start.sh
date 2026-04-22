#!/bin/bash
set -e

echo "Starting ProposalAI..."

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Backend ───────────────────────────────────────────────────────────────────
cd "$ROOT_DIR/backend"

if [ ! -d ".venv" ]; then
    echo "[1/4] Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "[2/4] Installing backend dependencies..."
source .venv/bin/activate
pip install -r requirements.txt --quiet

echo "[3/4] Running migrations..."
python manage.py migrate --run-syncdb

echo "[4/4] Starting Django server..."
python manage.py runserver &
DJANGO_PID=$!

echo "Starting Celery worker..."
celery -A config worker --loglevel=info &
CELERY_PID=$!

# ── Frontend ──────────────────────────────────────────────────────────────────
cd "$ROOT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "[5/5] Installing frontend dependencies..."
    npm install
fi

echo "Starting React frontend..."
npm run dev &
FRONTEND_PID=$!

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "✓ All services running."
echo ""
echo "  Frontend  →  http://localhost:5173"
echo "  Backend   →  http://localhost:8000/api/"
echo "  Admin     →  http://localhost:8000/admin/"
echo ""
echo "Press Ctrl+C to stop all services."

# Stop all on Ctrl+C
trap "kill $DJANGO_PID $CELERY_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT
wait
