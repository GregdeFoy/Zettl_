#!/usr/bin/env python3
"""
MCP Server Entry Point

Runs the Zettl MCP server with stdio transport.
This allows Claude (and the web app) to communicate with Zettl notes.
"""

import asyncio
import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from zettl.mcp.server import main

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    # Get JWT secret from environment
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        jwt_secret_file = os.getenv("JWT_SECRET_FILE")
        if jwt_secret_file and os.path.exists(jwt_secret_file):
            with open(jwt_secret_file, 'r') as f:
                jwt_secret = f.read().strip()

    if not jwt_secret:
        print("ERROR: JWT_SECRET or JWT_SECRET_FILE must be set", file=sys.stderr)
        sys.exit(1)

    # Run the server
    asyncio.run(main(jwt_secret))
