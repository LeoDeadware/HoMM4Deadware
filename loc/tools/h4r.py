"""Reads Heroes IV .h4r resource archives.

Layout: "H4R\x05", u32 directory offset; the directory is a u32 entry count
then per entry: u32 data offset, u32 stored size, u32 size, u32 time,
u16 name length + name, u16 path length + path, u16 0, u32 kind (3),
and the entries' data, each a gzip stream (or stored when sizes match).
"""
import gzip
import struct
import sys


class Entry:
    def __init__(self, offset, stored, size, time, name, path, extra):
        self.offset, self.stored, self.size, self.time = offset, stored, size, time
        self.name, self.path, self.extra = name, path, extra


def _entry_at(d, p):
    """The entry at p, or None if p does not hold a plausible one."""
    if p + 20 > len(d):
        return None
    off, stored, size, t = struct.unpack_from('<IIII', d, p)
    if off >= len(d) or off + stored > len(d) or stored > size * 2 + 64:
        return None
    n = struct.unpack_from('<H', d, p + 16)[0]
    name = d[p + 18:p + 18 + n].rstrip(b'\0')
    if not (4 <= len(name) < 200) or not all(32 <= c < 127 for c in name) or b'.' not in name:
        return None
    q = p + 18 + n
    n = struct.unpack_from('<H', d, q)[0]
    if n > 260:
        return None
    rpath = d[q + 2:q + 2 + n].rstrip(b'\0')
    e = Entry(off, stored, size, t, name.decode('latin-1'), rpath.decode('latin-1'), b'')
    e.at = p
    return e, q + 2 + n


def read_dir(path):
    with open(path, 'rb') as f:
        d = f.read()
    if d[:4] != b'H4R\x05':
        raise ValueError(path + ': not an H4R archive')
    # The directory: right after the header, or at the end of the file
    # (updates.h4r, text.h4r), at the offset in the header.
    p = struct.unpack_from('<I', d, 4)[0]
    count = struct.unpack_from('<I', d, p)[0]
    p += 4
    out = []
    for i in range(count):
        r = _entry_at(d, p)
        if not r:
            raise ValueError(f'{path}: bad entry {i} at {p:X}')
        e, p = r
        out.append(e)
        if i + 1 == count:
            break
        # Trailing fields (links to other resources, kind) vary in length:
        # the next entry starts at the first offset that reads as one.
        for k in range(6, 4096):
            if _entry_at(d, p + k):
                e.extra = d[p:p + k]
                p += k
                break
        else:
            raise ValueError(f'{path}: no entry after {i} ({e.name})')
    return d, out


def data(d, e):
    raw = d[e.offset:e.offset + e.stored]
    if raw[:2] == b'\x1f\x8b':
        return gzip.decompress(raw)
    return raw


if __name__ == '__main__':
    d, es = read_dir(sys.argv[1])
    for e in es:
        print(f'{e.offset:08X} {e.stored:8d} {e.size:8d} {e.extra.hex()} {e.name}')


def patch(path, replacements):
    """Replaces entries of the archive at path in place: {name: new bytes}.
    The new data is appended and the entries' offset and sizes rewritten
    (the directory keeps its length). Entries are stored uncompressed."""
    d, es = read_dir(path)
    byname = {e.name: e for e in es}
    with open(path, 'r+b') as f:
        f.seek(0, 2)
        for name, blob in replacements.items():
            e = byname[name]
            off = f.tell()
            f.write(blob)
            hdr = struct.pack('<III', off, len(blob), len(blob))
            pos = f.tell()
            f.seek(e.at)
            f.write(hdr)
            f.seek(pos)
