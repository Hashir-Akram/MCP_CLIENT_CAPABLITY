"""
02_resources_client.py
======================
Walks through the COMPLETE resource lifecycle against 01_resources_server.py:

  PHASE 1  Connect + initialize (capability negotiation)
  PHASE 2  Discover   -> resources/list  and  resources/templates/list
  PHASE 3  Read       -> static, dynamic, template, wildcard, binary
  PHASE 4  Errors     -> unknown URI, bad parameter, path traversal
  PHASE 5  Change     -> tool adds a resource, client re-discovers
  PHASE 6  Close      -> async context manager shuts the session down

Run:  python 02_resources_client.py
"""

import asyncio
import base64
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.messages import MessageHandler
from fastmcp.client.transports import StdioTransport

SERVER = Path(__file__).parent / "01_resources_server.py"


class WatchHandler(MessageHandler):
    """Receives SERVER -> CLIENT notifications (no request id, no reply)."""

    def __init__(self) -> None:
        super().__init__()
        self.list_changed_count = 0

    async def on_resource_list_changed(self, message) -> None:
        self.list_changed_count += 1
        print("  [notification] notifications/resources/list_changed received")


def banner(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


async def main() -> None:
    # PHASE 1 --------------------------------------------------------------
    # Entering the "async with" block performs:  initialize -> initialized
    transport = StdioTransport(command=sys.executable, args=[str(SERVER)])
    handler = WatchHandler()
    async with Client(transport, message_handler=handler) as client:
        banner("PHASE 1: connected")
        print("initialized; is_connected =", client.is_connected())

        # PHASE 2 ----------------------------------------------------------
        banner("PHASE 2a: resources/list  (static + class-based resources)")
        for r in await client.list_resources():
            print(f"  {str(r.uri):<34} {r.name:<20} [{r.mime_type}]")

        banner("PHASE 2b: resources/templates/list  (parameterised)")
        for t in await client.list_resource_templates():
            print(f"  {t.uri_template:<34} {t.name}")

        # PHASE 3 ----------------------------------------------------------
        banner("PHASE 3a: read STATIC  config://app/settings")
        content = await client.read_resource("config://app/settings")
        print(content[0].text)

        banner("PHASE 3b: read DYNAMIC twice -> timestamp changes")
        for _ in range(2):
            c = await client.read_resource("status://server/health")
            print(" ", c[0].text)
            await asyncio.sleep(1.1)

        banner("PHASE 3c: read TEMPLATE  employee://E102/profile")
        c = await client.read_resource("employee://E102/profile")
        print(c[0].text)

        banner("PHASE 3d: read TEMPLATE (2 params)  logs://payments/2026-10-04")
        c = await client.read_resource("logs://payments/2026-10-04")
        print(c[0].text)

        banner("PHASE 3e: read WILDCARD  kb://handbook/leave-policy.md")
        c = await client.read_resource("kb://handbook/leave-policy.md")
        print(c[0].text)

        banner("PHASE 3f: read BINARY  image://company/logo")
        c = await client.read_resource("image://company/logo")
        blob = c[0].blob                      # base64 string
        raw = base64.b64decode(blob)
        print(f"  mime={c[0].mime_type}  base64_chars={len(blob)}  decoded_bytes={len(raw)}")
        print("  PNG signature ok:", raw[:8] == b"\x89PNG\r\n\x1a\n")

        banner("PHASE 3g: read DirectoryResource  dir://handbook")
        c = await client.read_resource("dir://handbook")
        print(c[0].text)

        # PHASE 4 ----------------------------------------------------------
        banner("PHASE 4: error handling")
        for bad in (
            "nothing://here",                       # no such resource
            "employee://E999/profile",              # template matched, function raised
            "kb://handbook/..%2F..%2Fsecret.txt",   # encoded path traversal attempt
            "kb://handbook/missing.md",             # valid shape, file absent
        ):
            try:
                await client.read_resource(bad)
                print(f"  {bad}  -> UNEXPECTEDLY OK")
            except Exception as exc:                # noqa: BLE001
                print(f"  {bad}\n     -> {type(exc).__name__}: {str(exc)[:110]}")

        # PHASE 5 ----------------------------------------------------------
        banner("PHASE 5: runtime change")
        before = {str(r.uri) for r in await client.list_resources()}
        result = await client.call_tool(
            "publish_report",
            {"slug": "q3-summary", "body": "Q3 revenue grew 18% QoQ."},
        )
        print("tool result:", result.content[0].text)
        after = {str(r.uri) for r in await client.list_resources()}
        await asyncio.sleep(0.3)               # give the notification a moment to arrive
        print("new resources:", after - before)
        print("list_changed notifications seen:", handler.list_changed_count)
        c = await client.read_resource("report://q3-summary")
        print("read new resource:", c[0].text)

    # PHASE 6 --------------------------------------------------------------
    banner("PHASE 6: session closed (left the async-with block)")


if __name__ == "__main__":
    asyncio.run(main())
