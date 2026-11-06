"""Chord vocabulary and template matching."""

import math

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

QUALITIES = {
    "maj":  (0, 4, 7),
    "min":  (0, 3, 7),
    "7":    (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "dim":  (0, 3, 6),
    "sus4": (0, 5, 7),
}

# Harmonic templates: a chord tone does not emit one pitch class — it
# emits a decaying harmonic series, and harmonics fold back into other
# pitch classes (the 3rd partial of the major third lands on the major
# 7th of the root, so every major triad carries phantom-7th energy).
# Templates that EXPECT that overtone pattern stop misreading triads
# as 7th chords; cosine similarity then lets surplus full-strength
# energy pick the extended chord.
_PARTIALS = tuple((k, a) for k, a in enumerate(
    (1.0, 0.7, 0.5, 0.35, 0.25, 0.18, 0.12, 0.08), start=1))


def _harmonic_template(root, ivs):
    w = [0.0] * 12
    for iv in ivs:
        for k, amp in _PARTIALS:
            cls = (root + iv + int(12 * math.log2(k) + 0.5)) % 12
            w[cls] += amp
    top = max(w)
    return [x / top for x in w]


TEMPLATES = {}
for _root in range(12):
    for _name, _ivs in QUALITIES.items():
        TEMPLATES[(_root, _name)] = _harmonic_template(_root, _ivs)


def label(root, name):
    return NOTE_NAMES[root] + name


def rank_chords(pc):
    """All 84 chords scored against a chroma vector, best first."""
    norm_pc = math.sqrt(sum(p * p for p in pc))
    if norm_pc == 0.0:
        return []

    def score(t):
        num = sum(p * w for p, w in zip(pc, t))
        den = norm_pc * math.sqrt(sum(w * w for w in t))
        return num / den
    ranked = sorted(
        ((score(t), label(r, q)) for (r, q), t in TEMPLATES.items()),
        reverse=True,
    )
    return ranked


def best_chord(pc):
    return rank_chords(pc)[0][1]
