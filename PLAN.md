# PLAN — chordlens

## Problem

Two problems, one engine.

1. **Detection.** You hear a song and want to know what chords it plays —
   without uploading it anywhere. Chord detection is solved classical DSP
   (chromagram + harmonic templates) that needs no network and no model,
   yet public tools for it are cloud SaaS that ship your audio elsewhere.
2. **Learning.** Chord theory is taught as symbols on a page. The thing
   that makes it stick is *hearing* the difference (major vs minor, the
   V→I pull) and *doing* it (playing, being heard back). A local detector
   plus a synth is exactly the machinery a learning module needs: it can
   play any chord in any key AND listen to the learner.

**Pivot (2026-11-08, Principal's call):** chordlens grows from a detector
tool into an offline chord-learning platform — lessons, ear training,
quizzes, and progression exploration — with the detector as the
teacher's ear. The detector work already shipped becomes the moat: no
other chord-learning app can listen to you play. Design reference: the
Learning Coach's single-file interactive module (kept private at
~/repos/.plans/, not copied into the repo).

## Goals (ceiling)

- **Detect:** full quality labels (maj/min/7/maj7/min7/dim/sus4) on clean
  recordings; stable roots in dense mixes; chord boundaries with times.
- **Teach:** interactive lessons (what a triad is, the seven chords of a
  key, harmonic functions), a progression playground with named
  culturally-rooted progressions (Royal Road first; Arabic and
  Javanese/Sundanese in the registry later), an ear trainer, and a quiz —
  all playable offline through the browser.
- **Listen (the moat):** live chord reading from the learner's mic, so
  "now play a C major" exercises are graded by the same detector that
  reads songs. Audio never leaves the browser (client-side twin of the
  chroma+template matcher, deliberately implemented twice).
- **Everything offline:** no cloud, no accounts, no CDN dependency;
  progress persists in localStorage at most.

## Shipped (the foundation, 2026-11-06..08)

1. **Core + CLI.** Pure-stdlib FFT → chroma → harmonic chord templates;
   WAV in, chord timeline out. Deterministic fixtures with ground truth.
2. **Real-audio robustness.** Harmonic templates that expect overtone
   energy (a triad's 3rd partial of the major third *is* the major 7th);
   NO spectral whitening (measured on real guitar recordings: log-
   compression lifts overtones to parity with fundamentals and every
   triad reads as a 7th chord); silence gating; median smoothing. Real-
   song check: a known Am-F-C-G loop returns exactly those four triads.
3. **Web UI.** Dropzone, /api/analyze POST (32 MB cap, tempfile,
   deleted), chord timeline, chromagram, synced playback, demo loop.
4. **Progression playground.** Royal Road registry entry, any key/tempo
   render, self-detect loop (unit-gated read-back).

## Iteration ladder (one rung at a time, each shippable alone)

Each rung has a scope, an acceptance gate, and a deliberate NOT-list.
Nothing below ships until the rung above is green.

### v0.2 — Lessons: triads and the key
- **Scope:** two lesson pages in the existing Midnight client: (a) build
  a triad — root/quality selectors, piano-key highlight, play button;
  (b) the key — seven chord cards with numerals + functions, tap to
  hear, V→I resolution demo. Playback stays server-rendered (the
  existing synth, one engine); the progression registry gains the five
  classics from the reference module (I-V-vi-IV, I-IV-V-I, vi-IV-I-V,
  I-vi-IV-V, ii-V-I).
- **Gate:** an /api/key endpoint returns the seven chords for a key
  (unit-tested: C and F produce the correct labels); headless check —
  selectors move the piano highlight, every card plays.
- **NOT:** ear trainer, quiz, mic, client-side synth, localStorage.

### v0.3 — Ear trainer
- **Scope:** 10-round maj/min/dim game. Chords come from a seeded
  server endpoint (rounds replayable, tests deterministic); score line;
  per-answer feedback revealing the notes.
- **Gate:** a fixed seed produces a fixed question sequence (tested via
  API); a headless run records answers and shows the final score.
- **NOT:** mic input, difficulty beyond the three qualities, progress
  persistence across reloads.

### v0.4 — Quiz + practice plan
- **Scope:** data-driven quiz (question bank served by the server, not
  hardcoded in the client), explanation on every answer, scoring tiers,
  and the 7-day practice plan page.
- **Gate:** quiz endpoint serves the bank; a headless run answers
  everything correctly and lands the perfect-tier message.
- **NOT:** accounts, spaced repetition, multiple banks.

### v0.5 — Listen mode (the moat, and the hardest rung)
- **Scope:** browser mic → Web Audio AnalyserNode → a JS twin of the
  chroma+template matcher (literal mirror of the Python: same steps,
  same field names), showing the live chord name; "play X" exercises
  graded from the live stream. Client-side only — audio never posted.
- **Gate:** the JS twin passes the same asserts as the Python reference
  on synthetic frames drawn to a canvas (the proven tryon twin
  pattern); a headless synthetic-sine probe reads the right chord.
- **NOT:** server-side mic (none exists), polyphonic transcription,
  grading beyond "right chord sustained ~1 s".

### Later (parked, not promised)
- Cultural expansion: Arabic (Andalusian i-VII-VI-V) and Javanese/
  Sundanese progressions; pelog/slendro need a non-12-TET tuning
  extension — its own design pass, not a data entry.
- Quality-label accuracy on dense mixes; boundary sharpening
  (multi-resolution front end); progression editing/saving.

## Non-goals

- No ML, no model weights, no vendored binaries. Classical DSP only.
- No accounts, no server-side progress, no telemetry. localStorage only.
- No MP3/OGG decoding in Python — convert first (`ffmpeg -i in.mp3
  out.wav`); the browser's `<audio>` element plays the WAV locally.

## Rollback

Each iteration lands as its own commit range; `git revert` the range to
drop a rung. The server holds no state; `gh repo delete` or a local
`rm -rf chordlens` remains the full escape hatch.

## Offline guarantee

Dev and test run without network: `python3 -m unittest discover -s tests`
loops back to 127.0.0.1 only. The client's only external reference is an
optional Google-Fonts stylesheet for Geist Mono — the page is fully
styled and functional without it (offline by design, prettier online).
