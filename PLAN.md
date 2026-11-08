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

**Ladder revision 2 (2026-11-08, after the Chord Lab atlas review):**
the atlas bet is adopted - progressions taught as a map of moods,
mood-first, theory-second; the Royal Road leads. The detector moat
still ships before content scale-up; persistence lands with the
features that need it; PWA/mobile hardening is the pre-launch rung.
Items that break a standing principle (vendored deps, cloud, telemetry)
moved to a deliberate-exceptions tier below - adopting any of them is
an explicit decision, never drift. Note: the prototype roadmap's
urgent "lookahead scheduler" fix does not apply - that bug lives in
client-side oscillator loops; chordlens plays server-rendered WAVs
through <audio> elements and has no timer to drift.

### v0.2.1 — Atlas upgrade (SHIPPED 2026-11-08)
Mood/genre framing on every registry entry; 10 progressions (Royal
Road + its 7ths variant, Pop Axis, Classic Cadence, Axis Rotation,
Doo-Wop, Canon, 12-Bar Blues, Andalusian - first minor-key entry,
Jazz Cadence); per-chord click-to-hear chips with loop playhead;
augmented quality in the triad lab and renderer.

### v0.3 — Ear trainer I: qualities + name-that-progression
- **Scope:** two seeded server-driven modes: (a) chord quality ID
  (maj/min/dim/aug); (b) "name that progression" - hear a loop, pick
  the atlas card. Per-answer feedback revealing notes/degrees; best
  scores in localStorage.
- **Gate:** fixed seed -> fixed question sequence (API-tested);
  headless run answers and scores; best score survives reload.
- **NOT:** mic input, interval ID, difficulty tiers, cloud.

### v0.4 — Quiz + review queue + progress view
- **Scope:** data-driven quiz bank (served, not hardcoded), missed
  questions resurface until mastered (deterministic review queue),
  scoring tiers, 7-day practice plan, progress view (streak,
  completions, bests - localStorage; IndexedDB only when data
  outgrows strings).
- **Gate:** bank served by endpoint; headless perfect run lands the
  perfect-tier message; a wrong answer re-asks before finish;
  completions survive reload.
- **NOT:** accounts, spaced repetition scheduling, telemetry. The
  analytics funnel stays LOCAL until there are real learners.

### v0.5 — Listen mode (the moat, and the hardest rung)
- **Scope:** browser mic → Web Audio AnalyserNode → a JS twin of the
  chroma+template matcher (literal mirror of the Python: same steps,
  same field names), showing the live chord name; "play X" exercises
  graded from the live stream. Client-side only — audio never posted.
  Optional: Web MIDI input (native browser API, zero-dep) as an
  alternative answer path for keyboard owners.
- **Gate:** the JS twin passes the same asserts as the Python reference
  on synthetic frames drawn to a canvas (the proven tryon twin
  pattern); a headless synthetic-sine probe reads the right chord.
- **NOT:** server-side mic (none exists), polyphonic transcription,
  grading beyond "right chord sustained ~1 s".

### v0.6 — Progression builder (the creative rung)
- **Scope:** tap chords from a key palette into your own loop (V7 and
  bVII spice chords included), reorder/remove, set tempo, play with
  playhead, starter ideas, save named loops to localStorage, "read it
  back" through the detector, and export as MIDI (a .mid writer is a
  small pure-stdlib binary format - zero-dep by construction).
- **Gate:** built loop renders and the detector reads its chords back;
  saved loops survive reload; exported MIDI parses as a valid file
  (header chunk + track events byte-checked).
- **NOT:** sharing, accounts, MIDI recording of live input.

### v0.7 — Atlas deepening (the content rung)
- **Scope:** 10 → 30+ progressions as data entries: city pop, lo-fi,
  gospel, metal, K-pop, video-game loops - each with mood, genre,
  why-it-works; 8-bar "hear it in context" demos.
- **Gate:** each new entry passes the same registry tests (degrees,
  labels in two keys, render + RIFF); atlas page loads all entries.
- **NOT:** lesson pages per progression (mini-lessons land with v0.9
  curriculum), audio samples of real songs (synth demos only).

### v0.8 — Mobile + PWA + a11y hardening (the pre-launch rung)
- **Scope:** service worker + manifest (vanilla), installable icon,
  full keyboard-nav and ARIA sweep, visual fallbacks for every audio
  cue (the piano-highlight pattern extended), responsive polish.
- **Gate:** manifest served, SW caches, no horizontal scroll at
  320/375/414/768, every interactive element keyboard-reachable.
- **NOT:** app-store packaging, native shells.

### v0.9 — Curriculum depth (theory lessons as data)
- **Scope:** lessons/quizzes as served JSON: 7th chords, inversions,
  minor keys, sus/add, blues form, cadences; per-progression
  mini-lessons with a 3-question check; ear trainer difficulty tiers.
- **Gate:** new topics appear in lesson + quiz + ear trainer from data
  alone (no client change); each topic's quiz gate passes.
- **NOT:** staff notation (VexFlow - exceptions tier).

### Deliberate exceptions (each requires an explicit Principal decision)
These are good ideas that break a standing principle; adopting any one
is a decision, never drift:
- **Staff notation (VexFlow)** - first vendored JS dependency.
- **Accounts + cloud sync** - backend, auth, and the offline identity
  changes; anonymous-first stays until retention proves it.
- **Error monitoring / analytics beyond local** - telemetry of any kind
  leaves the machine; contradicts the offline promise.
- **Richer synth voices (bass, swing, style presets) + metronome
  click** - either a server click-track render or a client twin of the
  synth; both are engine growth competing with detector work.
- **Song-reference links per progression** - fine as plain outbound
  links; anything richer (embedded players) drags third-party assets.

### Post-launch (only after retention proves it)
- Static hosting, landing page + SEO, PWA store listing, privacy/COPPA
  pass, freemium or one-time unlock.
- Cultural expansion continues in the atlas registry: Arabic
  (Andalusian-adjacent), Javanese/Sundanese - pelog/slendro need a
  non-12-TET tuning extension, its own design pass.
- Quality-label accuracy on dense mixes; boundary sharpening
  (multi-resolution front end); guitar fretboard view; song-pattern
  library with reference titles (progressions aren't copyrightable;
  titles as references only).

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
