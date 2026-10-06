"""
01_roots_server_classic.py     (environment: requirements-classic.txt)
=====================================================================
"Workspace Explorer" - an MCP server that works ONLY inside the folders
(ROOTS) that the CLIENT tells it about.

BIG IDEA (simple words):
    The CLIENT says:  "These are the folders I am working in."   <- roots
    The SERVER asks:  "Which folders?"  (roots/list)             <- ctx.list_roots()
    The SERVER then focuses its work on those folders.

IMPORTANT TRUTH ABOUT ROOTS:
    Roots are GUIDANCE, not a lock. A client cannot force a server to behave,
    and a server must never trust a path just because it "looks" fine.
    That is why this server CHECKS every path itself (see inside_roots()).

Run through:  python 02_roots_client_classic.py   (starts this server for you)
"""

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("Workspace-Explorer")


# ---------------------------------------------------------------------------
# HELPER 1 - turn a root URI (file:///home/me/project) into a real Path
# ---------------------------------------------------------------------------
def uri_to_path(uri) -> Path:
    parsed = urlparse(str(uri))
    if parsed.scheme != "file":                       # roots are file:// URIs
        raise ToolError(f"Only file:// roots are supported, got: {uri}")
    return Path(url2pathname(parsed.path)).resolve()  # resolve() removes ".." and symlinks


# ---------------------------------------------------------------------------
# HELPER 2 - ask the client for its roots (the heart of this lesson)
# ---------------------------------------------------------------------------
async def get_roots(ctx: Context) -> list[tuple[str, Path]]:
    """Returns [(display_name, absolute_path), ...]. Asks the client EVERY time,
    so we always see the latest roots (the user may change them any moment)."""
    try:
        roots = await ctx.list_roots()                # -> sends  roots/list  to the client
    except Exception as exc:                          # client has no roots support
        raise ToolError("This client does not support roots (it never declared the capability).") from exc
    result = []
    for r in roots:
        path = uri_to_path(r.uri)
        result.append((r.name or path.name, path))
    return result


# ---------------------------------------------------------------------------
# HELPER 3 - the SAFETY CHECK. Never skip this.
# ---------------------------------------------------------------------------
def inside_roots(target: Path, roots: list[tuple[str, Path]]) -> bool:
    target = target.resolve()
    return any(target == base or base in target.parents for _, base in roots)


# ---------------------------------------------------------------------------
# TOOL 1 - show what the client told us
# ---------------------------------------------------------------------------
@mcp.tool
async def list_my_roots(ctx: Context) -> list[dict]:
    """Show the roots (folders) shared by the client."""
    roots = await get_roots(ctx)
    return [{"name": n, "path": str(p), "exists": p.exists()} for n, p in roots]


# ---------------------------------------------------------------------------
# TOOL 2 - search ONLY inside the roots
# ---------------------------------------------------------------------------
@mcp.tool
async def find_files(pattern: str, ctx: Context) -> list[str]:
    """Find files by pattern (example: *.py) inside the shared roots only."""
    roots = await get_roots(ctx)
    if not roots:
        raise ToolError("The client shared no roots. Ask the user to open a folder first.")
    found = []
    for name, base in roots:
        for p in sorted(base.rglob(pattern)):
            if p.is_file():
                found.append(f"{name}/{p.relative_to(base).as_posix()}")
    return found


# ---------------------------------------------------------------------------
# TOOL 3 - read a file, but ONLY if it is inside a root
# ---------------------------------------------------------------------------
@mcp.tool
async def read_file(path: str, ctx: Context) -> str:
    """Read a text file. Allowed only inside the shared roots."""
    roots = await get_roots(ctx)
    target = Path(path).resolve()                     # collapse ../ tricks first
    if not inside_roots(target, roots):
        raise ToolError("Access denied: that path is outside the shared roots.")
    if not target.is_file():
        raise ToolError("File not found.")
    return target.read_text(encoding="utf-8")[:2000]  # cap the size


# ---------------------------------------------------------------------------
# TOOL 4 - a quick summary per root
# ---------------------------------------------------------------------------
@mcp.tool
async def workspace_summary(ctx: Context) -> dict:
    """Count files per root."""
    roots = await get_roots(ctx)
    return {name: sum(1 for p in base.rglob("*") if p.is_file()) for name, base in roots}


if __name__ == "__main__":
    mcp.run(show_banner=False)
