"""
01_all_resource_types_server.py
===============================
EVERY way to define a resource, in ONE file. Simple language on purpose.

Big idea (read this first):
    A resource has TWO separate things:
      1. its ADDRESS  (the URI, like  employee://E101/profile)  -> the name on the door
      2. its SOURCE   (where the content comes from)            -> the room behind the door
    The address is just a label. It is NOT always a website link.
    The source can be: text in code, a function, a file, a folder, a website...

The 3 families below:
    FAMILY A - "Write a function"     (decorator @mcp.resource)      ways 1-7
    FAMILY B - "Use a ready-made box"  (resource classes)             ways 8-13
    FAMILY C - "Add or combine"        (runtime add, mount, hide)     ways 14-16

Run:  python 02_all_resource_types_client.py     (it starts this server for you)
"""

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from fastmcp import Context, FastMCP
from fastmcp.resources import (
    BinaryResource,
    DirectoryResource,
    FileResource,
    FunctionResource,
    HttpResource,
    ResourceContent,
    ResourceResult,
    TextResource,
)
from mcp import types as mcp_types

DATA = (Path(__file__).parent / "data").resolve()

mcp = FastMCP("All-Resource-Types", on_duplicate="error")


# ===========================================================================
# FAMILY A - WRITE A FUNCTION  (decorator)
# The function does NOT run when the client LISTS resources.
# It runs only when someone READS the resource.
# ===========================================================================

# WAY 1 - STATIC: one fixed address, content written in a function --------
@mcp.resource("config://app/settings", mime_type="application/json")
def settings() -> dict:
    """Fixed address. Content is the same every time."""
    return {"app": "TechNova", "version": "2.4.0"}


# WAY 2 - DYNAMIC: one fixed address, content CHANGES on each read --------
@mcp.resource("status://clock", mime_type="application/json")
def clock() -> dict:
    """Same address, but the answer is different every time you read it."""
    return {"utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# WAY 3 - TEMPLATE: the address has a BLANK {emp_id} -----------------------
# Server cannot list 10,000 employees, so it lists the PATTERN instead.
EMPLOYEES = {"E101": "Asha Rao", "E102": "Ravi Kumar"}


@mcp.resource("employee://{emp_id}/profile", mime_type="application/json")
def employee(emp_id: str) -> dict:
    if emp_id not in EMPLOYEES:
        raise ValueError(f"Unknown employee: {emp_id}")
    return {"id": emp_id, "name": EMPLOYEES[emp_id]}


# WAY 4 - TEMPLATE WITH TWO BLANKS ----------------------------------------
@mcp.resource("report://{year}/{month}", mime_type="text/plain")
def monthly_report(year: str, month: str) -> str:
    return f"Sales report for {month}/{year}: 120 orders."


# WAY 5 - WILDCARD {path*}: the blank may contain slashes ------------------
# Powerful but risky: always check the final path stays inside your folder.
@mcp.resource("docs://{path*}", mime_type="text/markdown")
def doc_file(path: str) -> str:
    target = (DATA / "docs" / path).resolve()
    if (DATA / "docs").resolve() not in target.parents:
        raise PermissionError("Outside the docs folder")
    if not target.is_file():
        raise FileNotFoundError(path)
    return target.read_text(encoding="utf-8")


# WAY 6 - OPTIONAL SETTINGS after a ?  ({?limit,lang}) ---------------------
# search://mcp               -> uses defaults
# search://mcp?limit=5&lang=hi -> overrides them
@mcp.resource("search://{topic}{?limit,lang}", mime_type="application/json")
def search(topic: str, limit: int = 3, lang: str = "en") -> dict:
    return {"topic": topic, "limit": limit, "lang": lang}


# WAY 7 - DIFFERENT RETURN TYPES (what the function gives back) ------------
@mcp.resource("demo://text", mime_type="text/plain")
def r_text() -> str:                       # str  -> text
    return "plain text"


@mcp.resource("demo://json", mime_type="application/json")
def r_json() -> dict:                      # dict/list -> JSON text (automatic)
    return {"ok": True, "items": [1, 2, 3]}


@mcp.resource("demo://bytes", mime_type="application/octet-stream")
def r_bytes() -> bytes:                    # bytes -> binary (sent as base64 "blob")
    return b"\x00\x01\x02MCP"


@mcp.resource("demo://multi", mime_type="text/plain")
def r_multi() -> ResourceResult:           # several parts in ONE resource
    return ResourceResult([
        ResourceContent("Summary: sales up 18%.", mime_type="text/plain"),
        ResourceContent({"sales_growth_percent": 18}),
    ])


# ===========================================================================
# FAMILY B - READY-MADE BOXES (resource classes). No function needed.
# Register them with  mcp.add_resource(...)
# ===========================================================================

# WAY 8 - TextResource: the text is already inside the box ----------------
mcp.add_resource(TextResource(
    uri="text://welcome", name="welcome", text="Welcome to TechNova!"))

# WAY 9 - FileResource (text file): re-reads the file on EVERY read -------
mcp.add_resource(FileResource(
    uri="file:///release-notes", path=DATA / "release-notes.txt",
    name="release_notes", mime_type="text/plain"))

# WAY 10 - Binary: image/PDF. FileResource(is_binary=True) or BinaryResource
mcp.add_resource(FileResource(
    uri="image://logo", path=DATA / "logo.png",
    name="logo", mime_type="image/png", is_binary=True))
mcp.add_resource(BinaryResource(
    uri="binary://sample", name="sample_bytes", data=b"\x89RAW", mime_type="application/octet-stream"))

# WAY 11 - DirectoryResource: lists the files inside a folder -------------
mcp.add_resource(DirectoryResource(
    uri="dir://docs", path=DATA / "docs", name="docs_index", recursive=False))

# WAY 12 - HttpResource: content comes from a WEBSITE/API, fetched on read.
# (For the demo we start a tiny local web server so it works offline.)
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):                                         # noqa: N802
        body = json.dumps({"source": "local web server", "price": 99}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):                                # keep stdout clean
        pass


