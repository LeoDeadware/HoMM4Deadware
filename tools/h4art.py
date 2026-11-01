#!/usr/bin/env python3
"""Reads Heroes of Might and Magic IV resource archives (.h4r) and sprites (.h4d).

    h4art.py list    ARCHIVE [prefix]            entry names and sizes
    h4art.py bitmap  ARCHIVE NAME OUT.rgba       a bitmap_raw entry
    h4art.py sprite  ARCHIVE NAME OUT.rgba [N]   image N (default: the first
                                                 non-empty one) of a sprite

OUT.png writes a PNG; OUT.rgba is a small raw format for tools/collage.cpp: u32 width, u32 height,
then width*height RGBA bytes (alpha 0..255).

Formats (little-endian), as documented by the community (the GOG build):
  archive  "H4R" u8 ver, u32 index offset; index: u32 count, then per entry
           u32 offset, size, unpacked size, mtime; three u16-length strings
           (name, author path, alias); u32 type (1 stored, 3 gzip).
  bitmap   u32 ver, height, width, byte count, then BGR24 rows.
  sprite   image records: palette (u16 n, u16 1, u16 speed, u8 0, n-1 BGR;
           index 0 transparent), u16-length name, u8 kind (4 full, 1 delta,
           0 empty), u32 left, top, right, bottom, per row u16 x0, u16 x1,
           u32 offset of the row's opaque span, one palette index per span
           pixel, and for kind 4 one alpha nibble (0..15) per span pixel.
"""
import gzip
import struct
import sys
import zlib


def read_index(path):
    data = open(path, 'rb').read()
    if data[:3] != b'H4R':
        sys.exit(f"{path}: not an H4R archive")
    off = struct.unpack_from('<I', data, 4)[0]
    count = struct.unpack_from('<I', data, off)[0]
    off += 4
    entries = {}
    order = []
    for _ in range(count):
        offset, size, unpacked, _mtime = struct.unpack_from('<IIII', data, off)
        off += 16
        strs = []
        for _ in range(3):
            n = struct.unpack_from('<H', data, off)[0]
            strs.append(data[off + 2:off + 2 + n].decode('latin1'))
            off += 2 + n
        etype = struct.unpack_from('<I', data, off)[0]
        off += 4
        e = dict(name=strs[0], alias=strs[2], offset=offset, size=size, unpacked=unpacked, type=etype)
        entries[strs[0].lower()] = e
        order.append(e)
    return data, entries, order


def payload(data, entries, name):
    e = entries[name.lower()]
    while e['alias']:
        e = entries[e['alias'].lower()]
    blob = data[e['offset']:e['offset'] + e['size']]
    return gzip.decompress(blob) if e['type'] == 3 else blob


def write_rgba(path, w, h, px):
    """OUT.rgba (see above), or an RGBA PNG when the name ends in .png."""
    if path.lower().endswith('.png'):
        rows = b''.join(b'\x00' + bytes(px[4 * w * y:4 * w * (y + 1)]) for y in range(h))

        def chunk(tag, body):
            return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body))

        with open(path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
                    chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))
        return
    with open(path, 'wb') as f:
        f.write(struct.pack('<II', w, h))
        f.write(bytes(px))


def bitmap(raw):
    _ver, h, w, _n = struct.unpack_from('<IIII', raw, 0)
    src = raw[16:]
    px = bytearray(w * h * 4)
    for i in range(w * h):
        b, g, r = src[3 * i], src[3 * i + 1], src[3 * i + 2]
        px[4 * i:4 * i + 4] = bytes((r, g, b, 255))
    return w, h, px


def palette_at(b, pos):
    """The palette header at pos, or None."""
    if pos + 7 > len(b):
        return None
    n, one = struct.unpack_from('<HH', b, pos)
    if not (1 <= n <= 256 and one == 1 and b[pos + 6] == 0):
        return None
    q = pos + 7 + (n - 1) * 3
    if q + 3 > len(b):
        return None
    ln = struct.unpack_from('<H', b, q)[0]
    name = b[q + 2:q + 2 + ln]
    if not (1 <= ln <= 512 and len(name) == ln and all(32 <= c < 127 for c in name)):
        return None
    if q + 2 + ln >= len(b) or b[q + 2 + ln] not in (0, 1, 4):
        return None
    pal = [(0, 0, 0)] + [(b[pos + 7 + 3 * i + 2], b[pos + 7 + 3 * i + 1], b[pos + 7 + 3 * i])
                         for i in range(n - 1)]
    return pal, q


def sprite_images(b):
    """Every image record in a sprite file: (name, kind, box, rgba bytes)."""
    images = []
    pos = 0
    while pos < len(b):
        found = palette_at(b, pos)
        if not found:
            pos += 1
            continue
        pal, q = found
        ln = struct.unpack_from('<H', b, q)[0]
        name = b[q + 2:q + 2 + ln].decode('latin1')
        p = q + 2 + ln
        kind = b[p]
        left, top, right, bottom = struct.unpack_from('<iiii', b, p + 1)
        p += 17
        w, h = right - left, bottom - top
        if kind == 0 or w <= 0 or h <= 0 or w > 4096 or h > 4096:
            images.append((name, kind, (left, top, right, bottom), None))
            pos = p
            continue
        rows = [struct.unpack_from('<HHI', b, p + 8 * y) for y in range(h)]
        p += 8 * h
        npix = sum(max(0, x1 - x0) for x0, x1, _ in rows)
        idx = b[p:p + npix]
        p += npix
        alpha = None
        if kind == 4:
            alpha = b[p:p + (npix + 1) // 2]
            p += (npix + 1) // 2
        # Row spans are relative to the image box in some files and absolute
        # in others: relative when they all fit inside the box's width.
        base = 0 if all(x1 <= w for _x0, x1, _o in rows) else left
        px = bytearray(w * h * 4)
        k = 0
        for y, (x0, x1, _off) in enumerate(rows):
            for x in range(x0, x1):
                i = idx[k] if k < len(idx) else 0
                a = 255
                if alpha is not None:
                    nib = alpha[k >> 1] >> (4 * (k & 1)) & 15 if (k >> 1) < len(alpha) else 15
                    a = nib * 17
                if i == 0:
                    a = 0
                r, g, bb = pal[i] if i < len(pal) else (0, 0, 0)
                o = 4 * (y * w + (x - base)) if 0 <= x - base < w else None
                if o is not None:
                    px[o:o + 4] = bytes((r, g, bb, a))
                k += 1
        images.append((name, kind, (left, top, right, bottom), px))
        pos = p
    return images


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, archive = sys.argv[1], sys.argv[2]
    data, entries, order = read_index(archive)
    if cmd == 'list':
        prefix = sys.argv[3].lower() if len(sys.argv) > 3 else ''
        for e in order:
            if e['name'].lower().startswith(prefix):
                print(f"{e['unpacked']:>9} {e['name']}" + (f" -> {e['alias']}" if e['alias'] else ''))
    elif cmd == 'bitmap':
        w, h, px = bitmap(payload(data, entries, sys.argv[3]))
        write_rgba(sys.argv[4], w, h, px)
        print(w, h)
    elif cmd == 'sprite':
        imgs = sprite_images(payload(data, entries, sys.argv[3]))
        want = int(sys.argv[5]) if len(sys.argv) > 5 else None
        full = [im for im in imgs if im[3] is not None and not im[0].startswith('shadow')]
        if not full:
            sys.exit('no image')
        name, _kind, box, px = full[want] if want is not None else full[0]
        w, h = box[2] - box[0], box[3] - box[1]
        write_rgba(sys.argv[4], w, h, px)
        print(name, w, h)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
