#!/bin/bash
# send_daily.sh - Send today's research digest by email.
# Called by launchd at 8:10 AM, after the Claude Code scheduled task
# has written the markdown report at 8:02 AM.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
REPORT="$SCRIPT_DIR/reports/$(date +%Y-%m-%d).md"

# Set up venv if not present
if [ ! -f "$PYTHON" ]; then
    echo "[send_daily] Setting up venv..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    "$SCRIPT_DIR/.venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
fi

# Wait for the report file (Claude Code task runs at 8:02, we run at 8:10)
if [ ! -f "$REPORT" ]; then
    echo "[send_daily] Report not found: $REPORT — skipping email."
    exit 1
fi

echo "[send_daily] Sending $REPORT..."
"$PYTHON" "$SCRIPT_DIR/email_report.py" "$REPORT"
