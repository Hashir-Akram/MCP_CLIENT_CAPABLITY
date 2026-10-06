"""
02_prompts_client.py
====================
Walks through the PROMPT lifecycle against 01_prompts_server.py:

  PHASE 1  Connect
  PHASE 2  Discover   -> prompts/list  (names, descriptions, ARGUMENTS)
  PHASE 3  Render     -> prompts/get   (fill arguments -> receive messages)
  PHASE 4  Typed args -> ints / lists travel as JSON strings
  PHASE 5  Embedded resource inside a prompt message
  PHASE 6  Errors     -> missing arg, bad type, unknown prompt, bad value
  PHASE 7  Use        -> convert MCP messages into an LLM chat request
  PHASE 8  Duplicates -> the four on_duplicate policies

Run:  python 02_prompts_client.py
"""

import asyncio
import json
import sys
from pathlib import Path

from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport

SERVER = Path(__file__).parent / "01_prompts_server.py"


def banner(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def show_messages(result) -> None:
    """Pretty-print the messages of a GetPromptResult."""
    for m in result.messages:
        c = m.content
        if c.type == "text":
            body = c.text.replace("\n", "\n            ")
            print(f"  [{m.role:<9}] {body}")
        elif c.type == "resource":
            print(f"  [{m.role:<9}] <embedded resource {c.resource.uri} "
                  f"({c.resource.mime_type}, {len(c.resource.text)} chars)>")


async def main() -> None:
    transport = StdioTransport(command=sys.executable, args=[str(SERVER)])
    async with Client(transport) as client:                      # PHASE 1
        banner("PHASE 1: connected")

        # PHASE 2 ---------------------------------------------------------
        banner("PHASE 2: prompts/list")
        for p in await client.list_prompts():
            args = ", ".join(
                f"{a.name}{'*' if a.required else ''}" for a in (p.arguments or [])
            ) or "(no arguments)"
            print(f"  {p.name:<20} {args:<34} {p.description or ''}")
        print("  (* = required argument)")

        banner("PHASE 2b: one prompt in detail  (code_review)")
        p = next(x for x in await client.list_prompts() if x.name == "code_review")
        for a in p.arguments:
            print(f"  - {a.name:<9} required={a.required!s:<5} {str(a.description)[:70]}")

        # PHASE 3 ---------------------------------------------------------
        banner("PHASE 3a: prompts/get  greet_new_joiner  (no args)")
        show_messages(await client.get_prompt("greet_new_joiner"))

        banner("PHASE 3b: prompts/get  code_review  (optional args omitted)")
        show_messages(await client.get_prompt("code_review", {"code": "def f(x): return x/0"}))

        banner("PHASE 3c: prompts/get  code_review  (optional args supplied)")
        r = await client.get_prompt(
            "code_review",
            {"code": "SELECT * FROM users WHERE id=" + "'" + "' + uid",
             "language": "sql", "focus": "security"},
        )
        show_messages(r)

        banner("PHASE 3d: multi-message prompt  classify_ticket")
        r = await client.get_prompt("classify_ticket", {"ticket_text": "App crashes on login"})
        print("  description:", r.description)
        show_messages(r)

        banner("PHASE 3e: async prompt  incident_summary")
        show_messages(await client.get_prompt(
            "incident_summary", {"incident_id": "INC-204", "audience": "executives"}))

        # PHASE 4 ---------------------------------------------------------
        banner("PHASE 4: typed arguments travel as strings (JSON for non-str)")
        r = await client.get_prompt(
            "study_plan",
            {"topic": "MCP prompts", "days": "3", "skills": json.dumps(["Python", "APIs"])},
        )
        show_messages(r)

        # PHASE 5 ---------------------------------------------------------
        banner("PHASE 5: embedded resource inside a prompt")
        r = await client.get_prompt(
            "explain_leave_policy", {"employee_question": "How many sick days do I get?"})
        show_messages(r)

        # PHASE 6 ---------------------------------------------------------
        banner("PHASE 6: error handling")
        cases = [
            ("missing required arg", "code_review", {}),
            ("bad type for int",     "study_plan", {"topic": "x", "days": "abc"}),
            ("out of range (le=30)", "study_plan", {"topic": "x", "days": "99"}),
            ("unknown prompt",       "does_not_exist", {}),
            ("bad business value",   "incident_summary", {"incident_id": "INC-999"}),
        ]
        for label, name, args in cases:
            try:
                await client.get_prompt(name, args)
                print(f"  {label:<22} -> UNEXPECTEDLY OK")
            except Exception as exc:                              # noqa: BLE001
                print(f"  {label:<22} -> {type(exc).__name__}: {str(exc).splitlines()[0][:80]}")

        # PHASE 7 ---------------------------------------------------------
        banner("PHASE 7: from MCP messages to an LLM request")
        rendered = await client.get_prompt(
            "classify_ticket", {"ticket_text": "I cannot reset my password"})
        llm_messages = [
            {"role": m.role, "content": m.content.text}
            for m in rendered.messages
            if m.content.type == "text"
        ]
        print("  Send this list to ANY chat-completion style API:")
        print(json.dumps(llm_messages, indent=2))
        print("  (The final message is the one the model must answer.)")

    # PHASE 8 ---------------------------------------------------------------
    banner("PHASE 8: duplicate prompt names - the four on_duplicate policies")
    for policy in ("error", "warn", "replace", "ignore"):
        server = FastMCP("dup-demo", on_duplicate=policy)

        @server.prompt(name="hello")
        def first() -> str:
            return "FIRST version"

        try:
            @server.prompt(name="hello")
            def second() -> str:
                return "SECOND version"
        except ValueError as exc:
            print(f"  on_duplicate={policy:<8} -> raised ValueError: {str(exc)[:45]}")
            continue
        async with Client(server) as c:
            winner = (await c.get_prompt("hello")).messages[0].content.text
        print(f"  on_duplicate={policy:<8} -> client receives: {winner}")


if __name__ == "__main__":
    asyncio.run(main())
