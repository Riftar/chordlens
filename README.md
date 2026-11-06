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
  7/7 chords correct.
- Dense mixes (drums + bass drone + gain wobble): chord *roots* stay
  findable (≥ 55% interior frames, ≥ 4/7 region majorities); quality
  labels degrade first. Real-song quality tuning is the open frontier.
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
- `tests/` — accuracy gates + server contract tests, loopback-only

## License

MIT — see [LICENSE](LICENSE).
