"""
02_all_prompt_types_client.py
=============================
Starts 01_all_prompt_types_server.py and tries EVERY way, one by one.
Run:  python 02_all_prompt_types_client.py
"""

import asyncio
import json
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.messages import MessageHandler
from fastmcp.client.transports import StdioTransport

SERVER = Path(__file__).parent / "01_all_prompt_types_server.py"


class Watch(MessageHandler):
    """Receives 'the prompt list changed' notices from the server."""

    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    async def on_prompt_list_changed(self, message) -> None:
        self.count += 1
        print("  [notice from server] prompts/list_changed")


def show(label: str, result) -> None:
    """Print each message: role + what it carries."""
    print(f"\n  {label}")
    for m in result.messages:
        c = m.content
        if c.type == "text":
            body = c.text.replace("\n", " | ")[:95]
        elif c.type == "image":
            body = f"<image {c.mime_type}, {len(c.data)} base64 chars>"
        elif c.type == "resource":
            body = f"<embedded document {c.resource.uri}>"
        else:
            body = f"<{c.type}>"
        print(f"     [{m.role:<9}] {body}")


async def main() -> None:
    watch = Watch()
    async with Client(StdioTransport(sys.executable, [str(SERVER)]), message_handler=watch) as client:

        print("\n=== LIST: prompts the user can pick (* = required blank) ===")
        for p in await client.list_prompts():
            blanks = ", ".join(f"{a.name}{'*' if a.required else ''}" for a in (p.arguments or [])) or "-"
            print(f"  {p.name:<18} ({blanks})")

        print("\n=== FAMILY A: write a function ===")
        show("1  simplest", await client.get_prompt("greet_new_joiner"))
        show("2  required blank", await client.get_prompt("summarize", {"text": "MCP has 3 features."}))
        show("3a optional blank skipped (default Hindi)", await client.get_prompt("translate", {"text": "Good morning"}))
        show("3b optional blank given (Tamil)", await client.get_prompt("translate", {"text": "Good morning", "language": "Tamil"}))
        show("4  fixed choice tone=formal", await client.get_prompt("rewrite", {"text": "send me the file", "tone": "formal"}))
        show("5  typed blanks (int, list, bool)", await client.get_prompt(
            "study_plan", {"topic": "MCP", "days": "3", "skills": json.dumps(["Python"]), "include_quiz": "true"}))
        show("6  several messages with roles", await client.get_prompt("classify_ticket", {"ticket_text": "App crashes"}))
        show("7  document inside the prompt", await client.get_prompt("leave_question", {"question": "How many sick days?"}))
        show("8  image inside the prompt", await client.get_prompt("describe_logo"))
        show("9  async (reads incident file)", await client.get_prompt("incident_summary", {"incident_id": "INC-204"}))
        show("10 prompt reads a resource (ctx)", await client.get_prompt("policy_helper", {"question": "Carry-forward limit?"}))
        show("11 decorator options (renamed)", await client.get_prompt("standup_report", {"notes": "fixed login bug"}))
        sp = next(p for p in await client.list_prompts() if p.name == "standup_report")
        print(f"     title={sp.title!r}  meta={getattr(sp, 'meta', None)}")

        print("\n=== FAMILY B: object and loop ===")
        show("12 made with Prompt.from_function", await client.get_prompt("thank_you_note", {"text": "your help on the release"}))
        show("12 made with Prompt.from_function", await client.get_prompt("bug_report", {"text": "login button does nothing"}))

        print("\n=== FAMILY C: add, combine, hide ===")
        before = {p.name for p in await client.list_prompts()}
        await client.call_tool("publish_prompt", {"name": "joke", "template": "Tell a short joke about {text}."})
        await asyncio.sleep(0.3)
        after = {p.name for p in await client.list_prompts()}
        print(f"  14 runtime add -> new prompt: {after - before}   notices seen: {watch.count}")
        show("14 use the new prompt", await client.get_prompt("joke", {"text": "Python"}))
        show("15 mounted from the hr server (name has prefix)", await client.get_prompt("hr_welcome_email", {"name": "Meera"}))
        print("\n  16 hidden prompt in list?", "salary_review" in after)
        try:
            await client.get_prompt("salary_review", {"employee": "X"})
            print("  16 using hidden prompt -> worked (unexpected)")
        except Exception as exc:                                    # noqa: BLE001
            print(f"  16 using hidden prompt -> blocked: {type(exc).__name__}")

        print("\n=== ERRORS ===")
        for label, name, args in [
            ("missing required blank", "summarize", {}),
            ("choice not allowed", "rewrite", {"text": "x", "tone": "angry"}),
            ("number out of range", "study_plan", {"topic": "x", "days": "99"}),
            ("unknown prompt", "nope", {}),
        ]:
            try:
                await client.get_prompt(name, args)
                print(f"  {label:<26} -> worked (unexpected)")
            except Exception as exc:                                # noqa: BLE001
                print(f"  {label:<26} -> {type(exc).__name__}: {str(exc).splitlines()[0][:70]}")


if __name__ == "__main__":
    asyncio.run(main())
