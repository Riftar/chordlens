# Vendored third-party file

- **File:** `vexflow.js` — VexFlow 5.0.0, full pre-built CJS/UMD bundle
- **Source:** https://cdn.jsdelivr.net/npm/vexflow@5.0.0/build/cjs/vexflow.js
  (canonical: https://www.npmjs.com/package/vexflow, MIT license)
- **SHA-256:** `7429f05593d79f9c9e5e24318c9177f054f63366f9bba977a60ae1d95fe31ecd`
- **Size:** 1,128,380 bytes
- **Vendored:** 2026-11-08, Principal-approved exception to the zero-vendored-deps
  rule (decision logged in PLAN.md). Downloaded once over the network; from here
  it is served like first-party code and works fully offline.
- **License:** MIT — copyright notice preserved in the bundle header
  (VexFlow contributors). See the header comment in the file itself.

Usage rule: load it LAZILY, only on views that render staff notation.
No other page may reference it — the rest of the client stays byte-light
and dependency-free. When a staff view is built (see PLAN), it should
append this script on demand, not include it in any page by default.
