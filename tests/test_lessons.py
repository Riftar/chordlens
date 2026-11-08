"""v0.2 lessons: the /api/key endpoint, single-chord rendering, and the
expanded progression registry. Acceptance gates per PLAN v0.2."""

import io
import json
import os
import sys
import unittest
import urllib.request
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chordlens import progressions  # noqa: E402
from chordlens.detect import analyze  # noqa: E402

PORT = 8973
BASE = f"http://127.0.0.1:{PORT}"


class TestKeyChords(unittest.TestCase):
    def test_c_major_seven_chords(self):
        labels = [c["label"] for c in progressions.key_chords(0)]
        self.assertEqual(labels,
                         ["Cmaj", "Dmin", "Emin", "Fmaj", "Gmaj", "Amin", "Bdim"])

    def test_f_major_seven_chords(self):
        labels = [c["label"] for c in progressions.key_chords(5)]
        # engine convention: sharp spelling (A#maj, D#dim), like every label
        self.assertEqual(labels,
                         ["Fmaj", "Gmin", "Amin", "A#maj", "Cmaj", "Dmin", "Edim"])

    def test_numerals_and_functions_align(self):
        chords = progressions.key_chords(0)
        self.assertEqual([c["numeral"] for c in chords],
                         ["I", "ii", "iii", "IV", "V", "vi", "vii°"])
        self.assertEqual([c["function"] for c in chords],
                         ["Tonic", "Subdominant", "Tonic", "Subdominant",
                          "Dominant", "Tonic", "Dominant"])
        # notes of the tonic chord are C E G
        self.assertEqual(chords[0]["notes"], ["C", "E", "G"])


class TestRegistryClassics(unittest.TestCase):
    def test_five_classics_present_with_correct_degrees(self):
        want = {
            "pop-axis": ["I", "V", "vi", "IV"],
            "classic-cadence": ["I", "IV", "V", "I"],
            "rotation": ["vi", "IV", "I", "V"],
            "doo-wop": ["I", "vi", "IV", "V"],
            "jazz-cadence": ["ii", "V", "I"],
        }
        for pid, degrees in want.items():
            self.assertIn(pid, progressions.PROGRESSIONS)
            self.assertEqual([s["degree"] for s in progressions.PROGRESSIONS[pid]["steps"]],
                             degrees)

    def test_pop_axis_c_major_labels(self):
        labels = [c["label"] for c in progressions.chords_for("pop-axis", 0)]
        self.assertEqual(labels, ["Cmaj", "Gmaj", "Amin", "Fmaj"])

    def test_self_detect_pop_axis(self):
        """The detector reads back I-V-vi-IV in C as exactly those four."""
        import tempfile
        data = progressions.render("pop-axis", 0, 100)
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
        self.assertEqual(top4, {"Cmaj", "Gmaj", "Amin", "Fmaj"})


class TestRenderSingle(unittest.TestCase):
    def test_valid_wav_and_duration(self):
        data = progressions.render_single(0, "maj", 1.4)
        self.assertEqual(data[:4], b"RIFF")
        with wave.open(io.BytesIO(data)) as w:
            dur = w.getnframes() / w.getframerate()
            self.assertTrue(1.5 < dur < 2.0, dur)

    def test_longer_duration_renders_longer(self):
        short = progressions.render_single(0, "min", 0.5)
        long = progressions.render_single(0, "min", 3.0)
        self.assertLess(len(short), len(long))


class TestAPI(unittest.TestCase):
    httpd = None

    @classmethod
    def setUpClass(cls):
        from server import serve
        import threading
        cls.httpd = serve(PORT)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def get(self, path):
        with urllib.request.urlopen(BASE + path, timeout=30) as r:
            return r.status, r.read()

    def test_key_endpoint_c(self):
        status, body = self.get("/api/key?key=0")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["key"], "C")
        self.assertEqual(data["chords"][0]["label"], "Cmaj")
        self.assertEqual(data["chords"][6]["label"], "Bdim")

    def test_key_endpoint_f(self):
        _, body = self.get("/api/key?key=5")
        data = json.loads(body)
        self.assertEqual([c["label"] for c in data["chords"]],
                         ["Fmaj", "Gmin", "Amin", "A#maj", "Cmaj", "Dmin", "Edim"])

    def test_chord_wav_endpoint(self):
        status, body = self.get("/api/chord.wav?root=0&quality=maj&dur=1.2")
        self.assertEqual(status, 200)
        self.assertEqual(body[:4], b"RIFF")

    def test_chord_wav_rejects_bad_quality(self):
        try:
            self.get("/api/chord.wav?root=0&quality=loud&dur=1.2")
            self.fail("accepted bad quality")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_lessons_page_served(self):
        status, body = self.get("/lessons.html")
        self.assertEqual(status, 200)
        self.assertIn(b"Build the chord. Hear the key.", body)


if __name__ == "__main__":
    unittest.main()
