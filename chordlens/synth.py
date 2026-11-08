"""Synth engine: wavetable additive with per-voice shaping, stereo, reverb.

Why the first engine sounded cheap (measured, not guessed):
  1. every partial shared ONE decay rate, so high harmonics never died
     faster than low ones (real strings/piano lose brightness over time)
  2. 11025 Hz render rate - a 5.5 kHz ceiling, i.e. no "air" at all
  3. all notes perfectly in phase and identical in timbre
  4. a 4.1 Hz tremolo on every note (a warble artifact, not an instrument)
  5. dry mono, no room, hard peak-normalise (clips on big chords)

This engine fixes all five with stdlib only:
  - per-partial amplitude tables + a decaying lowpass (brightness loss)
  - attack transient (filtered noise burst) for percussive timbres
  - detuned unison voices, per-note deterministic phase
  - stereo with per-note pan and a Schroeder reverb (comb + allpass)
  - soft saturation before normalisation (no clipping)

Timbre presets are PARAMETER BUNDLES (no copied code, no samples) - the
same discipline as the design-system presets in the web layer.
"""

import io
import math
import struct
import wave

TABLE_SIZE = 2048  # power of two, so phase wraps with a mask
BLOCK = 64         # coefficient refresh interval (per-sample exp() is slow)


def midi_hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


# ---------------------------------------------------------------- timbres
# amps: partial amplitudes (1st..Nth harmonic)
# decay: exponential decay rate (1/s); sustain: level the decay settles to
# attack: attack time (s); noise: transient noise level
# lpf_start/lpf_end: lowpass cutoff sweep across the note (bright -> dark)
# unison/unison_amps/detune: detuned copies for a "played" feel
TIMBRES = {
    "legacy": dict(
        amps=(1.0, 0.55, 0.3, 0.18, 0.1), decay=0.8, sustain=0.0, attack=0.02,
        noise=0.0, lpf_start=20000.0, lpf_end=20000.0, unison=1,
        unison_amps=(1.0,), detune=0.0, bass=False,
    ),
    "keys": dict(  # electric piano / Rhodes-ish: bell partials, warm
        amps=(1.0, 0.42, 0.24, 0.13, 0.08, 0.05, 0.03, 0.02),
        decay=1.6, sustain=0.22, attack=0.006, noise=0.16,
        lpf_start=7000.0, lpf_end=1400.0, unison=2, unison_amps=(0.72, 0.28),
        detune=0.0016, bass=True,
    ),
    "guitar": dict(  # plucked nylon: fast attack, quick bright decay
        amps=(1.0, 0.5, 0.3, 0.2, 0.14, 0.1, 0.07, 0.05, 0.03),
        decay=2.6, sustain=0.08, attack=0.003, noise=0.34,
        lpf_start=5200.0, lpf_end=900.0, unison=2, unison_amps=(0.78, 0.22),
        detune=0.0022, bass=False,
    ),
    "pad": dict(  # slow swell, sustains under a melody
        amps=(1.0, 0.5, 0.28, 0.16, 0.1, 0.06),
        decay=0.35, sustain=0.85, attack=0.35, noise=0.0,
        lpf_start=2600.0, lpf_end=1800.0, unison=3, unison_amps=(0.55, 0.3, 0.15),
        detune=0.003, bass=True,
    ),
    "organ": dict(  # drawbar-ish: steady, no decay
        amps=(1.0, 0.6, 0.35, 0.2, 0.12, 0.07),
        decay=0.05, sustain=1.0, attack=0.02, noise=0.0,
        lpf_start=9000.0, lpf_end=7000.0, unison=1, unison_amps=(1.0,),
        detune=0.0, bass=False,
    ),
    "bell": dict(  # glassy, long ring
        amps=(0.6, 0.3, 0.5, 0.12, 0.2, 0.05, 0.08),
        decay=0.9, sustain=0.1, attack=0.002, noise=0.1,
        lpf_start=9000.0, lpf_end=2600.0, unison=2, unison_amps=(0.7, 0.3),
        detune=0.0026, bass=False,
    ),
}

DEFAULT_TIMBRE = "keys"


def _lcg(seed):
    """Deterministic pseudo-random in [0,1) - stable across platforms."""
    x = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return x / 0x7FFFFFFF


# ------------------------------------------------------------- wavetables
_TABLES = {}


