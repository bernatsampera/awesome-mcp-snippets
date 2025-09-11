from mcp.server.fastmcp import FastMCP
import aiosqlite
import anyio

mcp = FastMCP("memory-crud")

DB_FILE = "db/memory.db"


async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL
            )
        """)
        await db.commit()


@mcp.tool()
async def create_memory(content: str) -> str:
    """Save a new memory entry.

    Args:
        content: Text to store in memory.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT INTO memory (content) VALUES (?)", (content,))
        await db.commit()
    return "Memory saved."


@mcp.tool()
async def list_memories() -> list[str]:
    """List all saved memories."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT id, content FROM memory")
        rows = await cursor.fetchall()
    return [f"{id}: {content}" for id, content in rows]


@mcp.tool()
async def update_memory(id: int, content: str) -> str:
    """Update a memory by ID.

    Args:
        id: ID of the memory to update
        content: New memory text
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE memory SET content = ? WHERE id = ?", (content, id))
        await db.commit()
    return f"Memory {id} updated."


@mcp.tool()
async def delete_memory(id: int) -> str:
    """Delete a memory by ID.

    Args:
        id: ID of the memory to delete
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM memory WHERE id = ?", (id,))
        await db.commit()
    return f"Memory {id} deleted."


async def run():
    await init_db()
    await mcp.run_stdio_async()


if __name__ == "__main__":
    anyio.run(run)
