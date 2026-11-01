"""Ukrainian campaign voice-over: packs loc/voice/raw/<clip>.mp3 into the
sound.Voice_Over.<clip>.h4d entries of the archives that hold them
(loc/voice/clips.json maps each clip to the text it reads).

An entry is a 19-byte header and an MP3 stream: u8 1, u16 0, u8 bits (16),
u8 channels, u32 rate, u32 decoded PCM bytes, u16 1 (MP3), u32 MP3 size.
The originals are 44.1 kHz stereo 128 kbit/s; the voice-over is re-encoded
to match.
"""
import json
import os
import struct
import subprocess
import tempfile

LOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(LOC, 'voice', 'raw')
RATE, CHANNELS = 44100, 2


def entry(mp3_path):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'v.mp3')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp3_path, '-ar', str(RATE),
                        '-ac', str(CHANNELS), '-b:a', '128k', '-map_metadata', '-1',
                        '-id3v2_version', '0', '-write_xing', '0', out], check=True)
        mp3 = open(out, 'rb').read()
        pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', out, '-f', 's16le', '-'],
                             check=True, capture_output=True).stdout
    head = struct.pack('<BHBBIIHI', 1, 0, 16, CHANNELS, RATE, len(pcm), 1, len(mp3))
    return head + mp3


def build(archives):
    """{archive file name: [entry names]} of the game -> {archive: {entry: bytes}}
    for every clip that has a recording."""
    clips = json.load(open(os.path.join(LOC, 'voice', 'clips.json')))
    out = {}
    for c in clips:
        src = os.path.join(RAW, c['clip'] + '.mp3')
        if not os.path.exists(src):
            continue
        name = f'sound.Voice_Over.{c["clip"]}.h4d'
        blob = None
        for archive, names in archives.items():
            if name in names:
                blob = blob or entry(src)
                out.setdefault(archive, {})[name] = blob
    return out
