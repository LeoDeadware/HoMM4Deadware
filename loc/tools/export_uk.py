"""Writes the shareable form of the translation: loc/catalog/*.json and
loc/voice/clips.json with the game's English text replaced by a key (the
first 12 hex digits of its SHA-1), so the repository carries no game text.
prepare.py puts the English back from the player's own copy of the game.

    export_uk.py <catalog dir> <clips.json> <out loc dir>
"""
import glob
import hashlib
import json
import os
import sys


def key(en):
    return hashlib.sha1(en.encode('utf-8')).hexdigest()[:12]


def strip(items):
    out = []
    for it in items:
        it = dict(it)
        it['key'] = key(it.pop('en'))
        out.append(it)
    return out


def main(catalog, clips, dst):
    os.makedirs(os.path.join(dst, 'uk'), exist_ok=True)
    for path in sorted(glob.glob(os.path.join(catalog, '*.json'))):
        en = json.load(open(path))
        items = strip(en)
        seen = {}
        for it, src in zip(items, en):
            assert seen.setdefault(it['key'], src['en']) == src['en'], f'{path}: key collision'
        json.dump(items, open(os.path.join(dst, 'uk', os.path.basename(path)), 'w'),
                  ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(dst, 'voice'), exist_ok=True)
    json.dump(strip(json.load(open(clips))), open(os.path.join(dst, 'voice', 'clips.json'), 'w'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:4])
