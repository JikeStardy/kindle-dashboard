#!/bin/sh

LOG="/tmp/dashboard.log"
echo "========================================" > "$LOG"
echo "[Boot] Started at $(date)" >> "$LOG"

BASE_DIR="/mnt/us/extensions/Kindle-Dashboard"
DAEMON="$BASE_DIR/bin/run_daemon.sh"

if [ ! -f "$DAEMON" ]; then
    echo "[Boot] Daemon not found at $DAEMON" >> "$LOG"
    exit 1
fi

# Double-fork to fully detach from KUAL parent
(
    sleep 5
    exec /bin/sh "$DAEMON" >> "$LOG" 2>&1
) &

echo "[Boot] Daemon detached, parent exiting" >> "$LOG"
exit 0
