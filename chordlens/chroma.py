"""Chromagram: fold spectral energy into 12 pitch-class buckets."""


import math

from .dsp import fft, hann

LOW_HZ = 82.41   # E2: above bass-drum rumble and sub-bass drones
HIGH_HZ = 2200.0 # above this, overtones we do not need for chords


def chroma_frame(frame, sr):
    """12-vector chroma of one time frame (list of floats, peak-normalised).

    `frame` is analysed with an FFT sized to len(frame) (power of two).
    No log-compression whitening: measured on real guitar recordings
    (2026-11-06, am-rock backing track), whitening lifts overtones to
    parity with fundamentals and every triad reads as a 7th chord; raw
    magnitude keeps fundamentals dominant and the chord tones separate.
    """
    size = len(frame)
    peak = max((abs(s) for s in frame), default=0.0)
    if peak <= 0.0:
        return [0.0] * 12
    win = hann(size)
    buf = [complex(frame[i] / peak * win[i], 0.0) for i in range(size)]
    spec = fft(buf)
    pc = [0.0] * 12
    for k in range(1, size // 2):
        f = k * sr / size
        if LOW_HZ <= f <= HIGH_HZ:
            m = abs(spec[k])
            midi = 12.0 * math.log2(f / 440.0) + 69.0
            pc[int(midi + 0.5) % 12] += m
    top = max(pc)
    if top > 0.0:
        pc = [p / top for p in pc]
    return pc
