"""Heroes IV bitmap fonts (font.*.h4d).

Header: u16 1, u8 ?, u8 size (glyph height), u8 line height, u8 ascent,
u16 ?, 3 x u8 0, then a short record of unknown use, then one glyph per
code from 32 to 255 (223 in Small Fonts): u32 width, u32 height (= size),
u32 ?, u32 advance-or-0, and width x height alpha bytes, row by row.
The glyph chain is found by trying start offsets until it runs exactly to
the end of the data.

    h4font.py dump <font.h4d> <out.pgm>   all glyphs on one sheet
"""
import struct
import sys


class Font:
    def __init__(self, b):
        self.b = b
        self.size, self.line, self.ascent = b[3], b[4], b[5]
        for start in range(11, 2000):
            glyphs = self._chain(start)
            if glyphs:
                self.start, self.glyphs = start, glyphs
                break
        else:
            raise ValueError('no glyph chain')
        self.first = 256 - len(self.glyphs)

    def _chain(self, q):
        b, out = self.b, []
        while q + 16 <= len(b):
            w, h, c, d = struct.unpack_from('<4I', b, q)
            if h != self.size or w > 96:
                return None
            out.append([w, h, c, d, bytearray(b[q + 16:q + 16 + w * h])])
            q += 16 + w * h
        return out if q == len(b) and len(out) >= 200 else None

    def glyph(self, code):
        return self.glyphs[code - self.first]

    def encode(self):
        out = bytearray(self.b[:self.start])
        for w, h, c, d, px in self.glyphs:
            out += struct.pack('<4I', w, h, c, d) + bytes(px)
        return bytes(out)


def sheet(font, codes):
    """A PGM image of the given glyphs side by side (white on black)."""
    h = font.size
    widths = [font.glyph(c)[0] + 2 for c in codes]
    W = sum(widths)
    img = bytearray(W * h)
    x0 = 0
    for c, wd in zip(codes, widths):
        w, _, _, _, px = font.glyph(c)
        for y in range(h):
            for x in range(w):
                img[y * W + x0 + x] = px[y * w + x]
        x0 += wd
    return b'P5 %d %d 255\n' % (W, h) + bytes(img)


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        f = Font(open(sys.argv[2], 'rb').read())
        print(f'size {f.size} line {f.line} ascent {f.ascent} start {f.start} '
              f'glyphs {len(f.glyphs)} first {f.first}')
        for code in (ord('A'), ord('a'), 0xC0, 0xC4, 0xE9):
            w, h, c, d, px = f.glyph(code)
            print(hex(code), 'w', w, 'c', c, 'adv', d, 'max', max(px), sorted(set(px))[:12])
        open(sys.argv[3], 'wb').write(sheet(f, range(f.first, 256)))
