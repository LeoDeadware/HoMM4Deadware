#!/bin/bash
# The DMG carries only our tools (kit R-L5): lifter, runtime libraries, h4's own objects, the
# translation without English text, our voice-over. Never lifted or generated game code, never game
# data. Scans every file of the image (DMG=path, default .cache/dmg/Heroes IV.dmg; tools/make_dmg.sh):
#   1. no lifted code: no Mach-O / archive / object defining lifted functions (more than 100
#      recomp::gen::f_XXXXXXXX: h4/src's overrides define a few; any f_X_lifted) or kLiftedFunctions, no gen_*.cpp / table.cpp;
#   2. no game file: no file with the content (sha1) of a file of the GOG game (H4Port/game), no PE
#      image (MZ), no 64-byte window of heroes4.exe's code (96 fixed samples) in any file;
#   3. no /Users/ path in any file (build paths in binaries, home paths in scripts);
#   4. tools/release_check.sh PASS (ALLOW_HD_PACKS=1).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DMG="${DMG:-$ROOT/.cache/dmg/Heroes IV.dmg}"
[[ -f "$DMG" ]] || { echo "dmg_no_game_code: no $DMG (tools/make_dmg.sh)"; exit 2; }
mkdir -p "$ROOT/.cache/tmp"
MNT="$(mktemp -d "$ROOT/.cache/tmp/dmgscan.XXXX")"
hdiutil attach -nobrowse -readonly -mountpoint "$MNT" "$DMG" >/dev/null || { echo "dmg_no_game_code: FAIL cannot mount"; exit 1; }
fails=0
python3 -I - "$MNT" "$ROOT/game" <<'PY' || fails=1
import hashlib, os, re, subprocess, sys
root, game = sys.argv[1], sys.argv[2]
bad, sha = [], set()
for d, _, fs in os.walk(game):
    for f in fs:
        p = os.path.join(d, f)
        if os.path.isfile(p) and os.path.getsize(p) >= 256:
            h = hashlib.sha1()
            with open(p, 'rb') as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b''):
                    h.update(chunk)
            sha.add(h.hexdigest())
exe = open(os.path.join(game, 'heroes4.exe'), 'rb').read()
step = (len(exe) - 0x20000) // 96
wins = [w for w in (exe[0x1000 + i * step:0x1000 + i * step + 64] for i in range(96)) if len(set(w)) > 16]
for d, _, fs in os.walk(root):
    for f in fs:
        p = os.path.join(d, f)
        if os.path.islink(p) or not os.path.isfile(p):
            continue
        rel = os.path.relpath(p, root)
        if re.fullmatch(r'gen_\d+\.(cpp|o)|table\.(cpp|o)', f):
            bad.append(f'{rel}: lifted code file')
        b = open(p, 'rb').read()
        if b[:2] == b'MZ':
            bad.append(f'{rel}: Windows PE image')
        if len(b) >= 256 and hashlib.sha1(b).hexdigest() in sha:
            bad.append(f'{rel}: a file of the game')
        hits = sum(1 for w in wins if w in b)
        if hits >= 2:
            bad.append(f'{rel}: {hits} windows of heroes4.exe code')
        if b'/Users/' in b:
            i = b.index(b'/Users/')
            bad.append(f'{rel}: a /Users/ path ({b[i:i + 60].split(bytes(1))[0].decode("latin-1")})')
        if b[:4] in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe') or b[:8] == b'!<arch>\n':
            nm = subprocess.run(['nm', '-gU', p], capture_output=True, text=True).stdout
            # h4/src's own overrides (lifter.manifest replace lines) define a few recomp::gen::f_X;
            # lifted code defines thousands, the renamed originals (f_X_lifted) and the table
            n = len(re.findall(r' [TtSD] __ZN6recomp3gen\d+f_[0-9A-F]{8}', nm))
            lifted = len(re.findall(r' [TtSD] __ZN6recomp3gen\d+f_[0-9A-F]{8}_lifted', nm))
            if n > 100 or lifted or 'kLiftedFunctions' in nm:
                bad.append(f'{rel}: lifted code ({n} lifted functions)')
print(f'scanned {root}: {len(wins)} exe windows, {len(sha)} game files')
for x in bad[:30]:
    print('  BAD', x)
sys.exit(1 if bad else 0)
PY
hdiutil detach -quiet "$MNT"; rmdir "$MNT" 2>/dev/null
ALLOW_HD_PACKS=1 bash "$ROOT/tools/release_check.sh" "$DMG" | tail -1 | grep -q PASS || { echo "release_check FAIL"; fails=1; }
(( fails )) && { echo "dmg_no_game_code: FAIL"; exit 1; }
echo "dmg_no_game_code: PASS"
