#!/usr/bin/env bash
# Setup: bikin venv + install dependencies
set -e

echo "📦 Creating virtual environment..."
python3 -m venv venv

echo "📥 Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "✅ Selesai! Aktifkan dengan: source venv/bin/activate"
