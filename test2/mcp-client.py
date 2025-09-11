import os
import json
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel as LangChainBaseModel, Field
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from dotenv import load_dotenv

load_dotenv()


# Define the tool call schema for Gemini
class ToolCall(LangChainBaseModel):
    name: str = Field(
        description="Name of the function to call: 'multiply' or 'divide'"
    )
    arguments: dict = Field(
        description="Dictionary of arguments, e.g., {'a': float, 'b': float}"
    )


# Initialize Google Gemini with LangChain
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    google_api_key=os.getenv("GOOGLE_API_KEY", ""),
)

# Define the prompt for Gemini to choose the tool
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You have access to these tools:
{tools}

Given an expression, return a JSON object with:
- 'name': The tool name ('multiply' or 'divide')
- 'arguments': A dictionary with 'a' and 'b' (float values)

Example:
Input: "6 times 4" → {"name": "multiply", "arguments": {"a": 6, "b": 4}}
Input: "8 divided by 2" → {"name": "divide", "arguments": {"a": 8, "b": 2}}

If the expression is unclear or invalid, throw an error.""",
        ),
        ("human", "Expression: {expression}"),
    ]
)

# Create LangChain chain with structured output
chain = prompt | llm.with_structured_output(ToolCall)


async def run_mcp_client(expression: str):
    """
    Simulates an LLM host: connects via Streamable HTTP, lists tools,
    uses Gemini to choose a tool, and calls it.
    """
    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            # Initialize session (negotiates protocol etc.)
            await session.initialize()

            # Step 1: List available tools
            tools_result = await session.list_tools()
            tools_json = [t.model_dump() for t in tools_result.tools]

            # Step 2: Use Gemini to choose the tool
            try:
                llm_response = chain.invoke(
                    {"expression": expression, "tools": json.dumps(tools_json, indent=2)}
                )
            except Exception as e:
                print(f"LLM error: {str(e)}")
                return

            # Step 3: Call the tool
            try:
                result = await session.call_tool(
                    name=llm_response.name, arguments=llm_response.arguments
                )

                # Prefer text content if present; otherwise show structured content or raw dump
                text_blocks = [b for b in result.content if getattr(b, "type", None) == "text"]
                if text_blocks:
                    print(f"Expression: {expression}")
                    print(f"Result: {text_blocks[0].text}")
                elif result.structuredContent is not None:
                    print(f"Expression: {expression}")
                    print("Result (structured):")
                    print(json.dumps(result.structuredContent, indent=2))
                else:
                    print(f"Expression: {expression}")
                    print("Result (raw):")
                    # Pydantic v2 models expose model_dump(); result is a BaseModel
                    print(json.dumps(result.model_dump(), indent=2))
            except Exception as e:
                print(f"Tool call error: {str(e)}")


# Run the client with an example expression
if __name__ == "__main__":
    expression = "6 times 4"  # Change this to test different inputs
    asyncio.run(run_mcp_client(expression))
