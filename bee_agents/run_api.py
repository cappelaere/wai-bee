#!/usr/bin/env python3
"""Startup script for the Scholarship Analysis API.

This script initializes and runs the FastAPI server for a specific scholarship.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT

Example:
    Run for Delaney Wings scholarship::
    
        python bee_agents/run_api.py
    
    Or specify different scholarship::
    
        python bee_agents/run_api.py --scholarship Evans_Wings
"""

import argparse
import uvicorn
from .api import initialize_services, app


def main():
    """Main entry point for running the API server."""
    parser = argparse.ArgumentParser(
        description="Scholarship Analysis API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run for Delaney Wings scholarship on default port 8000
  python bee_agents/run_api.py --scholarship Delaney_Wings
  
  # Run for Evans Wings scholarship on port 8001
  python bee_agents/run_api.py --scholarship Evans_Wings --port 8001
  
  # Run with custom output directory
  python bee_agents/run_api.py --scholarship Delaney_Wings --output-dir /path/to/outputs
        """
    )
    
    parser.add_argument(
        "--scholarship",
        type=str,
        default="Delaney_Wings",
        help="Scholarship name (default: Delaney_Wings)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Base output directory (default: outputs)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    args = parser.parse_args()
    
    print(f"Initializing API for scholarship: {args.scholarship}")
    print(f"Output directory: {args.output_dir}")
    print(f"Server will run on: http://{args.host}:{args.port}")
    print(f"API documentation: http://{args.host}:{args.port}/docs")
    print()
    
    # Initialize the data services
    try:
        initialize_services(args.output_dir)
        print(f"✓ Data services initialized successfully")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize data services: {e}")
        return 1
    
    # Run the server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )
    
    return 0


if __name__ == "__main__":
    exit(main())

# Made with Bob
