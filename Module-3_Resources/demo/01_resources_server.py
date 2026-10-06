"""
01_resources_server.py
======================
TechNova Knowledge Hub - an MCP server that exposes RESOURCES (read-only context).

Run it (STDIO):      python 01_resources_server.py
Inspect it:          python 02_resources_client.py

Covers every concept in the Resources lesson:
  STEP 1  Static resource            -> @mcp.resource("config://app/settings")
  STEP 2  Dynamic resource           -> function re-runs on EVERY read
  STEP 3  Resource templates         -> URI parameters {emp_id}, {service}/{date}
  STEP 4  Wildcard template          -> {path*} (multi-segment paths)
  STEP 5  Resource classes           -> TextResource / FileResource / BinaryResource / DirectoryResource
  STEP 6  Annotations, tags, titles  -> metadata that helps hosts decide what to show / load
  STEP 7  Runtime registration       -> a TOOL adds a new resource while the server is running
"""

from datetime import datetime, timezone
from pathlib import Path

from mcp import types as mcp_types

from fastmcp import Context, FastMCP
from fastmcp.resources import (
    BinaryResource,
    DirectoryResource,
    FileResource,
    TextResource,
)

# ---------------------------------------------------------------------------
# 0. Server + data location
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="TechNova-Knowledge-Hub",
    instructions="Read-only company knowledge: handbook, logs, employees, config.",
)

DATA_DIR = (Path(__file__).parent / "data").resolve()   # absolute path = safer


# ---------------------------------------------------------------------------
# STEP 1 - STATIC RESOURCE (fixed URI, fixed meaning)
# ---------------------------------------------------------------------------
# * URI scheme "config://" is a CUSTOM scheme - perfectly valid in MCP.
# * Returning a dict -> FastMCP serialises it to JSON text automatically.
# * mime_type tells the host how to interpret the bytes.
@mcp.resource(
    "config://app/settings",
    name="app_settings",
    title="Application Settings",
    description="Non-secret runtime settings of the TechNova platform.",
    mime_type="application/json",
    tags={"config", "public"},
)
def app_settings() -> dict:
    return {
        "app": "TechNova Platform",
        "version": "2.4.0",
        "region": "ap-south-1",
        "features": {"dark_mode": True, "beta_search": False},
        # NEVER put secrets (API keys, passwords) in a resource!
    }


# ---------------------------------------------------------------------------
# STEP 2 - DYNAMIC RESOURCE (same URI, DIFFERENT content each read)
# ---------------------------------------------------------------------------
# The function body runs LAZILY - only when a client calls resources/read.
# Listing the resource does NOT execute this function.
@mcp.resource(
    "status://server/health",
    name="server_health",
    description="Live health snapshot (recomputed on every read).",
    mime_type="application/json",
    tags={"live", "ops"},
)
def server_health() -> dict:
    return {
        "status": "healthy",
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "uptime_check": "ok",
    }


# ---------------------------------------------------------------------------
# STEP 3 - RESOURCE TEMPLATES (parameterised URIs = "structured access")
# ---------------------------------------------------------------------------
# {emp_id} in the URI MUST match the function parameter name.
# The client sends   employee://E102/profile   -> emp_id="E102"
EMPLOYEES = {
    "E101": {"name": "Asha Rao", "role": "Backend Engineer", "team": "Payments"},
    "E102": {"name": "Ravi Kumar", "role": "SRE", "team": "Platform"},
    "E103": {"name": "Meera Iyer", "role": "Data Scientist", "team": "Insights"},
}


@mcp.resource(
    "employee://{emp_id}/profile",
    name="employee_profile",
    description="Public profile of an employee by ID (e.g. E101).",
    mime_type="application/json",
    tags={"hr"},
)
def employee_profile(emp_id: str) -> dict:
    if emp_id not in EMPLOYEES:
        # Raising an error => client receives a JSON-RPC error for this read
        raise ValueError(f"Unknown employee id: {emp_id}")
    return {"id": emp_id, **EMPLOYEES[emp_id]}


# Template with TWO parameters: logs://payments/2026-10-04
@mcp.resource(
    "logs://{service}/{date}",
    name="service_logs",
    description="Daily log file for a service (service = payments|auth, date = YYYY-MM-DD).",
    mime_type="text/plain",
    tags={"ops", "logs"},
)
def service_logs(service: str, date: str) -> str:
    # {service} and {date} come from the URI - treat them as UNTRUSTED input.
    if service not in {"payments", "auth"}:
        raise ValueError(f"Unknown service: {service}")
    log_file = DATA_DIR / "logs" / f"{service}-{date}.log"
    if not log_file.is_file():
        raise FileNotFoundError(f"No log for {service} on {date}")
    return log_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# STEP 4 - WILDCARD TEMPLATE  {path*}  (matches slashes too)
