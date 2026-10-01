## Update 2026-07-23 (lab session, artificial ear, DT250 unit X)

Append this block to the **bottom** of `prolactin_open_issues_2026-07-18.md`.
Full detail in `session_changelog_2026-07-23_session_02.md`.

### Resolved

- **Spot-check per-frequency correction layer — RULED OUT (design question closed).**
  Post-FIR flatness on a good channel is within ±0.8 dB across 125–8000 Hz, and
  residuals are level-independent (15 of 22 frequency×ear cells show exactly zero
  spread across a 45 dB range). Candidate corrections would be smaller than or
  comparable to between-seat variance. Where a deviation *is* large and stable, the
  correct fix is regenerating the inverse filter, not stacking a lookup table on top
  of a known-bad FIR. No feature to build.

- **M11 (noise vs tone bias) — QUANTIFIED, and the sign was wrong.**
  Noise reads **quiet** by 0.6–0.8 dB, not loud by 1.3. Consistent across level.
  Bias differs slightly by ear (−0.92 L vs −0.74 R), pointing at the inverse filters
  rather than the stimulus generator. Root-cause diagnostic is a desk task — see
  new item L-a below.

### New items

| ID | Item | Priority |
|---|---|---|
| **M-a** | **`max_spl` not recomputed for `beyerdynamic_dt250_x_ucx2`** after the 2026-07-23 re-anchor. Formula `measured_spl + 20*log10(1/peak_after_FIR) - 3`, using the **quieter** ear — which switched from left to right. Current 105 is conservative, so not blocking. | MED |
| **M-b** | **Profile `_description` not updated** for the unit X re-anchor. Violates the doc-hygiene rule. Draft text prepared in the session changelog. | MED |
| **L-a** | **M11 root cause.** Desk task, no hardware: load the unit X inverse-filter WAVs, compare the RMS-average of \|G(f)\| over the noise band against \|G(1 kHz)\|, per ear. If it matches −0.92 / −0.74, M11 is explained acoustically. Next suspect is the RMS normalisation in the noise generator. **Gates M-d.** | MED |
| **M-c** | **Noise level convention undocumented.** Whether `--type noise` targets broadband SPL or spectrum level (dB SPL/Hz) is not stated anywhere. Matters for maskers, and blocks any noise-based anchoring. | MED |
| **M-d** | **Anchor robustness.** `measured_spl_*` is set from one 1 kHz tone at one seating. Swept-sine data puts the worst FIR residual within ~60 Hz of 1 kHz on both study units (A-L +2.38 dB @ 936 Hz; B-R −1.26 dB @ 1057 Hz), and 1 kHz was the most seat-sensitive frequency measured (0.70 dB between seats vs 0.00–0.10 elsewhere). Leading explanation for the channel-asymmetric anchor drift found on unit X. Three measures, cheapest first — multi-seat averaging (free), multi-frequency dB-domain mean (config field, no code), pink-noise anchor (gated on L-a and M-c). Full proposal in the session changelog. | MED |
| **M-e** | **Measure anchor spread on units A and B** at 250/500/1k/2k/4k/8k. **Do this before investing in M-d** — if the spread is small on the units actually in rotation, M-d is moot for study work. | MED |
| **L-b** | **Unit X right inverse filter defect, 125–500 Hz.** −2.50 dB @ 250 Hz next to **+1.40 dB @ 500 Hz** — non-monotonic, so not a seal leak. Reproducible across 5 reseatings (mean −2.52, spread 0.50). Deferred: X is a toolbox-test unit, not in study rotation. | LOW |
| **L-c** | **`calibration_check.py` section 6 seat-matching.** The tone term pools across seats while noise rows may exist at only one; cost 0.19 dB on 2026-07-23 data (−0.83 same-seat vs −0.64 pooled). | LOW |
| **L-d** | **Seating gate convention.** After every remount, request 60 dB at 1 kHz and expect within ~0.3 dB before starting a block. Would have caught two suspect mounts on 2026-07-23 at measurement zero rather than after five. | LOW |

### Updated existing items

- **C3** (routing re-verification) — **still open for units A, B, K.** The
  2026-07-23 session covered unit X only, which was already done. Not closed.
- **M15** (`spl_to_amplitude()` full-scale guard) — 105 dB requests produced
  104.80 / 105.00 with no distortion on a 105 dB-ceiling profile, so no evidence
  of clipping there. The guard is still absent and still needed for low-ceiling
  profiles (ER-2).
- **M10** (dB HL numeric spot-check) — tooling now exists
  (`calibration_check.py --retspl-config`). Not yet run.
- **L24** (ER-2 linearity re-measure) — deliberately skipped 2026-07-23: the
  splitter migration will invalidate it. Reconfirmed as correct to defer.
- **L22** (4157 mic cal file unverified) — unchanged. Note that the coupler was
  ruled out as a source of the unit X anchor drift, so L22 does not explain it.

### Verified, no action

- **Level linearity of the calibration chain.** Slope 0.999–1.002 at every
  frequency, r² = 1.0000, residual RMS ≤0.03 dB, over 30–105 dB. The `20*log10`
  relationship the whole calibration rests on holds.
- **B&K 1708 bandpass (22.4 Hz – 22.4 kHz)**: in vs out makes no measurable
  difference at 1 kHz. Configurations interchangeable.
- **Session drift**: B&K 4231 read 93.9 against 94.0 nominal after ~2 h.
  Broadband and 1/12-octave band readings agree to 0.03 dB.

### Naming note

The session changelog uses session-local IDs N1–N12. The IDs above (M-a … L-d)
are the intended migration into this document's H/M/L scheme. Renumber to fit
the existing sequence when merging; do not carry the N-prefix forward.
