#!/bin/bash

# LLM Parliament - Start script

echo "🏛️  Starting LLM Parliament..."
echo ""

# Check for .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create one with OPENROUTER_API_KEY and BRAVE_API_KEY."
    exit 1
fi

# Start backend
echo "🐍 Starting Backend (Port 8001)..."
# We use 'uv' as it was in your original setup, but pip works too if you run 'python -m backend.main'
uv run python -m backend.main &
BACKEND_PID=$!

# Wait a bit for backend to initialize
sleep 2

# Start frontend
echo "⚛️  Starting Frontend (Port 5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ System is running!"
echo "   Backend API: http://localhost:8001"
echo "   Frontend UI: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers."

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
