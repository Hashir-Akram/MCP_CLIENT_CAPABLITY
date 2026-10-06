"""
02_all_resource_types_client.py
===============================
Starts 01_all_resource_types_server.py and tries EVERY way, one by one.
Run:  python 02_all_resource_types_client.py
"""

import asyncio
import base64
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

SERVER = Path(__file__).parent / "01_all_resource_types_server.py"


def show(label: str, content) -> None:
    c = content[0]
    if getattr(c, "text", None) is not None:
        value = c.text.replace("\n", " | ")
        tag = "text"
    else:
        value = f"{len(base64.b64decode(c.blob))} bytes (base64 blob)"
        tag = "binary"
    print(f"  {label:<34} [{tag}] {value[:90]}")


async def main() -> None:
    async with Client(StdioTransport(sys.executable, [str(SERVER)])) as client:

        print("\n=== LIST: what the server shows (concrete resources) ===")
        for r in await client.list_resources():
            print(f"  {str(r.uri):<26} {r.name}")

        print("\n=== LIST: patterns with blanks (templates) ===")
        for t in await client.list_resource_templates():
            print(f"  {t.uri_template}")

        print("\n=== FAMILY A: functions ===")
        show("1 static   config://app/settings", await client.read_resource("config://app/settings"))
        show("2 dynamic  status://clock (1st)", await client.read_resource("status://clock"))
        await asyncio.sleep(1.1)
        show("2 dynamic  status://clock (2nd)", await client.read_resource("status://clock"))
        show("3 template employee://E102/profile", await client.read_resource("employee://E102/profile"))
        show("4 two blanks report://2026/10", await client.read_resource("report://2026/10"))
        show("5 wildcard docs://leave-policy.md", await client.read_resource("docs://leave-policy.md"))
        show("6 optional  search://mcp", await client.read_resource("search://mcp"))
        show("6 optional  search://mcp?limit=5&lang=hi", await client.read_resource("search://mcp?limit=5&lang=hi"))
        show("7 return str   demo://text", await client.read_resource("demo://text"))
        show("7 return dict  demo://json", await client.read_resource("demo://json"))
        show("7 return bytes demo://bytes", await client.read_resource("demo://bytes"))
        multi = await client.read_resource("demo://multi")
        print(f"  7 several parts demo://multi        -> {len(multi)} content items")
        for part in multi:
            print(f"        part: {part.text[:60]}")

        print("\n=== FAMILY B: ready-made boxes ===")
        show("8  TextResource text://welcome", await client.read_resource("text://welcome"))
        show("9  FileResource file:///release-notes", await client.read_resource("file:///release-notes"))
        show("10 binary image://logo", await client.read_resource("image://logo"))
        show("10 BinaryResource binary://sample", await client.read_resource("binary://sample"))
        show("11 DirectoryResource dir://docs", await client.read_resource("dir://docs"))
        show("12 HttpResource api://price", await client.read_resource("api://price"))
        show("13 FunctionResource fn://banner", await client.read_resource("fn://banner"))

        print("\n=== FAMILY C: add, combine, hide ===")
        before = {str(r.uri) for r in await client.list_resources()}
        await client.call_tool("publish_note", {"slug": "hello", "text": "Created at runtime"})
        after = {str(r.uri) for r in await client.list_resources()}
        print("  14 runtime add -> new:", after - before)
        show("14 read note://hello", await client.read_resource("note://hello"))
        show("15 mounted budget://finance/summary", await client.read_resource("budget://finance/summary"))
        print("  16 hidden resource in list?   ", "internal://secret-plan" in after)
        try:
            await client.read_resource("internal://secret-plan")
            print("  16 reading hidden resource    -> readable (unexpected)")
        except Exception as exc:                                  # noqa: BLE001
            print(f"  16 reading hidden resource    -> blocked: {type(exc).__name__}")


if __name__ == "__main__":
    asyncio.run(main())
