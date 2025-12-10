#!/usr/bin/env python3
"""
Start the FastAPI server for the scholarship chat agent system.

Usage:
    python run_server.py [--host HOST] [--port PORT] [--reload]
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start the scholarship chat agent server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         Scholarship Chat Agent Server                        ║
╚══════════════════════════════════════════════════════════════╝

Starting server...
  Host: {args.host}
  Port: {args.port}
  Reload: {args.reload}

Web Interface: http://localhost:{args.port}
API Docs: http://localhost:{args.port}/docs
Health Check: http://localhost:{args.port}/health

Press Ctrl+C to stop the server
""")
    
    uvicorn.run(
        "chat_agents.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()

# Made with Bob
