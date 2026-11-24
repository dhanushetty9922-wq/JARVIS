"""JARVIS API Server Startup Script.

Runs the FastAPI backend that bridges the JARVIS Python core with the React frontend.
Usage:  python start_api.py [--port 8765] [--host 127.0.0.1]
"""

from __future__ import annotations

import argparse
import sys

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start JARVIS API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"\n[JARVIS API] Starting server on http://{args.host}:{args.port}")
    print("[JARVIS API] Press Ctrl+C to stop.\n")

    uvicorn.run(
        "api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
