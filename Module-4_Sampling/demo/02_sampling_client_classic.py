"""
02_sampling_client_classic.py     (environment: requirements-classic.txt)
====================================================================
The CLIENT side of sampling. The client owns the AI model, so IT writes the
"sampling handler": a function that receives the server's request and returns text.

This calls REAL Groq models (groq.com - NOT xAI's Grok). Two real models are
wired in, and the client picks between them based on the server's
ModelPreferences:

    openai/gpt-oss-120b   default (no stated preference) - the smarter model
    openai/gpt-oss-20b    used when the server asks for cheap/fast (see
                          classify_sentiment's hint in 01_sampling_server_classic.py)

Set your key first (or put it in a .env file at the project root):
    Windows (PowerShell):  $env:GROQ_API_KEY = "gsk_..."
    macOS / Linux:         export GROQ_API_KEY="gsk_..."

  PART 1  Look at a full sampling request (every parameter)
  PART 2  Model preferences: the client chooses a model for the job
  PART 3  Human approval: the user says NO
  PART 4  A client with NO sampling support
  PART 5  Server-side budget (cost control)

Run:  python 02_sampling_client_classic.py
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from groq import Groq
from mcp.types import CreateMessageResult, ErrorData, TextContent

load_dotenv(find_dotenv(usecwd=True))          # picks up a .env anywhere above the cwd

SERVER = Path(__file__).parent / "01_sampling_server_classic.py"
GROQ_MODEL_SMART = "openai/gpt-oss-120b"       # default: no stated preference -> use the best model
GROQ_MODEL_FAST = "openai/gpt-oss-20b"         # used when the server asks for cheap/fast

if not os.environ.get("GROQ_API_KEY"):
    raise SystemExit(
        "Set GROQ_API_KEY first - copy .env.example to .env at the project root "
        "and fill in your key, or:  $env:GROQ_API_KEY = 'gsk_...'"
    )

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])


def banner(t: str) -> None:
    print(f"\n{'=' * 8} {t} {'=' * 8}")


# ---------------------------------------------------------------------------
# THE REAL MODEL - a blocking Groq call, run off the event loop thread
# ---------------------------------------------------------------------------
def call_groq(prompt: str, system_prompt: str | None, max_tokens: int, temperature: float,
               model: str = GROQ_MODEL_SMART) -> str:
    # gpt-oss models are REASONING models: they spend tokens on hidden chain-of-thought
    # before writing the visible answer. reasoning_effort="low" keeps that short so
    # max_tokens isn't eaten by reasoning before any visible content is produced.
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = groq_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max(max_tokens, 150),
        temperature=temperature,
        reasoning_effort="low",
    )
    return resp.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# choose_model - turns the server's advice into an ACTUAL choice between two
# real Groq models.
# ---------------------------------------------------------------------------
def choose_model(prefs) -> str:
    if prefs is None:
        return GROQ_MODEL_SMART                       # no preference stated -> use the best model
    hints = [h.name for h in (prefs.hints or [])]
    if any(GROQ_MODEL_FAST in h or "20b" in h for h in hints) or (prefs.costPriority or 0) > 0.7:
        return GROQ_MODEL_FAST                         # cheap and fast, as requested
    if (prefs.intelligencePriority or 0) > 0.7:
        return GROQ_MODEL_SMART
    return GROQ_MODEL_SMART


# ---------------------------------------------------------------------------
# HANDLER A - logs EVERYTHING the server sent, then answers with real Groq
# ---------------------------------------------------------------------------
async def logging_handler(messages, params, ctx):
    prefs = params.modelPreferences
    print("   --- sampling request received ---")
    print("   messages        :", [(m.role, m.content.text[:40] + "...") for m in messages])
    print("   system_prompt   :", params.systemPrompt)
    print("   max_tokens      :", params.maxTokens)
    print("   temperature     :", params.temperature)
    print("   stop_sequences  :", params.stopSequences)
    print("   include_context :", params.includeContext)
    if prefs:
        print("   model hints     :", [h.name for h in (prefs.hints or [])])
        print("   priorities      : cost=%s speed=%s intelligence=%s" % (
            prefs.costPriority, prefs.speedPriority, prefs.intelligencePriority))
    else:
        print("   model preferences: none")

    # The CLIENT picks the model. Hints and priorities are only advice.
    model = choose_model(prefs)
    text = await asyncio.to_thread(
        call_groq, messages[-1].content.text, params.systemPrompt,
        params.maxTokens or 60, params.temperature or 0.2, model,
    )
    print(f"   -> client chose model '{model}' and Groq answers: {text!r}")
    return CreateMessageResult(
        role="assistant",
        content=TextContent(type="text", text=text),
        model=model,
        stopReason="endTurn",
    )


# ---------------------------------------------------------------------------
# HANDLER B - a HUMAN-IN-THE-LOOP gate: the user approves or refuses
# ---------------------------------------------------------------------------
def make_approval_handler(user_says_yes: bool):
    async def approval_handler(messages, params, ctx):
        question = messages[-1].content.text[:50].replace("\n", " ")
        print(f"   [approval prompt] Server wants to ask the AI: {question!r}...  allow? ->",
              "YES" if user_says_yes else "NO")
        if not user_says_yes:
            return ErrorData(code=-1, message="The user refused this AI request.")
        return await logging_handler(messages, params, ctx)
    return approval_handler


async def call(client: Client, tool: str, args: dict | None = None):
    try:
        res = await client.call_tool(tool, args or {})
        return res.data if res.data is not None else res.content[0].text
    except Exception as exc:                                       # noqa: BLE001
        return f"ERROR: {str(exc)[:150]}"


def transport() -> StdioTransport:
    return StdioTransport(command=sys.executable, args=[str(SERVER)])


async def main() -> None:
    # ---------------------------------------------------------------- PART 1
    banner("PART 1: one complete sampling request")
    async with Client(transport(), sampling_handler=logging_handler) as client:
        print("RESULT:", await call(client, "summarize_note", {"note_id": "n1"}))

    # ---------------------------------------------------------------- PART 2
    banner("PART 2: model preferences (advice, not orders)")
    async with Client(transport(), sampling_handler=logging_handler) as client:
        print("RESULT:", await call(client, "classify_sentiment",
                                    {"text": "Customer complaint: the invoice is wrong, I want a refund."}))

    # ---------------------------------------------------------------- PART 3
    banner("PART 3: human approval - the user says NO")
    async with Client(transport(), sampling_handler=make_approval_handler(False)) as client:
        print("RESULT:", await call(client, "suggest_title", {"note_id": "n3"}))
    banner("PART 3b: human approval - the user says YES")
    async with Client(transport(), sampling_handler=make_approval_handler(True)) as client:
        print("RESULT:", await call(client, "suggest_title", {"note_id": "n3"}))

    # ---------------------------------------------------------------- PART 4
    banner("PART 4: client with NO sampling support")
    async with Client(transport()) as client:
        print("RESULT:", await call(client, "suggest_title", {"note_id": "n3"}))

    # ---------------------------------------------------------------- PART 5
    banner("PART 5: server-side budget (max 2 model calls per tool call)")
    call_count = 0

    async def counting_handler(messages, params, ctx):
        nonlocal call_count
        call_count += 1
        model = choose_model(params.modelPreferences)
        text = await asyncio.to_thread(
            call_groq, messages[-1].content.text, None, params.maxTokens or 60, params.temperature or 0.2, model,
        )
        return CreateMessageResult(role="assistant", content=TextContent(type="text", text=text),
                                   model=model, stopReason="endTurn")

    async with Client(transport(), sampling_handler=counting_handler) as client:
        out = await call(client, "summarize_all")
        print("RESULT:", out)
        print("handler was called", call_count, "times (real API calls)")


if __name__ == "__main__":
    asyncio.run(main())
