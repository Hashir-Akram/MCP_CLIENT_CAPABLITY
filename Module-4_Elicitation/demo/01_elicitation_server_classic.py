"""
01_elicitation_server_classic.py     (environment: requirements-classic.txt)
=====================================================================
"Travel Desk" - an MCP server that sometimes needs to ASK THE USER something
in the middle of a task. That asking is called ELICITATION.

BIG IDEA (simple words):
    SERVER (to client): "I need a bit more information. Please ask the user this."
    CLIENT            : shows a small form to the user.
    USER              : fills it in (ACCEPT), says no thanks (DECLINE) or closes it (CANCEL).
    SERVER            : continues with the answer - or stops politely.

Every elicitation has THREE possible outcomes. A good server handles all three:
    accept   -> the user gave data
    decline  -> the user clearly said NO
    cancel   -> the user closed the form without deciding

Run through:  python 02_elicitation_client_classic.py   (starts this server for you)
"""

from typing import Literal

from pydantic import BaseModel, Field

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("Travel-Desk")

BOOKINGS: dict[str, dict] = {"B100": {"destination": "Goa", "nights": 3}}
ALLOWED_DESTINATIONS = ["Goa", "Jaipur", "Kochi"]


# ---------------------------------------------------------------------------
# HELPER - what to say when the user did NOT accept
# ---------------------------------------------------------------------------
def not_accepted(result) -> str:
    if result.action == "decline":
        return "The user declined. Nothing was changed."
    return "The user cancelled. Nothing was changed."          # action == "cancel"


# ---------------------------------------------------------------------------
# TOOL 1 - a simple YES/NO confirmation before a risky action
# ---------------------------------------------------------------------------
@mcp.tool
async def cancel_booking(booking_id: str, ctx: Context) -> str:
    """Cancel a booking, but only after the user confirms."""
    if booking_id not in BOOKINGS:
        raise ToolError(f"Unknown booking: {booking_id}")

    result = await ctx.elicit(
        f"Cancel booking {booking_id} to {BOOKINGS[booking_id]['destination']}? This cannot be undone.",
        response_type=bool,                    # a yes/no question
    )
    if result.action != "accept":              # decline OR cancel
        return not_accepted(result)
    if result.data is True:                    # the user ticked "yes"
        del BOOKINGS[booking_id]
        return f"Booking {booking_id} was cancelled."
    return f"Booking {booking_id} was kept."


# ---------------------------------------------------------------------------
# TOOL 2 - pick ONE option from a list
# ---------------------------------------------------------------------------
@mcp.tool
async def choose_seat_class(ctx: Context) -> str:
    """Ask the user which seat class they want."""
    result = await ctx.elicit(
        "Which seat class would you like?",
        response_type=["economy", "business", "first"],     # shown as a dropdown
    )
    if result.action != "accept":
        return not_accepted(result)
    return f"Seat class chosen: {result.data}"


# ---------------------------------------------------------------------------
# TOOL 3 - a REAL FORM with several typed fields
# ---------------------------------------------------------------------------
class Trip(BaseModel):
    """The form the user will see. Every field becomes an input box."""

    destination: Literal["Goa", "Jaipur", "Kochi"] = Field(description="Where do you want to go?")
    nights: int = Field(ge=1, le=14, description="How many nights (1 to 14)?")
    email: str = Field(json_schema_extra={"format": "email"}, description="Where should we send the ticket?")
    travel_class: Literal["economy", "business"] = "economy"        # has a default
    wants_insurance: bool = False                                    # has a default


@mcp.tool
async def book_trip(ctx: Context) -> str:
    """Collect trip details with a form, then create a booking."""
    result = await ctx.elicit("Please fill in your trip details.", response_type=Trip)

    if result.action == "accept":
        trip: Trip = result.data                      # a real Trip object, already validated
        booking_id = f"B{101 + len(BOOKINGS)}"
        BOOKINGS[booking_id] = trip.model_dump()
        return f"Booked {booking_id}: {trip.nights} nights in {trip.destination} ({trip.travel_class})."
    return not_accepted(result)


# ---------------------------------------------------------------------------
# TOOL 4 - pick SEVERAL options (multi-select)
# ---------------------------------------------------------------------------
@mcp.tool
async def choose_extras(ctx: Context) -> str:
    """Let the user tick any extras they want."""
    result = await ctx.elicit(
        "Which extras would you like?",
        response_type=[["meal", "wifi", "lounge"]],         # list of lists = multi-select
    )
    if result.action != "accept":
        return not_accepted(result)
    return f"Extras chosen: {', '.join(result.data) if result.data else 'none'}"


# ---------------------------------------------------------------------------
# TOOL 5 - ask AGAIN when the answer is not usable (but never forever)
# ---------------------------------------------------------------------------
@mcp.tool
async def pick_destination(ctx: Context) -> str:
    """Ask for a destination we actually serve. Allow at most 3 attempts."""
    message = "Where do you want to go?"
    for attempt in range(1, 4):                                    # a hard limit!
        result = await ctx.elicit(message, response_type=str)
        if result.action != "accept":
            return not_accepted(result)
        choice = result.data.strip().title()
        if choice in ALLOWED_DESTINATIONS:
            return f"Great: {choice} (after {attempt} attempt(s))."
        message = f"Sorry, we do not fly to '{choice}'. Please choose one of: {', '.join(ALLOWED_DESTINATIONS)}."
    return "Too many attempts. Please try again later."


# ---------------------------------------------------------------------------
# TOOL 6 - only ASK for what is MISSING; and cope with clients that cannot ask
# ---------------------------------------------------------------------------
async def ask_user(ctx: Context, message: str, response_type, what: str):
    """Ask one question. If the client cannot ask users, explain how to continue."""
    try:
        return await ctx.elicit(message, response_type=response_type)
    except Exception as exc:                                       # client has no elicitation
        raise ToolError(
            f"I need {what}, but this client cannot ask the user. "
            f"Please call me again and pass {what} as an argument."
        ) from exc


@mcp.tool
async def quick_booking(destination: str | None = None, nights: int | None = None, ctx: Context = None) -> str:
    """Book a trip. Arguments you give are used as-is; only MISSING ones are asked."""
    if destination is None:
        result = await ask_user(ctx, "Which destination?", ALLOWED_DESTINATIONS, "the destination")
        if result.action != "accept":
            return not_accepted(result)
        destination = result.data

    if nights is None:
        result = await ask_user(ctx, "How many nights?", int, "the number of nights")
        if result.action != "accept":
            return not_accepted(result)
        nights = result.data

    return f"Quick booking: {nights} nights in {destination}."


if __name__ == "__main__":
    mcp.run(show_banner=False)
