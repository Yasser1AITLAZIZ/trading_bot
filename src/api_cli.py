#!/usr/bin/env python3
"""CLI for starting the API server."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from api.server import create_app
import uvicorn


def main():
    """Main entry point for API server."""
    app = create_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
