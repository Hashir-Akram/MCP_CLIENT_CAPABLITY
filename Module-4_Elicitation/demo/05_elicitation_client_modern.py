"""
05_elicitation_client_modern.py     (environment: requirements-modern.txt)
=====================================================================
Client for 04_elicitation_server_modern.py.

Notice: the elicitation handler is the SAME style as in the classic demo.
The FastMCP client answers "input required" and retries the tool call for you.
For a three-step tool the handler is simply called three times.

Run:  python 05_elicitation_client_modern.py
"""

import asyncio
import sys
import warnings
from pathlib import Path

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.client.transports import StdioTransport

warnings.simplefilter("ignore")

SERVER = Path(__file__).parent / "04_elicitation_server_modern.py"


class SimulatedUser:
    def __init__(self, script):
        self.script = list(script)

    async def handler(self, message, response_type, params, ctx):
        fields = list((params.requested_schema or {}).get("properties", {}))
        action, content = self.script.pop(0)
        print(f"   [question] {message}   fields={fields}")
        print(f"   [user does] {action}" + (f" -> {content}" if content else ""))
        return ElicitResult(action=action, content=content)


async def run(title: str, script, tool: str, args: dict | None = None) -> None:
    print(f"\n--- {title}")
    user = SimulatedUser(script)
    transport = StdioTransport(command=sys.executable, args=[str(SERVER)])
    async with Client(transport, elicitation_handler=user.handler) as client:
        res = await client.call_tool(tool, args or {})
        print("   RESULT:", res.content[0].text)


async def main() -> None:
    await run("cancel_booking: user says yes", [("accept", {"yes": True})], "cancel_booking", {"booking_id": "B100"})
    await run("cancel_booking: user declines", [("decline", None)], "cancel_booking", {"booking_id": "B100"})
    await run("book_trip: three rounds (one tool call, three questions)",
              [("accept", {"destination": "Goa"}), ("accept", {"nights": 4, "meal": True})], "book_trip")
    await run("book_trip: user cancels at step 2", [("accept", {"destination": "Kochi"}), ("cancel", None)], "book_trip")


if __name__ == "__main__":
    asyncio.run(main())