def wavetable(midi, timbre):
    """One cycle of the timbre for this pitch, normalised. Cached."""
    key = (midi, timbre)
    hit = _TABLES.get(key)
    if hit is not None:
        return hit
    t = TIMBRES[timbre]
    f0 = midi_hz(midi)
    n = TABLE_SIZE
    tab = [0.0] * n
    for k, a in enumerate(t["amps"], start=1):
        if f0 * k > 16000.0:      # keep it musical, not shrill
            break
        step = 2.0 * math.pi * k / n
        for i in range(n):
            tab[i] += a * math.sin(step * i)
    peak = max(abs(v) for v in tab) or 1.0
    tab = [v / peak for v in tab]
    _TABLES[key] = tab
    return tab


# ------------------------------------------------------------------ voices
def _add_voice(left, right, midi, t0, dur_s, sr, timbre, pan, gain, seed):
    """Render one note: unison oscillators + envelope + brightness sweep.

    Coefficients (envelope, filter cutoff) refresh every BLOCK samples -
    the per-sample exp() was the render bottleneck.
    """
    t = TIMBRES[timbre]
    tab = wavetable(midi, timbre)
    n = len(tab)
    mask = n - 1
    f0 = midi_hz(midi)
    inc_base = f0 * n / sr

    i0 = int(t0 * sr)
    i1 = int((t0 + dur_s) * sr)
    if i0 < 0:
        i0 = 0
    if i1 > len(left):
        i1 = len(left)
    if i1 <= i0:
        return

    unison = t["unison"]
    uamps = t["unison_amps"]
    det = t["detune"]
    att = t["attack"]
    dec = t["decay"]
    sus = t["sustain"]

    gl = math.cos((pan + 1.0) * math.pi / 4.0)
    gr = math.sin((pan + 1.0) * math.pi / 4.0)

    phases = [_lcg(seed + u) * n for u in range(unison)]
    lp_y = 0.0
    for i in range(i0, i1):
        if (i - i0) % BLOCK == 0:
            tt = (i - i0) / sr
            if att > 0 and tt < att:
                env = tt / att
            else:
                env = sus + (1.0 - sus) * math.exp(-(tt - att) * dec)
            fc = t["lpf_end"] + (t["lpf_start"] - t["lpf_end"]) * math.exp(-tt * dec * 0.7)
            a_lp = 1.0 - math.exp(-2.0 * math.pi * fc / sr)
        s = 0.0
        for u in range(unison):
            inc = inc_base * (1.0 + det * (u - (unison - 1) / 2.0))
            ph = phases[u]
            idx = int(ph)
            frac = ph - idx
            s += uamps[u] * ((1.0 - frac) * tab[idx & mask] +
                             frac * tab[(idx + 1) & mask])
            ph += inc
            if ph >= n:
                ph -= n
            phases[u] = ph
        lp_y += a_lp * (s - lp_y)
        v = lp_y * env * gain
        left[i] += v * gl
        right[i] += v * gr


def _add_transient(left, right, midi, t0, sr, timbre, pan, gain, seed):
    """Short filtered-noise burst: the 'thump' of a real attack."""
    t = TIMBRES[timbre]
    if t["noise"] <= 0.0:
        return
    i0 = int(t0 * sr)
    i1 = min(len(left), i0 + int(0.03 * sr))
    gl = math.cos((pan + 1.0) * math.pi / 4.0)
    gr = math.sin((pan + 1.0) * math.pi / 4.0)
    lp = 0.0
    for i in range(i0, i1):
        tt = (i - i0) / sr
        env = math.exp(-tt * 120.0)
        lp += 0.35 * ((_lcg(seed + i * 7) * 2.0 - 1.0) - lp)
        v = lp * env * gain * t["noise"]
        left[i] += v * gl
        right[i] += v * gr


