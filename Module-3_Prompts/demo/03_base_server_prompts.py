"""
03_base_server_prompts.py
=========================
The SAME prompt ideas, written with the LOW-LEVEL ("base") MCP Server of the
official `mcp` SDK. FastMCP generated all of this for you from decorators:

    prompts/list  -> on_list_prompts   (describe every prompt + its arguments)
    prompts/get   -> on_get_prompt     (validate args, build the messages)

Run (STDIO):  python 03_base_server_prompts.py
Test with:    python 04_base_client.py

Written for `mcp` SDK 2.x (handlers are passed to the Server constructor).
Older 1.x SDKs used decorators (@server.list_prompts(), @server.get_prompt()).
"""

import anyio
from mcp import types
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import MCPError

INVALID_PARAMS = -32602          # JSON-RPC standard code: "bad arguments"


# --------------------------------------------------------------------------
# 1. THE CATALOGUE: describe prompts as DATA
# --------------------------------------------------------------------------
# FastMCP derived this from your function signature. Here you write it by hand,
# which makes it obvious that a prompt "definition" is just:
#     name + description + list of arguments (name, description, required)
PROMPTS = {
    "summarize_text": types.Prompt(
        name="summarize_text",
        title="Summarise Text",
        description="Summarise any text in a chosen style.",
        arguments=[
            types.PromptArgument(name="text", description="The text to summarise", required=True),
            types.PromptArgument(name="style", description="bullets | paragraph | tweet", required=False),
        ],
    ),
    "translate": types.Prompt(
        name="translate",
        description="Translate text into a target language.",
        arguments=[
            types.PromptArgument(name="text", required=True),
            types.PromptArgument(name="language", required=True),
        ],
    ),
}

STYLE_HINTS = {
    "bullets": "as 3 to 5 short bullet points",
    "paragraph": "as one concise paragraph",
    "tweet": "as one tweet (max 280 characters)",
}


# --------------------------------------------------------------------------
# HANDLER 1 - prompts/list
# --------------------------------------------------------------------------
async def on_list_prompts(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListPromptsResult:
    return types.ListPromptsResult(prompts=list(PROMPTS.values()), next_cursor=None)


# --------------------------------------------------------------------------
# HANDLER 2 - prompts/get
# --------------------------------------------------------------------------
async def on_get_prompt(
    ctx: ServerRequestContext, params: types.GetPromptRequestParams
) -> types.GetPromptResult:
    prompt = PROMPTS.get(params.name)
    if prompt is None:
        raise MCPError(code=INVALID_PARAMS, message=f"Unknown prompt: {params.name}")

    args = params.arguments or {}              # always a dict of STRING -> STRING

    # YOU enforce required arguments (FastMCP did this automatically)
    missing = [a.name for a in (prompt.arguments or []) if a.required and a.name not in args]
    if missing:
        raise MCPError(code=INVALID_PARAMS, message=f"Missing required arguments: {missing}")

    if params.name == "summarize_text":
        style = args.get("style", "bullets")
        if style not in STYLE_HINTS:           # validate allowed values yourself
            raise MCPError(code=INVALID_PARAMS, message=f"style must be one of {sorted(STYLE_HINTS)}")
        text = f"Summarise the following text {STYLE_HINTS[style]}:\n\n{args['text']}"
        return types.GetPromptResult(
            description="Summarisation request",
            messages=[types.PromptMessage(role="user", content=types.TextContent(type="text", text=text))],
        )

    # translate: one user message that carries the instruction and the text ---
    return types.GetPromptResult(
        description="Translation request",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Translate to {args['language']}. Reply with the translation only.\n\n{args['text']}",
                ),
            ),
        ],
    )


# --------------------------------------------------------------------------
# Wire handlers into the Server and serve over STDIO
# --------------------------------------------------------------------------
server = Server(
    "prompt-base-server",
    on_list_prompts=on_list_prompts,
    on_get_prompt=on_get_prompt,
)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
