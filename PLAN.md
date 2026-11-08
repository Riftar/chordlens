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

**Ladder revision (2026-11-08, after the product roadmap review):** the
detector moat stays ahead of creative/convenience features; persistence
lands with the features that need it; PWA/mobile hardening is the
pre-launch rung, not an early one. Items that break a standing principle
(vendored deps, cloud, telemetry) moved to a deliberate-exceptions tier
below - adopting any of them is an explicit decision, never drift.
Note: the roadmap's urgent "lookahead scheduler" fix does not apply -
that bug lives in client-side oscillator loops; chordlens plays
server-rendered WAVs through one <audio> element and has no timer to
drift. The one-engine rule already paid for itself.

### v0.2 — Lessons: triads and the key (SHIPPED 2026-11-08, bbca0d7)
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
  per-answer feedback revealing the notes; best score kept in
  localStorage (first persistence, arriving with the first feature
  that produces a score worth keeping).
- **Gate:** a fixed seed produces a fixed question sequence (tested via
  API); a headless run records answers and shows the final score;
  reload keeps the best score.
- **NOT:** mic input, difficulty beyond the three qualities, cloud,
  cross-device sync.

### v0.4 — Quiz + practice plan + progress view
- **Scope:** data-driven quiz (question bank served by the server, not
  hardcoded in the client), explanation on every answer, scoring tiers,
  the 7-day practice plan page, and a small progress view (streak,
  lesson completions, ear/quiz bests - all localStorage; IndexedDB only
  when data outgrows strings, not before).
- **Gate:** quiz endpoint serves the bank; a headless run answers
  everything correctly and lands the perfect-tier message; completions
  survive a reload.
- **NOT:** accounts, spaced repetition, multiple banks, telemetry.
  The analytics funnel stays LOCAL (completion events in localStorage,
  exportable by hand) until there are real learners to instrument.

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
- **Scope:** drag/tap chords from a key into your own loop, set tempo,
  play it, save named loops to localStorage, and "read it back" through
  the detector (self-check for free). Saved loops render through the
  same /api/progression.wav engine.
- **Gate:** a built loop renders and the detector reads its chords back
  (same gate as the registry); saved loops survive reload; headless
  build-render-read pass.
- **NOT:** sharing/export, accounts, MIDI recording.

### v0.7 — Mobile + PWA + a11y hardening (the pre-launch rung)
- **Scope:** service worker + manifest (vanilla, offline by nature),
  installable icon, full keyboard-nav and ARIA sweep across all pages,
  visual fallbacks for every audio cue (the piano highlight pattern
  already does this - extend it), responsive polish on every page.
- **Gate:** Lighthouse-style manual checklist green headlessly
  (manifest served, SW caches, no horizontal scroll at 320/375/414/768,
  every interactive element reachable by keyboard).
- **NOT:** app-store packaging, native shells.

### v0.8 — Curriculum depth (content rung, after 10-learner feedback)
- **Scope:** lessons as served data (JSON lesson/quiz banks): 7th
  chords, inversions, minor keys, sus/add, blues form, cadences; ear
  trainer difficulty tiers with wrong-answer resurfacing (local,
  deterministic SM-2-lite).
- **Gate:** new topics appear in lesson + quiz + ear trainer from data
  alone (no client change); each new topic's quiz gate passes.
- **NOT:** staff notation (needs VexFlow - exceptions tier), adaptive
  sequencing beyond resurfacing.

### Deliberate exceptions (each requires an explicit Principal decision)
These are good ideas that break a standing principle; adopting any one
is a decision, never drift:
- **Staff notation (VexFlow)** - first vendored JS dependency.
- **Accounts + cloud sync** - backend, auth, and the offline identity
  changes; anonymous-first stays until retention proves it.
- **Error monitoring / analytics beyond local** - telemetry of any kind
  leaves the machine; contradicts the offline promise.
- **Richer synth voices (bass, swing, style presets)** - engine growth;
  fine, but it competes with detector work for the same hands.

### Later (parked, not promised)
- Cultural expansion: Arabic (Andalusian i-VII-VI-V) and Javanese/
  Sundanese progressions; pelog/slendro need a non-12-TET tuning
  extension — its own design pass, not a data entry.
- Quality-label accuracy on dense mixes; boundary sharpening
  (multi-resolution front end); song-pattern library with reference
  titles (progressions aren't copyrightable; titles as references only).
- Guitar fretboard view, Bb/Eb transpose, monetization - after launch
  and only if retention asks for them.

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
