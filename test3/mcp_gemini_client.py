import os
import json
import asyncio
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel as LangChainBaseModel, Field

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession


load_dotenv()


# --- Structured schema for tool selection ---
class ToolCall(LangChainBaseModel):
    name: str = Field(description="Name of the tool to call, e.g. 'add'")
    arguments: dict = Field(description="Dict of arguments for the tool call")


def make_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    )


async def invoke_tool_with_gemini(expression: str) -> None:
    """Ask Gemini to choose the tool and arguments, then call it via MCP."""
    llm = make_llm()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You have access to these MCP tools:
{tools}

From the user input, choose the best tool and arguments.
Return a JSON object with:
- name: the tool name (e.g. 'add')
- arguments: a dict of args (e.g. {{"a": int, "b": int}})

Do not call the tool yourself; only return the JSON.""",
            ),
            ("human", "Input: {expression}"),
        ]
    )

    chain = prompt | llm.with_structured_output(ToolCall)

    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools and feed into Gemini
            tools_result = await session.list_tools()
            tools_json = [t.model_dump() for t in tools_result.tools]

            llm_choice = chain.invoke(
                {"expression": expression, "tools": json.dumps(tools_json, indent=2)}
            )

            # Call the chosen tool via MCP
            result = await session.call_tool(name=llm_choice.name, arguments=llm_choice.arguments)

            # Prefer text content if present; else print structured/raw
            text_blocks = [b for b in result.content if getattr(b, "type", None) == "text"]
            if text_blocks:
                print("[Tool Invocation]")
                print(f"Input: {expression}")
                print(f"Tool: {llm_choice.name}")
                print(f"Result: {text_blocks[0].text}")
            elif result.structuredContent is not None:
                print("[Tool Invocation]")
                print(f"Input: {expression}")
                print(f"Tool: {llm_choice.name}")
                print("Result (structured):")
                print(json.dumps(result.structuredContent, indent=2))
            else:
                print("[Tool Invocation]")
                print(f"Input: {expression}")
                print(f"Tool: {llm_choice.name}")
                print("Result (raw):")
                print(json.dumps(result.model_dump(), indent=2))


async def greet_with_prompt(name: str, style: str = "friendly") -> None:
    """Fetch the MCP prompt 'greet_user' and have Gemini generate the greeting."""
    llm = make_llm()

    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Ask MCP for the prompt messages
            prompt_result = await session.get_prompt(
                name="greet_user", arguments={"name": name, "style": style}
            )

            # Extract the text parts from all messages
            parts = []
            for msg in prompt_result.messages:
                for block in (msg.content or []):
                    if getattr(block, "type", None) == "text":
                        parts.append(block.text)
            base_prompt = "\n".join(parts).strip()

            # Ask Gemini to fulfill the prompt
            greeting = llm.invoke(base_prompt)
            text = getattr(greeting, "content", None) or getattr(greeting, "text", None)

            print("[Greeting Invocation]")
            print(f"Name: {name}  Style: {style}")
            print("Prompt from MCP:")
            print(base_prompt)
            print("\nGemini response:")
            print(text if isinstance(text, str) else str(greeting))


async def main():
    # 1) Tool invocation via Gemini tool selection
    await invoke_tool_with_gemini("7 plus 5")

    # 2) Greeting via MCP prompt + Gemini completion
    await greet_with_prompt(name="Alex", style="friendly")


if __name__ == "__main__":
    asyncio.run(main())
