#!/usr/bin/env bash
# Serve the landing page locally and open it (macOS) or print the URL.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8765}"
URL="http://127.0.0.1:${PORT}/"
python3 -m http.server "${PORT}" --directory landing >/tmp/mirrorz-landing-http.log 2>&1 &
PID=$!
echo "Landing server pid=${PID} → ${URL}"
echo "Log: /tmp/mirrorz-landing-http.log"
if [[ "$(uname)" == "Darwin" ]] && command -v open >/dev/null; then
  sleep 0.4
  open "${URL}"
fi
echo "Stop with: kill ${PID}"
