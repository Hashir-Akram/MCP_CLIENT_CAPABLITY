# Module 4, Lesson 2 - MCP Sampling

| File | Purpose |
|------|---------|
| MCP_Sampling_Mentor_Guide.docx | Full guide (24 pages): concepts, parameters, preferences, safety, spec 2026-07-28 status |
| MCP_Sampling_Infographic_Slides.pptx | 15 slides |
| demo/01_sampling_server_classic.py | "Smart Notes" server with four sampling tools (classic env) |
| demo/02_sampling_client_classic.py | FastMCP client: request anatomy, preferences, approval, fallback, budget - calls REAL Groq models |
| demo/03_sampling_client_mcpuse.py | MCP-USE client (sampling_callback) - calls REAL Groq models |
| demo/04_sampling_server_modern.py | 2026-07-28 style (input-required) + direct-provider replacement - WAY B calls REAL Groq with the server's own key |
| demo/05_sampling_client_modern.py | Client for the modern server - WAY A calls REAL Groq too |

Every demo in this lesson calls a REAL model through the Groq API (groq.com - this is
Groq Cloud, NOT xAI's Grok). No simulated/rule-based model anywhere. You need a
GROQ_API_KEY environment variable - see .env.example at the project root (copy it to
`.env` and fill in your key; every script loads it automatically).

In 02 and 03, ModelPreferences drive a REAL decision between two real Groq models:
  - no preference stated -> openai/gpt-oss-120b (the smarter model, used as the default)
  - server hints "openai/gpt-oss-20b" + high cost/speed priority (see classify_sentiment
    in 01_sampling_server_classic.py) -> client actually switches to the cheaper/faster
    gpt-oss-20b

In 04/05, WAY A (the client's model) and WAY B (the server's own model) are two
independent real Groq calls - the client never sees which model the server used for
WAY B, and vice versa.

Note: gpt-oss models are reasoning models - they need `reasoning_effort="low"` and
enough `max_tokens`, or they burn the whole budget on hidden chain-of-thought and
return empty text (already handled everywhere in this lesson).

## Two environments
    # classic (files 01-03) - needs GROQ_API_KEY
    python -m venv venv-classic && source venv-classic/bin/activate
    pip install -r demo/requirements-classic.txt
    cd demo && python 02_sampling_client_classic.py && python 03_sampling_client_mcpuse.py

    # modern (files 04-05) - needs GROQ_API_KEY
    python -m venv venv-modern && source venv-modern/bin/activate
    pip install -r demo/requirements-modern.txt
    cd demo && python 05_sampling_client_modern.py

Tested on Python 3.12.
