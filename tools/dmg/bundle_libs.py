#!/usr/bin/env python3
"""Makes Mach-O files self-contained for the DMG: every non-system library they load (recursively:
Homebrew's SDL3, ffmpeg, glslang, innoextract's boost...) is copied into <frameworks>, its id set to
@rpath/<name>, every reference rewritten to @rpath/<name>, and every absolute rpath (build dirs,
/opt/homebrew) removed; each given executable gets the rpath <rpath>. Ad-hoc signed afterwards.

    bundle_libs.py <frameworks dir> <exe>:<rpath> [<exe>:<rpath> ...]
    e.g. bundle_libs.py App/Contents/Frameworks App/Contents/MacOS/h4-bin:@executable_path/../Frameworks
H4_FFMPEG_LIB=<dir>: libraries found there by name (tools/dmg/ffmpeg_lgpl.sh: the LGPL ffmpeg) are taken
instead of Homebrew's GPL build, replacing any copy already in <frameworks>.
"""
import os
import shutil
import subprocess
import sys


def deps(p):
    out = subprocess.run(['otool', '-L', p], capture_output=True, text=True, check=True).stdout.splitlines()[1:]
    own = subprocess.run(['otool', '-D', p], capture_output=True, text=True).stdout.splitlines()[1:]
    return [l.split()[0] for l in out if l.split() and l.split()[0] not in own]


def rpaths(p):
    lines = subprocess.run(['otool', '-l', p], capture_output=True, text=True).stdout.splitlines()
    return [lines[i + 2].split()[1] for i, l in enumerate(lines) if 'LC_RPATH' in l]


def run(*a):
    subprocess.run(a, check=True, capture_output=True)


def resolve(ref, origin):
    if ref.startswith('@loader_path/'):
        return os.path.realpath(os.path.join(os.path.dirname(origin), ref[13:]))
    if ref.startswith('@rpath/'):
        for rp in rpaths(origin):
            c = os.path.join(rp.replace('@loader_path', os.path.dirname(origin)), ref[7:])
            if os.path.exists(c):
                return os.path.realpath(c)
        return None
    return os.path.realpath(ref)


fw = os.path.abspath(sys.argv[1])
os.makedirs(fw, exist_ok=True)
ovr = os.environ.get('H4_FFMPEG_LIB', '')
ovr_names = {f for f in os.listdir(ovr) if f.endswith('.dylib')} if ovr else set()
for f in ovr_names & set(os.listdir(fw)):
    os.remove(os.path.join(fw, f))
roots = [a.rsplit(':', 1) for a in sys.argv[2:]]
todo = [os.path.abspath(e) for e, _ in roots] + [os.path.join(fw, f) for f in os.listdir(fw) if f.endswith('.dylib')]
done = set()
while todo:
    p = todo.pop()
    if p in done:
        continue
    done.add(p)
    os.chmod(p, 0o755)
    for ref in deps(p):
        if ref.startswith(('/usr/lib/', '/System/')):
            continue
        name = os.path.basename(ref)
        dst = os.path.join(fw, name)
        if not os.path.exists(dst):
            src = os.path.realpath(os.path.join(ovr, name)) if name in ovr_names else resolve(ref, p)
            if not src or not os.path.exists(src):
                sys.exit(f'bundle_libs: cannot find {ref} (from {p})')
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
            run('install_name_tool', '-id', '@rpath/' + name, dst)
        if ref != '@rpath/' + name:
            run('install_name_tool', '-change', ref, '@rpath/' + name, p)
        todo.append(dst)
    for rp in rpaths(p):
        if not rp.startswith('@'):
            run('install_name_tool', '-delete_rpath', rp, p)
    if p.endswith('.dylib'):
        run('install_name_tool', '-id', '@rpath/' + os.path.basename(p), p)
for e, rp in roots:
    if rp not in rpaths(e):
        run('install_name_tool', '-add_rpath', rp, e)
for p in done:
    subprocess.run(['strip', '-S', p], capture_output=True)  # no debug info: no build paths (OSO)
    run('codesign', '--force', '-s', '-', p)
print(f'bundle_libs: {len(done)} Mach-O files, {len([f for f in os.listdir(fw) if f.endswith(".dylib")])} in {fw}')
