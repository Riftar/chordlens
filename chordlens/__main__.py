"""CLI: python3 -m chordlens SONG.wav"""

import argparse
import json
import sys

from .detect import analyze


def main(argv=None):
    ap = argparse.ArgumentParser(prog="chordlens",
                                 description="Offline chord detection from a WAV file")
    ap.add_argument("wav", help="input WAV (16-bit PCM; convert mp3 first: ffmpeg -i in.mp3 out.wav)")
    ap.add_argument("--json", action="store_true", help="emit segments as JSON")
    args = ap.parse_args(argv)
    segs = analyze(args.wav)
    if args.json:
        print(json.dumps([{"start": a, "end": b, "chord": c} for a, b, c in segs]))
    else:
        for a, b, c in segs:
            print(f"{a:7.2f} - {b:7.2f}  {c}")
    if not segs:
        print("no chords detected", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
