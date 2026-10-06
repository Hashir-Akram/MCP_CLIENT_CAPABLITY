"""
02_elicitation_client_classic.py     (environment: requirements-classic.txt)
=====================================================================
The CLIENT side of elicitation. The client is the one who talks to the USER, so it
writes the "elicitation handler": a function that receives the server's question and
returns what the user answered.

To keep the demo repeatable we SIMULATE the user with a small script.
In a real app the handler would open a dialog or a form.

  PART 1  Look at one elicitation request (message + schema)
  PART 2  The three outcomes: accept / decline / cancel
  PART 3  A form: valid answer, then an INVALID answer
  PART 4  Multi-select and single choice
  PART 5  Ask again (retry loop with a limit)
  PART 6  Ask only what is missing / client that cannot ask

Run:  python 02_elicitation_client_classic.py
"""

import asyncio
import json
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.client.transports import StdioTransport

SERVER = Path(__file__).parent / "01_elicitation_server_classic.py"


def banner(t: str) -> None:
    print(f"\n{'=' * 8} {t} {'=' * 8}")


def transport() -> StdioTransport:
    return StdioTransport(command=sys.executable, args=[str(SERVER)])


async def call(client: Client, tool: str, args: dict | None = None):
    try:
        res = await client.call_tool(tool, args or {})
        return res.data if res.data is not None else res.content[0].text
    except Exception as exc:                                       # noqa: BLE001
        return f"ERROR: {str(exc)[:110]}"


# ---------------------------------------------------------------------------
# THE SIMULATED USER
#   script = a list of answers. Each answer is what the user "does" for the next question.
#   ("accept", {...})  fills the form      ("decline", None)  says no      ("cancel", None)  closes it
# ---------------------------------------------------------------------------
class SimulatedUser:
    def __init__(self, script: list[tuple[str, dict | None]], show_schema: bool = False):
        self.script = list(script)
        self.show_schema = show_schema

    async def handler(self, message, response_type, params, ctx):
        # The three things a handler receives:
        #   message        - the text to show the user
        #   response_type  - a Python type built from the server's schema
        #   params         - the raw protocol request (params.requestedSchema is the JSON schema)
        print(f"   [question to user] {message}")
        if self.show_schema:
            props = params.requestedSchema.get("properties", {})
            for name, spec in props.items():
                extras = {k: v for k, v in spec.items() if k not in ("title", "description")}
                print(f"      field {name!r:<18} {extras}")
            print("      required:", params.requestedSchema.get("required", []))
        action, content = self.script.pop(0)
        print(f"   [user does] {action}" + (f" -> {content}" if content else ""))
        return ElicitResult(action=action, content=content)


async def main() -> None:
    # ---------------------------------------------------------------- PART 1
    banner("PART 1: one complete request, as the client sees it")
    user = SimulatedUser([("accept", {"destination": "Goa", "nights": 4, "email": "asha@example.com",
                                      "travel_class": "business", "wants_insurance": True})], show_schema=True)
    async with Client(transport(), elicitation_handler=user.handler) as client:
        print("RESULT:", await call(client, "book_trip"))

    # ---------------------------------------------------------------- PART 2
    banner("PART 2: the three outcomes (yes / no / decline / cancel)")
    cases = [
        ("accept, ticked YES", ("accept", {"value": True})),
        ("accept, ticked NO ", ("accept", {"value": False})),
        ("decline           ", ("decline", None)),
        ("cancel            ", ("cancel", None)),
    ]
    for label, answer in cases:
        # every case needs a fresh booking, so every case starts a fresh server
        user = SimulatedUser([answer])
        async with Client(transport(), elicitation_handler=user.handler) as client:
            print(f"{label} -> {await call(client, 'cancel_booking', {'booking_id': 'B100'})}")

    # ---------------------------------------------------------------- PART 3
    banner("PART 3: a form - what if the user types something invalid?")
    bad = {"destination": "Goa", "nights": 99, "email": "asha@example.com"}       # nights must be 1..14
    user = SimulatedUser([("accept", bad)])
    async with Client(transport(), elicitation_handler=user.handler) as client:
        print("RESULT (nights=99):", await call(client, "book_trip"))

    # ---------------------------------------------------------------- PART 4
    banner("PART 4: single choice and multi-select")
    user = SimulatedUser([("accept", {"value": "business"}), ("accept", {"value": ["meal", "lounge"]}),
                          ("accept", {"value": []})])
    async with Client(transport(), elicitation_handler=user.handler) as client:
        print("RESULT:", await call(client, "choose_seat_class"))
        print("RESULT:", await call(client, "choose_extras"))
        print("RESULT (ticked nothing):", await call(client, "choose_extras"))

    # ---------------------------------------------------------------- PART 5
    banner("PART 5: asking again, with a limit of 3 attempts")
    user = SimulatedUser([("accept", {"value": "Paris"}), ("accept", {"value": "goa"})])
    async with Client(transport(), elicitation_handler=user.handler) as client:
        print("RESULT (fixes it on try 2):", await call(client, "pick_destination"))
    user = SimulatedUser([("accept", {"value": "Paris"}), ("accept", {"value": "Rome"}), ("accept", {"value": "Oslo"})])
    async with Client(transport(), elicitation_handler=user.handler) as client:
        print("RESULT (never fixes it):", await call(client, "pick_destination"))

    # ---------------------------------------------------------------- PART 6
    banner("PART 6: ask only what is missing / client that cannot ask")
    user = SimulatedUser([])                                   # nothing should be asked
    async with Client(transport(), elicitation_handler=user.handler) as client:
        print("all arguments given  ->", await call(client, "quick_booking", {"destination": "Kochi", "nights": 2}))
    user = SimulatedUser([("accept", {"value": 5})])           # only nights is asked
    async with Client(transport(), elicitation_handler=user.handler) as client:
        print("only nights missing  ->", await call(client, "quick_booking", {"destination": "Jaipur"}))
    async with Client(transport()) as client:                  # NO elicitation handler at all
        print("client cannot ask    ->", await call(client, "quick_booking", {"destination": "Jaipur"}))


if __name__ == "__main__":
    asyncio.run(main())
