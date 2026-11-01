"""Extracts the text of Heroes IV campaign files (game_maps.*.h4d, .h4c).

A campaign is an uncompressed header (H4CAMPAIGN, its name, description
and the scenario list) followed by one gzip stream per scenario map. Maps
are serialised sequentially; their text is stored as Pascal strings: a
u16 length and that many Windows-1252 bytes. Strings are found by scanning
for a u16 length followed by that many printable bytes that read as prose
or a name (binary data that happens to look like a short string is
filtered out by the heuristics below).

    campaign_text.py extract <campaign.h4d> <out.json>
"""
import gzip
import json
import re
import sys
import zlib

PRINTABLE = set(range(32, 127)) | {9, 10, 13} | set(range(0x80, 0x100))


def split_parts(b):
    """[(kind, offset, bytes)]: the header and each gzip map stream."""
    starts = [i for i in range(len(b) - 3) if b[i:i + 3] == b'\x1f\x8b\x08']
    parts = [('header', 0, b[:starts[0]] if starts else b)]
    for n, s in enumerate(starts):
        d = zlib.decompressobj(31)
        out = d.decompress(b[s:])
        used = len(b) - s - len(d.unused_data)
        parts.append(('map%d' % n, s, out, used))
    return parts


def looks_like_text(s):
    if len(s) < 2:
        return False
    if not all(c in PRINTABLE for c in s):
        return False
    t = s.decode('cp1252', 'replace')
    letters = sum(ch.isalpha() for ch in t)
    if letters < max(2, len(t) * 0.5):
        return False
    # Resource names and identifiers are not shown to the player.
    if re.fullmatch(r'[\w.\-]+\.(h4d|h4c|h4s|bik|wav|mp3)', t, re.I):
        return False
    return True


def strings(buf):
    """[(offset of the length, text bytes)] of plausible Pascal strings."""
    def at(i):
        L = buf[i] | buf[i + 1] << 8
        if 2 <= L <= 8000 and i + 2 + L <= len(buf):
            s = buf[i + 2:i + 2 + L]
            if looks_like_text(s):
                return s
        return None

    out = []
    i = 0
    n = len(buf)
    while i + 2 < n:
        s = at(i)
        if s is not None:
            # A length whose high byte is 0x00..0x1F can also be read one byte
            # early (e.g. 00 04 0D 'T'... = a false 1024-byte string starting
            # with CR); the longer reading one byte later is the real one.
            t = at(i + 1) if i + 3 < n else None
            if t is not None and len(t) > len(s):
                i, s = i + 1, t
            out.append((i, s))
            i += 2 + len(s)
            continue
        i += 1
    return out


def extract(path):
    b = open(path, 'rb').read()
    items = []
    for part in split_parts(b):
        kind, off, data = part[0], part[1], part[2]
        for pos, s in strings(data):
            items.append({'part': kind, 'pos': pos, 'en': s.decode('cp1252')})
    return items


if __name__ == '__main__':
    if sys.argv[1] == 'extract':
        items = extract(sys.argv[2])
        json.dump(items, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
        words = sum(len(i['en'].split()) for i in items)
        print(f'{sys.argv[2]}: {len(items)} strings, {words} words')


# ---- rebuilding -------------------------------------------------------------

import struct


def parse_header(b):
    """(prefix bytes before the name, name, desc, map sizes, header end)."""
    p = 0x21
    n = struct.unpack_from('<H', b, p)[0]
    name = b[p + 2:p + 2 + n]
    p += 2 + n
    n = struct.unpack_from('<H', b, p)[0]
    desc = b[p + 2:p + 2 + n]
    p += 2 + n
    count = struct.unpack_from('<H', b, p)[0]
    sizes = list(struct.unpack_from('<%dI' % count, b, p + 2))
    return b[:0x21], name, desc, sizes, p + 2 + 4 * count


def replace_strings(buf, table):
    """Rewrites the Pascal strings of buf found in table {old: new}."""
    out = bytearray()
    last = 0
    for pos, s in strings(buf):
        new = table.get(s)
        if new is None:
            continue
        out += buf[last:pos] + struct.pack('<H', len(new)) + new
        last = pos + 2 + len(s)
    out += buf[last:]
    return bytes(out)


def rebuild(path, table, out_path):
    """Writes the campaign with every string in table {bytes: bytes}
    replaced (header and maps)."""
    b = open(path, 'rb').read()
    if b[30] == 0:
        # A single scenario (the tutorial): header, then one gzip stream.
        m = replace_strings(gzip.decompress(b[31:]), table)
        out = b[:31] + gzip.compress(m, 9, mtime=0)
        out = out[:12] + struct.pack('<I', len(out) - 16) + out[16:]
        open(out_path, 'wb').write(out)
        return out
    # The header ends with a u16 map count and a u32 size per map, right
    # before the first map's gzip stream. Everything before that (campaign
    # name, description and, in Winds of War, the conqueror choices) is
    # rewritten string by string.
    first = b.find(b'\x1f\x8b\x08')
    n = struct.unpack_from('<H', b, first - 2 - 4 * len(split_parts(b)[1:]))[0]
    sizes = struct.unpack_from('<%dI' % n, b, first - 4 * n)
    assert sum(sizes) == len(b) - first, 'unexpected campaign header'
    head = replace_strings(b[:first - 2 - 4 * n], table)
    maps, p = [], first
    for size in sizes:
        maps.append(gzip.decompress(b[p:p + size]))
        p += size
    blobs = [gzip.compress(replace_strings(m, table), 9, mtime=0) for m in maps]
    out = head + struct.pack('<H', n) + b''.join(struct.pack('<I', len(x)) for x in blobs)
    out += b''.join(blobs)
    out = out[:12] + struct.pack('<I', len(out) - 16) + out[16:]
    open(out_path, 'wb').write(out)
    return out
