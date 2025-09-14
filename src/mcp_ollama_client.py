"""
This script demonstrates an AI agent that can select and execute tools
from a remote server based on natural language user input.

It works as follows:
1. Connects to an MCP (Modular Capabilities Platform) server.
2. Fetches a list of available tools and their schemas.
3. Dynamically generates a detailed prompt for a large language model (LLM),
   describing the tools.
4. For each user input, it asks the LLM to choose the best tool and its arguments.
5. Executes the chosen tool on the MCP server and prints the result.
"""

import asyncio
from typing import List, Dict, Any, Union
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from mcp import ClientSession, ListToolsResult, Tool
from mcp.client.streamable_http import streamablehttp_client

# --- Configuration ---
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
LLM_MODEL = "llama3.1:latest"

# --- LLM and Pydantic Model Setup ---


# The data structure the LLM must return after choosing a tool.
class ToolSelection(BaseModel):
    name: str
    arguments: Dict[str, Any]


# Initialize the LLM, configured to always output valid JSON
# matching the ToolSelection schema.
llm = ChatOllama(model=LLM_MODEL, temperature=0, format="json")
structured_llm = llm.with_structured_output(ToolSelection)


# Returns a prompt with the name of tools and it's available arguments
def create_tool_prompt(tool_list: ListToolsResult) -> str:
    """Generates a system prompt for the LLM describing available tools."""
    prompt = (
        "You are an expert tool selector. Based on the user's input, "
        "choose the single most appropriate tool and provide the necessary arguments."
        "\n\nHere are the available tools:"
    )

    for tool in tool_list.tools:
        prompt += f"- {tool.name}: {tool.description}\n"

    return prompt


async def process_user_request(
    session: ClientSession, user_input: str, tool_prompt: str
) -> None:
    """
    Selects a tool using an LLM, executes it, and prints the result.

    Args:
        session: An active MCP ClientSession.
        user_input: The user's natural language input.
        tool_prompt: The pre-generated prompt describing available tools.
    """
    # 1. Ask the LLM to choose a tool
    full_prompt = f'{tool_prompt}\n\n---\nUser Input: "{user_input}"'
    tool_selection = structured_llm.invoke(full_prompt)

    print(f"LLM Chose -> Tool: {tool_selection.name}, Args: {tool_selection.arguments}")

    # 2. Execute the chosen tool on the server
    result = await session.call_tool(tool_selection.name, tool_selection.arguments)

    # 3. Print the result from the server
    text_blocks = [block.text for block in result.content if hasattr(block, "text")]
    print("Server Response:")
    for text in text_blocks:
        print(f"- {text}")


async def main():
    """Main entry point: connects, fetches tools, and processes user inputs."""
    user_inputs = [
        "list the blog posts for me, just give me 5",
        # "add a blog post about the ww2, the title is 'World War 2' and the content is 'World War 2 was a global conflict that lasted from 1939 to 1945'",
        # "remove the blog post with id 1",
    ]

    print(f"Connecting to MCP server at {MCP_SERVER_URL}...")
    try:
        async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tool_list = await session.list_tools()

                # Generate the master tool prompt once
                dynamic_tool_prompt = create_tool_prompt(tool_list)

                print("\n--- LLM Tool Prompt ---")
                print(dynamic_tool_prompt)
                print("-----------------------\n")

                # Process each user request
                for user_input in user_inputs:
                    await process_user_request(session, user_input, dynamic_tool_prompt)
                    print("-" * 50)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
