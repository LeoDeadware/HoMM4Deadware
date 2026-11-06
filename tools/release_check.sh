#!/bin/bash
# Release gate (kit RULES R-L1/R-L2): a .app/.dmg/zip for anyone but the owner must contain NO game
# data and nothing derived from it (GOG files: .exe/.dll/.h4r/.aop/.ico/.pdf/.bik..., a game/ tree,
# the translation's English extracts loc/extract, loc/fonts_en, loc/catalog).
#   tools/release_check.sh path/to/Heroes\ IV.app|.dmg|.zip
# ALLOW_HD_PACKS=1 (only tools/make_dmg.sh, R-L5): Heroes IV.app/Contents/Resources/mods/hd_* allowed.
# Heroes IV has no HD packs (2D art scaled by FSR at run time), so nothing is allowed by it today.
# Our own Ukrainian voice-over (loc/voice, released in heroes4-mac-assets.zip by the owner's decision) passes.
set -uo pipefail
t="$1"; tmp=""
case "$t" in
  *.dmg) tmp="$(mktemp -d)"; hdiutil attach -nobrowse -readonly -mountpoint "$tmp" "$t" >/dev/null || exit 2; root="$tmp" ;;
  *.zip) tmp="$(mktemp -d)"; unzip -q "$t" -d "$tmp"; root="$tmp" ;;
  *) root="$t" ;;
esac
bad="$(find "$root" \( -iname '*.exe' -o -iname '*.dll' -o -iname '*.h4r' -o -iname '*.aop' -o -iname '*.asi' \
  -o -iname '*.ico' -o -iname '*.bik' -o -iname '*.pdf' -o -iname '*.chm' -o -iname '*.h4c' -o -iname '*.h4s' \
  -o -path '*/game/*' -o -path '*/game-uk/*' -o -path '*/loc/extract/*' -o -path '*/loc/fonts_en/*' \
  -o -path '*/loc/catalog/*' -o -path '*/mods/hd_*' -o -iname '*.gpr' \) -print 2>/dev/null)"
[[ "${ALLOW_HD_PACKS:-0}" == 1 ]] && bad="$(grep -vE "^$root/Heroes IV\.app/Contents/Resources/mods/hd_[a-z0-9_]+(/|\$)" <<< "$bad")"
[[ "$t" == *.dmg ]] && hdiutil detach -quiet "$tmp"
[[ -n "$tmp" && "$t" == *.zip ]] && rm -rf "$tmp"
if [[ -n "$bad" ]]; then echo "release_check: FAIL — game data / derived content:"; head -20 <<< "$bad"; exit 1; fi
echo "release_check: PASS (no game data found in $t)"
