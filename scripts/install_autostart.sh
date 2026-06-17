#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/CodexLocalApps/apparel-diagnosis"
LOG_DIR="$APP_DIR/logs"
PLIST="$HOME/Library/LaunchAgents/com.codex.apparel.diagnosis.plist"
LABEL="com.codex.apparel.diagnosis"

mkdir -p "$APP_DIR" "$LOG_DIR" "$HOME/Library/LaunchAgents"

ditto "$ROOT_DIR/app" "$APP_DIR/app"
ditto "$ROOT_DIR/public" "$APP_DIR/public"
ditto "$ROOT_DIR/data" "$APP_DIR/data"
ditto "$ROOT_DIR/run.sh" "$APP_DIR/run.sh"
ditto "$ROOT_DIR/requirements.txt" "$APP_DIR/requirements.txt"
chmod +x "$APP_DIR/run.sh"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd "$APP_DIR" &amp;&amp; exec ./run.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>WorkingDirectory</key>
  <string>$APP_DIR</string>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/server.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/server.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOST</key>
    <string>127.0.0.1</string>
    <key>PORT</key>
    <string>8765</string>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed $LABEL"
echo "App: $APP_DIR"
echo "URL: http://127.0.0.1:8765/"

