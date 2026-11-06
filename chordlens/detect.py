"""Read a WAV file and reduce it to a chord timeline."""

import array
import sys
import wave

from .chroma import chroma_frame
from .chords import best_chord
from .dsp import block_mean, frames

TARGET_SR = 11025  # enough bandwidth for chords (<= 2200 Hz content)
SIZE = 8192        # FFT frame: ~0.74 s at 11025 Hz
HOP = 4096         # 50% overlap
SILENCE = 1e-4     # peak amplitude below which a frame is silence
MIN_SEC = 0.3      # chord regions shorter than this merge into neighbours


def read_wav_mono(path):
    """Return (samples in [-1,1], sample_rate) — mono mixdown of a PCM WAV."""
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width == 2:
        arr = array.array("h", raw)
        if sys.byteorder == "big":
            arr.byteswap()
        samples = [s / 32768.0 for s in arr]
    elif width == 1:
        samples = [(b - 128) / 128.0 for b in raw]
    else:
        raise ValueError(f"unsupported sample width: {width} bytes (convert to 16-bit PCM)")
    if nch > 1:
        samples = samples[0::nch]
    factor = sr // TARGET_SR if sr // TARGET_SR >= 2 and sr % (sr // TARGET_SR) == 0 else 1
    return block_mean(samples, factor), sr // factor


def frame_labels(samples, sr, size=SIZE, hop=HOP):
    """Per-frame best chord; None for silent frames."""
    labels = []
    for _, frame in frames(samples, size, hop):
        if max((abs(s) for s in frame), default=0.0) < SILENCE:
            labels.append(None)
        else:
            labels.append(best_chord(chroma_frame(frame, sr)))
    return labels


def smooth(labels, radius=2):
    """Mode-of-window vote (a median filter for labels) to kill single-frame flips."""
    out = []
    for i in range(len(labels)):
        votes = {}
        for j in range(max(0, i - radius), min(len(labels), i + radius + 1)):
            if labels[j] is not None:
                votes[labels[j]] = votes.get(labels[j], 0) + 1
        out.append(max(votes, key=votes.get) if votes else None)
    return out


def segments_from(labels, hop_sec, min_sec=MIN_SEC):
    """Collapse a label sequence into (start, end, chord) segments."""
    segs = []
    for i, lab in enumerate(labels):
        start = i * hop_sec
        if segs and segs[-1][2] == lab:
            segs[-1][1] = start + hop_sec
        else:
            segs.append([start, start + hop_sec, lab])
    # merge too-short or silent regions into their longest neighbour
    changed = True
    while changed:
        changed = False
        for i, s in enumerate(segs):
            if s[2] is None or (s[1] - s[0]) < min_sec:
                neighbours = [n for n in (i - 1, i + 1) if 0 <= n < len(segs)]
                if not neighbours:
                    segs = []
                    changed = False
                    break
                best = max(neighbours, key=lambda n: segs[n][1] - segs[n][0])
                s[2] = segs[best][2]
                changed = True
                break
    # final collapse of same-label neighbours the merge may have created
    merged = []
    for s in segs:
        if s[2] is None:
            continue
        if merged and merged[-1][2] == s[2]:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [(round(a, 3), round(b, 3), c) for a, b, c in merged]


def analyze_detailed(path, size=SIZE, hop=HOP):
    """WAV file -> (segments, frames) where frames carry per-frame chroma
    for the chromagram view. Same pipeline as analyze(), richer payload."""
    samples, sr = read_wav_mono(path)
    hop_sec = hop / sr
    raw = []
    for off, frame in frames(samples, size, hop):
        t = off / sr
        if max((abs(s) for s in frame), default=0.0) < SILENCE:
            raw.append((t, None, None))
        else:
            pc = chroma_frame(frame, sr)
            raw.append((t, best_chord(pc), pc))
    labels = [lab for _, lab, _ in raw]
    smoothed = smooth(labels)
    frames_out = [
        {"t": round(t, 3), "label": s, "chroma": [round(c, 4) for c in pc] if pc else None}
        for (t, _, pc), s in zip(raw, smoothed)
    ]
    return segments_from(smoothed, hop_sec), frames_out


def analyze(path, size=SIZE, hop=HOP):
    """WAV file -> list of (start_s, end_s, chord_label)."""
    samples, sr = read_wav_mono(path)
    labels = frame_labels(samples, sr, size, hop)
    return segments_from(smooth(labels), hop / sr)
