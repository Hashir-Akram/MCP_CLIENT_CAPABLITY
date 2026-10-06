"""
05_roots_client_modern.py     (environment: requirements-modern.txt)
=====================================================================
Client for 04_roots_server_modern.py.

Notice: the client code for roots is EXACTLY the same as before (roots=[...]).
What changed is the wire: the server no longer pushes a request. It answers
"input required", and this client library automatically answers and retries.

Run:  python 05_roots_client_modern.py
"""

import asyncio
import sys
import warnings
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from mcp.types import Root

warnings.simplefilter("ignore")

HERE = Path(__file__).parent.resolve()
WORKSPACE = HERE / "workspace"
SERVER = HERE / "04_roots_server_modern.py"


async def main() -> None:
    roots = [Root(uri=(WORKSPACE / "project-alpha").as_uri(), name="Alpha")]
    transport = StdioTransport(command=sys.executable, args=[str(SERVER)])

    async with Client(transport, roots=roots) as client:
        print("protocol version negotiated:", client.protocol_version)

        print("\nWAY A  find_files_via_roots  (client roots = Alpha only)")
        res = await client.call_tool("find_files_via_roots", {"pattern": "*.md"})
        print("   ->", res.data if res.data is not None else res.content[0].text)

        print("\nWAY B  find_files_in         (server allow-list)")
        for label, folder in [
            ("allowed folder Beta", WORKSPACE / "project-beta"),
            ("forbidden folder private", WORKSPACE / "private"),
        ]:
            try:
                res = await client.call_tool("find_files_in", {"base_dir": str(folder), "pattern": "*"})
                print(f"   {label:<26} -> {res.data}")
            except Exception as exc:                                   # noqa: BLE001
                print(f"   {label:<26} -> ERROR: {str(exc)[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
