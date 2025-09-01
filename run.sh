#!/bin/bash
# Local dev runner (port 5001), not used on Render
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
python app.py --port 5001
