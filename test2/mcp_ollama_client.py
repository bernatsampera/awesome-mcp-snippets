import asyncio
from typing_extensions import Union, List, Dict, Any
from langchain_ollama import ChatOllama
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession, ListToolsResult
from pydantic import BaseModel


# LLM Instance with json format because the MCP server returns json
llm = ChatOllama(model="llama3.1:latest", temperature=0, format="json")
mcp_server_url = "http://127.0.0.1:8000/mcp"


# Define the possible argument schemas.
# NOTE: For a fully dynamic client, you might generate these Pydantic models
# on-the-fly from the server's JSON schema, but for this refactoring,
# we'll assume the client knows about these possible structures.
class GetBlogPostsArgs(BaseModel):
    limit: int


class AddBlogPostArgs(BaseModel):
    title: str
    content: str


class RemoveBlogPostArgs(BaseModel):
    id: int


# Main tool response schema that the LLM must adhere to.
class ToolSelection(BaseModel):
    name: str
    arguments: Union[GetBlogPostsArgs, AddBlogPostArgs, RemoveBlogPostArgs]


# Create a structured LLM that is guaranteed to return a JSON object
# matching the ToolSelection Pydantic model.
structured_llm = llm.with_structured_output(ToolSelection)


def create_tool_prompt(tool_list: ListToolsResult) -> str:
    """
    Dynamically generates a prompt for the LLM based on the list of tools
    received from the server.
    """
    prompt_lines = [
        "You are an expert tool selector. Based on the user's input, choose the single most appropriate tool and provide the necessary arguments.",
        "Here are the available tools:",
    ]

    for tool in tool_list.tools:
        prompt_lines.append(f"\n- Tool Name: `{tool.name}`")
        if tool.description:
            # Clean up the description for better LLM readability
            clean_description = " ".join(tool.description.strip().split())
            prompt_lines.append(f"  Description: {clean_description}")

        properties: Dict[str, Any] = tool.inputSchema.get("properties", {})
        required_args: List[str] = tool.inputSchema.get("required", [])

        if not properties:
            prompt_lines.append("  Arguments: None")
            continue

        prompt_lines.append("  Arguments:")
        for arg_name, arg_schema in properties.items():
            # Attempt to find the primary type, ignoring 'null' for simplicity
            arg_type = arg_schema.get("type", "any")
            if "anyOf" in arg_schema:
                types = [
                    t.get("type")
                    for t in arg_schema["anyOf"]
                    if t.get("type") != "null"
                ]
                if types:
                    arg_type = types[0]

            status = "required" if arg_name in required_args else "optional"
            prompt_lines.append(
                f"    - `{arg_name}` (type: {arg_type}, status: {status})"
            )

    return "\n".join(prompt_lines)


def choose_tool(expression: str, tool_prompt: str) -> ToolSelection:
    """
    Invokes the structured LLM with a dynamic prompt to choose a tool.

    Args:
        expression: The user's natural language input.
        tool_prompt: The dynamically generated prompt describing available tools.

    Returns:
        A ToolSelection object with the chosen tool and its arguments.
    """
    full_prompt = f'{tool_prompt}\n\n--- \nUser Input: "{expression}"'
    return structured_llm.invoke(full_prompt)


async def execute_tool_flow(
    session: ClientSession, expr: str, tool_prompt: str
) -> None:
    """
    Chooses a tool using the LLM and then executes it via the MCP session.

    Args:
        session: An active MCP ClientSession.
        expr: The user's natural language input.
        tool_prompt: The dynamically generated prompt for the LLM.
    """
    # 1. Let the LLM choose the tool based on the dynamic prompt
    tool_selection = choose_tool(expr, tool_prompt)
    # model_dump is used to convert the Pydantic object into a plain dictionary
    tool_call_data = tool_selection.model_dump()

    tool_name = tool_call_data["name"]
    tool_args = tool_call_data["arguments"]

    print(f"Input: {expr}")
    print(f"LLM Chose -> Tool: {tool_name}, Args: {tool_args}")

    # 2. Call the selected tool on the server
    result = await session.call_tool(tool_name, tool_args)

    # 3. Filter and print the result
    text_blocks = [b.text for b in result.content if getattr(b, "type", None) == "text"]

    print("Result from server:")
    if text_blocks:
        for block in text_blocks:
            print(f"- {block}")
    else:
        # Fallback to printing the full JSON if no text blocks are found
        print(result.model_dump_json(indent=2))


async def main():
    """
    Main entry point: connects to the server, gets tools, and runs the flow.
    """
    # Define a few example user inputs to test
    user_inputs = [
        "list the blog posts for me, just give me 5",
        # "add a blog post about the ww2, the title is 'World War 2' and the content is 'World War 2 was a global conflict that lasted from 1939 to 1945'",
        # "remove the blog post with id 3",
    ]

    # Open a single, persistent HTTP connection to the MCP server
    async with streamablehttp_client(mcp_server_url) as (read, write, _):
        # Create the client session using the connection
        async with ClientSession(read, write) as session:
            # Initialize the MCP session
            await session.initialize()

            # Fetch the list of available tools from the server
            print("Fetching tools from the server...")
            tool_list = await session.list_tools()

            # Generate the prompt for the LLM *once* based on the server's response
            dynamic_tool_prompt = create_tool_prompt(tool_list)

            print("\n--- Dynamically Generated Prompt for LLM ---")
            print(dynamic_tool_prompt)
            print("------------------------------------------\n")

            # Run the tool selection and execution flow for each user input
            for user_input in user_inputs:
                await execute_tool_flow(session, user_input, dynamic_tool_prompt)
                print("\n" + "=" * 40 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
