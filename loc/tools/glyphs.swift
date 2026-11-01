// Renders glyphs for Heroes IV bitmap fonts with CoreText.
//
//   glyphs cover <font name> <text>
//       prints the characters of text the font has no glyph for
//   glyphs render <font name> <point size> <cell height> <baseline row> <aa 0|1> <text>
//       one line per character: "<width> <hex alpha bytes, row by row>",
//       the glyph cropped to its ink horizontally, in a cell of the given
//       height with its baseline on the given row (0 = top)

import CoreGraphics
import CoreText
import Foundation

let args = CommandLine.arguments

func ctFont(_ name: String, _ size: CGFloat) -> CTFont {
    CTFontCreateWithName(name as CFString, size, nil)
}

if args.count >= 4 && args[1] == "cover" {
    let font = ctFont(args[2], 12)
    var missing = ""
    for ch in args[3] {
        var units = Array(String(ch).utf16)
        var glyphs = [CGGlyph](repeating: 0, count: units.count)
        if !CTFontGetGlyphsForCharacters(font, &units, &glyphs, units.count) { missing.append(ch) }
    }
    print(CTFontCopyFullName(font) as String, "missing:", missing)
    exit(0)
}

guard args.count >= 8 && args[1] == "render" else {
    FileHandle.standardError.write("usage: glyphs cover|render ...\n".data(using: .utf8)!)
    exit(2)
}
let font = ctFont(args[2], CGFloat(Double(args[3])!))
let cellH = Int(args[4])!
let baseline = Int(args[5])!
let antialias = args[6] == "1"
let canvasW = cellH * 4

for ch in args[7] {
    let attr: [NSAttributedString.Key: Any] = [kCTFontAttributeName as NSAttributedString.Key: font,
                kCTForegroundColorFromContextAttributeName as NSAttributedString.Key: true]
    let line = CTLineCreateWithAttributedString(NSAttributedString(string: String(ch), attributes: attr))
    var px = [UInt8](repeating: 0, count: canvasW * cellH)
    let cs = CGColorSpaceCreateDeviceGray()
    px.withUnsafeMutableBytes { buf in
        let ctx = CGContext(data: buf.baseAddress, width: canvasW, height: cellH, bitsPerComponent: 8,
                            bytesPerRow: canvasW, space: cs, bitmapInfo: CGImageAlphaInfo.none.rawValue)!
        ctx.setAllowsAntialiasing(antialias)
        ctx.setShouldAntialias(antialias)
        ctx.setShouldSmoothFonts(false)
        ctx.setFillColor(gray: 1, alpha: 1)
        // CoreGraphics' origin is bottom-left: the baseline row from the top
        // is cellH - 1 - baseline from the bottom.
        ctx.textPosition = CGPoint(x: CGFloat(cellH), y: CGFloat(cellH - 1 - baseline) + 0.0)
        CTLineDraw(line, ctx)
    }
    var minX = canvasW, maxX = -1
    for y in 0..<cellH { for x in 0..<canvasW where px[y * canvasW + x] > 24 { minX = min(minX, x); maxX = max(maxX, x) } }
    if maxX < 0 { print("0 "); continue }
    var hex = ""
    for y in 0..<cellH {
        for x in minX...maxX { hex += String(format: "%02x", px[y * canvasW + x]) }
    }
    print("\(maxX - minX + 1) \(hex)")
}
