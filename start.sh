#!/bin/bash

echo "Starting OBDsidian..."

cd ~/Projects/OBDsidian/pidgeon
source venv/bin/activate
uvicorn app.main:app --reload &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID)"

cd ~/Projects/OBDsidian/pidgeon/dashboard
npm run dev &
FRONTEND_PID=$!
echo "Dashboard started (PID $FRONTEND_PID)"

echo ""
echo "OBDsidian running."
echo "Dashboard: http://localhost:5173"
echo "API: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID; echo 'OBDsidian stopped.'" SIGINT
wait
