#!/bin/bash
# Installs the current h4 build as ~/Desktop/Heroes IV.app (kit rule R-I5, owner 2026-11-06): a real
# bundle whose executable is the Mach-O launcher tools/launcher/launcher.c (a bash script there cannot
# read the app's files when it is opened from Finder). Player files (registry, saves, crash reports,
# settings.toml, the log): ~/Library/Application Support/Heroes IV/player (the launcher's default; the
# owner's exception 2026-11-06: one folder per game, removed with it). The old .cache/player of this
# repo is moved there once.
#
# Inside the bundle: Contents/MacOS/h4-bin + Frameworks (x86recomp libraries), Resources/game (the
# original data, English) and Resources/game-uk (the Ukrainian patch, loc/tools/apply.py) - both APFS
# clones of H4Port/game (cp -c), only the patched archives take space; Resources/wings (combat wings).
#
#   tools/install_app.sh            update binary, libraries, launcher (game data kept)
#   tools/install_app.sh --data     also re-clone the game data and re-apply the translation
#   tools/install_app.sh --loc      re-apply the Ukrainian translation (loc/) only
#   H4_DMG=1 H4_APP=<path> tools/install_app.sh   the DMG installer app (tools/make_dmg.sh): no game
#                                   code, no game data; Resources/build = the first-run kit
# tools/app_smoke.sh then opens the installed app the way Finder does.
set -euo pipefail

H4PORT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$H4PORT/h4/out/build/release"
APP="$HOME/Desktop/Heroes IV.app"
[[ -n "${H4_APP:-}" ]] && APP="$H4_APP"   # a test or DMG staging install elsewhere
DMG="${H4_DMG:-0}"
C="$APP/Contents"
RES="$C/Resources"
PLAYER=""   # "" = the launcher's default, ~/Library/Application Support/Heroes IV/player
[[ -n "${H4_APP:-}" && "${H4_DMG:-0}" != 1 ]] && PLAYER="${H4_PLAYER:-}"
[[ -x "$BUILD/h4" ]] || { echo "no $BUILD/h4 - build first"; exit 2; }

# Never replace the game under a running copy (the owner may be playing): BUSY, nothing changed.
if pgrep -f "$C/MacOS/h4-bin" >/dev/null; then
  echo "install_app: BUSY - $APP is running; quit the game first (nothing changed)"; exit 2
fi
mkdir -p "$C/MacOS" "$C/Frameworks" "$RES"

# Binary and libraries; the binary finds the libraries next to it. Each is copied beside and renamed
# over the old one: a game still running keeps its files.
put() { cp "$1" "$2.new" && mv -f "$2.new" "$2"; }
put "$BUILD/h4" "$C/MacOS/h4-bin"
# Bundled libraries are rebuilt from scratch (no stale GPL ffmpeg dependencies left behind).
find "$C/Frameworks" -name '*.dylib' ! -name 'librecomp_*' -delete
for f in "$BUILD"/x86recomp/*.dylib; do put "$f" "$C/Frameworks/$(basename "$f")"; done
rm -f "$C/MacOS/h4"   # old layout
# Self-contained: Homebrew's SDL3/ffmpeg/glslang (and what they load) copied into Frameworks.
# ffmpeg: our LGPL build (tools/dmg/ffmpeg_lgpl.sh), not Homebrew's GPL one (x264/x265).
# h4 and librecomp_* are linked against it (h4 cmake: PKG_CONFIG_PATH=.cache/ffmpeg-lgpl/lib/pkgconfig).
# Never mix: a Homebrew-linked binary binds av_get_pix_fmt_name to libavformat, which the LGPL one lacks
# (2026-11-06: dyld stopped the owner's game). Refuse a build still linked to Homebrew's ffmpeg.
if otool -L "$BUILD/h4" "$BUILD"/x86recomp/*.dylib | grep -q '/opt/homebrew/.*/libav'; then
  echo "install_app: $BUILD is linked to Homebrew's ffmpeg - rebuild against .cache/ffmpeg-lgpl"; exit 2
fi
bash "$H4PORT/tools/dmg/ffmpeg_lgpl.sh" | tail -1
export H4_FFMPEG_LIB="$H4PORT/.cache/ffmpeg-lgpl/lib"
python3 -I "$H4PORT/tools/dmg/bundle_libs.py" "$C/Frameworks" "$C/MacOS/h4-bin:@executable_path/../Frameworks" | tail -1
if [[ $DMG == 1 ]]; then
  # No game code and no game data: the player's Mac builds both on the first run (tools/dmg).
  rm -f "$C/MacOS/h4-bin"; rm -rf "$RES/game" "$RES/game-uk" "$RES/h4.icns"
  python3 -I "$H4PORT/tools/dmg/kit.py" "$BUILD" "$RES/build" "$C/Frameworks" | tail -1
  cp "$H4PORT"/tools/dmg/{install_game.sh,clt.sh,progress.js} "$H4PORT/tools/icon/make_icns.sh" "$RES/build/"
  swiftc -O -o "$RES/build/squircle" "$H4PORT/tools/icon/squircle.swift"
  PLAYER=""   # ~/Library/Application Support/Heroes IV on the player's Mac
