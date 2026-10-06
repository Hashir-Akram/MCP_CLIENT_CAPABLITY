"""
03_sampling_client_mcpuse.py     (environment: requirements-classic.txt)
====================================================================
The SAME sampling idea with the MCP-USE client (the library used in your course),
calling REAL Groq models (groq.com - NOT xAI's Grok) instead of a simulated one.
Same two-tier model choice as 02_sampling_client_classic.py:

    openai/gpt-oss-120b   default (no stated preference) - the smarter model
    openai/gpt-oss-20b    used when the server asks for cheap/fast

MCP-USE option:   sampling_callback=<async function(context, params)>
The function must return a  CreateMessageResult  (or an ErrorData to refuse).

Set your key first (or put it in a .env file at the project root):
    Windows (PowerShell):  $env:GROQ_API_KEY = "gsk_..."
    macOS / Linux:         export GROQ_API_KEY="gsk_..."

Run:  python 03_sampling_client_mcpuse.py
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))          # picks up a .env anywhere above the cwd
os.environ["MCP_USE_ANONYMIZED_TELEMETRY"] = "false"         # keep the console clean

from groq import Groq                                          # noqa: E402
from mcp import types                                          # noqa: E402
from mcp_use import MCPClient                                  # noqa: E402

HERE = Path(__file__).parent.resolve()
CONFIG = {"mcpServers": {"notes": {
    "command": sys.executable,
    "args": [str(HERE / "01_sampling_server_classic.py")],
}}}

GROQ_MODEL_SMART = "openai/gpt-oss-120b"       # default: no stated preference -> use the best model
GROQ_MODEL_FAST = "openai/gpt-oss-20b"         # used when the server asks for cheap/fast

if not os.environ.get("GROQ_API_KEY"):
    raise SystemExit(
        "Set GROQ_API_KEY first - copy .env.example to .env at the project root "
        "and fill in your key, or:  $env:GROQ_API_KEY = 'gsk_...'"
    )

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])


def choose_model(prefs) -> str:
    if prefs is None:
        return GROQ_MODEL_SMART
    hints = [h.name for h in (prefs.hints or [])]
    if any(GROQ_MODEL_FAST in h or "20b" in h for h in hints) or (prefs.costPriority or 0) > 0.7:
        return GROQ_MODEL_FAST
    return GROQ_MODEL_SMART


def call_groq(prompt: str, system_prompt: str | None, max_tokens: int, temperature: float, model: str) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = groq_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max(max_tokens, 150),
        temperature=temperature,
        reasoning_effort="low",            # gpt-oss models: keep hidden reasoning short
    )
    return resp.choices[0].message.content.strip()


# 1. The sampling callback = "the AI model" of this client.
#    MCP-USE passes (context, params). params has messages, systemPrompt, maxTokens, ...
async def my_model(context, params: types.CreateMessageRequestParams):
    last = params.messages[-1].content.text
    model = choose_model(params.modelPreferences)
    print(f"   [callback] server asked: {last[:55]!r}...  max_tokens={params.maxTokens}, model={model}")

    answer = await asyncio.to_thread(
        call_groq, last, params.systemPrompt, params.maxTokens or 60, params.temperature or 0.2, model,
    )

    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text=answer),
        model=model,
        stopReason="endTurn",
    )


async def main() -> None:
    # 2. Give the callback to MCPClient
    client = MCPClient(CONFIG, sampling_callback=my_model)
    await client.create_all_sessions()
    session = client.get_session("notes")

    # 3. Call tools. The server will sample behind the scenes.
    for tool, args in [
        ("summarize_note", {"note_id": "n1"}),
        ("classify_sentiment", {"text": "Customer complaint: wrong total, I want a refund."}),
    ]:
        result = await session.call_tool(tool, args)
        print(f"{tool:<20} -> {result.content[0].text}")

    await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(main())
