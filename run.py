#!/usr/bin/env python3
"""
Development runner script for the Incident Extractor API.

Usage:
    python run.py                    # Run with default settings
    python run.py --port 8080       # Run on custom port
    python run.py --reload          # Enable auto-reload
    python run.py --debug           # Enable debug mode
"""

import argparse
import sys
from pathlib import Path

import uvicorn
from config import settings

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Main entry point for development server."""
    parser = argparse.ArgumentParser(description="Run Incident Extractor API")
    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"Host to bind to (default: {settings.host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to bind to (default: {settings.port})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.is_development,
        help="Enable auto-reload for development",
    )
    parser.add_argument("--debug", action="store_true", default=settings.debug, help="Enable debug mode")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=settings.log_level,
        help=f"Set log level (default: {settings.log_level})",
    )

    args = parser.parse_args()

    # Print startup information
    print(f"🚀 Starting {settings.api_title} v{settings.api_version}")
    print(f"📡 Server: http://{args.host}:{args.port}")
    print(f"📚 Documentation: http://{args.host}:{args.port}/docs")
    print(f"🔍 Health Check: http://{args.host}:{args.port}/health")
    print(f"🤖 LLM Provider: {settings.llm_provider}")
    print(f"🎯 Model: {settings.model_name}")

    if args.reload:
        print("🔄 Auto-reload: Enabled")
    if args.debug:
        print("🐛 Debug mode: Enabled")

    print("\n" + "=" * 50 + "\n")

    # Run the server
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
