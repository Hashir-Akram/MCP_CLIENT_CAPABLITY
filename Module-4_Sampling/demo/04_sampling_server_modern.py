"""
04_sampling_server_modern.py     (environment: requirements-modern.txt)
====================================================================
Sampling in the 2026-07-28 era. Two ways in ONE server:

  WAY A  summarize_via_sampling    sampling through the new "input required"
                                   pattern (MRTR). The tool asks, the client
                                   answers, the tool runs again.

  WAY B  summarize_direct          the REPLACEMENT the spec recommends:
                                   the SERVER calls an AI provider itself,
                                   with its own key - a REAL Groq call here
                                   (groq.com, NOT xAI's Grok), independent of
                                   whatever model the client uses for WAY A.

STATUS: Sampling is DEPRECATED in spec 2026-07-28. It still works (earliest
removal: first revision on or after 2027-07-28) but new projects should
integrate directly with AI provider APIs (WAY B).

Set your key first (or put it in a .env file at the project root):
    Windows (PowerShell):  $env:GROQ_API_KEY = "gsk_..."
    macOS / Linux:         export GROQ_API_KEY="gsk_..."
"""

import asyncio
import os
import warnings

from dotenv import find_dotenv, load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from groq import Groq
from mcp import types as t

warnings.simplefilter("ignore")        # demo only
load_dotenv(find_dotenv(usecwd=True))  # picks up a .env anywhere above the cwd

mcp = FastMCP("Smart-Notes-Modern")

GROQ_MODEL = "openai/gpt-oss-20b"      # the SERVER's own model choice - the client never sees this
_groq_client = Groq(api_key=os.environ["GROQ_API_KEY"]) if os.environ.get("GROQ_API_KEY") else None

NOTES = {
    "n1": ("Team meeting: the release moved to Friday. QA found two login bugs. "
           "Asha will fix them by Thursday. Everyone loves the new dashboard."),
}


# ---------------------------------------------------------------------------
# WAY A - sampling through "input required" (the guard pattern)
# ---------------------------------------------------------------------------
@mcp.tool
async def summarize_via_sampling(note_id: str, ctx: Context):
    """Summarise using the CLIENT's model (deprecated feature, new delivery)."""
    if note_id not in NOTES:
        raise ToolError(f"Unknown note: {note_id}")

    if ctx.input_responses is None:                         # ROUND 1: ask the client
        return t.InputRequiredResult(input_requests={
            "summary": t.CreateMessageRequest(params=t.CreateMessageRequestParams(
                messages=[t.SamplingMessage(role="user", content=t.TextContent(
                    type="text", text=f"Summarise in ONE sentence:\n\n{NOTES[note_id]}"))],
                max_tokens=60,
                system_prompt="You are a concise assistant.",
                temperature=0.2,
            ))
        })

    answer = ctx.input_responses["summary"]                 # ROUND 2: a CreateMessageResult
    return f"[client model: {answer.model}] {answer.content.text}"


# ---------------------------------------------------------------------------
# WAY B - the recommended replacement: the SERVER calls an AI provider itself,
# with its own key. No sampling, no client involvement at all.
# ---------------------------------------------------------------------------
def _call_groq_sync(prompt: str, max_tokens: int) -> str:
    # gpt-oss models are REASONING models: reasoning_effort="low" keeps hidden
    # chain-of-thought short so max_tokens isn't eaten before any visible
    # content is produced.
    resp = _groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max(max_tokens, 150),
        temperature=0.2,
        reasoning_effort="low",
    )
    return resp.choices[0].message.content.strip()


async def call_llm_provider(prompt: str, max_tokens: int = 60) -> str:
    """Calls a real provider with the SERVER's own API key - independent of
    whatever model (if any) the client supplies for WAY A."""
    if _groq_client is None:
        raise ToolError("Server has no GROQ_API_KEY configured - set it in .env or the environment.")
    return await asyncio.to_thread(_call_groq_sync, prompt, max_tokens)


@mcp.tool
async def summarize_direct(note_id: str) -> str:
    """Summarise by calling an AI provider directly (recommended for new projects)."""
    if note_id not in NOTES:
        raise ToolError(f"Unknown note: {note_id}")
    text = await call_llm_provider(f"Summarise in ONE sentence:\n\n{NOTES[note_id]}")
    return f"[server's own model: {GROQ_MODEL}] {text}"


if __name__ == "__main__":
    mcp.run(show_banner=False)
