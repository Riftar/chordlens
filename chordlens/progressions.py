"""Named chord-progressions registry + renderer (the playground engine).

Each entry: relative semitone offsets + qualities from the key root, so
one render serves all twelve keys. Royal Road first (IV-V-iii-vi,
the J-pop/anime staple); Arabic and Javanese/Sundanese progressions
slot into the same registry when they arrive (non-12-TET scales will
need a tuning extension - noted as ceiling, not promised).
"""

from .chords import NOTE_NAMES
from .synth import render_chord

SR = 11025
BEATS_PER_CHORD = 4
LOOPS = 2

PROGRESSIONS = {
    "royal-road": {
        "name": "Royal Road",
        "origin": "Japan",
        "native": "王道進行",
        "description": ("IV - V - iii - vi. The J-pop and anime staple: "
                        "two rising steps, then a soft landing on vi. "
                        "Endless in anime openings and city-pop choruses."),
        "steps": [
            {"degree": "IV", "semitones": 5, "quality": "maj"},
            {"degree": "V", "semitones": 7, "quality": "maj"},
            {"degree": "iii", "semitones": 4, "quality": "min"},
            {"degree": "vi", "semitones": 9, "quality": "min"},
        ],
    },
    # future: "andalusian" (i-VII-VI-V, Spain/Arabic-adjacent descent),
    # javanese/sundanese pelog progressions (needs non-12-TET tuning).
}

QUALITY_INTERVALS = {
    "maj": (0, 4, 7), "min": (0, 3, 7), "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11), "min7": (0, 3, 7, 10), "dim": (0, 3, 6),
    "sus4": (0, 5, 7),
}


def chords_for(prog_id, key_root):
    """Chord labels + voicing midis for one pass, e.g. Fmaj/Gmaj/Emin/Amin."""
    prog = PROGRESSIONS[prog_id]
    root_midi = 48 + key_root  # C3-based octave
    out = []
    for step in prog["steps"]:
        base = root_midi + step["semitones"]
        midis = [base + iv for iv in QUALITY_INTERVALS[step["quality"]]]
        midis.append(base + 12)
        label = NOTE_NAMES[base % 12] + step["quality"]
        out.append({"degree": step["degree"], "label": label, "midis": midis})
    return out


def render(prog_id, key_root=0, bpm=100, loops=LOOPS):
    """Deterministic WAV bytes for a progression in a key at a tempo."""
    chord_dur = BEATS_PER_CHORD * 60.0 / bpm
    lead_in = 0.5
    total = lead_in + chord_dur * len(PROGRESSIONS[prog_id]["steps"]) * loops + 0.5
    buf = [0.0] * int(total * SR)
    chords = chords_for(prog_id, key_root)
    t = lead_in
    for _ in range(loops):
        for ch in chords:
            render_chord(buf, ch["midis"], t, chord_dur - 0.05, SR)
            t += chord_dur
    from .synth import samples_to_wav_bytes
    return samples_to_wav_bytes(buf, SR)
