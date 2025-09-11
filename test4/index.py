"""
Minimal FastMCP server with math tools.

Usage with HTTP runner:
  uv run python test4/server_http.py
Then connect a client to http://127.0.0.1:8000/mcp
"""

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("DemoMath")


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Division by zero is not allowed")
    return a / b

