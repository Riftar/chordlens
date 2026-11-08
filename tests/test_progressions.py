"""Progression playground: registry, renderer, and the self-detect loop
(render the Royal Road, feed it to the detector, expect the same chords)."""

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

PORT = 8972
BASE = f"http://127.0.0.1:{PORT}"


class TestRegistry(unittest.TestCase):
    def test_royal_road_present_with_four_steps(self):
        p = progressions.PROGRESSIONS["royal-road"]
        self.assertEqual([s["degree"] for s in p["steps"]], ["IV", "V", "iii", "vi"])

    def test_chords_for_c_major(self):
        labels = [c["label"] for c in progressions.chords_for("royal-road", 0)]
        self.assertEqual(labels, ["Fmaj", "Gmaj", "Emin", "Amin"])

    def test_render_is_deterministic_and_valid_wav(self):
        a = progressions.render("royal-road", 0, 100)
        b = progressions.render("royal-road", 0, 100)
        self.assertEqual(a, b)
        self.assertEqual(a[:4], b"RIFF")
        with wave.open(io.BytesIO(a)) as w:
            self.assertEqual(w.getnchannels(), 1)
            self.assertEqual(w.getsampwidth(), 2)
            self.assertEqual(w.getframerate(), 11025)
            # 4 chords x 4 beats @100bpm x 2 loops + ~1s lead/tail
            dur = w.getnframes() / 11025
            self.assertTrue(18.5 < dur < 20.5, dur)

    def test_render_faster_bpm_is_shorter(self):
        slow = progressions.render("royal-road", 0, 60)
        fast = progressions.render("royal-road", 0, 160)
        self.assertLess(len(fast), len(slow))


class TestSelfDetect(unittest.TestCase):
    """The playground's party trick, gated: render the Royal Road in C,
    analyze it, and the four truth chords must be the top-4 by time."""

    def test_detector_reads_back_royal_road(self):
        import tempfile
        data = progressions.render("royal-road", 0, 100)
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
                         f"segments {segs[:8]}... weights {weights}")


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

    def test_progressions_list_and_key_chords(self):
        status, body = self.get("/api/progressions")
        self.assertEqual(status, 200)
        entry = json.loads(body)[0]
        self.assertEqual(entry["id"], "royal-road")
        self.assertNotIn("chords", entry)
        _, keyed = self.get("/api/progressions?key=2")  # D major
        self.assertEqual(json.loads(keyed)[0]["chords"], ["Gmaj", "Amaj", "F#min", "Bmin"])

    def test_progression_wav_endpoint(self):
        status, body = self.get("/api/progression.wav?id=royal-road&key=0&bpm=120")
        self.assertEqual(status, 200)
        self.assertEqual(body[:4], b"RIFF")

    def test_bad_params_rejected(self):
        for q in ("id=nope&key=0&bpm=100", "id=royal-road&key=0&bpm=999",
                  "id=royal-road&key=zero&bpm=100"):
            try:
                self.get("/api/progression.wav?" + q)
                self.fail(f"accepted bad params: {q}")
            except urllib.error.HTTPError as e:
                self.assertIn(e.code, (400, 404))

    def test_playground_page_served(self):
        status, body = self.get("/progressions.html")
        self.assertEqual(status, 200)
        self.assertIn(b"Progression playground", body)


if __name__ == "__main__":
    unittest.main()
