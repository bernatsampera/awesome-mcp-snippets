"""
Minimal FastMCP server with math tools.

Usage with HTTP runner:
  uv run python test4/server_http.py
Then connect a client to http://127.0.0.1:8000/mcp
"""

from typing import Optional
import aiosqlite
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Samperalabs")

DB_FILE = "content.db"


async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)
        await db.commit()


@mcp.tool()
async def get_blog_posts(limit: Optional[int] = None) -> str:
    """Get blog posts with basic metadata.

    Args:
        limit: Optional max number of posts to return.
    """
    query = "SELECT id, title, content FROM posts "
    params: list = []
    if limit is not None and isinstance(limit, int) and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    print("rows", rows)
    list_of_rows = [_format_post_row(r) for r in rows]
    return "\n".join(list_of_rows)


@mcp.tool()
async def add_blog_post(title: str, content: str) -> str:
    """Add a blog post.

    Args:
        title: The title of the blog post.
        content: The content of the blog post.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT INTO posts (title, content) VALUES (?, ?)",
            (title, content),
        )
        await db.commit()
        return "Blog post added successfully"


@mcp.tool()
async def remove_blog_post(id: int) -> str:
    """Remove a blog post.

    Args:
        id: The id of the blog post to remove.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM posts WHERE id = ?", (id,))
        await db.commit()
        return "Blog post removed successfully"


def _format_post_row(row: tuple) -> str:
    id_, title, content = row
    return f"id: {id_} | title: {title} | content={content}"


# uv run test5/server_http.py
