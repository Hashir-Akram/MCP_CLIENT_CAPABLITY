# Module 4, Lesson 3 - MCP Elicitation

| File | Purpose |
|------|---------|
| MCP_Elicitation_Mentor_Guide.docx | Full guide (26 pages): concepts, field types, three outcomes, safety, spec 2026-07-28 changes, Module 4 recap |
| MCP_Elicitation_Infographic_Slides.pptx | 16 slides |
| demo/01_elicitation_server_classic.py | "Travel Desk" server with six tools (classic env) |
| demo/02_elicitation_client_classic.py | FastMCP client with a simulated user: all outcomes, forms, invalid answer, retry |
| demo/03_elicitation_client_mcpuse.py | MCP-USE client (elicitation_callback) |
| demo/04_elicitation_server_modern.py | 2026-07-28 style (input-required), including a three-round tool with request_state |
| demo/05_elicitation_client_modern.py | Client for the modern server |

URL-mode elicitation is explained in the guide but was NOT exercised in the demos.

## Two environments
    # classic (files 01-03)
    python -m venv venv-classic && source venv-classic/bin/activate
    pip install -r demo/requirements-classic.txt
    cd demo && python 02_elicitation_client_classic.py && python 03_elicitation_client_mcpuse.py

    # modern (files 04-05)
    python -m venv venv-modern && source venv-modern/bin/activate
    pip install -r demo/requirements-modern.txt
    cd demo && python 05_elicitation_client_modern.py

Tested on Python 3.12.
