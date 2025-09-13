import asyncio
from typing_extensions import Union
from langchain_ollama import ChatOllama
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from pydantic import BaseModel


# LLM Instance with json format because the MCP server returns json
llm = ChatOllama(model="llama3.1:latest", temperature=0, format="json")
mcp_server_url = "http://127.0.0.1:8000/mcp"


# Define the possible argument schemas
class GetBlogPostsArgs(BaseModel):
    limit: int


class AddBlogPostArgs(BaseModel):
    title: str
    content: str


class RemoveBlogPostArgs(BaseModel):
    id: int


# Main tool response schema
class ToolSelection(BaseModel):
    name: str
    arguments: Union[GetBlogPostsArgs, AddBlogPostArgs, RemoveBlogPostArgs]


# Create structured LLM to return a json of the class ToolSelection
structured_llm = llm.with_structured_output(ToolSelection)


tool_chooser_prompt = """
You are a tool selector. Choose the appropriate tool and provide the arguments.
Allowed tools: 
1. get_blog_posts
    Arguments: limit (number) - optional (10 if not provided)
2. add_blog_post
    Arguments: title (string) - required and content (string) - required
3. remove_blog_post
    Arguments: id (number) - required
"""


# Create structured LLM to return a json of the class ToolSelection
def tool_choser(expression: str) -> ToolSelection:
    """Choose tool and return structured response with guaranteed valid JSON."""
    return structured_llm.invoke(f"""
    {tool_chooser_prompt}

Input: {expression}""")


# Call the selected tool with its arguments
async def call_tool_with_llm(expr: str) -> None:
    # Why model_dump? Because the MCP server returns a json of the class ToolSelection
    tool = tool_choser(expr).model_dump()

    # Open HTTP connection to MCP server and create client session (nested context managers)
    async with (
        streamablehttp_client(mcp_server_url) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        # Initialize the MCP session
        await session.initialize()
        # Call the selected tool with its arguments
        result = await session.call_tool(tool["name"], tool["arguments"])

        # Filter result content to find text blocks only
        text_blocks = [b for b in result.content if getattr(b, "type", None) == "text"]

        # Print input expression and tool info on separate lines
        print(f"Input: {expr}\nTool: {tool['name']}  Args: {tool['arguments']}")
        # Print text blocks if found, otherwise print full JSON result
        print(
            f"Result: {text_blocks}"
            if text_blocks
            else result.model_dump_json(indent=2)
        )


async def main():
    # user_input = "add a blog post about the ww2, the title is 'World War 2' and the content is 'World War 2 was a global conflict that lasted from 1939 to 1945'"
    user_input = "list blog posts"
    # user_input = "remove the blog post with id 3"
    await call_tool_with_llm(user_input)


if __name__ == "__main__":
    asyncio.run(main())
