"""
03_base_server_resources.py
===========================
The SAME ideas as FastMCP, but written with the LOW-LEVEL ("base") MCP Server
from the official `mcp` SDK. FastMCP hides these handlers from you; here you
write each protocol method yourself, so you SEE the lifecycle:

    resources/list            -> on_list_resources
    resources/templates/list  -> on_list_resource_templates
    resources/read            -> on_read_resource
    subscriptions/listen      -> on_subscriptions_listen   (spec 2026-07-28, NEW way)
    resources/subscribe       -> on_subscribe_resource     (spec <= 2025-11-25, legacy)
    resources/unsubscribe     -> on_unsubscribe_resource   (spec <= 2025-11-25, legacy)

Run (STDIO):  python 03_base_server_resources.py
Test with:    python 04_base_client.py

NOTE: written for `mcp` SDK 2.x (handlers are passed to the Server constructor).
Older 1.x SDKs used decorators (@server.list_resources()) - same concepts.
"""

import json

import anyio
from mcp import types
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.server.subscriptions import (
    InMemorySubscriptionBus,
    ListenHandler,
    ResourcesListChanged,
    ResourceUpdated,
)
from mcp.shared.exceptions import MCPError

RESOURCE_NOT_FOUND = -32002          # error code defined by the MCP spec

# --------------------------------------------------------------------------
# Our "database": support tickets kept in memory
# --------------------------------------------------------------------------
TICKETS = {
    "101": "Customer cannot reset password - needs manual verification.",
    "102": "Invoice #8841 shows wrong GST amount.",
    "103": "Mobile app crashes on login for Android 14.",
}
SUBSCRIPTIONS: set[str] = set()      # legacy-era subscriptions (pre 2026-07-28)

# Fan-out "bus": the server publishes events here, every open
# `subscriptions/listen` stream receives the ones its client opted into.
bus = InMemorySubscriptionBus()


# --------------------------------------------------------------------------
# HANDLER 1 - resources/list  (what concrete resources exist?)
# --------------------------------------------------------------------------
async def on_list_resources(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListResourcesResult:
    resources = [
        types.Resource(
            uri="tickets://summary",
            name="ticket_summary",
            title="Ticket Summary",
            description="How many tickets are open.",
            mime_type="application/json",
        )
    ]
    # One concrete resource per ticket (so they show up in the list)
    for tid in TICKETS:
        resources.append(
            types.Resource(
                uri=f"tickets://{tid}",
                name=f"ticket_{tid}",
                description=f"Support ticket {tid}",
                mime_type="text/plain",
            )
        )
    # next_cursor=None  => no more pages (use a cursor string for pagination)
    return types.ListResourcesResult(resources=resources, next_cursor=None)


# --------------------------------------------------------------------------
# HANDLER 2 - resources/templates/list  (what PATTERNS can be read?)
# --------------------------------------------------------------------------
async def on_list_resource_templates(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListResourceTemplatesResult:
    return types.ListResourceTemplatesResult(
        resource_templates=[
            types.ResourceTemplate(
                uri_template="tickets://{ticket_id}",
                name="ticket_by_id",
                description="Fetch any ticket by its numeric id.",
                mime_type="text/plain",
            )
        ]
    )


# --------------------------------------------------------------------------
# HANDLER 3 - resources/read  (return the actual content)
# --------------------------------------------------------------------------
async def on_read_resource(
    ctx: ServerRequestContext, params: types.ReadResourceRequestParams
) -> types.ReadResourceResult:
    uri = str(params.uri)

    if uri == "tickets://summary":
        body = json.dumps({"open_tickets": len(TICKETS), "ids": sorted(TICKETS)})
        return types.ReadResourceResult(
            contents=[
                types.TextResourceContents(
                    uri=uri, mime_type="application/json", text=body
                )
            ]
        )

    prefix = "tickets://"
    if uri.startswith(prefix):
        ticket_id = uri[len(prefix):]
        if ticket_id in TICKETS:                       # validate the parameter!
            return types.ReadResourceResult(
                contents=[
                    types.TextResourceContents(
                        uri=uri, mime_type="text/plain", text=TICKETS[ticket_id]
                    )
                ]
            )

    # Spec-defined error for "resource does not exist"
    raise MCPError(code=RESOURCE_NOT_FOUND, message=f"Resource not found: {uri}")


# --------------------------------------------------------------------------
# HANDLERS 4 & 5 - subscribe / unsubscribe  (track who wants updates)
# --------------------------------------------------------------------------
async def on_subscribe_resource(
    ctx: ServerRequestContext, params: types.SubscribeRequestParams
) -> types.EmptyResult:
    SUBSCRIPTIONS.add(str(params.uri))
    return types.EmptyResult()


async def on_unsubscribe_resource(
    ctx: ServerRequestContext, params: types.UnsubscribeRequestParams
) -> types.EmptyResult:
    SUBSCRIPTIONS.discard(str(params.uri))
    return types.EmptyResult()


# --------------------------------------------------------------------------
# A tiny TOOL so we can CHANGE data and trigger resource notifications.
# (Tools act, resources inform - this tool changes what a resource says.)
# --------------------------------------------------------------------------
async def on_list_tools(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="update_ticket",
                description="Replace the text of an existing ticket (or create a new one).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["ticket_id", "text"],
                },
            )
        ]
    )


async def on_call_tool(
    ctx: ServerRequestContext, params: types.CallToolRequestParams
) -> types.CallToolResult:
    args = params.arguments or {}
    ticket_id, text = str(args["ticket_id"]), str(args["text"])
    is_new = ticket_id not in TICKETS
    TICKETS[ticket_id] = text

    # Tell every listener what changed:
    #   * a NEW ticket changes the LIST of resources
    #   * an edit changes the CONTENT of one resource
    if is_new:
        await bus.publish(ResourcesListChanged())
    await bus.publish(ResourceUpdated(uri=f"tickets://{ticket_id}"))

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Saved ticket {ticket_id}")]
    )


# --------------------------------------------------------------------------
# Wire the handlers into the Server and serve over STDIO
# --------------------------------------------------------------------------
server = Server(
    "ticket-resources-base-server",
    on_list_resources=on_list_resources,
    on_list_resource_templates=on_list_resource_templates,
    on_read_resource=on_read_resource,
    on_subscribe_resource=on_subscribe_resource,
    on_unsubscribe_resource=on_unsubscribe_resource,
    on_subscriptions_listen=ListenHandler(bus),     # 2026-07-28 notification stream
    on_list_tools=on_list_tools,
    on_call_tool=on_call_tool,
)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    anyio.run(main)
