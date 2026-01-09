#!/bin/bash
#
# Setup script for daily cron job
#
# This script installs a cron job that runs the AI News Agent at 6:00 AM daily
#
# Usage:
#   bash scripts/setup_cron.sh

set -e  # Exit on error

# Get the absolute path to the project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "AI News Agent - Cron Setup"
echo "=========================================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Determine Python path (prefer python3)
if command -v python3 &> /dev/null; then
    PYTHON_CMD="$(which python3)"
else
    PYTHON_CMD="$(which python)"
fi

echo "Python executable: $PYTHON_CMD"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Create cron entry
# Format: minute hour day month weekday command
# 0 6 * * * = Every day at 6:00 AM
CRON_ENTRY="0 6 * * * cd $PROJECT_DIR && $PYTHON_CMD scripts/run_agent.py >> logs/cron.log 2>&1"

echo "Cron entry to be installed:"
echo "$CRON_ENTRY"
echo ""

# Check if entry already exists
if crontab -l 2>/dev/null | grep -q "ai_news_agent"; then
    echo "⚠️  Warning: An AI News Agent cron job already exists"
    echo "   Existing cron jobs:"
    crontab -l | grep "ai_news_agent"
    echo ""
    read -p "   Remove existing and install new? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled"
        exit 1
    fi
    # Remove existing entry
    (crontab -l | grep -v "ai_news_agent") | crontab -
fi

# Add new cron entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job installed successfully!"
echo ""
echo "Verification:"
echo "  Current crontab entries for ai_news_agent:"
crontab -l | grep "ai_news_agent"
echo ""
echo "Next execution:"
echo "  Daily at 6:00 AM"
echo ""
echo "Logs:"
echo "  Location: $PROJECT_DIR/logs/cron.log"
echo "  View: tail -f $PROJECT_DIR/logs/cron.log"
echo ""
echo "To remove the cron job:"
echo "  crontab -e  # Then delete the line containing 'ai_news_agent'"
echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
