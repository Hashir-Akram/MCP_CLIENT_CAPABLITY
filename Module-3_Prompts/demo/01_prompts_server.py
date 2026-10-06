"""
01_prompts_server.py
====================
TechNova Prompt Library - an MCP server that exposes PROMPTS
(reusable, parameterised message templates that the USER chooses).

Run it (STDIO):   python 01_prompts_server.py
Explore it:       python 02_prompts_client.py

  STEP 1  Simplest prompt          -> returns a str  (becomes ONE user message)
  STEP 2  Arguments                -> required vs optional, defaults, Literal choices
  STEP 3  Rich argument metadata   -> Annotated[..., Field(description=...)]
  STEP 4  Multi-message prompt     -> Message(role="user"/"assistant"), few-shot style
  STEP 5  Async prompt             -> fetches data before building the text
  STEP 6  Embedded resource        -> prompt that carries a document inside the message
  STEP 7  Name / title / tags      -> decorator arguments
  STEP 8  Duplicate handling       -> on_duplicate policy
"""

from pathlib import Path
from typing import Annotated, Literal

from mcp import types as mcp_types
from pydantic import Field

from fastmcp import FastMCP
from fastmcp.prompts import Message, PromptResult

DATA_DIR = (Path(__file__).parent / "data").resolve()

mcp = FastMCP(
    name="TechNova-Prompt-Library",
    instructions="Reusable prompt templates for engineering, HR and operations.",
    on_duplicate="error",          # STEP 8: refuse silent overwrites (see below)
)


