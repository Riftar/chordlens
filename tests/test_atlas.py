"""v0.2.1 atlas upgrade: mood/genre registry, new progressions
(canon, 12-bar blues, andalusian, royal-road-7), aug quality."""

import json
import os
import sys
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chordlens import progressions  # noqa: E402

PORT = 8974
BASE = f"http://127.0.0.1:{PORT}"


class TestAtlasRegistry(unittest.TestCase):
    def test_ten_entries_with_mood_and_genre(self):
        self.assertEqual(len(progressions.PROGRESSIONS), 10)
        for pid, p in progressions.PROGRESSIONS.items():
            self.assertTrue(p.get("mood"), f"{pid} missing mood")
            self.assertTrue(p.get("genre"), f"{pid} missing genre")

    def test_new_entries_degrees(self):
        cases = {
            "royal-road-7": ["IVmaj7", "V7", "iii7", "vi7"],
            "canon": ["I", "V", "vi", "iii", "IV", "I", "IV", "V"],
            "blues-12": ["I"] * 4 + ["IV"] * 2 + ["I"] * 2 + ["V", "IV", "I", "V"],
            "andalusian": ["i", "VII", "VI", "V"],
        }
        for pid, degrees in cases.items():
            self.assertEqual(
                [s["degree"] for s in progressions.PROGRESSIONS[pid]["steps"]],
                degrees)

    def test_royal_road_7_labels_in_c(self):
        labels = [c["label"] for c in progressions.chords_for("royal-road-7", 0)]
        self.assertEqual(labels, ["Fmaj7", "G7", "Emin7", "Amin7"])

    def test_andalusian_labels_key_c_is_minor_tonic(self):
        labels = [c["label"] for c in progressions.chords_for("andalusian", 0)]
        self.assertEqual(labels, ["Cmin", "A#maj", "G#maj", "Gmaj"])

    def test_canon_labels_in_c(self):
        labels = [c["label"] for c in progressions.chords_for("canon", 0)]
        self.assertEqual(labels, ["Cmaj", "Gmaj", "Amin", "Emin", "Fmaj",
                                  "Cmaj", "Fmaj", "Gmaj"])

    def test_aug_quality_renders(self):
        data = progressions.render_single(0, "aug", 0.8)
        self.assertEqual(data[:4], b"RIFF")

    def test_blues_renders_full_form(self):
        """12 bars x 2 loops at 100bpm = 57.6s of chords + margins."""
        import io
        import wave
        data = progressions.render("blues-12", 0, 100, loops=1)
        with wave.open(io.BytesIO(data)) as w:
            dur = w.getnframes() / w.getframerate()
        self.assertTrue(28 < dur < 31, dur)  # 12 bars x 2.4s + lead/tail


class TestAtlasAPI(unittest.TestCase):
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
        with urllib.request.urlopen(BASE + path, timeout=60) as r:
            return r.status, r.read()

    def test_progressions_carry_mood_and_genre(self):
        _, body = self.get("/api/progressions")
        entries = json.loads(body)
        self.assertEqual(len(entries), 10)
        royal = entries[0]
        self.assertEqual(royal["id"], "royal-road")
        self.assertIn("Yearning", royal["mood"])
        self.assertIn("anime", royal["genre"])

    def test_andalusian_wav_endpoint(self):
        status, body = self.get("/api/progression.wav?id=andalusian&key=0&bpm=100")
        self.assertEqual(status, 200)
        self.assertEqual(body[:4], b"RIFF")

    def test_aug_chord_endpoint(self):
        status, body = self.get("/api/chord.wav?root=0&quality=aug&dur=1.0")
        self.assertEqual(status, 200)
        self.assertEqual(body[:4], b"RIFF")


if __name__ == "__main__":
    unittest.main()
