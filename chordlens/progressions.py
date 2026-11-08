"""Named chord-progressions registry + renderer (the playground engine).

Each entry: relative semitone offsets + qualities from the key root, so
one render serves all twelve keys. Royal Road first (IV-V-iii-vi,
the J-pop/anime staple); Arabic and Javanese/Sundanese progressions
slot into the same registry when they arrive (non-12-TET scales will
need a tuning extension - noted as ceiling, not promised).
"""

from .chords import NOTE_NAMES
from .synth import render_chord, render_chord_stereo

SR = 11025          # fixture sample rate (legacy mono path, byte-stable)
PLAY_SR = 22050     # playback sample rate (new stereo engine)
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


def _S(semis, label, quality):
    return {"degree": label, "semitones": semis, "quality": quality}


PROGRESSIONS = {
    "royal-road": {
        "name": "Royal Road",
        "origin": "Japan",
        "native": "王道進行",
        "genre": "anime · J-pop",
        "mood": "Yearning, soaring, nostalgic",
        "description": ("IV - V - iii - vi. Never lands on I, so tension "
                        "circles forever. Endless in anime openings and "
                        "city-pop choruses. Learn this plain-triad version "
                        "first, then graduate to the 7ths variant."),
        "steps": [
            _S(5, "IV", "maj"), _S(7, "V", "maj"),
            _S(4, "iii", "min"), _S(9, "vi", "min"),
        ],
    },
    "royal-road-7": {
        "name": "Royal Road (7ths)",
        "origin": "Japan",
        "native": "王道進行",
        "genre": "anime · J-pop",
        "mood": "The full anime sound, silkier and more grown-up",
        "description": ("IVmaj7 - V7 - iii7 - vi7. The same loop with 7th "
                        "chords - the shimmer you hear under late-night "
                        "anime endings and city-pop bridges."),
        "steps": [
            _S(5, "IVmaj7", "maj7"), _S(7, "V7", "7"),
            _S(4, "iii7", "min7"), _S(9, "vi7", "min7"),
        ],
    },
    "pop-axis": {
        "name": "Pop Axis",
        "origin": "Western pop",
        "native": "",
        "genre": "pop · worldwide",
        "mood": "Confident, sing-along",
        "description": ("I - V - vi - IV. The four-chord loop behind "
                        "thousands of hits. Starts and keeps returning "
                        "home - the opposite game from the Royal Road."),
        "steps": [
            _S(0, "I", "maj"), _S(7, "V", "maj"),
            _S(9, "vi", "min"), _S(5, "IV", "maj"),
        ],
    },
    "classic-cadence": {
        "name": "Classic Cadence",
        "origin": "Western common practice",
        "native": "",
        "genre": "classical · folk",
        "mood": "Steady, homeward",
        "description": ("I - IV - V - I. The sentence shape of Western "
                        "music for three centuries: leave home, build "
                        "tension, return."),
        "steps": [
            _S(0, "I", "maj"), _S(5, "IV", "maj"),
            _S(7, "V", "maj"), _S(0, "I", "maj"),
        ],
    },
    "rotation": {
        "name": "Axis Rotation",
        "origin": "Western pop",
        "native": "",
        "genre": "pop · ballad",
        "mood": "Wistful but driving",
        "description": ("vi - IV - I - V. The pop axis starting from the "
                        "relative minor: opens minor-colored, lifts when "
                        "I arrives."),
        "steps": [
            _S(9, "vi", "min"), _S(5, "IV", "maj"),
            _S(0, "I", "maj"), _S(7, "V", "maj"),
        ],
    },
    "doo-wop": {
        "name": "Doo-Wop",
        "origin": "USA, 1950s",
        "native": "",
        "genre": "'50s · vintage",
        "mood": "Sweet, retro, romantic",
        "description": ("I - vi - IV - V. Blue moon, stand by me. I echoes "
                        "into vi like an answer, then a gentle sway home. "
                        "The first progression most guitarists learn."),
        "steps": [
            _S(0, "I", "maj"), _S(9, "vi", "min"),
            _S(5, "IV", "maj"), _S(7, "V", "maj"),
        ],
    },
    "canon": {
        "name": "Canon",
        "origin": "Baroque, 1700s",
        "native": "",
        "genre": "classical · pop",
        "mood": "Flowing, inevitable",
        "description": ("I - V - vi - iii - IV - I - IV - V. Pachelbel's "
                        "ground bass, still under countless ballads and "
                        "wedding songs four centuries later."),
        "steps": [
            _S(0, "I", "maj"), _S(7, "V", "maj"), _S(9, "vi", "min"),
            _S(4, "iii", "min"), _S(5, "IV", "maj"), _S(0, "I", "maj"),
            _S(5, "IV", "maj"), _S(7, "V", "maj"),
        ],
    },
    "blues-12": {
        "name": "12-Bar Blues",
        "origin": "USA, Delta blues",
        "native": "",
        "genre": "blues · rock",
        "mood": "Rough, storytelling",
        "description": ("I - I - I - I - IV - IV - I - I - V - IV - I - V. "
                        "The form itself: the turnaround at the end spits "
                        "you back to the top. Twelve bars, whole genre."),
        "steps": [
            _S(0, "I", "maj"), _S(0, "I", "maj"), _S(0, "I", "maj"), _S(0, "I", "maj"),
            _S(5, "IV", "maj"), _S(5, "IV", "maj"),
            _S(0, "I", "maj"), _S(0, "I", "maj"),
            _S(7, "V", "maj"), _S(5, "IV", "maj"), _S(0, "I", "maj"), _S(7, "V", "maj"),
        ],
    },
    "andalusian": {
        "name": "Andalusian",
        "origin": "Spain / flamenco",
        "native": "",
        "genre": "flamenco · minor",
        "mood": "Dark, dramatic descent",
        "description": ("i - VII - VI - V. The first minor-key cadence in "
                        "the atlas: a walk-down that snaps back to the top. "
                        "Here 'key' means the MINOR tonic - key C plays "
                        "Cm - B - Ab - G. Root of Arabic-descended "
                        "progressions too."),
        "steps": [
            _S(0, "i", "min"), _S(10, "VII", "maj"),
            _S(8, "VI", "maj"), _S(7, "V", "maj"),
        ],
    },
    "jazz-cadence": {
        "name": "Jazz Cadence",
        "origin": "Jazz",
        "native": "",
        "genre": "jazz",
        "mood": "Smooth, resolving",
        "description": ("ii - V - I. Three chords that summarize all of "
                        "functional harmony; learn this one and you can "
                        "sit in with a jazz band."),
        "steps": [
            _S(2, "ii", "min"), _S(7, "V", "maj"), _S(0, "I", "maj"),
        ],
    },
    # future: city pop, lo-fi, gospel, metal, K-pop, video-game loops -
    # the atlas grows as data entries. Javanese/Sundanese pelog needs a
    # non-12-TET tuning extension (own design pass).
}

