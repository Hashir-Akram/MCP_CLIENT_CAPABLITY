"""
04_base_client.py
=================
Tests 03_base_server_prompts.py with the OFFICIAL `mcp` client
(no FastMCP) so you see the raw protocol objects.

Run:  python 04_base_client.py
"""

import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.shared.exceptions import MCPError

SERVER = Path(__file__).parent / "03_base_server_prompts.py"


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with Client(params) as client:
        # 1. CAPABILITY NEGOTIATION -----------------------------------------
        print("server prompts capability:", client.server_capabilities.prompts)

        # 2. DISCOVERY -------------------------------------------------------
        listing = await client.list_prompts()
        print("\nprompts/list:")
        for p in listing.prompts:
            args = ", ".join(f"{a.name}{'*' if a.required else ''}" for a in (p.arguments or []))
            print(f"  {p.name:<16} ({args})  {p.description}")

        # 3. GET (render) ----------------------------------------------------
        print("\nprompts/get summarize_text  style=tweet")
        result = await client.get_prompt(
            "summarize_text",
            {"text": "MCP has tools, resources and prompts. Prompts are user-controlled.",
             "style": "tweet"},
        )
        print("  description:", result.description)
        for m in result.messages:
            print(f"  [{m.role}] {m.content.text}")

        print("\nprompts/get translate  language=Hindi")
        result = await client.get_prompt("translate", {"text": "Good morning", "language": "Hindi"})
        print(f"  [{result.messages[0].role}] {result.messages[0].content.text}")

        # 4. ERROR PATHS -------------------------------------------------------
        for label, name, args in [
            ("missing argument", "translate", {"text": "hi"}),
            ("bad style value", "summarize_text", {"text": "x", "style": "poem"}),
            ("unknown prompt", "nope", {}),
        ]:
            try:
                await client.get_prompt(name, args)
            except MCPError as exc:
                print(f"\n{label}: code {exc.code} -> {exc.message}")


if __name__ == "__main__":
    asyncio.run(main())
