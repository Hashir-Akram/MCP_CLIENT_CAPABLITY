"""
05_sampling_client_modern.py     (environment: requirements-modern.txt)
====================================================================
Client for 04_sampling_server_modern.py.

Notice: the sampling handler is the SAME function style as before.
The FastMCP client answers the server's "input required" and retries for you.

WAY A's "client model" and WAY B's "server model" are both REAL Groq calls
(groq.com - NOT xAI's Grok), running independently - the client never sees
which model the server used for WAY B, and vice versa.

Set your key first (or put it in a .env file at the project root):
    Windows (PowerShell):  $env:GROQ_API_KEY = "gsk_..."
    macOS / Linux:         export GROQ_API_KEY="gsk_..."

Run:  python 05_sampling_client_modern.py
"""

import asyncio
import os
import sys
import warnings
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from groq import Groq
from mcp.types import CreateMessageResult, TextContent

warnings.simplefilter("ignore")
load_dotenv(find_dotenv(usecwd=True))          # picks up a .env anywhere above the cwd

SERVER = Path(__file__).parent / "04_sampling_server_modern.py"
GROQ_MODEL = "openai/gpt-oss-20b"              # the CLIENT's own model choice for WAY A

if not os.environ.get("GROQ_API_KEY"):
    raise SystemExit(
        "Set GROQ_API_KEY first - copy .env.example to .env at the project root "
        "and fill in your key, or:  $env:GROQ_API_KEY = 'gsk_...'"
    )

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])


def call_groq(prompt: str, system_prompt: str | None, max_tokens: int, temperature: float) -> str:
    # gpt-oss-20b is a REASONING model: reasoning_effort="low" keeps hidden
    # chain-of-thought short so max_tokens isn't eaten before any visible
    # content is produced.
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    resp = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=max(max_tokens, 150),
        temperature=temperature,
        reasoning_effort="low",
    )
    return resp.choices[0].message.content.strip()


async def my_model(messages, params, ctx):
    prompt = messages[-1].content.text
    print(f"   [client model] asked: {prompt[:45]!r}...  max_tokens={params.max_tokens}, temperature={params.temperature}")
    text = await asyncio.to_thread(
        call_groq, prompt, params.system_prompt, params.max_tokens or 60, params.temperature or 0.2,
    )
    print(f"   -> Groq ({GROQ_MODEL}) answers: {text!r}")
    return CreateMessageResult(role="assistant", content=TextContent(type="text", text=text),
                               model=GROQ_MODEL, stop_reason="endTurn")


async def main() -> None:
    transport = StdioTransport(command=sys.executable, args=[str(SERVER)])
    async with Client(transport, sampling_handler=my_model) as client:
        print("protocol version negotiated:", client.protocol_version)

        print("\nWAY A  summarize_via_sampling  (the CLIENT's real Groq model)")
        res = await client.call_tool("summarize_via_sampling", {"note_id": "n1"})
        print("   ->", res.content[0].text)

        print("\nWAY B  summarize_direct        (the SERVER's own real Groq model; no client involvement)")
        res = await client.call_tool("summarize_direct", {"note_id": "n1"})
        print("   ->", res.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
