#!/bin/bash

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Starting OBDsidian..."

cd "$REPO_DIR/pidgeon"
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID)"

cd "$REPO_DIR/dashboard"
npm run dev &
FRONTEND_PID=$!
echo "Dashboard started (PID $FRONTEND_PID)"

echo ""
echo "OBDsidian running."
echo "  Dashboard: http://localhost:5173"
echo "  API:       http://localhost:8000"
echo "  Health:    http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'OBDsidian stopped.'" SIGINT SIGTERM
wait
