"""Server contract tests: static containment, demo fixture, analyze API."""

import json
import os
import sys
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import serve  # noqa: E402

PORT = 8971
BASE = f"http://127.0.0.1:{PORT}"
FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")


class TestServer(unittest.TestCase):
    httpd = None

    @classmethod
    def setUpClass(cls):
        cls.httpd = serve(PORT)
        import threading
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def get(self, path):
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return r.status, r.read()

    def test_index_served(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"chordlens", body)

    def test_non_root_static_file(self):
        """A static branch that only serves `/` would 404 tokens.css silently."""
        status, body = self.get("/tokens.css")
        self.assertEqual(status, 200)
        self.assertIn(b"--color-accent", body)

    def test_fixture_wav_served_for_demo(self):
        status, body = self.get("/fixtures/clean.wav")
        self.assertEqual(status, 200)
        self.assertEqual(body[:4], b"RIFF")

    def test_traversal_blocked(self):
        for path in ("/../server.py", "/%2e%2e/server.py", "/fixtures/../../server.py"):
            try:
                self.get(path)
                self.fail(f"traversal {path} was served")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 404)

    def test_analyze_roundtrip(self):
        with open(os.path.join(FIX, "clean.wav"), "rb") as f:
            wav = f.read()
        req = urllib.request.Request(BASE + "/api/analyze", data=wav,
                                     headers={"Content-Type": "audio/wav"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read())
        self.assertIn("segments", body)
        self.assertGreater(len(body["segments"]), 0)
        # first chord of the progression is C (maj/maj7 split at the edge is
        # expected; the ROOT is the stable fact)
        self.assertTrue(body["segments"][0]["chord"].startswith("C"),
                        body["segments"][0])
        self.assertTrue(all(len(f["chroma"]) == 12 for f in body["frames"] if f["chroma"]))

    def test_analyze_rejects_garbage(self):
        req = urllib.request.Request(BASE + "/api/analyze", data=b"not a wav at all",
                                     headers={"Content-Type": "audio/wav"})
        try:
            urllib.request.urlopen(req, timeout=30)
            self.fail("garbage body accepted")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 422)


if __name__ == "__main__":
    unittest.main()
