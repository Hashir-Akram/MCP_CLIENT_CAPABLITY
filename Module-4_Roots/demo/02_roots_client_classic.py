"""
02_roots_client_classic.py     (environment: requirements-classic.txt)
=====================================================================
The CLIENT side of roots, using the FastMCP client.

  PART 1  Static roots        Client(..., roots=[...])
  PART 2  Dynamic roots       roots=<function>  +  send_roots_list_changed()
  PART 3  Boundary tests      the server must refuse paths outside the roots
  PART 4  No roots at all     what the server sees if the client shares nothing

Run:  python 02_roots_client_classic.py
"""

import asyncio
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from mcp.types import Root

HERE = Path(__file__).parent.resolve()
WORKSPACE = HERE / "workspace"
SERVER = HERE / "01_roots_server_classic.py"

ALPHA = Root(uri=(WORKSPACE / "project-alpha").as_uri(), name="Alpha")
BETA = Root(uri=(WORKSPACE / "project-beta").as_uri(), name="Beta")


def banner(t: str) -> None:
    print(f"\n{'=' * 8} {t} {'=' * 8}")


def transport() -> StdioTransport:
    return StdioTransport(command=sys.executable, args=[str(SERVER)])


async def call(client: Client, tool: str, args: dict | None = None):
    """Call a tool and return text, or the error message."""
    try:
        res = await client.call_tool(tool, args or {})
        return res.data if res.data is not None else res.content[0].text
    except Exception as exc:                                      # noqa: BLE001
        return f"ERROR: {str(exc)[:90]}"


async def main() -> None:
    # ---------------------------------------------------------------- PART 1
    banner("PART 1: static roots (Alpha + Beta)")
    # The client DECLARES roots when it connects. Behind the scenes this
    # switches on the 'roots' capability during the handshake.
    async with Client(transport(), roots=[ALPHA, BETA]) as client:
        print("list_my_roots     ->", await call(client, "list_my_roots"))
        print("find_files *.py   ->", await call(client, "find_files", {"pattern": "*.py"}))
        print("find_files *.md   ->", await call(client, "find_files", {"pattern": "*.md"}))
        print("workspace_summary ->", await call(client, "workspace_summary"))

    # ---------------------------------------------------------------- PART 2
    banner("PART 2: dynamic roots (the user changes folders while connected)")
    current_roots = [ALPHA, BETA]

    async def roots_handler(_ctx):                                # called on every roots/list
        return list(current_roots)

    async with Client(transport(), roots=roots_handler) as client:
        print("before ->", await call(client, "find_files", {"pattern": "*.md"}))

        current_roots.remove(BETA)                                # user closes Beta
        await client.send_roots_list_changed()                    # tell the server
        print("after removing Beta ->", await call(client, "find_files", {"pattern": "*.md"}))

        current_roots.append(BETA)                                # user opens Beta again
        await client.send_roots_list_changed()
        print("after adding Beta   ->", await call(client, "find_files", {"pattern": "*.md"}))

    # ---------------------------------------------------------------- PART 3
    banner("PART 3: boundary tests (server must protect itself)")
    private_file = WORKSPACE / "private" / "payroll.csv"
    inside_file = WORKSPACE / "project-alpha" / "README.md"
    sneaky = WORKSPACE / "project-alpha" / ".." / "private" / "payroll.csv"
    async with Client(transport(), roots=[ALPHA]) as client:
        print("read inside root       ->", str(await call(client, "read_file", {"path": str(inside_file)})).replace("\n", " | "))
        print("read outside root      ->", await call(client, "read_file", {"path": str(private_file)}))
        print("read with ../ trick    ->", await call(client, "read_file", {"path": str(sneaky)}))

    # ---------------------------------------------------------------- PART 4
    banner("PART 4: client shares NO roots")
    async with Client(transport()) as client:
        print("find_files ->", await call(client, "find_files", {"pattern": "*.py"}))


if __name__ == "__main__":
    asyncio.run(main())
