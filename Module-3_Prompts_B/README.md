# Module 3, Part 3 - Version B: Prompts in Simple Words

Every way to define a prompt: 16 ways in 3 families (write a function, build as an object, add/combine/hide).

| File | Purpose |
|------|---------|
| MCP_Prompts_B_Simple_Guide.docx | Plain-language guide (17 pages) |
| MCP_Prompts_B_Simple_Slides.pptx | 15 picture slides |
| demo/01_all_prompt_types_server.py | One server with all 16 ways |
| demo/02_all_prompt_types_client.py | Tries each way, prints results |

Way 13 (low-level server) lives in ../Module-3_Prompts/demo/03_base_server_prompts.py.

## Run
    python -m venv venv && source venv/bin/activate
    pip install -r demo/requirements.txt
    cd demo && python 02_all_prompt_types_client.py

Tested: Python 3.12, fastmcp 4.0.11, mcp 2.3.0.
