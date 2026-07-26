#!/bin/sh
set -e

cd /app

echo "[entrypoint] running initial fetch..."
MUF_OUTPUT_DIR=/data python3 muf.py || echo "[entrypoint] initial fetch failed, cron will retry in 15 min"

echo "[entrypoint] starting web server on :8080 (serving /data)"
python3 -m http.server 8080 --directory /data &

echo "[entrypoint] starting cron in foreground"
exec cron -f
