"""Interface text of Heroes IV (text.h4r): catalogs and rebuilt tables.

The tables in text.h4r are spreadsheets: u32 row count, then per row a u16
cell count and that many u16-length strings (Windows-1252); a strings.*
table is followed by a sorted index of its rows, kept as it is (only cell
values change, never the keys it sorts by).

    ui_text.py extract <text.h4r>     writes catalog/UI.<table>.json

A catalog lists every distinct English string once, with the cells
("row:column") it fills, so one translation covers all its uses.
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import h4r

# archive entry -> [(catalog name, columns shown to the player, key columns)]
TABLES = {
    'table.Interface.h4d': [('UI.Interface', (2, 3), (0, 1))],
    'strings.Text.h4d': [('UI.Text', (1,), (0,))],
    'table.creatures.h4d': [('Names.creatures', (1, 2, 3, 4), (0,)),
                            ('Help.creatures', (26, 27), (0,))],
    'table.Spells.h4d': [('Names.spells', (1, 2), (0,)),
                         ('Help.spells', (33, 35, 36), (0,)),
                         ('Flavor.spells', (34,), (0,))],
    'table.skills.h4d': [('Names.skills', (1,), (0,)),
                         ('Help.skills', (2,), (0,))],
    'table.buildings.h4d': [('Names.buildings', (1,), (0,)),
                            ('Help.buildings', (9,), (0,))],
    'table.Artifacts.h4d': [('Names.artifacts', (2, 3), (0,)),
                            ('Help.artifacts', (7,), (0,)),
                            ('Flavor.artifacts', (8, 9), (0,))],
    'table.Adventure Object.h4d': [('Objects', (4,), (0, 1, 3))],
    'table.heroes.h4d': [('Names.heroes', (1,), (0,)), ('Bio.heroes', (4,), (0,))],
    'table.random_names.h4d': [('Names.random', (1,), (0,))],
    'table.creature_abilities.h4d': [('Names.abilities', (1,), (0,)),
                                     ('Help.abilities', (2,), (0,))],
}


def parse(x):
    n = struct.unpack_from('<I', x, 0)[0]
    p = 4
    rows = []
    for _ in range(n):
        c = struct.unpack_from('<H', x, p)[0]
        p += 2
        row = []
        for _ in range(c):
            ln = struct.unpack_from('<H', x, p)[0]
            row.append(x[p + 2:p + 2 + ln])
            p += 2 + ln
        rows.append(row)
    return rows, x[p:]


def encode(rows, tail):
    out = [struct.pack('<I', len(rows))]
    for row in rows:
        out.append(struct.pack('<H', len(row)))
        for cell in row:
            out.append(struct.pack('<H', len(cell)) + cell)
    return b''.join(out) + tail


def shown(cell):
    return re.search(rb'[A-Za-z]{2}', cell) is not None


def extract(archive):
    d, es = h4r.read_dir(archive)
    for e in es:
        if e.name not in TABLES:
            continue
        rows, _ = parse(h4r.data(d, e))
        for cat, cols, keys in TABLES[e.name]:
            _extract_catalog(rows, cat, cols, keys)


def _extract_catalog(rows, cat, cols, keys):
    items, by_en = [], {}
    for r, row in enumerate(rows):
        if not row or not row[0]:
            continue
        where = '/'.join(row[k].decode('cp1252') for k in keys if k < len(row))
        for c in cols:
            if c >= len(row) or not shown(row[c]):
                continue
            en = row[c].decode('cp1252')
            if en not in by_en:
                by_en[en] = {'id': len(items), 'where': where, 'cells': [], 'en': en, 'uk': ''}
                items.append(by_en[en])
            by_en[en]['cells'].append(f'{r}:{c}')
    path = os.path.join(LOC, 'catalog', cat + '.json')
    if os.path.exists(path):
        # keep translations already made
        old = {it['en']: it['uk'] for it in json.load(open(path))}
        for it in items:
            it['uk'] = old.get(it['en'], '')
    json.dump(items, open(path, 'w'), ensure_ascii=False, indent=1)
    print(f'{cat}: {len(items)} strings, {sum(len(it["en"].split()) for it in items)} words')


def build(archive, encode_text):
    """{entry name: rebuilt table} for the tables with translations."""
    d, es = h4r.read_dir(archive)
    out = {}
    for e in es:
        if e.name not in TABLES:
            continue
        items = []
        for cat, _, _ in TABLES[e.name]:
            path = os.path.join(LOC, 'catalog', cat + '.json')
            if os.path.exists(path):
                items += [it for it in json.load(open(path)) if it.get('uk')]
        if not items:
            continue
        rows, tail = parse(h4r.data(d, e))
        for it in items:
            for cell in it['cells']:
                r, c = map(int, cell.split(':'))
                assert rows[r][c].decode('cp1252') == it['en'], (e.name, cell)
                rows[r][c] = encode_text(it['uk'])
        out[e.name] = encode(rows, tail)
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'extract':
        extract(sys.argv[2])
