"""Gives the Heroes IV fonts Ukrainian glyphs in their Windows-1251 slots.

The fonts cover codes 32..255 as Windows-1252; the translated text is
written in Windows-1251. Cyrillic letters that look like Latin ones
(А В Е К М Н О Р С Т Х І Ї Ё, а е о р с у х і ї ё) get a copy of the game's
own Latin glyph, so most of a Ukrainian line is drawn in the original face.
The rest are rendered by CoreText (tools/glyphs) from a system font with
Cyrillic: capitals sized so H is as tall as the game's H, small letters so
x is as tall as the game's x, with the game's 1-pixel right bearing.
Punctuation both code pages share (« » – — „ “ ” ‘ ’ …) keeps its original glyph.

    build_fonts.py <in dir with font.*.h4d> <out dir> [preview dir]
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h4font

GLYPHS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glyphs')

# Windows-1251 code -> Windows-1252 code of the Latin look-alike.
HOMOGLYPHS = {
    0xC0: ord('A'), 0xC2: ord('B'), 0xC5: ord('E'), 0xCA: ord('K'), 0xCC: ord('M'),
    0xCD: ord('H'), 0xCE: ord('O'), 0xD0: ord('P'), 0xD1: ord('C'), 0xD2: ord('T'),
    0xD5: ord('X'), 0xB2: ord('I'), 0xAF: 0xCF, 0xA8: 0xCB,
    0xE0: ord('a'), 0xE5: ord('e'), 0xEE: ord('o'), 0xF0: ord('p'), 0xF1: ord('c'),
    0xF3: ord('y'), 0xF5: ord('x'), 0xB3: ord('i'), 0xBF: 0xEF, 0xB8: 0xEB,
}
# Cyrillic letters and marks with no look-alike, rendered from a system font.
RENDERED = [c for c in list(range(0xC0, 0x100)) + [0xA5, 0xB4, 0xAA, 0xBA, 0xB9] if c not in HOMOGLYPHS]

# Game font family -> (system font, antialiased).
FACES = {
    'Prose_Antique': ('GillSans-SemiBold', True),
    'Script': ('SnellRoundhand-Bold', True),
    'Small Fonts': ('Geneva', False),
}


def family(name):
    for k in FACES:
        if k in name:
            return k
    raise KeyError(name)


def render(face, pt, cell, base, aa, text):
    out = subprocess.run([GLYPHS, 'render', face, '%.2f' % pt, str(cell), str(base), '1' if aa else '0', text],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    glyphs = []
    for line in out:
        w, _, hexpx = line.partition(' ')
        glyphs.append((int(w), bytes.fromhex(hexpx)))
    return glyphs


def ink_rows(w, h, px, threshold=60):
    rows = [y for y in range(h) if any(px[y * w + x] > threshold for x in range(w))]
    return (rows[0], rows[-1]) if rows else (0, -1)


def fit(font, face, aa, ch='H'):
    """(point size, baseline row) at which ch is as tall as the game's."""
    w, h, _, _, px = font.glyph(ord(ch))
    top, bottom = ink_rows(w, h, px)
    want = bottom - top + 1
    best = None
    pt = want * (1.0 if ch == 'H' else 1.4)
    for _ in range(40):
        (rw, rpx), = render(face, pt, h, bottom, aa, ch)
        t, b = ink_rows(rw, h, rpx)
        got = b - t + 1
        err = abs(got - want)
        if best is None or err < best[0]:
            best = (err, pt)
        if got == want:
            break
        pt *= want / max(got, 1)
        pt += 0.25 if got < want else -0.25
    return best[1], bottom


def convert(px, aa):
    if aa:
        return bytearray(min(240, v * 240 // 255) for v in px)
    return bytearray(240 if v > 127 else 0 for v in px)


def pad(w, h, px, left, right):
    out = bytearray()
    for y in range(h):
        out += bytes(left) + px[y * w:(y + 1) * w] + bytes(right)
    return w + left + right, out


def build(path_in, path_out):
    name = os.path.basename(path_in)
    font = h4font.Font(open(path_in, 'rb').read())
    fam = family(name)
    face, aa = FACES[fam]
    left = 1 if fam == 'Small Fonts' else 0
    for code, latin in HOMOGLYPHS.items():
        if code >= font.first and latin >= font.first:
            w, h, c, d, px = font.glyph(latin)
            g = font.glyph(code)
            g[0], g[2], g[3], g[4] = w, c, d, bytearray(px)
    sizes = {'H': fit(font, face, aa, 'H'), 'x': fit(font, face, aa, 'x')}
    text = bytes(RENDERED).decode('cp1251')
    for case, (pt, base) in sizes.items():
        for code, ch, (w, px) in zip(RENDERED, text, render(face, pt, font.size, sizes['H'][1], aa, text)):
            small = ch.islower() or ch == '№'
            if (case == 'x') != small or code < font.first or w == 0:
                continue
            w2, px2 = pad(w, font.size, convert(px, aa), left, 1)
            g = font.glyph(code)
            g[0], g[2], g[3], g[4] = w2, 0, 0, px2
    open(path_out, 'wb').write(font.encode())
    return font, face, sizes


def line(font, data):
    """A PGM image of a line of text set with the font."""
    h = font.size
    glyphs = [font.glyph(c) for c in data if c >= font.first]
    W = sum(g[0] for g in glyphs) + 4
    img = bytearray(W * h)
    x0 = 2
    for w, _, _, _, px in glyphs:
        for y in range(h):
            for x in range(w):
                img[y * W + x0 + x] = px[y * w + x]
        x0 += w
    return b'P5 %d %d 255\n' % (W, h) + bytes(img)


SAMPLE = 'Treasure Chest — Скриня зі скарбом: «Флакон кислоти». Ґанок, Єва, Їжак, щука, ЖЮЯ!'

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    prev = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        if not name.startswith('font.'):
            continue
        font, face, sizes = build(os.path.join(src, name), os.path.join(dst, name))
        print(f"{name}: {face} H {sizes['H'][0]:.2f}pt x {sizes['x'][0]:.2f}pt")
        if prev:
            open(os.path.join(prev, name + '.pgm'), 'wb').write(line(font, SAMPLE.encode('cp1251')))
