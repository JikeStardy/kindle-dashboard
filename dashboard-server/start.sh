#!/bin/bash
set -e

PORT=${PORT:-15000}

echo "[Entrypoint] Starting application on port $PORT..."
exec uv run gunicorn -w 1 --worker-class gthread --threads 4 -b 0.0.0.0:"$PORT" --timeout 120 app:app
