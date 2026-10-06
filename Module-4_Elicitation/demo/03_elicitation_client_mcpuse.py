"""
03_elicitation_client_mcpuse.py     (environment: requirements-classic.txt)
=====================================================================
The SAME elicitation idea with the MCP-USE client (the library used in your course).

MCP-USE option:   elicitation_callback=<async function(context, params)>
The function returns a  types.ElicitResult(action=..., content=...)

Run:  python 03_elicitation_client_mcpuse.py
"""

import asyncio
import os
import sys
from pathlib import Path

os.environ["MCP_USE_ANONYMIZED_TELEMETRY"] = "false"         # keep the console clean

from mcp import types                                          # noqa: E402
from mcp_use import MCPClient                                  # noqa: E402

HERE = Path(__file__).parent.resolve()
CONFIG = {"mcpServers": {"travel": {
    "command": sys.executable,
    "args": [str(HERE / "01_elicitation_server_classic.py")],
}}}

# What our simulated user will "do" for each question (matched by the question text)
ANSWERS = {
    "Cancel booking": types.ElicitResult(action="accept", content={"value": True}),
    "Which seat class": types.ElicitResult(action="accept", content={"value": "first"}),
    "Please fill in your trip details": types.ElicitResult(action="accept", content={
        "destination": "Kochi", "nights": 2, "email": "ravi@example.com"}),
    "Which extras": types.ElicitResult(action="decline"),
}


# 1. The elicitation callback = "the user" of this client.
#    params.message is the question; params.requestedSchema describes the form.
async def ask_the_user(context, params: types.ElicitRequestParams):
    print(f"   [callback] question: {params.message!r}")
    print(f"              fields  : {list(params.requestedSchema['properties'])}")
    for start, answer in ANSWERS.items():
        if params.message.startswith(start):
            print(f"              user    : {answer.action}")
            return answer
    return types.ElicitResult(action="cancel")


async def main() -> None:
    # 2. Give the callback to MCPClient
    client = MCPClient(CONFIG, elicitation_callback=ask_the_user)
    await client.create_all_sessions()
    session = client.get_session("travel")

    # 3. Call tools. The server will ask the user behind the scenes.
    for tool, args in [
        ("cancel_booking", {"booking_id": "B100"}),
        ("choose_seat_class", {}),
        ("book_trip", {}),
        ("choose_extras", {}),
    ]:
        result = await session.call_tool(tool, args)
        print(f"{tool:<18} -> {result.content[0].text}\n")

    await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(main())
