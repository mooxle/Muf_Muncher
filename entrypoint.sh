#!/bin/sh
set -e

cd /app

echo "[entrypoint] running initial fetch..."
MUF_OUTPUT_DIR=/data python3 muf.py || echo "[entrypoint] initial fetch failed, cron will retry in 15 min"

# muf-cron hardcodes MUF_OUTPUT_DIR since cron doesn't inherit the
# container's environment - regenerate it with MUF_HOME_LOCATOR baked in
# too (if the user set one, e.g. via docker-compose's `environment:`), so
# it reaches the recurring 15-min runs, not just this initial fetch.
# Variable assignments only apply to job lines that come after them in a
# crontab, so the whole file is rewritten rather than patched in place.
cat > /etc/cron.d/muf-cron <<CRON
PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
MUF_OUTPUT_DIR=/data
MUF_HOME_LOCATOR=$MUF_HOME_LOCATOR
*/15 * * * * root cd /app && python3 muf.py >> /var/log/muf-cron.log 2>&1
CRON
chmod 0644 /etc/cron.d/muf-cron

echo "[entrypoint] starting web server on :8080 (serving /data)"
python3 -m http.server 8080 --directory /data &

echo "[entrypoint] starting cron in foreground"
exec cron -f
