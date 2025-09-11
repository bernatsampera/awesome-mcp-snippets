from fastapi import FastAPI
from mcp.server import Server
from typing import Any, Dict
from fastapi.responses import JSONResponse
import uvicorn

# Initialize FastAPI app
app = FastAPI()

# Initialize MCP server with HTTP transport
server = Server("math-tools-server")


# Define the multiply tool
@server.tool()
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b.
    """
    return a * b


# Define the divide tool
@server.tool()
def divide(a: float, b: float) -> float:
    """Divides two numbers.

    Args:
        a: Dividend
        b: Divisor (cannot be zero)

    Returns:
        The quotient of a divided by b.
    """
    if b == 0:
        raise ValueError("Division by zero is not allowed")
    return a / b


# FastAPI route for MCP JSON-RPC endpoint
@app.post("/mcp")
async def handle_mcp_request(request: Dict[str, Any]):
    """
    Handles MCP JSON-RPC requests (e.g., tools/list, tools/call).
    """
    try:
        # Process the JSON-RPC request using MCP server
        response = await server.handle_jsonrpc_request(request)
        return JSONResponse(content=response)
    except Exception as e:
        # Return JSON-RPC error
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request.get("id"),
            }
        )


# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
