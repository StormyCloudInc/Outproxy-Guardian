#!/bin/bash

# Feedback System Startup Script

echo "======================================"
echo "  Feedback & Voting System"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f backend/.env ]; then
    echo "⚠️  Configuration file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example backend/.env
    echo "✓ Created backend/.env"
    echo ""
    echo "⚠️  Please edit backend/.env with your configuration"
    echo "   Then run this script again."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "Creating virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
    echo "✓ Virtual environment created"
fi

# Activate virtual environment and install dependencies
echo "Installing/updating dependencies..."
cd backend
source venv/bin/activate

if [ ! -f "venv/installed" ]; then
    pip install -r requirements.txt
    touch venv/installed
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies already installed"
fi

echo ""
echo "======================================"
echo "  Starting Feedback System"
echo "======================================"
echo ""
echo "Admin Panel: http://localhost:5000/admin/index.html"
echo "API Server:  http://localhost:5000"
echo "Examples:    file://$(pwd)/../example.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python app.py
