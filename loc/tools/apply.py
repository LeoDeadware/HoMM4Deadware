"""Applies the Ukrainian translation to a Heroes IV game directory.

Rebuilds every campaign that has translated strings (loc/catalog/*.json,
entries with a non-empty "uk") and writes the Cyrillic fonts
(loc/fonts_uk), patching the archives of <game dir>/Data in place: the
campaigns live in updates.h4r (expansions in storm.h4r and x2.h4r, the tutorial in heroes4.h4r), the fonts in heroes4.h4r, the interface
text in text.h4r. Patch a fresh
copy of the archives each time (the new data is appended).

    apply.py <game dir>
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import campaign_text as ct
import h4r
import ui_text
import voice


def encode(s):
    # The few typographic marks Windows-1251 lacks fall back to its own.
    s = s.replace('’', "'").replace('ʼ', "'")
    return s.encode('cp1251', 'replace')


def check_keywords():
    # The game cuts a %keyword out of the text as a run of isalnum/_/% bytes,
    # with the byte sign-extended, so a Cyrillic letter or a guillemet next
    # to it joins the run and the keyword is left unreplaced.
    bad = []
    for path in sorted(glob.glob(os.path.join(LOC, 'catalog', '*.json'))):
        for it in json.load(open(path)):
            uk = it.get('uk') or ''
            for m in re.finditer(r'%[A-Za-z_][A-Za-z0-9_]*', uk):
                for c in uk[m.start() - 1:m.start()] + uk[m.end():m.end() + 1]:
                    if ord(c) > 127 or c.isalnum() or c == '_':
                        bad.append(f'{os.path.basename(path)} #{it["id"]}: {m.group()} next to {c!r}')
    assert not bad, 'keywords glued to text:\n' + '\n'.join(bad)


def main(game):
    check_keywords()
    data = os.path.join(game, 'Data')
    # Campaign file catalogs, by the archive that holds the campaign.
    archives = {'Campaign.': 'updates.h4r', 'storm_campaign.': 'storm.h4r',
                'wow_campaign.': 'x2.h4r', 'single.': 'heroes4.h4r'}
    patches = {a: {} for a in archives.values()}
    for path in sorted(glob.glob(os.path.join(LOC, 'catalog', '*.json'))):
        base = os.path.basename(path)[:-5]
        archive = next((a for p, a in archives.items() if base.startswith(p)), None)
        if archive is None:
            continue
        campaigns = patches[archive]
        items = json.load(open(path))
        table = {it['en'].encode('cp1252'): encode(it['uk']) for it in items if it.get('uk')}
        if not table:
            continue
        name = 'game_maps.' + base + '.h4d'
        src = os.path.join(LOC, 'extract', name)
        campaigns[name] = ct.rebuild(src, table, os.path.join(LOC, 'build', name))
        # Every map must still parse into as many strings as the original;
        # a misread string boundary would leave stale bytes and crash the map.
        old = [len(ct.strings(p[2])) for p in ct.split_parts(open(src, 'rb').read())]
        new = [len(ct.strings(p[2])) for p in ct.split_parts(campaigns[name])]
        assert old == new, f'{name}: string layout changed {old} -> {new}'
        print(f'{name}: {len(table)} strings')
    for archive, campaigns in patches.items():
        if campaigns and archive != 'heroes4.h4r':
            h4r.patch(os.path.join(data, archive), campaigns)
    tables = ui_text.build(os.path.join(data, 'text.h4r'), encode)
    if tables:
        h4r.patch(os.path.join(data, 'text.h4r'), tables)
        print(f'{len(tables)} interface tables')
    names = {a: {e.name for e in h4r.read_dir(os.path.join(data, a))[1]}
             for a in ('heroes4.h4r', 'storm.h4r', 'x2.h4r')}
    clips = voice.build(names)
    for archive in ('storm.h4r', 'x2.h4r'):
        if clips.get(archive):
            h4r.patch(os.path.join(data, archive), clips[archive])
    print(f'{sum(map(len, clips.values()))} voice-over entries')
    fonts_dir = os.path.join(LOC, 'fonts_uk')
    fonts = {n: open(os.path.join(fonts_dir, n), 'rb').read() for n in os.listdir(fonts_dir)}
    h4r.patch(os.path.join(data, 'heroes4.h4r'),
              {**fonts, **patches['heroes4.h4r'], **clips.get('heroes4.h4r', {})})
    print(f'{len(fonts)} fonts')


if __name__ == '__main__':
    os.makedirs(os.path.join(LOC, 'build'), exist_ok=True)
    main(sys.argv[1])
