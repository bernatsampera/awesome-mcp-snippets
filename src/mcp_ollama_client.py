import os
import asyncio
from typing import Dict
import json
from langchain_ollama import ChatOllama
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession


llm = ChatOllama(model="llama3.1:latest", temperature=0, format="json")


def choose_with_langchain(expression: str) -> Dict:
    system = (
        "You are a tool selector. Return ONLY JSON with keys 'name' and 'arguments'. "
        "Allowed tools: "
        "1. 'get_blog_posts'. 'arguments' MUST be {\"limit\": number}. "
        "2. 'add_blog_post'. 'arguments' MUST be {'title': string, 'content': string}. "
        "3. 'remove_blog_post'. 'arguments' MUST be {'id': number}. "
        "Use numeric literals; do NOT return a JSON schema or descriptions."
    )
    print("expression", expression)
    prompt = system + "\n\nInput: " + expression

    return llm.invoke(prompt)


async def call_math_with_llm(expr: str, model_name: str) -> None:
    choice = json.loads(choose_with_langchain(expr).content)
    print("choice", choice)

    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                name=choice["name"], arguments=choice["arguments"]
            )
            text_blocks = [
                b for b in result.content if getattr(b, "type", None) == "text"
            ]
            print(f"Input: {expr}")
            print(f"Tool: {choice['name']}  Args: {choice['arguments']}")
            if text_blocks:
                print(f"Result: {text_blocks}")
            else:
                print(result.model_dump_json(indent=2))


async def main():
    model_name = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

    # await call_math_with_llm(
    #     "add a blog post about the ww2, the title is 'World War 2' and the content is 'World War 2 was a global conflict that lasted from 1939 to 1945'",
    #     model_name,
    # )
    # await call_math_with_llm("remove the blog post with id 1", model_name)
    await call_math_with_llm("list the blog posts", model_name)


if __name__ == "__main__":
    asyncio.run(main())