# ------------------------------------------------------------------ reverb
def _reverb_channel(buf, sr, comb_ms, allpass_ms, detune, decay, mix):
    n = len(buf)
    out = [0.0] * n
    comb_states = []
    for ms in comb_ms:
        d = max(1, int(sr * (ms * detune) / 1000.0))
        comb_states.append({"buf": [0.0] * d, "idx": 0, "d": d})
    ap_states = []
    for ms in allpass_ms:
        d = max(1, int(sr * (ms * detune) / 1000.0))
        ap_states.append({"buf": [0.0] * d, "idx": 0, "d": d})
    for i in range(n):
        x = buf[i]
        acc = 0.0
        for st in comb_states:
            y = st["buf"][st["idx"]]
            st["buf"][st["idx"]] = x + y * decay
            st["idx"] += 1
            if st["idx"] >= st["d"]:
                st["idx"] = 0
            acc += y
        acc *= 0.25
        for st in ap_states:
            y = st["buf"][st["idx"]]
            st["buf"][st["idx"]] = acc + y * 0.5
            st["idx"] += 1
            if st["idx"] >= st["d"]:
                st["idx"] = 0
            acc = y - acc
        out[i] = acc
    for i in range(n):
        buf[i] = buf[i] * (1.0 - mix) + out[i] * mix


def _reverb(left, right, sr, mix=0.22, decay=0.76):
    """Schroeder reverb: 4 parallel combs -> 2 series allpass, per channel."""
    comb_ms = (29.7, 37.1, 41.1, 43.7)
    allpass_ms = (5.0, 1.7)
    for buf, detune in ((left, 1.0), (right, 0.86)):
        _reverb_channel(buf, sr, comb_ms, allpass_ms, detune, decay, mix)


# ------------------------------------------------------------------ public
def render_chord_stereo(left, right, midis, start_s, dur_s, sr,
                        timbre=DEFAULT_TIMBRE, gain=1.0, pan_spread=0.28, seed=1):
    """Render a chord into a stereo pair of buffers."""
    n_midi = len(midis)
    for idx, m in enumerate(midis):
        rel = (m - 60) / 24.0
        pan = max(-1.0, min(1.0, rel * pan_spread))
        g = gain / max(1.0, n_midi * 0.5)
        _add_voice(left, right, m, start_s, dur_s, sr, timbre, pan, g,
                   seed * 131 + idx * 17)
        _add_transient(left, right, m, start_s, sr, timbre, pan, g,
                       seed * 977 + idx * 31)
    t = TIMBRES[timbre]
    if t["bass"] and midis:
        root = min(midis)
        _add_voice(left, right, root - 12, start_s, dur_s, sr, timbre, 0.0,
                   gain * 0.5, seed * 613)


def master(left, right, sr, drive=1.15, peak=0.89):
    """Soft saturation then normalise - no hard clipping on big chords."""
    norm = math.tanh(drive)
    for buf in (left, right):
        for i in range(len(buf)):
            buf[i] = math.tanh(buf[i] * drive) / norm
    mx = 0.0
    for buf in (left, right):
        for v in buf:
            av = abs(v)
            if av > mx:
                mx = av
    if mx > 0:
        g = peak / mx
        for buf in (left, right):
            for i in range(len(buf)):
                buf[i] *= g


def render_stereo(midis, dur_s, sr, timbre=DEFAULT_TIMBRE, seed=1, reverb=True):
    """Render a chord to (left, right) sample lists, ready to write."""
    left = [0.0] * int(dur_s * sr)
    right = [0.0] * int(dur_s * sr)
    render_chord_stereo(left, right, midis, 0.0, dur_s, sr, timbre, seed=seed)
    if reverb:
        _reverb(left, right, sr)
    master(left, right, sr)
    return left, right


# ------------------------------------------------------- legacy mono path
def render_chord(buffer_, midis, start_s, dur_s, sr=11025,
                 partial_amps=(1.0, 0.55, 0.3, 0.18, 0.1)):
    """Legacy mono additive path - used by the FIXTURE generator only.

    The fixture corpus stays on this path so the synthetic test data
    remains byte-stable and keeps its own voice (not the app's timbre).
    """
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


# ------------------------------------------------------------------ output
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
    peak = max(abs(s) for s in samples) or 1.0
    scaled = [max(-1.0, min(1.0, s / peak * 0.85)) for s in samples]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in scaled))
    return buf.getvalue()


def stereo_to_wav_bytes(left, right, sr):
    """16-bit stereo WAV bytes."""
    peak = 0.0
    for buf in (left, right):
        for v in buf:
            av = abs(v)
            if av > peak:
                peak = av
    g = (0.89 / peak) if peak > 0 else 1.0
    out = bytearray()
    n = min(len(left), len(right))
    for i in range(n):
        l = int(max(-1.0, min(1.0, left[i] * g)) * 32767)
        r = int(max(-1.0, min(1.0, right[i] * g)) * 32767)
        out += struct.pack("<hh", l, r)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(out))
    return buf.getvalue()