# A resource we will EMBED inside a prompt in STEP 6 -------------------------
@mcp.resource("policy://leave", mime_type="text/markdown")
def leave_policy() -> str:
    return (DATA_DIR / "leave-policy.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# STEP 1 - SIMPLEST PROMPT
# ---------------------------------------------------------------------------
# * The decorator registers the function as a prompt named after the function.
# * The docstring becomes the prompt DESCRIPTION shown in the client's menu.
# * Returning a plain str => FastMCP wraps it in ONE message with role "user".
@mcp.prompt
def greet_new_joiner() -> str:
    """Write a warm welcome message for a new TechNova employee."""
    return (
        "Write a short, friendly welcome message for a new employee joining "
        "TechNova. Mention the onboarding guide and the buddy programme."
    )


# ---------------------------------------------------------------------------
# STEP 2 - ARGUMENTS: required, optional, defaults, restricted choices
# ---------------------------------------------------------------------------
# * Parameter WITHOUT default  => REQUIRED argument  (code)
# * Parameter WITH default     => OPTIONAL argument  (language, focus)
# * Literal[...]               => the allowed values are advertised to the client
@mcp.prompt
def code_review(
    code: str,
    language: str = "python",
    focus: Literal["bugs", "security", "performance", "readability"] = "bugs",
) -> str:
    """Review a code snippet with a chosen focus."""
    return (
        f"You are a senior {language} engineer. Review the code below.\n"
        f"Focus ONLY on: {focus}.\n"
        f"Give a numbered list of findings, each with a one-line fix.\n\n"
        f"```{language}\n{code}\n```"
    )


# ---------------------------------------------------------------------------
# STEP 3 - RICH ARGUMENT METADATA (for good UIs)
# ---------------------------------------------------------------------------
# MCP prompt arguments are STRINGS on the wire. For int/list/etc. the client
# sends text (JSON encoded) and FastMCP converts it back to your Python type.
# Annotated + Field(description=...) shows a help text next to the input box.
@mcp.prompt(title="Study Plan Generator")
def study_plan(
    topic: Annotated[str, Field(description="What the learner wants to study")],
    days: Annotated[int, Field(description="Number of days available (1-30)", ge=1, le=30)] = 5,
    skills: Annotated[list[str] | None, Field(description="Skills the learner already has")] = None,
) -> str:
    """Create a day-by-day study plan."""
    known = ", ".join(skills) if skills else "no prior knowledge"
    return (
        f"Create a {days}-day study plan for: {topic}.\n"
        f"The learner already knows: {known}.\n"
        f"For each day give: goal, 2 learning tasks, 1 mini-exercise."
    )


# ---------------------------------------------------------------------------
# STEP 4 - MULTI-MESSAGE PROMPT (roles + few-shot examples)
# ---------------------------------------------------------------------------
# Return PromptResult([...Message...]) to control EXACT roles and order.
# Here we "teach by example": one user/assistant pair, then the real request.
@mcp.prompt
def classify_ticket(ticket_text: str) -> PromptResult:
    """Classify a support ticket as billing, technical or account."""
    return PromptResult(
        [
            Message(
                "Classify support tickets into exactly one label: "
                "billing, technical, account. Reply with the label only.",
                role="user",
            ),
            Message("Understood. Send me the ticket.", role="assistant"),
            Message("Ticket: I was charged twice this month.", role="user"),
            Message("billing", role="assistant"),                  # worked example
            Message(f"Ticket: {ticket_text}", role="user"),         # the real one
        ],
        description="Few-shot ticket classifier",
    )


# ---------------------------------------------------------------------------
# STEP 5 - ASYNC PROMPT (do I/O before building the text)
# ---------------------------------------------------------------------------
# Prompts can be `async def` - useful when the text depends on a database,
# an API or a file. FastMCP awaits it for you.
@mcp.prompt
async def incident_summary(
    incident_id: str,
    audience: Literal["engineers", "executives"] = "executives",
) -> str:
    """Summarise an incident for a chosen audience (reads the incident record)."""
    path = DATA_DIR / f"incident-{incident_id}.txt"
    if not path.is_file():                                   # validate input!
        raise ValueError(f"Unknown incident: {incident_id}")
    record = path.read_text(encoding="utf-8")                 # (could be async I/O)
    style = (
        "plain business language, max 4 sentences, no jargon"
        if audience == "executives"
        else "technical detail, timeline, suspected root cause and next steps"
    )
    return f"Summarise this incident for {audience} in {style}.\n\n{record}"


# ---------------------------------------------------------------------------
# STEP 6 - EMBEDDED RESOURCE INSIDE A PROMPT
# ---------------------------------------------------------------------------
# A prompt message can carry a RESOURCE (document) as its content, so the
# host receives the instruction AND the data together.
#   Prompt  = how to ask      (user-chosen)
#   Resource = what to read   (app-loaded)   -> combined here
@mcp.prompt
def explain_leave_policy(employee_question: str) -> PromptResult:
    """Answer a leave question using the official leave policy document."""
    policy_text = (DATA_DIR / "leave-policy.md").read_text(encoding="utf-8")
    embedded = mcp_types.EmbeddedResource(
        type="resource",
        resource=mcp_types.TextResourceContents(
            uri="policy://leave", mime_type="text/markdown", text=policy_text
        ),
    )
    return PromptResult(
        [
            Message(
                "Answer ONLY from the policy document attached next. "
                "If the answer is not in it, say you don't know."
            ),
            Message(embedded),                                   # <- the document
            Message(f"Question: {employee_question}"),
        ]
    )


# ---------------------------------------------------------------------------
# STEP 7 - DECORATOR ARGUMENTS: name, title, description, tags
# ---------------------------------------------------------------------------
@mcp.prompt(
    name="standup_report",                      # public name (default: function name)
    title="Daily Stand-up Report",              # friendly label for menus
    description="Turn rough notes into a 3-part stand-up update.",
    tags={"engineering", "daily"},
)
def make_standup(notes: str) -> str:
    return (
        "Rewrite my notes as a stand-up update with three headings: "
        f"Yesterday, Today, Blockers.\n\nNotes:\n{notes}"
    )


# ---------------------------------------------------------------------------
# STEP 8 - DUPLICATES
# ---------------------------------------------------------------------------
# We created the server with on_duplicate="error". Registering a second prompt
# with the SAME name now raises immediately - see 02_prompts_client.py (PHASE 8)
# which demonstrates all four policies on throw-away servers.


if __name__ == "__main__":
    mcp.run(show_banner=False)       # STDIO
