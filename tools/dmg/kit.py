#!/usr/bin/env python3
"""The DMG's build kit (Resources/build) from a build dir: only our code, never game code.

    python3 -I tools/dmg/kit.py <build dir> <kit dir> <frameworks dir>

bin/recomp_lift (our lifter) + bin/innoextract (unpacks the player's GOG installer; zlib licence),
lift/ (symbols, lifter.manifest), include/runtime/*.h (the headers lifted code includes),
src/lifted_table.cpp (runtime part of the lifted target), lib/*.o (h4's own sources) + link.txt
(the h4 link line with the lifted objects left out, libraries as @FW@/<name>), loc/ (the translation:
tools + uk catalogs without English text, Ukrainian voice clips; the public heroes4-mac layout),
wings/ is not here (Resources/wings). install_game.sh compiles the player's own lift with these.
"""
import os
import shlex
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# the public layout of loc/ (no English game text): this repo itself in heroes4-mac, else its sibling export
PUB = ROOT if os.path.exists(os.path.join(ROOT, '.publish-allow')) else os.path.join(os.path.dirname(ROOT), 'heroes4-mac')
build, kit, fw = (os.path.abspath(a) for a in sys.argv[1:4])
X = os.path.join(ROOT, 'third_party', 'x86recomp')
shutil.rmtree(kit, ignore_errors=True)
for d in ('bin', 'lift', 'include/runtime', 'src', 'lib'):
    os.makedirs(os.path.join(kit, d))
shutil.copy2(os.path.join(build, 'x86recomp', 'tools', 'lifter', 'recomp_lift'), os.path.join(kit, 'bin'))
shutil.copy2(os.path.realpath(shutil.which('innoextract') or '/opt/homebrew/bin/innoextract'),
             os.path.join(kit, 'bin', 'innoextract'))
shutil.copytree(os.path.join(ROOT, 'symbols'), os.path.join(kit, 'lift', 'symbols'))
shutil.copy2(os.path.join(ROOT, 'h4', 'lifter.manifest'), os.path.join(kit, 'lift'))
rt = os.path.join(X, 'src', 'runtime')
for d, _, fs in os.walk(rt):
    for f in fs:
        if f.endswith('.h'):
            dst = os.path.join(kit, 'include', 'runtime', os.path.relpath(os.path.join(d, f), rt))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(d, f), dst)
shutil.copy2(os.path.join(rt, 'lifted_table.cpp'), os.path.join(kit, 'src'))
cmd = subprocess.run(['ninja', '-C', build, '-t', 'commands', 'h4'], capture_output=True, text=True,
                     check=True).stdout.strip().splitlines()[-1]
link = shlex.split(cmd.split('&&')[1])
for a in link[1:link.index('-o')]:
    if a.endswith('.o') and '/h4.dir/' in a:
        name = os.path.basename(a)[:-6] + '.o'   # main.cpp.o -> main.o
        shutil.copy2(os.path.join(build, a), os.path.join(kit, 'lib', name))
        subprocess.run(['strip', '-S', os.path.join(kit, 'lib', name)], check=True)
# library args: the bundled names (what the h4 binary in the tested app loads)
libs = [l.split()[0] for l in subprocess.run(['otool', '-L', os.path.join(build, 'h4')], capture_output=True,
        text=True, check=True).stdout.splitlines()[1:] if not l.split()[0].startswith(('/usr/lib', '/System'))]
link_args = ['@FW@/' + os.path.basename(l) for l in libs]
open(os.path.join(kit, 'lib', 'link.txt'), 'w').write('\n'.join(link_args) + '\n')
# the translation (public layout: no English game text in it; prepare.py extracts it on the player's Mac)
loc = os.path.join(kit, 'loc')
shutil.copytree(os.path.join(PUB, 'loc', 'tools'), os.path.join(loc, 'tools'),
                ignore=shutil.ignore_patterns('__pycache__', 'glyphs'))
for f in ('apply.py', 'voice.py'):  # the newest (H4Port first, then the public export)
    shutil.copy2(os.path.join(ROOT, 'loc', 'tools', f), os.path.join(loc, 'tools'))
shutil.copytree(os.path.join(PUB, 'loc', 'uk'), os.path.join(loc, 'uk'))
os.makedirs(os.path.join(loc, 'voice'))
shutil.copy2(os.path.join(PUB, 'loc', 'voice', 'clips.json'), os.path.join(loc, 'voice'))
# the voice-over entries encoded here (voice.entry needs ffmpeg, which the player's Mac lacks)
sys.path.insert(0, os.path.join(ROOT, 'loc', 'tools'))
import voice  # noqa: E402
os.makedirs(os.path.join(loc, 'voice', 'entries'))
for f in sorted(os.listdir(os.path.join(ROOT, 'loc', 'voice', 'raw'))):
    if f.endswith('.mp3'):
        open(os.path.join(loc, 'voice', 'entries', f[:-4] + '.h4d'), 'wb').write(
            voice.entry(os.path.join(ROOT, 'loc', 'voice', 'raw', f)))
os.makedirs(os.path.join(loc, 'voice', 'raw'))
for f in os.listdir(os.path.join(loc, 'voice', 'entries')):  # build() looks for raw/<clip>.mp3: markers
    open(os.path.join(loc, 'voice', 'raw', f[:-4] + '.mp3'), 'wb').close()
# the glyph renderer, compiled here (a player's Mac may lack swiftc)
subprocess.run(['swiftc', '-O', '-o', os.path.join(loc, 'tools', 'glyphs'),
                os.path.join(loc, 'tools', 'glyphs.swift')], check=True, capture_output=True)
# the lifter and innoextract load their libraries from the app's Frameworks
subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(__file__), 'bundle_libs.py'), fw,
                os.path.join(kit, 'bin', 'recomp_lift') + ':@executable_path/../../../Frameworks',
                os.path.join(kit, 'bin', 'innoextract') + ':@executable_path/../../../Frameworks'], check=True)
print(f'kit: {kit}: {len(link_args)} libraries')
