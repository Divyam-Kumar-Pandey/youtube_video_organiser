#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/app"

cd "${APP_DIR}"

echo "Installing/updating dependencies with uv..."
if [ -f "uv.lock" ]; then
  uv sync --frozen --no-dev || uv sync --no-dev
else
  uv sync --no-dev
fi

echo "Starting Streamlit app with uv..."
exec uv run streamlit run app.py \
  --server.port="${PORT:-8501}" \
  --server.address=0.0.0.0