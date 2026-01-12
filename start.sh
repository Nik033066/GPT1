#!/bin/bash
# Agentic Local - Start Script

echo "🚀 Starting Agentic Local..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Create screenshots directory
mkdir -p .screenshots

# Start backend
echo "📡 Starting backend API on port 7777..."
python3 api.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start"
    exit 1
fi

echo "✅ Backend running on http://localhost:7777"

# Start frontend
echo "🎨 Starting frontend..."
cd frontend/jarvis-ui

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

npm start &
FRONTEND_PID=$!

cd ../..

echo ""
echo "✅ Agentic Local is running!"
echo "   - Backend:  http://localhost:7777"
echo "   - Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop..."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
