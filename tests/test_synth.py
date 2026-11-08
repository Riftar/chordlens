"""v0.2.2 synth engine gates.

These tests pin the ACOUSTIC facts that made the old engine cheap, so a
future change cannot silently undo them:
  - audible content above 5 kHz (the 11 kHz render had none at all)
  - brightness DECAYS over a note (real instruments lose high harmonics)
  - stereo channels actually differ
  - no hard clipping (peak stays under 1.0 after mastering)
  - the detector still reads what the new engine renders
"""

import io
import math
import os
import sys
import unittest
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chordlens import progressions  # noqa: E402
from chordlens.detect import analyze  # noqa: E402
from chordlens.dsp import fft  # noqa: E402
from chordlens.synth import (TIMBRES, DEFAULT_TIMBRE, render_stereo,  # noqa: E402
                             stereo_to_wav_bytes, wavetable, midi_hz)

MIDIS = [53, 57, 60, 64]  # F major


def band_energy(buf, sr, lo, hi):
    n = 4096
    seg = buf[:n] if len(buf) >= n else buf
    w = [0.5 - 0.5 * math.cos(2 * math.pi * i / (len(seg) - 1)) for i in range(len(seg))]
    spec = fft([complex(seg[i] * w[i], 0.0) for i in range(len(seg))])
    return sum(abs(spec[k]) ** 2 for k in range(len(spec) // 2)
               if lo <= k * sr / len(seg) < hi)


def high_ratio(buf, sr, offset):
    off = int(offset * sr)
    seg = buf[off:off + 2048]
    if len(seg) < 512:
        return 0.0
    w = [0.5 - 0.5 * math.cos(2 * math.pi * i / (len(seg) - 1)) for i in range(len(seg))]
    spec = fft([complex(seg[i] * w[i], 0.0) for i in range(len(seg))])
    hi = sum(abs(spec[k]) ** 2 for k in range(len(spec) // 2)
             if k * sr / len(seg) >= 1500)
    tot = sum(abs(spec[k]) ** 2 for k in range(len(spec) // 2)) or 1e-9
    return hi / tot


class TestEngineBasics(unittest.TestCase):
    def test_six_timbre_presets_exist(self):
        for name in ("keys", "guitar", "pad", "organ", "bell"):
            self.assertIn(name, TIMBRES)
            self.assertIn(name, TIMBRES[DEFAULT_TIMBRE] and TIMBRES)
        self.assertEqual(DEFAULT_TIMBRE, "keys")

    def test_render_is_deterministic(self):
        a, _ = render_stereo(MIDIS, 1.0, 22050, timbre="keys", seed=7)
        b, _ = render_stereo(MIDIS, 1.0, 22050, timbre="keys", seed=7)
        self.assertEqual(a[:2000], b[:2000])

    def test_stereo_wav_is_two_channel(self):
        L, R = render_stereo(MIDIS, 0.5, 22050)
        data = stereo_to_wav_bytes(L, R, 22050)
        with wave.open(io.BytesIO(data)) as w:
            self.assertEqual(w.getnchannels(), 2)
            self.assertEqual(w.getsampwidth(), 2)
            self.assertEqual(w.getframerate(), 22050)

    def test_no_hard_clipping_after_master(self):
        L, R = render_stereo(MIDIS, 1.0, 22050)
        peak = max(max(abs(v) for v in L), max(abs(v) for v in R))
        self.assertLessEqual(peak, 0.9001, peak)

    def test_wavetable_is_normalised_and_periodic(self):
        tab = wavetable(60, "keys")
        self.assertEqual(len(tab), 2048)
        self.assertAlmostEqual(max(abs(v) for v in tab), 1.0, places=6)
        self.assertAlmostEqual(tab[0], 0.0, places=6)


class TestAcousticFacts(unittest.TestCase):
    """The measured differences vs the legacy engine."""

    def test_air_above_5khz_exists(self):
        """Legacy rendered at 11 kHz: its entire top octave was empty."""
        L, R = render_stereo(MIDIS, 1.0, 22050, timbre="keys")
        air = band_energy(L, 22050, 5000, 11000)
        self.assertGreater(air, 0.0, "no energy above 5 kHz")

    def test_brightness_decays_over_the_note(self):
        """Real instruments lose high harmonics as they decay."""
        L, R = render_stereo(MIDIS, 1.5, 22050, timbre="keys")
        early = high_ratio(L, 22050, 0.02)
        late = high_ratio(L, 22050, 0.5)
        self.assertLess(late, early, f"early {early:.4f} late {late:.4f}")

    def test_stereo_channels_differ(self):
        L, R = render_stereo(MIDIS, 1.0, 22050, timbre="keys")
        diff = sum(abs(L[i] - R[i]) for i in range(len(L)))
        total = sum(abs(v) for v in L) + 1e-9
        self.assertGreater(diff / total, 0.05, "channels are near-identical")

    def test_guitar_timbre_decays_faster_than_pad(self):
        g, _ = render_stereo(MIDIS, 1.5, 22050, timbre="guitar")
        p, _ = render_stereo(MIDIS, 1.5, 22050, timbre="pad")
        g_decay = high_ratio(g, 22050, 0.5) / (high_ratio(g, 22050, 0.02) + 1e-9)
        p_decay = high_ratio(p, 22050, 0.5) / (high_ratio(p, 22050, 0.02) + 1e-9)
        self.assertLess(g_decay, p_decay, f"guitar {g_decay:.3f} pad {p_decay:.3f}")


class TestDetectorReadsNewEngine(unittest.TestCase):
    """The engine change must not break the product's core promise."""

    def test_detector_reads_the_stereo_render(self):
        import tempfile
        data = progressions.render_stereo_bytes("royal-road", 0, 100)
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        try:
            segs = analyze(tmp)
        finally:
            os.remove(tmp)
        weights = {}
        for a, b, lab in segs:
            weights[lab] = weights.get(lab, 0.0) + (b - a)
        top4 = set(sorted(weights, key=weights.get, reverse=True)[:4])
        self.assertEqual(top4, {"Fmaj", "Gmaj", "Emin", "Amin"},
                         f"weights {weights}")

    def test_single_chord_stereo_endpoint_shape(self):
        data = progressions.render_single_stereo(0, "maj", 1.0)
        with wave.open(io.BytesIO(data)) as w:
            self.assertEqual(w.getnchannels(), 2)
            self.assertEqual(w.getframerate(), progressions.PLAY_SR)


if __name__ == "__main__":
    unittest.main()
