# MCP & A2A - Mentoring Path

| Module | Folder | Contents |
|--------|--------|----------|
| Module 3, Part 2 | Module-3_Resources | Full guide + 13 slides + demo |
| Module 3, Part 2 (Version B) | Module-3_Resources_B | Simple-words guide + 13 slides + demo of all 16 ways |
| Module 3, Part 3 | Module-3_Prompts | Full guide + 18 slides + demo |
| Module 3, Part 3 (Version B) | Module-3_Prompts_B | Simple-words guide + 15 slides + demo of all 16 ways |
| Module 4, Lesson 1 | Module-4_Roots | Guide (24 pp) + 15 slides + classic and modern demos |
| Module 4, Lesson 2 | Module-4_Sampling | Guide (24 pp) + 15 slides + classic and modern demos - all calling REAL Groq models |
| Module 4, Lesson 3 | Module-4_Elicitation | Guide (26 pp) + 16 slides + classic and modern demos |

Module 4 demos need two environments (classic: fastmcp 3.4.8 + mcp-use 1.7.1; modern: fastmcp 4.0.11). See each lesson's README.
Spec note: in 2026-07-28, Roots and Sampling are deprecated (still working); Elicitation is not.

## Setup

    setup_environments.bat        (Windows)
    bash setup_environments.sh    (macOS/Linux)

Builds BOTH venvs in one go:
- `.venv-main` - Module 3 (all of it) + Module 4 modern demos (files `04`/`05`)
- `.venv-classic` - Module 4 classic/mcp-use demos only (files `01`-`03`)

## Real-model demo (Groq)

Every file in Module-4_Sampling (`02`, `03`, `04`, `05`) calls a real model through the
Groq API (groq.com - this is Groq Cloud, NOT xAI's Grok) - there is no simulated model
left in that lesson. Copy `.env.example` to `.env` at the project root and fill in
`GROQ_API_KEY` (get one at https://console.groq.com/keys). Every script loads it
automatically.
