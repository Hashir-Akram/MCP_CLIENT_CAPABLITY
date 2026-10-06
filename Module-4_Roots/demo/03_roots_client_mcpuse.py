"""
03_roots_client_mcpuse.py     (environment: requirements-classic.txt)
=====================================================================
The SAME roots idea, but with the MCP-USE client library (used in your course).

MCP-USE options for roots:
    roots=[Root(...), ...]          -> a fixed list of roots
    list_roots_callback=<function>  -> your own function, called on every roots/list

Run:  python 03_roots_client_mcpuse.py
"""

import asyncio
import os
import sys
from pathlib import Path

os.environ["MCP_USE_ANONYMIZED_TELEMETRY"] = "false"        # keep the console clean

from mcp.types import Root                                   # noqa: E402
from mcp_use import MCPClient                                # noqa: E402

HERE = Path(__file__).parent.resolve()
WORKSPACE = HERE / "workspace"

# 1. Tell MCP-USE how to start the server (same idea as a config file)
CONFIG = {
    "mcpServers": {
        "workspace": {
            "command": sys.executable,
            "args": [str(HERE / "01_roots_server_classic.py")],
        }
    }
}


async def main() -> None:
    # 2. Create the client and hand it the roots
    client = MCPClient(
        CONFIG,
        roots=[
            Root(uri=(WORKSPACE / "project-alpha").as_uri(), name="Alpha"),
            Root(uri=(WORKSPACE / "project-beta").as_uri(), name="Beta"),
        ],
    )
    await client.create_all_sessions()                       # connects + handshake
    session = client.get_session("workspace")

    # 3. Use the server's tools. The server will ask us for roots behind the scenes.
    for tool, args in [
        ("list_my_roots", {}),
        ("find_files", {"pattern": "*.md"}),
        ("workspace_summary", {}),
    ]:
        result = await session.call_tool(tool, args)
        print(f"{tool:<18} -> {result.content[0].text[:150]}")

    await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(main())
