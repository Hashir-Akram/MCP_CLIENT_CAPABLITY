# Module 3, Part 2 - MCP Resources

| File | Purpose |
|------|---------|
| MCP_Resources_Mentor_Guide.docx | Full guide: concepts, lifecycle, wire messages, every code snippet explained, project plan, exercises |
| MCP_Resources_Infographic_Slides.pptx | 13 infographic slides for revision / teaching |
| demo/01_resources_server.py | FastMCP server (static, dynamic, template, wildcard, classes, annotations, runtime) |
| demo/02_resources_client.py | FastMCP client walking through all lifecycle phases |
| demo/03_base_server_resources.py | Low-level `mcp` server with subscriptions/listen |
| demo/04_base_client.py | Official `mcp` client for the base server |

## Run
    python -m venv venv && source venv/bin/activate
    pip install -r demo/requirements.txt
    cd demo
    python 02_resources_client.py
    python 04_base_client.py

Tested: Python 3.12, fastmcp 4.0.11, mcp 2.3.0 (MCP spec 2026-07-28).
