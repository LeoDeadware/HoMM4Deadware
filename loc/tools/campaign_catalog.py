"""Builds a catalog of the player-visible strings of a campaign file.

    campaign_catalog.py <extract/game_maps.X.h4d> <catalog/X.json>

Keeps prose and titles (strings with a space), drops object-type keys
such as "mountains.Grass rough.17" (a dot followed by a non-space with no
sentence break). The campaign name and description in the header are
always kept. Existing translations in the catalog are preserved."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import campaign_text as ct


def visible(t):
    if ' ' not in t:
        return False
    if re.search(r'\.\S', t) and not re.search(r'[.!?]["\')]*\s', t):
        return False
    return True


def build(src, out):
    old = {}
    if os.path.exists(out):
        old = {e['en']: e['uk'] for e in json.load(open(out))}
    items, seen = [], set()
    for k, r in enumerate(ct.extract(src)):
        t = r['en']
        part = r['part']
        if part == 'header':
            where = 'campaign name' if not items else 'campaign description'
            ok = len(t) > 1
        else:
            where = 'map %d' % (int(part[3:]) + 1)
            ok = visible(t)
        if ok and t not in seen:
            seen.add(t)
            items.append({'id': len(items), 'where': where, 'en': t, 'uk': old.get(t, '')})
    json.dump(items, open(out, 'w'), ensure_ascii=False, indent=1)
    return items


if __name__ == '__main__':
    items = build(sys.argv[1], sys.argv[2])
    print(f'{sys.argv[2]}: {len(items)} strings, {sum(len(i["en"].split()) for i in items)} words')
