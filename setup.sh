#!/bin/bash
"""
Setup Script for Mac Battery Cycle Tracker

This script sets up the virtual environment and installs dependencies.
"""

echo "🔋 Setting up Mac Battery Cycle Tracker..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3 and try again."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Test the battery tracker
echo "🧪 Testing battery tracker..."
python3 battery_tracker.py --status

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the web server:"
echo "  source venv/bin/activate"
echo "  python3 app.py"
echo ""
echo "Then open http://localhost:5000 in your browser"
echo ""
echo "To set up automatic data collection, run:"
echo "  crontab -e"
echo "And add this line to record every 6 hours:"
echo "  0 */6 * * * /path-to/folder/mac-battery-cycle/cron_battery_check.sh"