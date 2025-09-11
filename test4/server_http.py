"""
Run the FastMCP server from index.py over Streamable HTTP on /mcp.

Usage:
  uv run python test4/server_http.py
Then connect a client to http://127.0.0.1:8000/mcp
"""

from uvicorn import run as uvicorn_run
import os
import sys

# Make sibling module importable when run as a script
sys.path.insert(0, os.path.dirname(__file__))

# Reuse the FastMCP instance defined in index.py
from index import mcp  # noqa: F401


def main() -> None:
    app = mcp.streamable_http_app()  # Starlette app with /mcp route
    uvicorn_run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
