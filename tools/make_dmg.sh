#!/bin/bash
# Heroes IV.dmg: an unsigned disk image with Heroes IV.app WITHOUT game code and game data (kit R-L5).
#   tools/make_dmg.sh [out.dmg]      (default: .cache/dmg/Heroes IV.dmg)
# The app is install_app.sh in DMG mode (H4_DMG=1): Frameworks self-contained (SDL3, ffmpeg...),
# Resources/build = the first-run kit (tools/dmg/kit.py: our lifter, innoextract, runtime headers,
# h4's own objects, the translation without English text, our voice-over). On the first run the
# launcher finds the player's GOG installer, installs Command Line Tools if missing, unpacks the
# installer, lifts and compiles heroes4.exe, makes the Ukrainian version and puts Heroes IV.app on
# the Desktop (tools/dmg/install_game.sh). Game data: ~/Library/Application Support/Heroes IV.
# Ready HD packs (R-L5): Heroes IV has none (2D art, FSR at run time); mods/hd_* of the tested app
# (HD_FROM) would be copied if one appears. Gates: tools/release_check.sh (ALLOW_HD_PACKS=1) and
# tests/scripts/dmg_no_game_code.sh. Unsigned: first open is right-click → Open ("Read me first.txt").
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DMG="${1:-$ROOT/.cache/dmg/Heroes IV.dmg}"
HD_FROM="${HD_FROM:-$HOME/Desktop/Heroes IV.app/Contents/Resources/mods}"
STAGE="$ROOT/.cache/dmg-stage"
export TMPDIR="$ROOT/.cache/tmp"; mkdir -p "$TMPDIR" "$(dirname "$DMG")"
rm -rf "$STAGE"; mkdir -p "$STAGE"
APP="$STAGE/Heroes IV.app"
H4_DMG=1 H4_APP="$APP" bash "$ROOT/tools/install_app.sh" | tail -3
for d in "$HD_FROM"/hd_*; do   # none today; kept so a future HD pack ships as the owner decided
  [[ -d "$d" ]] || continue
  mkdir -p "$APP/Contents/Resources/mods/$(basename "$d")"
  find "$d" -maxdepth 1 -type f | { grep -E '/([0-9a-f]+\.png|manifest\.tsv)$' || true; } |
    while read -r f; do cp -c "$f" "$APP/Contents/Resources/mods/$(basename "$d")/"; done
done
# License notices of everything the app redistributes (ffmpeg LGPL + source offer, SDL3, x86recomp...).
python3 -I "$ROOT/tools/dmg/notices.py" "$APP" "$APP/Contents/Resources/THIRD_PARTY_NOTICES.txt"
cp "$APP/Contents/Resources/THIRD_PARTY_NOTICES.txt" "$STAGE/Third-party notices.txt"
codesign --force --deep -s - "$APP" >/dev/null 2>&1 || echo "warning: ad-hoc signing failed"
ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/Read me first.txt" <<'TXT'
Heroes of Might and Magic IV for Mac (unofficial port, not signed by Apple)

1. Buy Heroes of Might and Magic IV: Complete on GOG and download its Windows installer
   (setup_heroes_of_might_and_magic_4_complete_....exe, plus the .bin file if offered) into Downloads.
2. Drag Heroes IV.app to Applications.
3. First open: right-click Heroes IV.app -> Open -> Open (Gatekeeper: the app is not signed by Apple;
   after that it opens normally).
4. Choose the language (English or Українська); you can change it at every start.
5. Apple Command Line Tools are needed: if they are missing, the system dialog opens - click Install.
   Heroes IV then builds the game from your GOG installer on this Mac (15-40 minutes, a progress
   window) and puts Heroes IV.app on the Desktop. The game data and code come only from your installer.

Heroes of Might and Magic IV для Mac (неофіційний порт, без підпису Apple)

1. Купіть Heroes of Might and Magic IV: Complete на GOG і завантажте інсталятор для Windows
   (setup_heroes_of_might_and_magic_4_complete_....exe і файл .bin, якщо є) у «Завантаження».
2. Перетягніть Heroes IV.app у «Applications».
3. Перший запуск: клацніть Heroes IV.app правою кнопкою → «Відкрити» → «Відкрити».
4. Оберіть мову (English або Українська); її можна змінити при кожному запуску.
5. Потрібні Command Line Tools від Apple: якщо їх немає, відкриється системне вікно — натисніть
   «Встановити». Далі гра збирається з вашого інсталятора GOG (15–40 хвилин, вікно з прогресом),
   і готова Heroes IV.app з'являється на робочому столі.
TXT
rm -f "$DMG"
hdiutil create -quiet -fs HFS+ -volname "Heroes IV" -srcfolder "$STAGE" -format UDZO "$DMG"
ALLOW_HD_PACKS=1 bash "$ROOT/tools/release_check.sh" "$DMG"
echo "dmg: $DMG ($(du -h "$DMG" | cut -f1))"
