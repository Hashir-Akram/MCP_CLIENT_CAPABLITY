# Module 4, Lesson 1 - MCP Roots

| File | Purpose |
|------|---------|
| MCP_Roots_Mentor_Guide.docx | Full guide (24 pages): concepts, security, spec 2026-07-28 status, every snippet explained |
| MCP_Roots_Infographic_Slides.pptx | 15 slides |
| demo/01_roots_server_classic.py | Server that asks for roots and enforces boundaries (classic env) |
| demo/02_roots_client_classic.py | FastMCP client: static roots, dynamic roots, attack tests |
| demo/03_roots_client_mcpuse.py | MCP-USE client |
| demo/04_roots_server_modern.py | 2026-07-28 style (input-required) + recommended replacement |
| demo/05_roots_client_modern.py | Client for the modern server |

## Two environments
    # classic (files 01-03)
    python -m venv venv-classic && source venv-classic/bin/activate
    pip install -r demo/requirements-classic.txt
    cd demo && python 02_roots_client_classic.py && python 03_roots_client_mcpuse.py

    # modern (files 04-05)
    python -m venv venv-modern && source venv-modern/bin/activate
    pip install -r demo/requirements-modern.txt
    cd demo && python 05_roots_client_modern.py

Tested on Python 3.12.
