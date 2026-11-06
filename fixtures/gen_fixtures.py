"""Deterministic fixture generator: renders chord progressions to WAV.

All randomness comes from a fixed-seed LCG so output is byte-identical
on every run. truth.json carries the ground truth the tests gate on.

Run:  python3 fixtures/gen_fixtures.py
"""

import json
import math
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SR = 11025

# A small LCG: deterministic stand-in for random.random()
_seed = 20260101


def rnd():
    global _seed
    _seed = (1103515245 * _seed + 12345) % (1 << 31)
    return _seed / (1 << 31)


def midi_hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def render_chord(buffer_, midis, start_s, dur_s, partial_amps=(1.0, 0.55, 0.3, 0.18, 0.1)):
    """Additive synth: each note gets decaying harmonics + slow tremolo."""
    n0 = int(start_s * SR)
    n1 = int((start_s + dur_s) * SR)
    for m in midis:
        f0 = midi_hz(m)
        for pi_, amp in enumerate(partial_amps, start=1):
            f = f0 * pi_
            if f > SR / 2 - 100:
                break
            w = 2.0 * math.pi * f / SR
            trem = 0.9 + 0.1 * math.sin(2.0 * math.pi * 4.1 * (n0 / SR))
            for i in range(n0, n1):
                t = (i - n0) / SR
                env = min(1.0, t * 50.0) * math.exp(-t * 0.8)
                buffer_[i] += amp * env * trem * math.sin(w * i)


def add_drums(buffer_, start_s, dur_s):
    """Percussion proxy: decaying white-noise bursts every half second."""
    n0 = int(start_s * SR)
    n1 = int((start_s + dur_s) * SR)
    i = n0
    while i < n1:
        burst = int(0.05 * SR)
        level = 0.5 + 0.3 * rnd()
        for j in range(min(burst, n1 - i)):
            t = j / SR
            buffer_[i + j] += level * math.exp(-t * 60.0) * (rnd() * 2.0 - 1.0)
        i += int(0.5 * SR)


def write_wav(path, samples):
    peak = max(abs(s) for s in samples) or 1.0
    scaled = [max(-1.0, min(1.0, s / peak * 0.85)) for s in samples]
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in scaled))


QUALITY_INTERVALS = {
    "maj": (0, 4, 7), "min": (0, 3, 7), "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11), "min7": (0, 3, 7, 10),
    "dim": (0, 3, 6), "sus4": (0, 5, 7),
}

# 0 = C. A musically sane loop: I - V - vi - IV in C, then a colour turn.
PROGRESSION = [
    (48, "maj", 2.0),   # C
    (43, "maj", 2.0),   # G
    (45, "min", 2.0),   # Am
    (41, "maj", 2.0),   # F
    (40, "min7", 2.0),  # Em7
    (46, "7", 2.0),     # Bb7 (borrowed dominant)
    (48, "maj", 2.0),   # C (return)
]


def label_of(root_midi, quality):
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return names[root_midi % 12] + quality


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    total = sum(d for _, _, d in PROGRESSION) + 2.0  # +2 s leading silence
    buf = [0.0] * int(total * SR)

    t = 2.0
    truth = []
    for root, quality, dur in PROGRESSION:
        midis = [root + iv for iv in QUALITY_INTERVALS[quality]]
        midis += [root + 12]  # double the root an octave up, like a real voicing
        render_chord(buf, midis, t, dur - 0.05)  # 50 ms gap = clear boundaries
        truth.append({"start": round(t, 3), "end": round(t + dur, 3),
                      "chord": label_of(root, quality)})
        t += dur

    write_wav(os.path.join(here, "clean.wav"), buf)

    # Messy variant: same progression + drums + sub-bass drone + gain wobble
    messy = buf[:]
    add_drums(messy, 2.0, total - 2.0)
    for i in range(int(2.0 * SR), len(messy)):
        f = 55.0  # A1 drone: in-key for C major loop
        messy[i] += 0.15 * math.sin(2.0 * math.pi * f * i / SR)
        messy[i] *= 0.8 + 0.2 * math.sin(2.0 * math.pi * 0.7 * i / SR)
    write_wav(os.path.join(here, "messy.wav"), messy)

    write_wav(os.path.join(here, "silence.wav"), [0.0] * int(3.0 * SR))

    with open(os.path.join(here, "truth.json"), "w") as f:
        json.dump(truth, f, indent=1)
    print(f"wrote clean.wav, messy.wav, silence.wav, truth.json ({len(truth)} chords)")


if __name__ == "__main__":
    main()
