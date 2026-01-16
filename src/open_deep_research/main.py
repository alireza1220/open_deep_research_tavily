"""Main entry point for running the FastAPI server."""

import argparse
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import uvicorn

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print("\nShutting down server...")
    sys.exit(0)


def main():
    """Main entry point for the FastAPI server."""
    parser = argparse.ArgumentParser(
        description="Run the Open Deep Research FastAPI server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to run the server on (default: PORT env var or 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    
    args = parser.parse_args()
    
    # Determine port
    port = args.port or int(os.getenv("PORT", "8000"))
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the server
    uvicorn.run(
        "open_deep_research.api:app",
        host=args.host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