QUALITY_INTERVALS = {
    "maj": (0, 4, 7), "min": (0, 3, 7), "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11), "min7": (0, 3, 7, 10), "dim": (0, 3, 6),
    "sus4": (0, 5, 7), "aug": (0, 4, 8),
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


def render_single_stereo(root_pc, quality, dur=1.4, base_midi=48,
                         timbre="keys", seed=1):
    """One chord, new stereo engine - what the app actually plays."""
    midis = [base_midi + root_pc + iv for iv in QUALITY_INTERVALS[quality]]
    midis.append(base_midi + root_pc + 12)
    from .synth import render_stereo, stereo_to_wav_bytes
    left, right = render_stereo(midis, dur + 0.25, PLAY_SR, timbre=timbre,
                                 seed=seed)
    return stereo_to_wav_bytes(left, right, PLAY_SR)


def render_stereo(prog_id, key_root=0, bpm=100, loops=LOOPS, timbre="keys"):
    """A progression rendered with the new stereo engine -> (left, right)."""
    chord_dur = BEATS_PER_CHORD * 60.0 / bpm
    lead_in = 0.5
    total = lead_in + chord_dur * len(PROGRESSIONS[prog_id]["steps"]) * loops + 0.5
    left = [0.0] * int(total * PLAY_SR)
    right = [0.0] * int(total * PLAY_SR)
    chords = chords_for(prog_id, key_root)
    t = lead_in
    for loop in range(loops):
        for ch in chords:
            render_chord_stereo(left, right, ch["midis"], t, chord_dur - 0.05,
                                PLAY_SR, timbre, seed=int(t * 1000) + loop * 7919)
            t += chord_dur
    from .synth import _reverb, master
    _reverb(left, right, PLAY_SR)
    master(left, right, PLAY_SR)
    return left, right


def render_stereo_bytes(prog_id, key_root=0, bpm=100, timbre="keys"):
    """Progression -> stereo WAV bytes (the app's playback format)."""
    from .synth import stereo_to_wav_bytes
    left, right = render_stereo(prog_id, key_root, bpm, timbre=timbre)
    return stereo_to_wav_bytes(left, right, PLAY_SR)


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
