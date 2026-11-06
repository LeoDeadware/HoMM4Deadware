#!/bin/bash
# A minimal LGPL ffmpeg for the DMG (Homebrew's is GPL: x264/x265). Same version as Homebrew's (ABI of
# libavcodec.63 etc.), only what the runtime uses: MP3 (Miles streams, audio/source.cpp) and Bink
# video + audio (hle/binkw32.cpp), swscale for the frames. minos 13.0 (below the app floor, macOS 26: fine). No --enable-gpl / --enable-nonfree.
# bundle_libs.py takes these instead of Homebrew's when H4_FFMPEG_LIB points here (make_dmg.sh does).
#   tools/dmg/ffmpeg_lgpl.sh  ->  .cache/ffmpeg-lgpl/lib/*.dylib
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
V=9.0.2
SHA=8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e   # = Homebrew formula's
SRC="$ROOT/.cache/ffmpeg-src"; OUT="$ROOT/.cache/ffmpeg-lgpl"
[[ -f "$OUT/lib/libavcodec.dylib" && "${1:-}" != "--force" ]] && { echo "ffmpeg_lgpl: $OUT ready"; exit 0; }
mkdir -p "$SRC"
[[ -f "$SRC/ffmpeg-$V.tar.xz" ]] || curl -fsSL -o "$SRC/ffmpeg-$V.tar.xz" "https://ffmpeg.org/releases/ffmpeg-$V.tar.xz"
echo "$SHA  $SRC/ffmpeg-$V.tar.xz" | shasum -a 256 -c - >/dev/null
rm -rf "$SRC/ffmpeg-$V"; tar -xJf "$SRC/ffmpeg-$V.tar.xz" -C "$SRC"
cd "$SRC/ffmpeg-$V"
 # neutral prefix: ffmpeg embeds its configure line (av*_configuration) in every dylib; no /Users path in the DMG
./configure --prefix=/h4-ffmpeg-lgpl --enable-shared --disable-static --disable-programs --disable-doc \
  --disable-everything --disable-autodetect --disable-network --disable-avdevice --disable-avfilter \
  --enable-avformat --enable-avcodec --enable-swscale --enable-swresample \
  --enable-decoder=mp3,mp3float,bink,binkaudio_rdft,binkaudio_dct \
  --enable-parser=mpegaudio --enable-demuxer=bink,mp3 --enable-protocol=file \
  --install-name-dir='@rpath' --extra-cflags=-mmacosx-version-min=13.0 \
  --extra-ldflags=-mmacosx-version-min=13.0 > "$SRC/configure.log" 2>&1 || { tail -20 "$SRC/configure.log"; exit 1; }
grep -q "License: LGPL" "$SRC/configure.log" || { echo "ffmpeg_lgpl: not LGPL"; exit 1; }
make -j"${H4_BUILD_JOBS:-3}" > "$SRC/make.log" 2>&1 || { tail -20 "$SRC/make.log"; exit 1; }
rm -rf "$SRC/dest" "$OUT"; make install DESTDIR="$SRC/dest" > /dev/null
mv "$SRC/dest/h4-ffmpeg-lgpl" "$OUT"
sed -i "" "s|/h4-ffmpeg-lgpl|$OUT|g" "$OUT"/lib/pkgconfig/*.pc
cp COPYING.LGPLv2.1 "$OUT/COPYING.LGPLv2.1"
echo "ffmpeg_lgpl: $OUT ($(grep 'License:' "$SRC/configure.log"))"
