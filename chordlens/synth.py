"""Additive-synth rendering shared by fixtures and the progression API."""

import math
import struct
import wave


def midi_hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def render_chord(buffer_, midis, start_s, dur_s, sr=11025,
                 partial_amps=(1.0, 0.55, 0.3, 0.18, 0.1)):
    """Additive synth: each note gets decaying harmonics + slow tremolo."""
    n0 = int(start_s * sr)
    n1 = int((start_s + dur_s) * sr)
    for m in midis:
        f0 = midi_hz(m)
        for pi_, amp in enumerate(partial_amps, start=1):
            f = f0 * pi_
            if f > sr / 2 - 100:
                break
            w = 2.0 * math.pi * f / sr
            trem = 0.9 + 0.1 * math.sin(2.0 * math.pi * 4.1 * (n0 / sr))
            for i in range(n0, n1):
                t = (i - n0) / sr
                env = min(1.0, t * 50.0) * math.exp(-t * 0.8)
                buffer_[i] += amp * env * trem * math.sin(w * i)


def write_wav(path, samples, sr=11025):
    peak = max(abs(s) for s in samples) or 1.0
    scaled = [max(-1.0, min(1.0, s / peak * 0.85)) for s in samples]
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in scaled))


def samples_to_wav_bytes(samples, sr):
    """Same as write_wav but returns bytes (for the HTTP API)."""
    import io
    peak = max(abs(s) for s in samples) or 1.0
    scaled = [max(-1.0, min(1.0, s / peak * 0.85)) for s in samples]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in scaled))
    return buf.getvalue()
