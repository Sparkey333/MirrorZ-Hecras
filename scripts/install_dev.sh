#!/usr/bin/env bash
# Phase 4 — warm Cursor / local bootstrap for MirrorZ-Hecras.
# Idempotent. Safe to re-run in cloud agents.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3-venv python3-tk >/dev/null
fi

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt pytest reportlab >/dev/null

echo "==> Dev environment ready"
echo "    source .venv/bin/activate"
echo "    pytest -q"
echo "    python main.py --run examples/simple_channel.json"
