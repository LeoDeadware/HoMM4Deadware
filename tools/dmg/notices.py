#!/usr/bin/env python3
"""THIRD_PARTY_NOTICES.txt for Heroes IV.app (the DMG app): every third-party part it redistributes.

    python3 -I tools/dmg/notices.py <app> <out.txt>

H4's variant of the kit's tools/notices.py: the parts are picked by what the app really carries
(Contents/Frameworks/*.dylib, Resources/build/bin/*), so a library that is bundled always has its notice
and nothing unshipped is listed. ffmpeg (LGPL 2.1+) gets its full license text and the source offer.
Exit 1 if a bundled library has no known notice (a DMG with an unexplained library is a release FAIL).
"""
import glob
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUILD = os.path.join(ROOT, 'h4', 'out', 'build', 'release')
HB = '/opt/homebrew/opt'
FF = os.path.join(ROOT, '.cache', 'ffmpeg-lgpl')
FF_V, FF_SHA = '9.0.2', '8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e'

FF_OFFER = f"""ffmpeg {FF_V} (libavcodec, libavformat, libavutil, libswscale, libswresample) is used under the
GNU Lesser General Public License version 2.1 or later (full text below). It is dynamically linked:
the .dylib files in Heroes IV.app/Contents/Frameworks can be replaced with your own build of the same
ffmpeg version. Built WITHOUT --enable-gpl and --enable-nonfree; only the MP3 and Bink decoders.

Source code: the unmodified release ffmpeg-{FF_V}.tar.xz from https://ffmpeg.org/releases/
(SHA-256 {FF_SHA}); the exact build script with its configure line is tools/dmg/ffmpeg_lgpl.sh in
https://github.com/LeoDeadware/HoMM4Deadware . On request (an issue in that repository) we send a copy
of the corresponding source code for at least three years after the last release of this app."""


def read(p):
    return open(p, encoding='utf-8', errors='replace').read().strip()


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    app, out = sys.argv[1:]
    fw = os.path.join(app, 'Contents', 'Frameworks')
    libs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(fw, '*.dylib')))
    bins = sorted(os.path.basename(p) for p in glob.glob(os.path.join(app, 'Contents', 'Resources', 'build', 'bin', '*')))
    # (name, applies?, [license files], extra text)
    deps = os.path.join(BUILD, '_deps')
    table = [
        ('x86recomp (librecomp_*.dylib, recomp_lift) - MIT', lambda l: l.startswith('librecomp_') or l == 'recomp_lift',
         [os.path.join(ROOT, 'third_party', 'x86recomp', 'LICENSE')], ''),
        ('Zydis (in recomp_lift) - MIT', lambda l: l == 'recomp_lift', [os.path.join(deps, 'zydis-src', 'LICENSE')], ''),
        ('Zycore (in recomp_lift) - MIT', lambda l: l == 'recomp_lift',
         glob.glob(os.path.join(deps, 'zydis-src', 'dependencies', 'zycore', 'LICENSE')), ''),
        ('Berkeley SoftFloat 3e (in librecomp_x87) - BSD-3-Clause', lambda l: l == 'librecomp_x87.dylib',
         [os.path.join(deps, 'softfloat-src', 'COPYING.txt')], ''),
        ('CORE-MATH (in librecomp_x87) - MIT', lambda l: l == 'librecomp_x87.dylib',
         [os.path.join(deps, 'coremath-src', 'LICENSE')], ''),
        ('SDL3 (libSDL3) - zlib', lambda l: l.startswith('libSDL3'), [f'{HB}/sdl3/LICENSE.txt'], ''),
        ('glslang (libglslang, libSPIRV) - BSD-3-Clause and others', lambda l: l.startswith(('libglslang', 'libSPIRV.')),
         [f'{HB}/glslang/LICENSE.txt'], ''),
        ('SPIRV-Tools (libSPIRV-Tools) - Apache-2.0', lambda l: l.startswith('libSPIRV-Tools'), [f'{HB}/spirv-tools/LICENSE'], ''),
        ('innoextract (unpacks your GOG installer) - zlib', lambda l: l == 'innoextract', [f'{HB}/innoextract/LICENSE'], ''),
        ('Boost (libboost_*, used by innoextract) - BSL-1.0', lambda l: l.startswith('libboost_'),
         [os.path.join(ROOT, 'tools', 'dmg', 'licenses', 'BSL-1.0.txt')], ''),
        ('liblzma from XZ Utils (used by innoextract) - 0BSD', lambda l: l.startswith('liblzma'), [f'{HB}/xz/COPYING.0BSD'], ''),
        ('Zstandard (libzstd, used by innoextract via Boost.Iostreams) - BSD-3-Clause', lambda l: l.startswith('libzstd'),
         [f'{HB}/zstd/LICENSE'], ''),
        ('ffmpeg (libav*, libsw*) - LGPL-2.1-or-later', lambda l: l.startswith(('libav', 'libsw')),
         [os.path.join(FF, 'COPYING.LGPLv2.1')], FF_OFFER),
    ]
    parts, covered = [], set()
    for name, hit, files, extra in table:
        used = [x for x in libs + bins if hit(x)]
        if not used:
            continue
        missing = [f for f in files if not os.path.exists(f)]
        if missing or not files:
            print(f'notices: {name}: license file missing {missing}', file=sys.stderr)
            return 1
        covered.update(used)
        body = '\n\n'.join(([extra] if extra else []) + [read(f) for f in files])
        parts.append(f'== {name}\n\n{body}')
    # inline notice blocks of our patches (AMD FidelityFX FSR1 in the x86recomp patch -> librecomp_gfx)
    for p in sorted(glob.glob(os.path.join(ROOT, 'patches', '*.patch'))):
        cur = []
        for line in open(p, encoding='utf-8', errors='replace').read().splitlines() + ['']:
            m = re.match(r'^\+\s*(//|#|\*|/\*)\s?(.*)$', line)
            if m:
                cur.append(m.group(2))
                continue
            if any('Copyright' in c for c in cur):
                parts.append(f'== {os.path.basename(p)} (inline notice, in librecomp_gfx)\n\n' + '\n'.join(cur).strip())
            cur = []
    unknown = [x for x in libs + bins if x not in covered and x not in ('squircle',)]
    if unknown:
        print(f'notices: no notice for bundled {unknown}', file=sys.stderr)
        return 1
    head = ('Heroes of Might and Magic IV for Mac (unofficial port): third-party software in this app and the\n'
            'licenses it is used under. Our own code: MIT (LICENSE in https://github.com/LeoDeadware/HoMM4Deadware).\n'
            'No game code or game data is included: the app builds them from your own GOG installer.\n\n')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(head + '\n\n'.join(parts) + '\n')
    print(f'notices: {len(parts)} notices -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
