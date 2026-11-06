#!/bin/bash
# The player's Mac builds the game (the DMG never carries game code or game data; the installer
# compiles with Apple Command Line Tools' clang):
#   install_game.sh <kit dir> <support dir> <out h4-bin> <GOG installer .exe> [progress file]
# kit (Resources/build, tools/install_app.sh H4_DMG=1): bin/innoextract, bin/recomp_lift, lift/,
# include/, src/, lib/ (h4's objects + link.txt), loc/ (the translation), ../../Frameworks.
# Steps: 1. Command Line Tools (clt.sh); 2. unpack the GOG installer -> <support>/game (heroes4.exe
# checked against GOG Complete 3.0); 3. lift heroes4.exe -> C++; 4. compile (all cores, nice);
# 5. link + ad-hoc sign; 6. the Ukrainian version <support>/game-uk (clone + loc/tools prepare/apply);
# 7. the icon from the GOG installer's icon. Resumable: finished steps are kept.
# Progress lines "N text" (0..100) go to the progress file (the launcher's window reads it).
set -uo pipefail
KIT=$1 SUP=$2 OUT=$3 SETUP=$4 PROG="${5:-/dev/null}"
EXE_SHA256=b7c2f6caeeba640b1c5f1d812b172938bb4dd4ec62e34ec93ad827bd1ffaec87
WORK="$SUP/build-work"
msg() { [[ "${H4_UI_LANG:-en}" == uk ]] && echo "$2" || echo "$1"; }
report() { echo "$1 $2" >> "$PROG"; echo "install_game: [$1%] $2"; }
die() { report 100 "$(msg ERROR ПОМИЛКА): $1"; exit 1; }
: > "$PROG"
mkdir -p "$WORK"
# 1. compiler
bash "$KIT/clt.sh" "$PROG" || die "$(msg "Command Line Tools are not installed" "Command Line Tools не встановлено")"
CXX="$(xcrun -f clang++)"
SDK="$(xcrun --show-sdk-path 2>/dev/null)"
[[ -d "$SDK" ]] || die "no macOS SDK in Command Line Tools (xcrun --show-sdk-path)"
report 2 "$(msg Compiler Компілятор): $("$CXX" --version | head -1)"
# 2. the game files from the player's own GOG installer
G="$SUP/game"
if [[ ! -f "$G/heroes4.exe" ]]; then
  report 3 "$(msg "Unpacking the GOG installer" "Розпаковую інсталятор GOG")"
  rm -rf "$G.tmp"
  "$KIT/bin/innoextract" -s -d "$G.tmp" "$SETUP" > "$WORK/inno.log" 2>&1 ||
    die "$(msg "cannot unpack" "не вдалося розпакувати") $(basename "$SETUP"): $(tail -1 "$WORK/inno.log")"
  [[ -f "$G.tmp/heroes4.exe" ]] || die "$(msg "no heroes4.exe in the installer" "в інсталяторі немає heroes4.exe")"
  mv "$G.tmp" "$G"
fi
[[ "$(shasum -a 256 "$G/heroes4.exe" | cut -d' ' -f1)" == "$EXE_SHA256" ]] ||
  die "$(msg "heroes4.exe is not from GOG Complete 3.0" "heroes4.exe не з GOG Complete 3.0")"
# 3. lift
if [[ ! -f "$WORK/gen/lift_report.txt" ]]; then
  report 8 "$(msg "Translating the game code (heroes4.exe)" "Перекладаю код гри (heroes4.exe)")"
  rm -rf "$WORK/gen"; mkdir -p "$WORK/gen"
  nice -n 10 "$KIT/bin/recomp_lift" --exe "$G/heroes4.exe" --symbols "$KIT/lift/symbols" \
    --manifest "$KIT/lift/lifter.manifest" --out "$WORK/gen" > "$WORK/lift.log" 2>&1 ||
    die "lift failed: $(tail -2 "$WORK/lift.log")"
