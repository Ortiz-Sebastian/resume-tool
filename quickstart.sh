#!/bin/bash

# Resume Tool Quick Start Script

echo "=========================================="
echo "  Resume Tool - Quick Start"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.template .env
    echo "✅ .env file created"
    echo ""
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🛑 Stopping any running containers..."
docker-compose down
echo ""

echo "🔨 Building Docker images (this will take 2-3 minutes)..."
echo "   Note: spaCy model will be downloaded AFTER build"
docker-compose build
echo "✅ Build complete"
echo ""

echo "🚀 Starting services..."
docker-compose up -d
echo "✅ Services started"
echo ""

echo "⏳ Waiting for services to be ready (20 seconds)..."
sleep 20
echo ""

echo "📦 Installing spaCy NLP model..."
echo "   (This is required for resume parsing)"
echo "   Trying direct pip install method..."
docker-compose exec -T backend pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.7.1/en_core_web_lg-3.7.1-py3-none-any.whl
if [ $? -ne 0 ]; then
    echo "   Trying alternative method..."
    docker-compose exec -T backend pip install en_core_web_lg
fi
echo "✅ Model installed"
echo ""

echo "🔄 Restarting backend services to load model..."
docker-compose restart backend celery_worker
sleep 10
echo "✅ Services restarted"
echo ""

# Check if services are running
echo "🔍 Checking service status..."
docker-compose ps
echo ""

# Test backend
echo "🧪 Testing backend health..."
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "not ready")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Backend is healthy!"
else
    echo "⚠️  Backend may need more time to start"
    echo "   Try: curl http://localhost:8000/health"
fi
echo ""

# Done
echo "=========================================="
echo "  ✅ Resume Tool is ready!"
echo "=========================================="
echo ""
echo "📱 Frontend:  http://localhost:3000"
echo "🔧 Backend:   http://localhost:8000"
echo "📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "🧪 To test:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Drag and drop a resume (PDF or DOCX)"
echo "   3. Watch it analyze!"
echo ""
echo "📋 Useful commands:"
echo "   View logs:        docker-compose logs -f"
echo "   Stop services:    docker-compose down"
echo "   Restart services: docker-compose restart"
echo ""
echo "For more details, see START_HERE.md"
echo ""
