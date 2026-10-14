#!/usr/bin/env bash
# Starts the vision service (port 8000) and the dashboard (port 3000, override with WEB_PORT) together.
set -euo pipefail
cd "$(dirname "$0")"
[ -f server/models/face_detection_yunet_2023mar.onnx ] || server/scripts/download_models.sh
[ -d server/.venv ] || (cd server && uv sync)
[ -d web/node_modules ] || (cd web && npm install)
trap 'kill 0' EXIT
(cd server && .venv/bin/uvicorn rollcall.main:app --port 8000 --reload) &
(cd web && npm run dev -- --port "${WEB_PORT:-3000}") &
wait
