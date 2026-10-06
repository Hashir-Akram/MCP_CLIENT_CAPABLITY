# Module 3, Part 3 - MCP Prompts

| File | Purpose |
|------|---------|
| MCP_Prompts_Mentor_Guide.docx | Full guide: concepts, lifecycle, wire messages, every code snippet explained, project plan, exercises |
| MCP_Prompts_Infographic_Slides.pptx | 18 slides: concept infographics + code walkthrough slides |
| demo/01_prompts_server.py | FastMCP prompt library (8 steps) |
| demo/02_prompts_client.py | Client walking through all 8 phases |
| demo/03_base_server_prompts.py | Low-level `mcp` server with list/get handlers |
| demo/04_base_client.py | Official `mcp` client for the base server |

## Run
    python -m venv venv && source venv/bin/activate
    pip install -r demo/requirements.txt
    cd demo
    python 02_prompts_client.py
    python 04_base_client.py

Tested: Python 3.12, fastmcp 4.0.11, mcp 2.3.0 (MCP spec 2026-07-28).