fi
cp "$KIT/src/lifted_table.cpp" "$WORK/gen/zz_lifted_table.cpp"
# 4. compile (resumable: existing objects newer than their source are kept)
mkdir -p "$WORK/obj"
srcs=("$WORK"/gen/*.cpp); n=${#srcs[@]}
(( n > 1 )) || die "no generated code"
jobs=${H4_BUILD_JOBS:-$(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || sysctl -n hw.ncpu)}
mem=$(( $(sysctl -n hw.memsize) >> 30 )); (( jobs > mem / 2 )) && jobs=$(( mem / 2 )); (( jobs < 1 )) && jobs=1
FLAGS=(-isysroot "$SDK" -std=gnu++20 -O2 -g0 -DNDEBUG -arch arm64 -mmacosx-version-min=26.0 -fno-strict-aliasing
       -fnon-call-exceptions -ffp-contract=off -fno-fast-math -fno-omit-frame-pointer
       -mno-omit-leaf-frame-pointer -I "$KIT/include")
# paths hold spaces ("Application Support"): flags through a response file, names via -0
for f in "${FLAGS[@]}"; do printf '"%s"\n' "$f"; done > "$WORK/flags.rsp"
export CXX WORK
done_n() { ls "$WORK"/obj/*.o 2>/dev/null | wc -l | tr -d ' '; }
printf '%s\0' "${srcs[@]}" | xargs -0 -P "$jobs" -n 1 bash -c '
  s="$1"; o="$WORK/obj/$(basename "${s%.cpp}").o"
  [[ -f "$o" && "$o" -nt "$s" ]] && exit 0
  nice -n 10 "$CXX" @"$WORK/flags.rsp" -c "$s" -o "$o.tmp" 2>>"$WORK/compile.log" && mv "$o.tmp" "$o"' _ &
cpid=$!
while kill -0 $cpid 2>/dev/null; do
  report $((10 + 70 * $(done_n) / n)) "$(msg Compiling Компілюю) $(done_n)/$n"
  sleep 5
done
wait $cpid
(( $(done_n) == n )) || die "compile failed: $(grep -m2 error "$WORK/compile.log")"
# 5. link
report 81 "$(msg "Linking the game" "Збираю гру")"
FW="$(cd "$KIT/../../Frameworks" && pwd)"
libs=(); while read -r l; do [[ -n "$l" ]] && libs+=("${l//@FW@/$FW}"); done < "$KIT/lib/link.txt"
"$CXX" -isysroot "$SDK" -arch arm64 -mmacosx-version-min=26.0 -Wl,-headerpad_max_install_names -o "$OUT.tmp" \
  "$WORK"/obj/*.o "$KIT"/lib/*.o "${libs[@]}" -Wl,-rpath,@executable_path/../Frameworks > "$WORK/link.log" 2>&1 ||
  die "link failed: $(grep -m2 -i error "$WORK/link.log")"
codesign --force -s - "$OUT.tmp" >/dev/null 2>&1
mv "$OUT.tmp" "$OUT"
# 6. the Ukrainian version: a clone of the game, the translation applied (The Gathering Storm English)
if [[ ! -f "$SUP/game-uk/.uk-done" ]]; then
  report 85 "$(msg "Preparing the Ukrainian version" "Готую українську версію")"
  rm -rf "$SUP/game-uk" "$WORK/loc"; cp -c -R "$G" "$SUP/game-uk"; cp -R "$KIT/loc" "$WORK/loc"
  for a in heroes4.h4r updates.h4r text.h4r storm.h4r x2.h4r; do
    rm -f "$SUP/game-uk/Data/$a"; cp "$G/Data/$a" "$SUP/game-uk/Data/$a"
  done
  { /usr/bin/python3 -I "$WORK/loc/tools/prepare.py" "$G" && /usr/bin/python3 -I "$WORK/loc/tools/apply.py" "$SUP/game-uk"; } \
    > "$WORK/loc.log" 2>&1 || die "$(msg "translation failed" "переклад не вдався"): $(tail -1 "$WORK/loc.log")"
  touch "$SUP/game-uk/.uk-done"
fi
# 7. the app icon from the installer's own icon (tools/icon/make_icns.sh)
report 97 "$(msg "Making the icon" "Готую іконку")"
ico="$(ls "$G"/goggame-*.ico 2>/dev/null | head -1)"
[[ -n "$ico" ]] && bash "$KIT/make_icns.sh" "$ico" "$(dirname "$OUT")/../Resources/h4.icns" >/dev/null 2>&1 &&
  touch "$(dirname "$OUT")/../.." || true
rm -rf "$WORK"
report 100 "$(msg Done Готово)"
