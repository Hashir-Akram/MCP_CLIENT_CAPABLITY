"""
01_all_prompt_types_server.py
=============================
EVERY way to define a prompt, in ONE file. Simple language on purpose.

Big idea (read this first):
    A prompt = a NAME + some BLANKS (arguments) + a MESSAGE TEMPLATE.
    The user picks the name, fills the blanks, and the server returns ready-made
    MESSAGES. The server never talks to the AI model. The host does that.

The 3 families below:
    FAMILY A - "Write a function"     (decorator @mcp.prompt)        ways 1-11
    FAMILY B - "Build it as an object" (Prompt.from_function)         way 12
                                       (and the low-level server)     way 13
    FAMILY C - "Add, combine, hide"    (runtime add, mount, hide)     ways 14-16

Run:  python 02_all_prompt_types_client.py     (it starts this server for you)
"""

import base64
from pathlib import Path
from typing import Annotated, Literal

from mcp import types as mcp_types
from pydantic import Field

from fastmcp import Context, FastMCP
from fastmcp.prompts import Message, Prompt, PromptResult

DATA = (Path(__file__).parent / "data").resolve()

mcp = FastMCP("All-Prompt-Types", on_duplicate="error")


# A resource we use in ways 7 and 10 --------------------------------------
@mcp.resource("policy://leave", mime_type="text/markdown")
def leave_policy() -> str:
    return (DATA / "leave-policy.md").read_text(encoding="utf-8")


# ===========================================================================
# FAMILY A - WRITE A FUNCTION  (decorator @mcp.prompt)
# The function runs only when the user USES the prompt (prompts/get),
# never when the list of prompts is shown.
# ===========================================================================

# WAY 1 - SIMPLEST: no blanks, returns one piece of text -------------------
@mcp.prompt
def greet_new_joiner() -> str:
    """Write a welcome message for a new employee."""      # docstring = description
    return "Write a short, friendly welcome message for a new employee joining TechNova."


# WAY 2 - REQUIRED BLANK: no default value = the user MUST fill it ---------
@mcp.prompt
def summarize(text: str) -> str:
    """Summarise any text."""
    return f"Summarise the following text in 3 bullet points:\n\n{text}"


# WAY 3 - OPTIONAL BLANK: has a default value = the user MAY skip it -------
@mcp.prompt
def translate(text: str, language: str = "Hindi") -> str:
    """Translate text (default language: Hindi)."""
    return f"Translate to {language}. Reply with the translation only.\n\n{text}"


# WAY 4 - FIXED CHOICES: Literal lets only listed values through -----------
@mcp.prompt
def rewrite(text: str, tone: Literal["formal", "friendly", "short"] = "friendly") -> str:
    """Rewrite text in a chosen tone."""
    return f"Rewrite this text in a {tone} tone:\n\n{text}"


# WAY 5 - TYPED BLANKS WITH HELP TEXT AND LIMITS ---------------------------
# On the wire every blank is a STRING. FastMCP converts "3" -> 3 and
# '["a","b"]' -> ["a","b"] for you, and enforces the limits.
@mcp.prompt
def study_plan(
    topic: Annotated[str, Field(description="What the learner wants to study")],
    days: Annotated[int, Field(description="Days available (1-30)", ge=1, le=30)] = 5,
    skills: Annotated[list[str] | None, Field(description="Skills already known")] = None,
    include_quiz: Annotated[bool, Field(description="Add a quiz at the end?")] = False,
) -> str:
    """Create a day-by-day study plan."""
    known = ", ".join(skills) if skills else "nothing yet"
    quiz = " End with a 5-question quiz." if include_quiz else ""
    return f"Create a {days}-day study plan for {topic}. Learner knows: {known}.{quiz}"


# WAY 6 - SEVERAL MESSAGES WITH ROLES (few-shot examples) ------------------
# Return PromptResult([...]) or a list of Message(...). Roles: user / assistant.
@mcp.prompt
def classify_ticket(ticket_text: str) -> PromptResult:
    """Classify a support ticket (few-shot)."""
    return PromptResult(
        [
            Message("Classify tickets as: billing, technical, account. Label only.", role="user"),
            Message("Understood. Send me the ticket.", role="assistant"),
            Message("Ticket: I was charged twice.", role="user"),
            Message("billing", role="assistant"),            # a worked example
            Message(f"Ticket: {ticket_text}", role="user"),   # the real question
        ],
        description="Few-shot ticket classifier",
    )


