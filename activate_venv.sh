#!/bin/bash
# Quick activation script for the Python 3.12 virtual environment

echo "Activating Python 3.12 virtual environment..."
source venv/bin/activate

echo ""
echo "✅ Virtual environment activated!"
echo ""
echo "Python version: $(python --version)"
echo ""
echo "Available commands:"
echo "  python chat_agents/run_server.py    - Start the web server"
echo "  python chat_agents/example_chat.py  - Run CLI chat interface"
echo "  deactivate                          - Exit virtual environment"
echo ""

# Made with Bob
