#!/bin/bash
# Agentic Local - Start Script with SearxNG

echo "🚀 Starting Agentic Local with SearxNG..."
echo ""

is_port_in_use() {
    lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

find_free_port() {
    local port="$1"
    while is_port_in_use "$port"; do
        port=$((port + 1))
    done
    echo "$port"
}

backend_healthy() {
    curl -fsS "http://localhost:$1/health" >/dev/null 2>&1
}

# Check if Docker is available and running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    echo "   You can download Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running. Please start Docker."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

echo "🐳 Starting SearxNG container..."
# Start SearxNG in detached mode
if command -v docker-compose &> /dev/null; then
    docker-compose up -d searxng
else
    docker compose up -d searxng
fi

# Wait for SearxNG to be ready
echo "⏳ Waiting for SearxNG to start..."
sleep 10

# Check if SearxNG is running
if docker ps | grep -q searxng; then
    echo "✅ SearxNG is running on http://localhost:8080"
else
    echo "❌ Failed to start SearxNG container"
    exit 1
fi

# Update environment variable to use local SearxNG
echo "🔧 Updating environment configuration..."
if [ -f ".env" ]; then
    # Backup original .env
    cp .env .env.backup
    # Update SEARXNG_BASE_URL to local instance
    sed -i.bak 's|SEARXNG_BASE_URL=.*|SEARXNG_BASE_URL=http://localhost:8080|' .env
    echo "✅ Updated SEARXNG_BASE_URL to use local instance"
else
    echo "⚠️  .env file not found, creating one with local SearxNG configuration"
    cat > .env << EOF
# Jarvis AI Configuration

# Work directory for code execution (required)
WORK_DIR=/tmp/jarvis_workspace

# SearxNG search engine URL (required for web search)
SEARXNG_BASE_URL=http://localhost:8080

# Optional: HuggingFace token for gated models
# HF_TOKEN=your_token_here

# Backend port (default: 7777)
BACKEND_PORT=7777

# Frontend backend URL
REACT_APP_BACKEND_URL=http://localhost:7777
EOF
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Create screenshots directory
mkdir -p .screenshots

# Start backend
backend_port_from_env_file=""
if [ -f ".env" ]; then
    backend_port_from_env_file=$(grep -E '^BACKEND_PORT=' .env | head -n 1 | cut -d= -f2)
fi
desired_backend_port="${BACKEND_PORT:-${backend_port_from_env_file:-7777}}"
backend_port="$desired_backend_port"
backend_already_running="false"

if is_port_in_use "$backend_port"; then
    if backend_healthy "$backend_port"; then
        backend_already_running="true"
    else
        backend_port="$(find_free_port "$backend_port")"
    fi
fi

export SEARXNG_BASE_URL="http://localhost:8080"
export BACKEND_PORT="$backend_port"

BACKEND_PID=""
if [ "$backend_already_running" = "true" ]; then
    echo "📡 Backend API già attivo su port $backend_port"
else
    echo "📡 Starting backend API on port $backend_port..."
    python3 api.py &
    BACKEND_PID=$!
fi

# Wait for backend to start
sleep 3

if [ -n "${BACKEND_PID:-}" ]; then
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "❌ Backend failed to start"
        if command -v docker-compose &> /dev/null; then
            docker-compose down
        else
            docker compose down
        fi
        exit 1
    fi
fi

if ! backend_healthy "$backend_port"; then
    echo "❌ Backend non risponde su http://localhost:$backend_port/health"
    # Stop SearxNG if backend fails
    if command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker compose down
    fi
    exit 1
fi

echo "✅ Backend running on http://localhost:$backend_port"

# Start frontend
echo "🎨 Starting frontend..."
cd frontend/jarvis-ui

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

frontend_port="${PORT:-3000}"
frontend_port="$(find_free_port "$frontend_port")"

export PORT="$frontend_port"
export REACT_APP_BACKEND_URL="http://localhost:$backend_port"

npm start &
FRONTEND_PID=$!

cd ../..

echo ""
echo "✅ Agentic Local is running with local SearxNG!"
echo "   - SearxNG:  http://localhost:8080"
echo "   - Backend:  http://localhost:$backend_port"
echo "   - Frontend: http://localhost:$frontend_port"
echo ""
echo "Press Ctrl+C to stop..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ -n "${BACKEND_PID:-}" ]; then
        kill "$BACKEND_PID" 2>/dev/null
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
        kill "$FRONTEND_PID" 2>/dev/null
    fi
    if command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker compose down
    fi
    echo "✅ All services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup INT TERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
