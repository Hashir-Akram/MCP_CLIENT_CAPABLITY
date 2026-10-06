"""
04_elicitation_server_modern.py     (environment: requirements-modern.txt)
=====================================================================
Elicitation in the 2026-07-28 era. Elicitation is NOT deprecated - it is the
recommended way for a server to ask the user something. What changed is HOW:

    BEFORE: the server pushes an  elicitation/create  request to the client.
    NOW   : the tool RETURNS "input required" (with the question inside) and the
            client answers and CALLS THE TOOL AGAIN. This is MRTR
            (multi round-trip request).

Two tools:
  1. cancel_booking   ONE question, all three outcomes (the simplest guard pattern)
  2. book_trip        THREE rounds (uses request_state as a sticky note)
"""

import json
import warnings

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp import types as t

warnings.simplefilter("ignore")        # demo only

mcp = FastMCP("Travel-Desk-Modern")

BOOKINGS = {"B100": {"destination": "Goa", "nights": 3}}


def past(action: str) -> str:
    """'decline' -> 'declined', 'cancel' -> 'cancelled' (for friendly messages)."""
    return {"decline": "declined", "cancel": "cancelled"}[action]


def form(message: str, properties: dict, required: list[str]) -> t.ElicitRequest:
    """Build an elicitation request: a message plus a flat form (JSON schema)."""
    return t.ElicitRequest(params=t.ElicitRequestFormParams(
        message=message,
        requested_schema={"type": "object", "properties": properties, "required": required},
    ))


# ---------------------------------------------------------------------------
# TOOL 1 - one question, two rounds of the SAME call
# ---------------------------------------------------------------------------
@mcp.tool
async def cancel_booking(booking_id: str, ctx: Context):
    """Cancel a booking after the user confirms."""
    if booking_id not in BOOKINGS:
        raise ToolError(f"Unknown booking: {booking_id}")

    if ctx.input_responses is None:                                 # ROUND 1: ask
        return t.InputRequiredResult(input_requests={
            "confirm": form(
                f"Cancel booking {booking_id}? This cannot be undone.",
                {"yes": {"type": "boolean", "title": "Yes, cancel it"}}, ["yes"]),
        })

    answer = ctx.input_responses["confirm"]                         # ROUND 2: use the answer
    if answer.action != "accept":
        return f"The user {past(answer.action)}. Nothing was changed."
    if answer.content.get("yes") is True:
        del BOOKINGS[booking_id]
        return f"Booking {booking_id} was cancelled."
    return f"Booking {booking_id} was kept."


# ---------------------------------------------------------------------------
# TOOL 2 - a multi-step conversation: destination -> details -> done
# ---------------------------------------------------------------------------
@mcp.tool
async def book_trip(ctx: Context):
    """Ask for the destination first, then for details that depend on it."""
    responses = ctx.input_responses or {}

    # ROUND 3: we have the details; the sticky note holds the destination
    if "details" in responses:
        saved = json.loads(ctx.request_state)                       # our own sticky note
        d = responses["details"]
        if d.action != "accept":
            return f"The user {past(d.action)} at the details step. Nothing was booked."
        return (f"Booked: {d.content['nights']} nights in {saved['destination']} "
                f"(meal included: {d.content.get('meal', False)}).")

    # ROUND 2: we have the destination; ask the details (and write the sticky note)
    if "destination" in responses:
        d = responses["destination"]
        if d.action != "accept":
            return f"The user {past(d.action)} at the destination step. Nothing was booked."
        destination = d.content["destination"]
        return t.InputRequiredResult(
            input_requests={"details": form(
                f"{destination}: how long, and do you want meals?",
                {"nights": {"type": "integer", "minimum": 1, "maximum": 14, "title": "Nights"},
                 "meal": {"type": "boolean", "title": "Include meals", "default": False}},
                ["nights"])},
            request_state=json.dumps({"destination": destination}),  # remembered for round 3
        )

    # ROUND 1: nothing yet; ask for the destination
    return t.InputRequiredResult(input_requests={"destination": form(
        "Where do you want to go?",
        {"destination": {"type": "string", "enum": ["Goa", "Jaipur", "Kochi"], "title": "Destination"}},
        ["destination"])})


if __name__ == "__main__":
    mcp.run(show_banner=False)