_httpd = HTTPServer(("127.0.0.1", 0), _Handler)               # port 0 = any free port
threading.Thread(target=_httpd.serve_forever, daemon=True).start()
mcp.add_resource(HttpResource(
    uri="api://price", name="price_api",
    url=f"http://127.0.0.1:{_httpd.server_port}/price", mime_type="application/json"))


# WAY 13 - FunctionResource: a function wrapped in a box (no decorator) ---
def _build_banner() -> str:
    return "Built by FunctionResource at read time."


mcp.add_resource(FunctionResource(uri="fn://banner", name="banner", fn=_build_banner))


# ===========================================================================
# FAMILY C - ADD, COMBINE, HIDE
# ===========================================================================

# WAY 14 - ADD AT RUNTIME: a tool creates a new resource while server runs -
@mcp.tool
async def publish_note(slug: str, text: str, ctx: Context) -> str:
    """Create note://<slug> and tell clients the list changed."""
    mcp.add_resource(TextResource(uri=f"note://{slug}", name=f"note_{slug}", text=text))
    await ctx.send_notification(mcp_types.ResourceListChangedNotification())
    return f"created note://{slug}"


# WAY 15 - MOUNT: plug a whole other server inside this one --------------
# Resources of the child get a namespace in their address.
finance = FastMCP("finance")


@finance.resource("budget://summary")
def budget() -> str:
    return "Budget: 1.2M used of 2.0M"


mcp.mount(finance, namespace="finance")      # becomes budget://finance/summary


# WAY 16 - HIDE: keep a resource out of the list using a tag --------------
@mcp.resource("internal://secret-plan", tags={"internal"})
def secret_plan() -> str:
    return "Not for clients"


mcp.disable(tags={"internal"})               # hidden: not listed, not readable


if __name__ == "__main__":
    mcp.run(show_banner=False)
