#!/bin/bash
# make_icns.sh <icon.ico|png> <out.icns>: the app icon from the GOG installer's round icon (256 px),
# made at install time (never committed). Upscaled 4x by Real-ESRGAN when it is installed
# (ROTKPort/.cache/tools/realesrgan or H4Port/.cache/tools/realesrgan), else by sips; squircle.swift
# fits the round art into the macOS icon grid (824 px rounded square, transparent margin) so it sits
# in the Finder container like native apps; iconutil builds the .icns (16..1024 px).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
IN="$1"; OUT="$2"
T="$(mktemp -d "${TMPDIR:-/tmp}/h4_icon.XXXXXX")"; trap 'rm -rf "$T"' EXIT
sips -s format png "$IN" --out "$T/icon.png" >/dev/null
big="$T/icon.png"
for E in "$ROOT/.cache/tools/realesrgan/x" "$ROOT/../ROTKPort/.cache/tools/realesrgan/x"; do
  if [[ -x "$E/realesrgan-ncnn-vulkan" ]] &&
     "$E/realesrgan-ncnn-vulkan" -i "$T/icon.png" -o "$T/x4.png" -m "$E/models" -n realesrgan-x4plus >/dev/null 2>&1; then
    big="$T/x4.png"; break
  fi
done
if [[ -x "$HERE/squircle" ]]; then "$HERE/squircle" "$big" "$T/sq.png"; else swift "$HERE/squircle.swift" "$big" "$T/sq.png"; fi
mkdir -p "$T/i.iconset"
for s in 16 32 128 256 512; do
  sips -z $s $s "$T/sq.png" --out "$T/i.iconset/icon_${s}x${s}.png" >/dev/null
  sips -z $((s * 2)) $((s * 2)) "$T/sq.png" --out "$T/i.iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns -o "$OUT" "$T/i.iconset"
echo "icon $(basename "$big" .png) -> $OUT"
