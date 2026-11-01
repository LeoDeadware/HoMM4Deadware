"""Gets the translation ready for apply.py from the player's own copy of the
game: extracts the campaign files and fonts it rebuilds (loc/extract,
loc/fonts_en), puts the English text back into the catalogs (loc/uk ->
loc/catalog, matched by key, see export_uk.py), builds tools/glyphs and the
Cyrillic fonts (loc/fonts_uk).

    prepare.py <game dir>
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import campaign_text as ct
import h4r
import ui_text

ARCHIVES = {'Campaign.': 'updates.h4r', 'storm_campaign.': 'storm.h4r',
            'wow_campaign.': 'x2.h4r', 'single.': 'heroes4.h4r'}


def key(en):
    return hashlib.sha1(en.encode('utf-8')).hexdigest()[:12]


def entries(path):
    d, es = h4r.read_dir(path)
    return {e.name: (d, e) for e in es}


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(data)


def main(game):
    data = os.path.join(game, 'Data')
    archives = {a: entries(os.path.join(data, a))
                for a in set(ARCHIVES.values()) | {'text.h4r'}}

    # English candidates: every string of the campaign files, every table cell.
    found = {}
    for path in sorted(glob.glob(os.path.join(LOC, 'uk', '*.json'))):
        base = os.path.basename(path)[:-5]
        archive = next((a for p, a in ARCHIVES.items() if base.startswith(p)), None)
        if archive is None:
            continue
        name = 'game_maps.' + base + '.h4d'
        out = os.path.join(LOC, 'extract', name)
        write(out, h4r.data(*archives[archive][name]))
        for r in ct.extract(out):
            found[key(r['en'])] = r['en']
    for name in ui_text.TABLES:
        rows, _ = ui_text.parse(h4r.data(*archives['text.h4r'][name]))
        for row in rows:
            for cell in row:
                en = cell.decode('cp1252')
                found[key(en)] = en

    os.makedirs(os.path.join(LOC, 'catalog'), exist_ok=True)
    missing = 0
    for path in sorted(glob.glob(os.path.join(LOC, 'uk', '*.json'))):
        items = []
        for it in json.load(open(path)):
            en = found.get(it['key'])
            if en is None:
                missing += 1
                print(f'{os.path.basename(path)} #{it["id"]}: not in this copy of the game')
                continue
            items.append({k: v for k, v in it.items() if k not in ('key', 'uk')}
                         | {'en': en, 'uk': it['uk']})
        json.dump(items, open(os.path.join(LOC, 'catalog', os.path.basename(path)), 'w'),
                  ensure_ascii=False, indent=1)
    assert not missing, f'{missing} strings missing: is it GOG Complete 3.0?'

    # Fonts: the game's own, with Ukrainian glyphs drawn in.
    fonts_en = os.path.join(LOC, 'fonts_en')
    for name, de in archives['heroes4.h4r'].items():
        if name.startswith('font.'):
            write(os.path.join(fonts_en, name), h4r.data(*de))
    glyphs = os.path.join(HERE, 'glyphs')
    if not os.path.exists(glyphs):
        subprocess.run(['swiftc', '-O', '-o', glyphs, glyphs + '.swift'], check=True)
    os.makedirs(os.path.join(LOC, 'fonts_uk'), exist_ok=True)
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'build_fonts.py'),
                    fonts_en, os.path.join(LOC, 'fonts_uk')], check=True)
    print(f'{len(found)} game strings, catalogs and fonts ready')


if __name__ == '__main__':
    main(sys.argv[1])