fi

# Game data (1.1 GB, cloned: no space): English = original, Ukrainian = patched copy.
if [[ $DMG == 1 ]]; then :; elif [[ ! -d "$RES/game" || "${1:-}" == "--data" ]]; then
  rm -rf "$RES/game"; cp -c -R "$H4PORT/game" "$RES/game"
fi
if [[ $DMG != 1 ]] && [[ ! -d "$RES/game-uk" || "${1:-}" == "--data" ]]; then
  rm -rf "$RES/game-uk"; cp -c -R "$H4PORT/game" "$RES/game-uk"; set -- --loc
fi
# The patch appends to the archives it touches: fresh copies first (real copies, not clones).
if [[ $DMG != 1 && "${1:-}" == "--loc" ]]; then
  for a in heroes4.h4r updates.h4r text.h4r storm.h4r x2.h4r; do
    rm -f "$RES/game-uk/Data/$a"; cp "$H4PORT/game/Data/$a" "$RES/game-uk/Data/$a"
  done
  python3 -I "$H4PORT/loc/tools/apply.py" "$RES/game-uk" | tail -3
fi

# Combat wings (left/right panels beside the 1280 combat screen in wide mode).
mkdir -p "$RES/wings"
for w in paradise hell; do
  sips -s format bmp "$H4PORT/art/combat_wings/${w}_296x2048.png" --out "$RES/wings/$w.bmp" >/dev/null
done
for f in "$H4PORT"/art/combat_wings/factions/*_light.png "$H4PORT"/art/combat_wings/factions/*_dark.png; do
  sips -s format bmp "$f" --out "$RES/wings/$(basename "$f" .png).bmp" >/dev/null
done

# Icon: the GOG installer's round icon fitted into the macOS grid (tools/icon).
[[ $DMG == 1 ]] || [[ -f "$RES/h4.icns" && "${1:-}" != "--data" ]] ||
  bash "$H4PORT/tools/icon/make_icns.sh" "$H4PORT/game/goggame-1207658915.ico" "$RES/h4.icns" || echo "warning: no icon"

# Old layout: player files in <repo>/.cache/player -> the Application Support folder (once).
SUPPORT="$HOME/Library/Application Support/Heroes IV/player"
if [[ -z "${H4_APP:-}" && -d "$H4PORT/.cache/player" && ! -e "$SUPPORT" ]]; then
  mkdir -p "$(dirname "$SUPPORT")" && mv "$H4PORT/.cache/player" "$SUPPORT" && echo "player files moved to $SUPPORT"
fi

# The bundle executable: a small Mach-O (env, log with a size cap, language window, then execv).
[[ -n "$PLAYER" ]] && mkdir -p "$PLAYER"
clang -O2 -DH4_PLAYER_ROOT="\"$PLAYER\"" -o "$C/MacOS/heroes4.new" "$H4PORT/tools/launcher/launcher.c"
mv -f "$C/MacOS/heroes4.new" "$C/MacOS/heroes4"

cat > "$C/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Heroes IV</string>
  <key>CFBundleDisplayName</key><string>Heroes IV</string>
  <key>CFBundleIdentifier</key><string>local.h4port.heroes4</string>
  <key>CFBundleVersion</key><string>0.2</string>
  <key>CFBundleShortVersionString</key><string>0.2</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>heroes4</string>
  <key>CFBundleIconFile</key><string>h4</string>
  <key>LSMinimumSystemVersion</key><string>26.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <!-- No App Nap: it coalesces the game's millisecond timers and stalls its animation. -->
  <key>NSAppSleepDisabled</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.strategy-games</string>
</dict>
</plist>
EOF

touch "$APP"   # Finder re-reads the icon
codesign --force --deep -s - "$APP" >/dev/null 2>&1 || echo "warning: ad-hoc signing failed"
[[ -n "${H4_APP:-}" ]] || /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP"
[[ -n "${H4_APP:-}" ]] && { echo "installed: $APP"; exit 0; }

# The old layout: the Terminal shortcut, the in-project app, ~/Applications and its Desktop symlink.
rm -f "$HOME/Desktop/Heroes IV.command"
[[ -L "$HOME/Desktop/Heroes IV" ]] && rm -f "$HOME/Desktop/Heroes IV"
[[ -d "$HOME/Applications/Heroes IV.app" ]] && rm -rf "$HOME/Applications/Heroes IV.app"
echo "installed: $APP"
