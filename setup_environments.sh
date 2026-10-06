#!/usr/bin/env bash
# One command that builds BOTH environments.   Usage:  bash setup_environments.sh
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

echo "==> Main environment (.venv-main): Module 3 + Module 4 modern demos"
$PY -m venv .venv-main
.venv-main/bin/pip install -q -r requirements.txt

echo "==> Classic environment (.venv-classic): Module 4 demos 01-03 (+ MCP-USE)"
$PY -m venv .venv-classic
.venv-classic/bin/pip install -q -r requirements-classic.txt

cat <<'MSG'

Done. How to run:
  Module 3 and Module 4 files 04-05, 07 :  source .venv-main/bin/activate
  Module 4 files 01-03, 06              :  source .venv-classic/bin/activate
Then:  cd <lesson>/demo  &&  python <script>.py
MSG
