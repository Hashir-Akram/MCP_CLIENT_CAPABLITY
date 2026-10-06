@echo off
REM One command that builds BOTH environments (Windows).   Usage:  setup_environments.bat
cd /d "%~dp0"
echo ==> Main environment (.venv-main): Module 3 + Module 4 modern demos
python -m venv .venv-main
.venv-main\Scripts\pip install -q -r requirements.txt
echo ==> Classic environment (.venv-classic): Module 4 demos 01-03 (+ MCP-USE)
python -m venv .venv-classic
.venv-classic\Scripts\pip install -q -r requirements-classic.txt
echo.
echo Done. Activate one with:
echo   .venv-main\Scripts\activate      (Module 3 and Module 4 files 04-05, 07)
echo   .venv-classic\Scripts\activate   (Module 4 files 01-03, 06)
