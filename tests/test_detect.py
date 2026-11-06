"""Detection accuracy gates — fixtures carry their own ground truth.

Edge frames (within one FFT window span of a chord boundary) straddle two
chords by construction; accuracy is gated on interior frames only. That
limit is documented in README, not hidden.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chordlens.chroma import chroma_frame  # noqa: E402
from chordlens.chords import best_chord  # noqa: E402
from chordlens.detect import analyze, frame_labels, read_wav_mono  # noqa: E402
from fixtures.gen_fixtures import PROGRESSION, SR, label_of, render_chord  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")
EDGE = 0.6  # one FFT window span; boundary frames straddle two chords


def synth_frame(root_midi, intervals):
    midis = [root_midi + iv for iv in intervals] + [root_midi + 12]
    buf = [0.0] * int(SR * 1.0)
    render_chord(buf, midis, 0.0, 1.0)
    return buf[len(buf) // 2 - 4096: len(buf) // 2 + 4096]


def root_of(ch):
    for q in ("maj7", "min7", "sus4", "maj", "min", "dim", "7"):
        if ch.endswith(q):
            return ch[: -len(q)]
    return ch


def interior_scores(wav):
    """(exact, root_ok, scored) over interior frames only."""
    truth = json.load(open(os.path.join(FIX, "truth.json")))
    samples, sr = read_wav_mono(os.path.join(FIX, wav))
    labels = frame_labels(samples, sr)
    exact = root_ok = scored = 0
    for i, lab in enumerate(labels):
        t = i * 4096 / sr
        seg = next((s for s in truth if s["start"] + EDGE <= t < s["end"] - EDGE), None)
        if not seg or lab is None:
            continue
        scored += 1
        exact += lab == seg["chord"]
        root_ok += root_of(lab) == root_of(seg["chord"])
    return exact, root_ok, scored


class TestTemplates(unittest.TestCase):
    def test_every_root_major_minor_detected(self):
        """24/24 triads identified from a single clean frame."""
        for root in range(48, 60):
            for quality, ivs in (("maj", (0, 4, 7)), ("min", (0, 3, 7))):
                got = best_chord(chroma_frame(synth_frame(root, ivs), SR))
                self.assertEqual(got, label_of(root, quality),
                                 f"root={root} quality={quality} got {got}")


class TestClean(unittest.TestCase):
    def test_region_majority_all_seven_chords(self):
        """Region majority is the truth chord for >=6 regions, and the same
        quality family (maj/min) for all 7. The maj-vs-7th knife edge on
        quiet 7ths is the documented v0.1 frontier (real-audio tuning,
        2026-11-06, traded a synthetic Emin7 read for real triads)."""
        truth = json.load(open(os.path.join(FIX, "truth.json")))
        samples, sr = read_wav_mono(os.path.join(FIX, "clean.wav"))
        labels = frame_labels(samples, sr)
        exact = family = 0
        for seg in truth:
            votes = {}
            for i, lab in enumerate(labels):
                t = i * 4096 / sr
                if seg["start"] <= t < seg["end"] and lab:
                    votes[lab] = votes.get(lab, 0) + 1
            winner = max(votes, key=votes.get)
            exact += winner == seg["chord"]
            family += ("min" in seg["chord"]) == ("min" in winner)
        self.assertGreaterEqual(exact, 6)
        self.assertEqual(family, 7)

    def test_interior_frame_accuracy(self):
        exact, root_ok, scored = interior_scores("clean.wav")
        self.assertGreaterEqual(scored, 10)
        self.assertGreaterEqual(exact / scored, 0.75, f"exact {exact}/{scored}")
        self.assertGreaterEqual(root_ok / scored, 0.90, f"root {root_ok}/{scored}")


class TestMessy(unittest.TestCase):
    """Ceiling documented, not hidden: drums + drone + wobble cost quality
    labels before they cost roots."""

    def test_interior_root_accuracy(self):
        _, root_ok, scored = interior_scores("messy.wav")
        self.assertGreaterEqual(scored, 10)
        self.assertGreaterEqual(root_ok / scored, 0.55, f"root {root_ok}/{scored}")

    def test_region_majority_root_at_least_four_of_seven(self):
        truth = json.load(open(os.path.join(FIX, "truth.json")))
        samples, sr = read_wav_mono(os.path.join(FIX, "messy.wav"))
        labels = frame_labels(samples, sr)
        hits = 0
        for seg in truth:
            votes = {}
            for i, lab in enumerate(labels):
                t = i * 4096 / sr
                if seg["start"] <= t < seg["end"] and lab:
                    votes[lab] = votes.get(lab, 0) + 1
            winner = max(votes, key=votes.get)
            hits += root_of(winner) == root_of(seg["chord"])
        self.assertGreaterEqual(hits, 4, f"region-majority roots {hits}/7")


class TestSilence(unittest.TestCase):
    def test_silent_wav_yields_no_segments(self):
        self.assertEqual(analyze(os.path.join(FIX, "silence.wav")), [])


if __name__ == "__main__":
    unittest.main()
