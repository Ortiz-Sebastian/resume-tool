#!/bin/bash

# Resume Tool - Automated Setup Script
# Run this to get everything working!

set -e  # Exit on error

echo "=========================================="
echo "  Resume Tool - Automated Setup"
echo "=========================================="
echo ""

# Navigate to project directory
cd "$(dirname "$0")"

# Step 1: Create .env file
echo "📝 Step 1: Creating .env file..."
if [ ! -f .env ]; then
    cp env.template .env
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi
echo ""

# Step 2: Stop any running containers
echo "🛑 Step 2: Stopping any running containers..."
docker-compose down
echo "✅ Stopped"
echo ""

# Step 3: Build images
echo "🔨 Step 3: Building Docker images..."
echo "   (This will take 2-3 minutes on first run)"
docker-compose build
echo "✅ Images built"
echo ""

# Step 4: Start services
echo "🚀 Step 4: Starting services..."
docker-compose up -d
echo "✅ Services started"
echo ""

# Step 5: Wait for services
echo "⏳ Step 5: Waiting for services to initialize..."
sleep 25
echo "✅ Services initialized"
echo ""

# Step 6: Check services
echo "🔍 Step 6: Checking service status..."
docker-compose ps
echo ""

# Step 7: Download spaCy model
echo "📦 Step 7: Downloading spaCy NLP model..."
echo "   (This is a one-time download, ~500MB)"
docker-compose exec -T backend python -m spacy download en_core_web_lg
echo "✅ Model downloaded"
echo ""

# Step 8: Restart to load model
echo "🔄 Step 8: Restarting backend services..."
docker-compose restart backend celery_worker
echo "✅ Services restarted"
sleep 10
echo ""

# Step 9: Test backend
echo "🧪 Step 9: Testing backend..."
HEALTH_CHECK=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend may not be ready yet"
    echo "   Response: $HEALTH_CHECK"
fi
echo ""

# Step 10: Check parser
echo "🔍 Step 10: Checking parser status..."
PARSER_INFO=$(curl -s http://localhost:8000/api/parser/info)
echo "$PARSER_INFO" | python3 -m json.tool 2>/dev/null || echo "$PARSER_INFO"
echo ""

# Done!
echo "=========================================="
echo "  ✅ Setup Complete!"
echo "=========================================="
echo ""
echo "🎉 Your Resume Tool is ready!"
echo ""
echo "📍 Access points:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "🧪 Quick test:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Drag and drop a resume (PDF or DOCX)"
echo "   3. Watch it parse and analyze!"
echo ""
echo "📋 Useful commands:"
echo "   View logs:      docker-compose logs -f"
echo "   Stop services:  docker-compose down"
echo "   Restart:        docker-compose restart"
echo ""
echo "📚 Documentation: See START_HERE.md for more details"
echo ""


