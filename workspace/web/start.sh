#!/usr/bin/env bash
set -euo pipefail

WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_VENV="$WEB_DIR/.venv"

if [[ ! -x "$WEB_VENV/bin/python" ]]; then
  python3 -m venv "$WEB_VENV"
fi

if ! "$WEB_VENV/bin/python" -c "import importlib.metadata; raise SystemExit(importlib.metadata.version('imageio-ffmpeg') != '0.5.1')"; then
  "$WEB_VENV/bin/python" -m pip install --disable-pip-version-check -r "$WEB_DIR/requirements.txt"
fi

exec "$WEB_VENV/bin/python" "$WEB_DIR/server.py" --host 0.0.0.0 --port "${PHOTOMANAGER_PORT:-8000}"