# WAY 7 - A DOCUMENT INSIDE THE PROMPT (embedded resource) -----------------
@mcp.prompt
def leave_question(question: str) -> PromptResult:
    """Answer a leave question using the policy document."""
    doc = mcp_types.EmbeddedResource(
        type="resource",
        resource=mcp_types.TextResourceContents(
            uri="policy://leave", mime_type="text/markdown",
            text=(DATA / "leave-policy.md").read_text(encoding="utf-8")),
    )
    return PromptResult([
        Message("Answer ONLY from the attached policy. If unknown, say you don't know."),
        Message(doc),
        Message(f"Question: {question}"),
    ])


# WAY 8 - AN IMAGE INSIDE THE PROMPT ---------------------------------------
@mcp.prompt
def describe_logo() -> list[Message]:
    """Ask the model to describe the company logo."""
    image = mcp_types.ImageContent(
        type="image", mime_type="image/png",
        data=base64.b64encode((DATA / "logo.png").read_bytes()).decode())
    return [Message("Describe this logo in one sentence."), Message(image)]


# WAY 9 - ASYNC PROMPT: use async def when you must wait for data ----------
@mcp.prompt
async def incident_summary(
    incident_id: str, audience: Literal["engineers", "executives"] = "executives"
) -> str:
    """Summarise an incident (reads the incident record)."""
    path = DATA / f"incident-{incident_id}.txt"
    if not path.is_file():                                   # always check the blank
        raise ValueError(f"Unknown incident: {incident_id}")
    return f"Summarise this incident for {audience}:\n\n{path.read_text(encoding='utf-8')}"


# WAY 10 - READ A RESOURCE FROM INSIDE THE PROMPT (using ctx) --------------
# The prompt asks the SERVER itself for a resource while it builds the text.
@mcp.prompt
async def policy_helper(question: str, ctx: Context) -> str:
    """Answer a question using the live leave policy resource."""
    result = await ctx.read_resource("policy://leave")
    policy = result.contents[0].content
    return f"Using only this policy:\n{policy}\n\nAnswer: {question}"


# WAY 11 - DECORATOR OPTIONS: name, title, description, tags, version, meta
@mcp.prompt(
    name="standup_report",                       # public name (function is make_standup)
    title="Daily Stand-up Report",               # friendly label in menus
    description="Turn rough notes into a 3-part stand-up update.",
    tags={"engineering", "daily"},               # labels for grouping / hiding
    version="2",                                 # version label
    meta={"team": "engineering"},                # extra info for hosts
)
def make_standup(notes: str) -> str:
    return f"Rewrite as a stand-up update (Yesterday, Today, Blockers):\n\n{notes}"


# ===========================================================================
# FAMILY B - BUILD IT AS AN OBJECT (no decorator)
# ===========================================================================

# WAY 12 - Prompt.from_function + mcp.add_prompt: great for LOOPS and CONFIG
# Imagine these templates live in a database or YAML file.
TEMPLATES = {
    "thank_you_note": ("Write a thank-you note to a colleague.", "Write a warm thank-you note about: {text}"),
    "bug_report": ("Turn rough notes into a bug report.", "Write a clear bug report (steps, expected, actual) from: {text}"),
}


def _make_prompt(name: str, description: str, template: str) -> Prompt:
    def render(text: str) -> str:
        return template.format(text=text)
    return Prompt.from_function(render, name=name, description=description, tags={"generated"})


for _name, (_desc, _tpl) in TEMPLATES.items():
    mcp.add_prompt(_make_prompt(_name, _desc, _tpl))

# WAY 13 - LOW-LEVEL (base server): see ../Module-3_Prompts/demo/03_base_server_prompts.py
# There you write the catalogue (names + blanks) and the "get" handler by hand.


# ===========================================================================
# FAMILY C - ADD, COMBINE, HIDE
# ===========================================================================

# WAY 14 - ADD A PROMPT WHILE THE SERVER RUNS ------------------------------
@mcp.tool
async def publish_prompt(name: str, template: str, ctx: Context) -> str:
    """Create a new one-blank prompt. Use {text} inside the template."""
    mcp.add_prompt(_make_prompt(name, f"Runtime prompt: {name}", template))
    await ctx.send_notification(mcp_types.PromptListChangedNotification())   # tell clients
    return f"created prompt {name}"


# WAY 15 - MOUNT: plug a whole other server into this one ------------------
hr = FastMCP("hr")


@hr.prompt
def welcome_email(name: str) -> str:
    """Write a welcome email."""
    return f"Write a welcome email for {name}."


mcp.mount(hr, namespace="hr")                  # name becomes  hr_welcome_email


# WAY 16 - HIDE A PROMPT -----------------------------------------------------
@mcp.prompt(tags={"internal"})
def salary_review(employee: str) -> str:
    """Internal only."""
    return f"Prepare a salary review for {employee}."


mcp.disable(tags={"internal"})                 # not listed, cannot be used


if __name__ == "__main__":
    mcp.run(show_banner=False)
