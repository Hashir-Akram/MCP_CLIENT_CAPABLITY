"""
04_roots_server_modern.py     (environment: requirements-modern.txt)
=====================================================================
Roots in the 2026-07-28 era. Two ways in ONE server:

  WAY A  find_files_via_roots   the (deprecated) roots idea, new delivery:
                                the tool RETURNS "I need the roots" and the
                                client answers, then the tool runs again.
                                This is called  MRTR  (multi round-trip request).

  WAY B  find_files_in          the REPLACEMENT the spec recommends:
                                the folder comes as a tool PARAMETER and the
                                server checks it against its OWN allow-list.

STATUS: Roots are DEPRECATED in spec 2026-07-28. They still work (earliest
removal: first spec revision on or after 2027-07-28) but new projects should
prefer WAY B.
"""

import warnings
from pathlib import Path

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp import types as t

warnings.simplefilter("ignore")        # demo only: hide deprecation warnings in the console

mcp = FastMCP("Workspace-Explorer-Modern")

WORKSPACE = (Path(__file__).parent / "workspace").resolve()

# WAY B uses SERVER-SIDE configuration instead of client roots
ALLOWED_DIRS = [WORKSPACE / "project-alpha", WORKSPACE / "project-beta"]


def _inside(target: Path, bases: list[Path]) -> bool:
    target = target.resolve()
    return any(target == b or b in target.parents for b in bases)


def _uri_to_path(uri) -> Path:
    from urllib.parse import urlparse
    from urllib.request import url2pathname
    return Path(url2pathname(urlparse(str(uri)).path)).resolve()


def _search(bases: list[Path], pattern: str) -> list[str]:
    out = []
    for base in bases:
        for p in sorted(base.rglob(pattern)):
            if p.is_file():
                out.append(f"{base.name}/{p.relative_to(base).as_posix()}")
    return out


# ---------------------------------------------------------------------------
# WAY A - roots through MRTR (the "guard pattern")
# ---------------------------------------------------------------------------
@mcp.tool
async def find_files_via_roots(pattern: str, ctx: Context):
    """Find files inside the client's roots (deprecated feature, new delivery)."""
    # ROUND 1: nothing answered yet -> ask the client for its roots
    if ctx.input_responses is None:
        return t.InputRequiredResult(
            input_requests={"my_roots": t.ListRootsRequest()}      # "please run roots/list"
        )
    # ROUND 2: the client answered and retried this same call
    answer = ctx.input_responses["my_roots"]                        # a ListRootsResult
    bases = [_uri_to_path(r.uri) for r in answer.roots]
    if not bases:
        raise ToolError("The client shared no roots.")
    return _search(bases, pattern)


# ---------------------------------------------------------------------------
# WAY B - the recommended replacement: parameter + server allow-list
# ---------------------------------------------------------------------------
@mcp.tool
async def find_files_in(base_dir: str, pattern: str) -> list[str]:
    """Find files inside ONE folder that the server itself allows."""
    target = Path(base_dir).resolve()
    if not _inside(target, ALLOWED_DIRS):
        raise ToolError("That folder is not on the server's allow-list.")
    return _search([target], pattern)


if __name__ == "__main__":
    mcp.run(show_banner=False)
