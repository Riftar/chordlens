# chordlens

Name the chords in any recording — offline, in pure Python stdlib. No
cloud, no model, no upload: a Fourier transform folds your audio into
twelve pitch-class buckets (a *chromagram*), and harmonic chord templates
pick the best match per frame.

## Quick start

```bash
python3 fixtures/gen_fixtures.py          # regenerates the demo WAVs + truth
python3 -m unittest discover -s tests     # all tests, offline
python3 server.py                         # web UI at http://127.0.0.1:8740
```

In the UI: drop a 16-bit PCM WAV (or click the demo loop). You get a
clickable chord timeline, a chromagram heatmap, and synced playback.

CLI:

```bash
python3 -m chordlens song.wav             # timeline to stdout
python3 -m chordlens song.wav --json      # machine-readable
ffmpeg -i song.mp3 song.wav               # mp3? convert first
```

## What it detects

maj, min, 7, maj7, min7, dim, sus4 — 84 chords from 12 roots × 7
qualities, via harmonic templates that *expect* overtone energy (the 3rd
partial of a major triad's third lands on the major 7th; naive templates
read every major chord as maj7 because of it).

## Honest limits (measured, not hidden)

- Frames within one FFT window (~0.7 s) of a chord boundary straddle two
  chords; interior frames are what the accuracy gates score.
- Clean synthetic recordings: interior exact ≥ 75%, region majority
  6/7 chords exact + 7/7 quality family.
- Real songs (verified on guitar backing tracks, 2026-11-06): a known
  Am-F-C-G loop comes back as exactly those four triads, top-4 by time.
  Dense mixes keep their roots and key palette; individual chord *edges*
  still flicker between neighboring qualities (sus4 vs 7 vs triad) —
  boundary refinement is the open frontier.
- The maj-vs-7th knife edge on quiet 7ths is a known trade-off tuned in
  favor of real triads.
- 16-bit PCM WAV in; 8/24/32-bit and float WAVs are rejected with a
  clear message (convert first).

## Layout

- `chordlens/` — `dsp.py` (FFT, windowing), `chroma.py` (chromagram),
  `chords.py` (harmonic templates + matching), `detect.py` (WAV IO,
  smoothing, segmentation), CLI in `__main__.py`
- `server.py` — stdlib HTTP server: static client, `/api/analyze`
- `www/` — single-file client + `tokens.css`
- `fixtures/` — deterministic generator (fixed-seed LCG): clean /
  messy / silence WAVs + `truth.json`
- `songs/` — four real guitar backing tracks (mono 11 kHz WAV) used to
  calibrate the detector on real audio (2026-11-06): `am-rock.wav` is the
  calibration reference — a stated Am-F-C-G loop the detector returns as
  exactly those four triads
- `tests/` — accuracy gates + server contract tests, loopback-only

## License

MIT — see [LICENSE](LICENSE).
