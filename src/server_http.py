"""
Run the FastMCP server from index.py over Streamable HTTP on /mcp.

Usage:
  uv run python test5/server_http.py
Then connect a client to http://127.0.0.1:8000/mcp
"""

import asyncio
from uvicorn import run as uvicorn_run
from mcp_tools import mcp, init_db


def main() -> None:
    app = mcp.streamable_http_app()  # Starlette app with /mcp route
    uvicorn_run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    asyncio.run(init_db())
    main()
