import os
import json
import re
import asyncio
from typing import Any, Dict, List

import ollama
from dotenv import load_dotenv

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession


load_dotenv()


def _extract_json_object(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from text and parse it.

    Ollama models can sometimes include prose; this tries to robustly
    find the first {...} object and json.loads it.
    """
    # Fast path: direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Heuristic: find first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in model output")

    return json.loads(match.group(0))


def _ollama_chat(model: str, system: str, user: str) -> str:
    """Call Ollama chat and return assistant content as a string."""
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options={
            # Slightly increase determinism for JSON selection
            "temperature": 0.2,
        },
    )
    return resp.get("message", {}).get("content", "")


async def invoke_tool_with_ollama(expression: str, model: str = "llama3.1:8b") -> None:
    """Ask Ollama to choose the tool and arguments, then call it via MCP."""
    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools_result = await session.list_tools()
            tools_json = [t.model_dump() for t in tools_result.tools]

            system = (
                "You are a strict JSON function-selector. Given tools and an input, "
                "you ONLY output a JSON object with keys 'name' and 'arguments'. No prose."
            )
            user = (
                "Available tools as JSON array:\n"
                + json.dumps(tools_json, indent=2)
                + "\n\nInput: "
                + expression
                + '\n\nRespond ONLY with JSON in the form: {"name": string, "arguments": object}.'
            )

            content = _ollama_chat(model=model, system=system, user=user)
            choice = _extract_json_object(content)

            if (
                not isinstance(choice, dict)
                or "name" not in choice
                or "arguments" not in choice
            ):
                raise ValueError(f"Invalid tool choice JSON: {choice}")

            result = await session.call_tool(
                name=choice["name"], arguments=choice["arguments"]
            )

            text_blocks = [
                b for b in result.content if getattr(b, "type", None) == "text"
            ]
            if text_blocks:
                print("[Tool Invocation]")
                print(f"Input: {expression}")
                print(f"Tool: {choice['name']}")
                print(f"Result: {text_blocks[0].text}")
            elif result.structuredContent is not None:
                print("[Tool Invocation]")
                print(f"Input: {expression}")
                print(f"Tool: {choice['name']}")
                print("Result (structured):")
                print(json.dumps(result.structuredContent, indent=2))
            else:
                print("[Tool Invocation]")
                print(f"Input: {expression}")
                print(f"Tool: {choice['name']}")
                print("Result (raw):")
                print(json.dumps(result.model_dump(), indent=2))


async def greet_with_prompt_ollama(
    name: str, style: str = "friendly", model: str = "llama3.1:8b"
) -> None:
    """Fetch the MCP prompt 'greet_user' and ask Ollama to produce the greeting."""
    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            prompt_result = await session.get_prompt(
                name="greet_user", arguments={"name": name, "style": style}
            )

            # get_prompt returns messages; each message has a list of content blocks
            parts: List[str] = []
            for msg in prompt_result.messages:
                for block in msg.content or []:
                    if getattr(block, "type", None) == "text":
                        parts.append(block.text)
            base_prompt = "\n".join(parts).strip()

            system = "You write short, natural greetings."
            user = base_prompt
            content = _ollama_chat(model=model, system=system, user=user)

            print("[Greeting Invocation]")
            print(f"Name: {name}  Style: {style}")
            print("Prompt from MCP:")
            print(base_prompt)
            print("\nOllama response:")
            print(content)


async def main():
    # Adjust model name to one you have pulled locally, e.g. 'llama3.1:8b', 'qwen2.5:7b', etc.
    model = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

    await invoke_tool_with_ollama("7 plus 5", model=model)
    await greet_with_prompt_ollama(name="Alex", style="friendly", model=model)


if __name__ == "__main__":
    asyncio.run(main())
