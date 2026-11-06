#!/bin/bash
# Removes the test install of Heroes of Might and Magic IV: ~/Desktop/Heroes IV.app and its player files in
# ~/Library/Application Support/Heroes IV (settings, saves, logs; RULES R-I5, owner 2026-11-06: that folder
# goes together with the game). Never under a running game (BUSY = exit 2).
#   tools/uninstall_app.sh [--keep-saves]     # --keep-saves: remove only the app
set -euo pipefail
APP="${H4_APP:-$HOME/Desktop/Heroes IV.app}"
SUP="$HOME/Library/Application Support/Heroes IV"
if pgrep -f "$APP/Contents/MacOS/h4-bin" > /dev/null; then
  echo "uninstall_app: BUSY — the game is running; nothing removed"; exit 2
fi
[[ -d "$APP" ]] && rm -rf "$APP" && echo "removed $APP"
if [[ "${1:-}" != --keep-saves && -d "$SUP" ]]; then rm -rf "$SUP" && echo "removed $SUP"; fi
echo "uninstall_app: done"
