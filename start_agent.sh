#!/usr/bin/env bash
# ==============================================================================
# Telegram AI Companion Launcher (Alias to start.sh)
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start.sh" "$@"
