#!/usr/bin/env python3

import asyncio
from datetime import datetime
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Create a server instance
server = Server("simple-mcp-server")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="echo",
            description="Echo back the input text",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to echo back",
                    }
                },
                "required": ["text"],
            },
        ),
        types.Tool(
            name="current_time",
            description="Get the current date and time",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="add_numbers",
            description="Add two numbers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "First number",
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number",
                    },
                },
                "required": ["a", "b"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    """
    if name == "echo":
        text = arguments.get("text", "") if arguments else ""
        return [types.TextContent(type="text", text=f"Echo: {text}")]

    elif name == "current_time":
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [types.TextContent(type="text", text=f"Current time: {current_time}")]

    elif name == "add_numbers":
        if not arguments:
            raise ValueError("Arguments required for add_numbers")

        a = arguments.get("a")
        b = arguments.get("b")

        if a is None or b is None:
            raise ValueError("Both 'a' and 'b' parameters are required")

        result = a + b
        return [types.TextContent(type="text", text=f"Result: {a} + {b} = {result}")]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="simple-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
