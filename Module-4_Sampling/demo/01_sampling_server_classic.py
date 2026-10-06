"""
01_sampling_server_classic.py     (environment: requirements-classic.txt)
====================================================================
"Smart Notes" - an MCP server that needs an AI model, but has NO model of its own
and NO API key. It BORROWS the model of the CLIENT. This borrowing is "sampling".

BIG IDEA (simple words):
    SERVER (to client): "Please ask YOUR AI model this question and give me the answer."
    CLIENT            : runs its own model (maybe after asking the user), returns the text.
    SERVER            : uses the text to finish its tool.

Why is that nice?
    * The server needs no API key and pays nothing.
    * The USER stays in control: their model, their billing, their approval.

Run through:  python 02_sampling_client_classic.py   (starts this server for you)
"""

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ModelHint, ModelPreferences

mcp = FastMCP("Smart-Notes")

NOTES = {
    "n1": ("Team meeting: the release moved to Friday. QA found two login bugs. "
           "Asha will fix them by Thursday. Everyone loves the new dashboard."),
    "n2": ("Customer complaint: the invoice total is wrong and support has not replied for "
           "three days. The customer is very disappointed and wants a refund."),
    "n3": ("Idea: add a dark mode to the mobile app. Users asked for it in the survey "
           "and it would help at night."),
}

MAX_SAMPLES_PER_CALL = 2          # cost control: never loop forever (see summarize_all)


def get_note(note_id: str) -> str:
    if note_id not in NOTES:
        raise ToolError(f"Unknown note: {note_id}")
    return NOTES[note_id]


# ---------------------------------------------------------------------------
# TOOL 1 - the basic pattern: system prompt + user message + limits
# ---------------------------------------------------------------------------
@mcp.tool
async def summarize_note(note_id: str, ctx: Context) -> str:
    """Summarise a note in one sentence using the client's AI model."""
    note = get_note(note_id)
    result = await ctx.sample(
        messages=f"Summarise this note in ONE sentence:\n\n{note}",   # the user message
        system_prompt="You are a concise assistant. Never add facts that are not in the text.",
        max_tokens=60,                 # hard limit on the length of the answer
        temperature=0.2,               # low = steady, high = creative
    )
    return result.text                 # the model's answer as plain text


# ---------------------------------------------------------------------------
# TOOL 2 - model PREFERENCES: tell the client what kind of model suits the job
# ---------------------------------------------------------------------------
@mcp.tool
async def classify_sentiment(text: str, ctx: Context) -> str:
    """Classify text as positive, negative or neutral (a cheap, fast job)."""
    # NOTE: in the classic SDK these field names are camelCase (costPriority, ...)
    prefs = ModelPreferences(
        hints=[ModelHint(name="openai/gpt-oss-20b")],  # a real, small/fast Groq model
        costPriority=0.9,                  # 0..1: how much do I care about low cost?
        speedPriority=0.8,                 # 0..1: how much do I care about speed?
        intelligencePriority=0.2,          # 0..1: how much do I need a very smart model?
    )
    result = await ctx.sample(
        messages=f"Classify the sentiment of this text. Answer with ONE word: "
                 f"positive, negative or neutral.\n\n{text}",
        system_prompt="You are a sentiment classifier.",
        max_tokens=5,
        temperature=0.0,
        model_preferences=prefs,
    )
    return result.text.strip().lower()


# ---------------------------------------------------------------------------
# TOOL 3 - a graceful FALLBACK when the client cannot do sampling
# ---------------------------------------------------------------------------
@mcp.tool
async def suggest_title(note_id: str, ctx: Context) -> str:
    """Suggest a short title. Works even if the client has no AI model to lend."""
    note = get_note(note_id)
    try:
        result = await ctx.sample(
            messages=f"Write a title of at most 5 words for this note:\n\n{note}",
            max_tokens=15,
        )
        return f"[AI title] {result.text.strip()}"
    except Exception as exc:                            # client has no sampling / user refused
        first_words = " ".join(note.split()[:4])
        return f"[fallback title] {first_words}...  (reason: {str(exc)[:50]})"


# ---------------------------------------------------------------------------
# TOOL 4 - COST CONTROL: a budget for how many model calls one tool may make
# ---------------------------------------------------------------------------
@mcp.tool
async def summarize_all(ctx: Context) -> dict:
    """Summarise notes, but never more than MAX_SAMPLES_PER_CALL model calls."""
    summaries, calls = {}, 0
    for note_id, note in NOTES.items():
        if calls >= MAX_SAMPLES_PER_CALL:
            summaries[note_id] = "(skipped: sampling budget reached)"
            continue
        result = await ctx.sample(
            f"Summarise in ONE sentence:\n\n{note}", max_tokens=60, temperature=0.2)
        summaries[note_id] = result.text
        calls += 1
    return {"model_calls_used": calls, "summaries": summaries}


if __name__ == "__main__":
    mcp.run(show_banner=False)