# ---------------------------------------------------------------------------
# kb://handbook/leave-policy.md  -> path="handbook/leave-policy.md"
# FastMCP 4 screens template params for "../", absolute paths and null bytes
# BEFORE this function runs (ResourceSecurity). We still resolve + check
# ourselves = defence in depth.
@mcp.resource(
    "kb://{path*}",
    name="knowledge_base_file",
    description="Any markdown/text file under the knowledge base folder.",
    mime_type="text/markdown",
    tags={"docs"},
)
def kb_file(path: str) -> str:
    target = (DATA_DIR / path).resolve()
    if DATA_DIR not in target.parents:                 # blocks path traversal
        raise PermissionError("Access outside the knowledge base is not allowed")
    if not target.is_file():
        raise FileNotFoundError(f"Not found: {path}")
    return target.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# STEP 5 - RESOURCE CLASSES (no decorator, you build the object yourself)
# ---------------------------------------------------------------------------
# 5a. TextResource - content already in memory
mcp.add_resource(
    TextResource(
        uri="text://welcome",
        name="welcome_banner",
        description="Static welcome text.",
        text="Welcome to the TechNova Knowledge Hub!",
    )
)

# 5b. FileResource - reads a file from disk on each read (absolute path REQUIRED)
mcp.add_resource(
    FileResource(
        uri=f"file://{(DATA_DIR / 'release-notes.txt').as_posix()}",
        path=DATA_DIR / "release-notes.txt",
        name="release_notes",
        description="Latest release notes.",
        mime_type="text/plain",
        tags={"docs"},
    )
)

# 5c. BinaryResource / FileResource with is_binary=True - images, PDFs, ...
#     Binary data travels as a base64 "blob" in the MCP response.
mcp.add_resource(
    FileResource(
        uri="image://company/logo",
        path=DATA_DIR / "logo.png",
        name="company_logo",
        description="Company logo (PNG).",
        mime_type="image/png",
        is_binary=True,
    )
)
mcp.add_resource(
    BinaryResource(
        uri="binary://demo/bytes",
        name="demo_bytes",
        description="A few raw bytes to show base64 blobs.",
        data=b"\x00\x01\x02MCP",
        mime_type="application/octet-stream",
    )
)

# 5d. DirectoryResource - lists files in a folder as JSON
mcp.add_resource(
    DirectoryResource(
        uri="dir://handbook",
        path=DATA_DIR / "handbook",
        name="handbook_index",
        description="List of all handbook files.",
        recursive=False,
    )
)


# ---------------------------------------------------------------------------
# STEP 6 - ANNOTATIONS (hints for the HOST, not enforced by the server)
# ---------------------------------------------------------------------------
#   audience : who is it for?  ["user"], ["assistant"] or both
#   priority : 0.0 (optional) -> 1.0 (must include)
@mcp.resource(
    "policy://security/summary",
    name="security_policy",
    title="Security Policy (Summary)",
    description="Must-read security rules for the AI assistant.",
    mime_type="text/markdown",
    annotations={"audience": ["user", "assistant"], "priority": 1.0},
    tags={"policy"},
)
def security_policy() -> str:
    return (DATA_DIR / "handbook" / "security.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# STEP 7 - RUNTIME REGISTRATION + list_changed NOTIFICATION
# ---------------------------------------------------------------------------
# A TOOL (model-controlled action) creates a NEW resource (app-controlled data).
# Afterwards we tell connected clients: "the resource list changed - re-list!"
@mcp.tool
async def publish_report(slug: str, body: str, ctx: Context) -> str:
    """Publish a text report as a new readable resource: report://<slug>."""
    uri = f"report://{slug}"
    mcp.add_resource(
        TextResource(
            uri=uri,
            name=f"report_{slug}",
            description=f"Report published at runtime: {slug}",
            text=body,
        )
    )
    # -> JSON-RPC notification: notifications/resources/list_changed
    await ctx.send_notification(mcp_types.ResourceListChangedNotification())
    return f"Published {uri}"


if __name__ == "__main__":
    mcp.run(show_banner=False)   # default transport = STDIO
