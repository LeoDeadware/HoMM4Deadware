#!/bin/bash
# Smoke test of the INSTALLED app (kit R-I3/R-I5), launched exactly the way Finder does it:
# `open -n "$APP"` (LaunchServices; the app is its own responsible process for macOS privacy, TCC).
# Checks: the bundle's executable is a Mach-O (a bash script there cannot read the app's files under
# ~/Desktop when opened from Finder), the game reaches the main menu silently (H4_BACKGROUND, dummy
# audio), takes a screenshot through TEST_INPUT and quits; no crash report.
#   tools/app_smoke.sh [en|uk]      # APP=~/Desktop/Heroes IV.app by default; language en
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${APP:-$HOME/Desktop/Heroes IV.app}"
LANG_="${1:-en}"
C="$APP/Contents"
[[ -x "$C/MacOS/h4-bin" ]] || { echo "app_smoke: FAIL no $APP"; exit 1; }
exe="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$C/Info.plist" 2>/dev/null)"
fails=0
file -b "$C/MacOS/$exe" | grep -q "Mach-O" \
  || { echo "app_smoke: FAIL CFBundleExecutable '$exe' is not a Mach-O"; fails=1; }
# Never touch a running game: it is the owner playing (HP2 2026-11-06: a pkill here killed his game).
# BUSY = not tested, exit 2 (PIT-never-kill-running-game).
if pgrep -f "$C/MacOS/h4-bin" >/dev/null; then
  echo "app_smoke: BUSY - Heroes IV is running (pid $(pgrep -f "$C/MacOS/h4-bin" | tr '\n' ' ')); not touched, not tested"; exit 2
fi
RUN="$HOME/Library/Application Support/Heroes IV/runs/app_smoke-$(date +%Y%m%d-%H%M%S)-$$"; mkdir -p "$RUN/data"
printf '14 key Escape\n17 key Escape\n24 shot menu\n25 quit\n' > "$RUN/input.txt"
# A run player root outside ~/Desktop (the game hangs on writes there when opened from Finder, TCC);
# the player's own saves and settings are not touched.
open -n "$APP" --env H4_PLAYER_ROOT="$RUN" --env H4_BACKGROUND=1 --env SDL_AUDIO_DRIVER=dummy \
  --env H4_LANG="$LANG_" --env H4_TEST_INPUT="$RUN/input.txt" --env H4_SHOT_DIR="$RUN" \
  || { echo "app_smoke: FAIL open -n $APP"; fails=1; }
mine=""   # the pids of this run only (nothing ran before the open)
for _ in $(seq 1 120); do [[ -z "$mine" ]] && mine="$(pgrep -f "$C/MacOS/h4-bin" | tr '\n' ' ')"; grep -q "TEST_INPUT: quit" "$RUN/logs/h4.log" 2>/dev/null && break; sleep 0.5; done
sleep 1
for p in $mine; do kill -0 "$p" 2>/dev/null && { kill "$p"; echo "app_smoke: FAIL timeout (killed own run pid $p)"; fails=1; }; done
grep -q "launcher: language $LANG_" "$RUN/logs/h4.log" 2>/dev/null || { echo "app_smoke: FAIL no launcher line"; fails=1; }
[[ -s "$RUN/menu.bmp" ]] || { echo "app_smoke: FAIL no screenshot (the game did not render)"; fails=1; }
ls "$RUN/data/h4/crashes/"* >/dev/null 2>&1 && { echo "app_smoke: FAIL crash report"; fails=1; }
(( fails )) && { echo "app_smoke: evidence $RUN"; exit 1; }
rm -rf "${RUN:?}"   # evidence is kept only for a failure
echo "app_smoke: PASS ($LANG_)"
