"""
04_base_client.py
=================
Tests 03_base_server_resources.py with the OFFICIAL `mcp` SDK client
(no FastMCP involved) so you see the raw protocol objects.

Run:  python 04_base_client.py
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.shared.exceptions import MCPError

SERVER = Path(__file__).parent / "03_base_server_resources.py"


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])

    async with Client(params) as client:
        # 1. CAPABILITY NEGOTIATION ----------------------------------------
        # The server told us during `initialize` which features it supports.
        caps = client.server_capabilities
        print("server resources capability:", caps.resources)

        # 2. DISCOVERY -------------------------------------------------------
        listing = await client.list_resources()
        print("\nresources/list:")
        for r in listing.resources:
            print(f"  {r.uri:<20} {r.name:<16} {r.mime_type}")

        templates = await client.list_resource_templates()
        print("\nresources/templates/list:")
        for t in templates.resource_templates:
            print(f"  {t.uri_template:<24} {t.name}")

        # 3. READ ------------------------------------------------------------
        print("\nresources/read tickets://summary")
        result = await client.read_resource("tickets://summary")
        print(" ", json.loads(result.contents[0].text))

        print("\nresources/read tickets://102   (matches the template)")
        result = await client.read_resource("tickets://102")
        print(" ", result.contents[0].text)

        # 4. LISTEN FOR CHANGES (spec 2026-07-28: subscriptions/listen) -----
        # One long-lived stream. We opt in to exactly two kinds of events:
        #   - list_changed        -> "the set of resources changed, re-list"
        #   - resource_subscriptions -> "THIS resource's content changed, re-read"
        print("\nopening subscriptions/listen ...")
        async with client.listen(
            resources_list_changed=True,
            resource_subscriptions=["tickets://101"],
        ) as sub:
            print("  server honored:", sub.honored)

            # (a) edit an existing ticket -> ResourceUpdated(tickets://101)
            await client.call_tool(
                "update_ticket",
                {"ticket_id": "101", "text": "Password reset DONE - verified by phone."},
            )
            # (b) create a new ticket     -> ResourcesListChanged
            await client.call_tool(
                "update_ticket", {"ticket_id": "104", "text": "New: VPN not connecting."}
            )

            for _ in range(2):
                event = await asyncio.wait_for(anext(sub), timeout=5)
                print("  event received:", event)
                # Notifications carry NO data - they only say "something changed".
                # The client must refetch with resources/read or resources/list:
                if type(event).__name__ == "ResourceUpdated":
                    fresh = await client.read_resource(event.uri)
                    print("    re-read ->", fresh.contents[0].text)
                else:
                    again = await client.list_resources()
                    print("    re-listed ->", [str(r.uri) for r in again.resources])

        # 5. ERROR PATH ------------------------------------------------------
        try:
            await client.read_resource("tickets://999")
        except MCPError as exc:
            print(f"\nread tickets://999 -> error code {exc.code}: {exc.message}")


if __name__ == "__main__":
    asyncio.run(main())
