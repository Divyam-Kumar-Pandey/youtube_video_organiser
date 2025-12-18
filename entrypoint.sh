#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Divyam-Kumar-Pandey/youtube_video_organiser.git"
APP_DIR="/app/youtube_video_organiser"

echo "Cloning or updating repository from ${REPO_URL}..."

if [ ! -d "${APP_DIR}/.git" ]; then
  rm -rf "${APP_DIR}"
  git clone --depth 1 "${REPO_URL}" "${APP_DIR}"
else
  cd "${APP_DIR}"
  git fetch --all --prune
  git reset --hard origin/main
fi

cd "${APP_DIR}"

echo "Installing/updating dependencies with uv..."
# Use locked deps if available, fall back to resolving if needed
if [ -f "uv.lock" ]; then
  uv sync --frozen --no-dev || uv sync --no-dev
else
  uv sync --no-dev
fi

echo "Starting Streamlit app with uv..."
exec uv run streamlit run app.py \
  --server.port="${PORT:-8501}" \
  --server.address=0.0.0.0

