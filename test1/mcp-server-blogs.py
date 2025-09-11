from mcp.server.fastmcp import FastMCP
import aiosqlite
import anyio
from typing import Optional, List


mcp = FastMCP("blog-posts")

DB_FILE = "db/content.db"


async def init_db():
    """Ensure the posts table exists (idempotent)."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                description TEXT,
                image_url TEXT,
                image_alt TEXT,
                pub_date TEXT NOT NULL,
                tags TEXT,
                content TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_posts_pub_date ON posts(pub_date)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug)"
        )
        await db.commit()


def _format_post_row(row: tuple) -> str:
    id_, title, author, pub_date, slug, tags = row
    tags_display = tags if tags is not None else ""
    return f"{id_} | {pub_date} | {title} by {author} | slug={slug} | tags={tags_display}"


@mcp.tool()
async def list_posts(limit: Optional[int] = None, order: str = "desc") -> List[str]:
    """List all blog posts with basic metadata.

    Args:
        limit: Optional max number of posts to return.
        order: Sort by pub_date; 'desc' (newest first) or 'asc'.
    """
    order = order.lower()
    if order not in {"asc", "desc"}:
        order = "desc"

    query = (
        "SELECT id, title, author, pub_date, slug, tags FROM posts "
        f"ORDER BY pub_date {order.upper()}"
    )
    params: list = []
    if limit is not None and isinstance(limit, int) and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
    return [_format_post_row(r) for r in rows]


@mcp.tool()
async def filter_posts(
    author: Optional[str] = None,
    tag: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    search: Optional[str] = None,
    order: str = "desc",
    limit: Optional[int] = None,
) -> List[str]:
    """List blog posts matching filters.

    Args:
        author: Exact author match (case-insensitive).
        tag: Tag contained in tags field (case-insensitive, substring match).
        since: Include posts with pub_date >= this ISO date/time string.
        until: Include posts with pub_date <= this ISO date/time string.
        search: Substring match in title, description, or content.
        order: Sort by pub_date; 'desc' (newest first) or 'asc'.
        limit: Optional max number of posts to return.
    """
    order = order.lower()
    if order not in {"asc", "desc"}:
        order = "desc"

    base = "SELECT id, title, author, pub_date, slug, tags FROM posts"
    where = []
    params: list = []

    if author:
        where.append("LOWER(author) = LOWER(?)")
        params.append(author)

    if tag:
        # Works for both comma-separated and JSON-ish tags via substring match
        where.append("LOWER(tags) LIKE '%' || LOWER(?) || '%'")
        params.append(tag)

    if since:
        where.append("pub_date >= ?")
        params.append(since)

    if until:
        where.append("pub_date <= ?")
        params.append(until)

    if search:
        where.append(
            "(title LIKE ? OR description LIKE ? OR content LIKE ?)"
        )
        like = f"%{search}%"
        params.extend([like, like, like])

    query = base
    if where:
        query += " WHERE " + " AND ".join(where)
    query += f" ORDER BY pub_date {order.upper()}"

    if limit is not None and isinstance(limit, int) and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    return [_format_post_row(r) for r in rows]


async def run():
    await init_db()
    await mcp.run_stdio_async()


if __name__ == "__main__":
    anyio.run(run)

