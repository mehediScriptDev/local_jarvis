#!/bin/bash
# ───────────────────────────────────────────────────────────────
# JARVIS Voice Agent — One-command installer
# Sets up dependencies, LaunchAgent, and starts JARVIS.
# Usage:  chmod +x install.sh && ./install.sh
# ───────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
VOICE_SCRIPT="$SCRIPT_DIR/jarvis_voice.py"
PLIST_LABEL="com.mehedi.jarvis.voice"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
LOG_PATH="$HOME/Library/Logs/jarvis_voice.log"

echo "╔══════════════════════════════════════════╗"
echo "║       JARVIS Voice Agent Installer       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Check Python ──────────────────────────────────────────
echo "[1/5] Checking Python …"
if [ -z "$PYTHON" ]; then
    echo "  ✗ Python3 not found. Please install it."
    exit 1
fi
echo "  ✓ $($PYTHON --version)"

# ── 2. Install dependencies ──────────────────────────────────
echo "[2/5] Installing Python dependencies …"
$PYTHON -m pip install --user --quiet sounddevice numpy requests openai-whisper 2>&1 | tail -3
echo "  ✓ Dependencies installed."

# ── 3. Check Ollama ──────────────────────────────────────────
echo "[3/5] Checking Ollama …"
if ! command -v ollama &>/dev/null; then
    echo "  ✗ Ollama not found. Install from https://ollama.ai"
    exit 1
fi

# Try to reach Ollama API
if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "  ✓ Ollama is running."
else
    echo "  ⚠ Ollama is not running. Starting Ollama app …"
    open -a Ollama
    sleep 5
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "  ✓ Ollama started."
    else
        echo "  ⚠ Could not start Ollama. Please open it manually."
    fi
fi

# Check for llama2 model
if curl -sf http://localhost:11434/api/tags 2>/dev/null | grep -q "llama2"; then
    echo "  ✓ llama2 model available."
else
    echo "  ⚠ llama2 model not found. Pulling it now (this may take a few minutes) …"
    ollama pull llama2
fi

# ── 4. Run diagnostics ───────────────────────────────────────
echo "[4/5] Running diagnostics …"
$PYTHON "$VOICE_SCRIPT" --test
echo ""

# ── 5. Install LaunchAgent ───────────────────────────────────
echo "[5/5] Setting up auto-start on login …"

# Unload old agents if they exist
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl unload "$HOME/Library/LaunchAgents/com.mehedi.jarvis.daemon.plist" 2>/dev/null || true
launchctl unload "$HOME/Library/LaunchAgents/com.mehedi.jarvis.hotword.plist" 2>/dev/null || true

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$VOICE_SCRIPT</string>
    <string>--log</string>
    <string>$LOG_PATH</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_PATH</string>
  <key>StandardErrorPath</key>
  <string>$LOG_PATH</string>
</dict>
</plist>
PLIST

launchctl load "$PLIST_PATH"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║          ✓ JARVIS is now LIVE!           ║"
echo "║                                          ║"
echo "║  Say \"Jarvis\" to wake him up.          ║"
echo "║  He'll auto-start every time you log in. ║"
echo "║                                          ║"
echo "║  Logs: ~/Library/Logs/jarvis_voice.log   ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Useful commands:"
echo "  View logs:     tail -f ~/Library/Logs/jarvis_voice.log"
echo "  Stop JARVIS:   launchctl unload $PLIST_PATH"
echo "  Start JARVIS:  launchctl load $PLIST_PATH"
echo ""
