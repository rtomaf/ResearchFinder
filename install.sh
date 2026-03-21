#!/bin/bash
# install.sh - Setup ResearchFinder on macOS with daily scheduling via launchd
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PLIST_NAME="com.researchfinder.daily"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
LOG_DIR="$SCRIPT_DIR/logs"

echo "=== ResearchFinder Setup ==="
echo ""

# Create virtual environment
echo "[1/4] Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "[2/4] Installing dependencies..."
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$SCRIPT_DIR/reports"

# Generate launchd plist with correct paths
PYTHON_PATH="$VENV_DIR/bin/python"

echo "[3/4] Creating launchd schedule (daily at 8:00 AM)..."
cat > "$PLIST_DST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_DIR/main.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# Load the launchd job
echo "[4/4] Loading launchd job..."
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "  Schedule:  Daily at 8:00 AM"
echo "  Reports:   $SCRIPT_DIR/reports/"
echo "  Logs:      $LOG_DIR/"
echo ""
echo "NEXT STEPS:"
echo "  1. Copy .env.example to .env and fill in your credentials:"
echo "     cp .env.example .env"
echo "     nano .env"
echo ""
echo "  2. Test it now:"
echo "     $PYTHON_PATH $SCRIPT_DIR/main.py"
echo ""
echo "  To uninstall:"
echo "     launchctl unload $PLIST_DST && rm $PLIST_DST"
