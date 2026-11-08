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

# Major-scale degree table: semitone offset + triad quality per degree.
# Qualities are DERIVED from stacking thirds (scale steps 0-2-4), matching
# music theory: I ii iii IV V vi vii°.
MAJOR_STEPS = (0, 2, 4, 5, 7, 9, 11)
NUMERALS = ("I", "ii", "iii", "IV", "V", "vi", "vii°")
FUNCTIONS = ("Tonic", "Subdominant", "Tonic", "Subdominant", "Dominant",
             "Tonic", "Dominant")


def _degree_quality(deg):
    """Stack thirds on scale degree `deg` (0..6) -> (semitones, quality)."""
    def pick(i):
        return MAJOR_STEPS[i % 7] + 12 * (i // 7)
    root, third, fifth = pick(deg), pick(deg + 2), pick(deg + 4)
    iv3, iv5 = third - root, fifth - root
    if iv5 == 6:
        quality = "dim"
    elif iv3 == 4:
        quality = "maj"
    else:
        quality = "min"
    return root, quality


def key_chords(key_root):
    """The seven diatonic triads of a major key: numeral, label, notes,
    harmonic function. One endpoint serves every key."""
    out = []
    for deg in range(7):
        semis, quality = _degree_quality(deg)
        base_pc = (key_root + semis) % 12
        notes = [NOTE_NAMES[(base_pc + iv) % 12]
                 for iv in QUALITY_INTERVALS[quality]]
        out.append({
            "numeral": NUMERALS[deg],
            "label": NOTE_NAMES[base_pc] + quality,
            "notes": notes,
            "function": FUNCTIONS[deg],
        })
    return out


def _deg_step(deg, degree_label):
    semis, quality = _degree_quality(deg)
    return {"degree": degree_label, "semitones": semis, "quality": quality}


PROGRESSIONS = {
    "royal-road": {
        "name": "Royal Road",
        "origin": "Japan",
        "native": "王道進行",
        "description": ("IV - V - iii - vi. The J-pop and anime staple: "
                        "two rising steps, then a soft landing on vi. "
                        "Endless in anime openings and city-pop choruses."),
        "steps": [
            _deg_step(3, "IV"), _deg_step(4, "V"),
            _deg_step(2, "iii"), _deg_step(5, "vi"),
        ],
    },
    "pop-axis": {
        "name": "Pop Axis",
        "origin": "Western pop",
        "native": "",
        "description": ("I - V - vi - IV. The four-chord loop behind "
                        "thousands of hits; nearly every campfire song "
                        "lives here."),
        "steps": [
            _deg_step(0, "I"), _deg_step(4, "V"),
            _deg_step(5, "vi"), _deg_step(3, "IV"),
        ],
    },
    "classic-cadence": {
        "name": "Classic Cadence",
        "origin": "Western common practice",
        "native": "",
        "description": ("I - IV - V - I. The sentence shape of Western "
                        "music for three centuries: leave home, build "
                        "tension, return."),
        "steps": [
            _deg_step(0, "I"), _deg_step(3, "IV"),
            _deg_step(4, "V"), _deg_step(0, "I"),
        ],
    },
    "rotation": {
        "name": "Axis Rotation",
        "origin": "Western pop",
        "native": "",
        "description": ("vi - IV - I - V. The pop axis starting from the "
                        "relative minor: same four chords, darker first "
                        "impression."),
        "steps": [
            _deg_step(5, "vi"), _deg_step(3, "IV"),
            _deg_step(0, "I"), _deg_step(4, "V"),
        ],
    },
    "doo-wop": {
        "name": "Doo-Wop",
        "origin": "USA, 1950s",
        "native": "",
        "description": ("I - vi - IV - V. The '50s standby - blue moon, "
                        "stand by me. The first progression most "
                        "guitarists ever learn."),
        "steps": [
            _deg_step(0, "I"), _deg_step(5, "vi"),
            _deg_step(3, "IV"), _deg_step(4, "V"),
        ],
    },
    "jazz-cadence": {
        "name": "Jazz Cadence",
        "origin": "Jazz",
        "native": "",
        "description": ("ii - V - I. Three chords that summarize all of "
                        "functional harmony; learn this one and you can "
                        "sit in with a jazz band."),
        "steps": [
            _deg_step(1, "ii"), _deg_step(4, "V"), _deg_step(0, "I"),
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


def render_single(root_pc, quality, dur=1.4, base_midi=48):
    """One chord as WAV bytes - the lesson pages' playback primitive."""
    midis = [base_midi + root_pc + iv for iv in QUALITY_INTERVALS[quality]]
    midis.append(base_midi + root_pc + 12)
    buf = [0.0] * int((dur + 0.3) * SR)
    render_chord(buf, midis, 0.05, dur, SR)
    from .synth import samples_to_wav_bytes
    return samples_to_wav_bytes(buf, SR)


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
