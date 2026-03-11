#!/bin/bash
# YouTube Intelligence & Automation OS — Setup Script

set -e

echo "🚀 YouTube Intelligence & Automation OS — Setup"
echo "================================================"

# Check dependencies
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required. Install: https://nodejs.org"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.12+ required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required"; exit 1; }

echo "✅ Dependencies check passed"

# Frontend setup
echo ""
echo "📦 Setting up Frontend (Next.js)..."
cd frontend
cp -n .env.example .env.local 2>/dev/null || true
npm install
echo "✅ Frontend dependencies installed"
cd ..

# Backend setup
echo ""
echo "🐍 Setting up Backend (FastAPI)..."
cd backend
cp -n .env.example .env 2>/dev/null || true
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "✅ Backend dependencies installed"
cd ..

# Docker infrastructure
echo ""
echo "🐳 Starting Docker services (PostgreSQL + Redis)..."
docker-compose up -d postgres redis
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Run migrations
echo ""
echo "🗄️ Running database migrations..."
cd backend
source venv/bin/activate
alembic upgrade head
echo "✅ Migrations complete"
cd ..

echo ""
echo "================================================"
echo "✅ Setup complete!"
echo ""
echo "Start development:"
echo "  Backend:  cd backend && uvicorn main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo "  Full stack: docker-compose up"
echo ""
echo "API Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
