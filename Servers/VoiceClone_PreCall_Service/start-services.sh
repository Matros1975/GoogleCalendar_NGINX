#!/bin/bash
# Quick start script for Asterisk + VoiceClone service

set -e

cd "$(dirname "$0")"

echo "🚀 Starting Asterisk + VoiceClone Service"
echo "========================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "   Copy from .env.example and configure it first"
    exit 1
fi

# Build containers
echo ""
echo "📦 Building Docker containers..."
docker-compose build

# Start services
echo ""
echo "🎬 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check Asterisk
echo ""
echo "🔍 Checking Asterisk..."
if docker exec asterisk-voiceclone asterisk -rx "core show version" > /dev/null 2>&1; then
    echo "✅ Asterisk is running"
    docker exec asterisk-voiceclone asterisk -rx "core show version" | grep "Asterisk"
else
    echo "❌ Asterisk is not responding"
    docker-compose logs asterisk
    exit 1
fi

# Check ARI
echo ""
echo "🔍 Checking Asterisk ARI..."
if curl -s -f http://localhost:8088/ari/api-docs/resources.json \
    -u voiceclone:voiceclone_secret_2024 > /dev/null; then
    echo "✅ ARI is accessible"
else
    echo "❌ ARI is not accessible"
    exit 1
fi

# Check Python service
echo ""
echo "🔍 Checking Python service..."
sleep 3
if curl -s -f http://localhost:8000/health > /dev/null; then
    echo "✅ Python service is running"
else
    echo "⚠️  Python service not responding yet (may still be starting)"
fi

echo ""
echo "========================================"
echo "✅ Services started successfully!"
echo ""
echo "📞 Test with Linphone:"
echo "   SIP URI: sip:test@92.5.238.158:5060"
echo ""
echo "📊 Monitor logs:"
echo "   docker-compose logs -f asterisk"
echo "   docker-compose logs -f voiceclone-service"
echo ""
echo "🔧 Asterisk console:"
echo "   docker exec -it asterisk-voiceclone asterisk -rvvv"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo "========================================"
