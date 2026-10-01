# PROLACTIN — Session Changelog 2026-07-23 (session 02)

**Lab session: artificial-ear verification of the FIR + SPL calibration chain, unit X.**

---

## Session start protocol (NEXT session)

1. **Push all local working copies into the project before anything else.** The
   16 files from session 01 (2026-07-23) plus everything below.
2. Verify the Key Signatures section against uploaded project files. Grep a
   *paradigm* signature too, not just `adaptive_paradigm.py`.
3. Review Open Issues below, and `prolactin_open_issues_2026-07-18.md`.

---

## High-level summary

First end-to-end verification of the calibration chain on the B&K artificial
ear. Two new standalone tools built (`calibration_check.py`,
`measure_runner.py`), 131 measurements collected on DT250 unit X, both ears.

Headline: **the method works.** Level linearity is essentially perfect over
75 dB, and the left channel's post-FIR flatness is within ±0.8 dB across
125–8000 Hz. The proposed "spot-check per-frequency correction" feature is
**ruled out** on evidence — corrections would be smaller than seating variance.

Two real defects found: the unit X SPL anchor was stale by ~2 dB (corrected),
and the unit X **right** inverse filter has a genuine low-frequency defect at
125–500 Hz. X is a toolbox-test unit, not a study unit, so the IR is not being
regenerated now.

---

## Work completed

### New: `utils/calibration_check.py`

Standalone analysis tool. No PROLACTIN imports (stdlib csv + numpy +
matplotlib only) so it runs without PsychoPy or the conda env. Reads a flat
measurement CSV, emits an 8-section text report, a 4-panel PNG per unit, and an
optional candidate-correction JSON.

Sections: level linearity; frequency flatness; level-independence of the
residual; within-seat repeatability and between-seat variability; L/R
asymmetry; noise-vs-tone bias; candidate correction table; dB HL spot-check.

`--template` generates a blank pre-populated CSV that doubles as the bench
checklist.

Design decisions worth preserving:
- Section 7 requires **three** gates: model validity (residual must not slope
  with level), a noise gate at 2× the **per-frequency** between-seat SD, and a
  materiality gate at `flat-tol / 2`. An earlier single-scalar floor over-flagged
  badly — 12 cells vs the 3 that survive the current rule.
- Section 4 separates within-seat (instrument) from between-seat (adds the
  seal). Only between-seat feeds the correction floor, because in real use the
  headphone is reseated on every participant.
- Section 6 restricts the tone term to the anchor frequency; pooling all
  frequencies folded the frequency-response spread into the bias estimate.

### New: `utils/measure_runner.py`

Interactive bench driver. Walks pending CSV rows, invokes `level_validator`,
prompts for the RTA reading, writes back after **every** entry via temp file +
atomic replace. Filters: `--ear`, `--only` (notes substring), `--level`,
`--redo`, `--order freq`, `--dry-run`. `--guard` (default 15 dB) requires
retyping any implausible entry — three doubled-keystroke typos occurred before
it existed. Populates a `timestamp` column when present.

### New: `docs/calibration_check_output_guide.md`

Generic reference for the three artifacts, section by section. No
session-specific numbers. Includes a common-pitfalls list.

### Modified: `calibration_data/calibration_config.json`

`beyerdynamic_dt250_x_ucx2` re-anchored against a calibrator-anchored chain:

| field | old | new |
|---|---|---|
| `measured_spl_left` | 99.2 | **101.3** |
| `measured_spl_right` | 99.8 | **100.6** |

Both verify at 94.0 dB when 94 is requested. Note the channels moved by
different amounts (+2.1 / +0.8) — the old L/R *relationship* was also wrong, and
the sign has flipped (right was 0.6 dB louder, left is now 0.7 dB louder).

**`max_spl` NOT yet recomputed** — see Open Issues.
**Profile `_description` NOT yet updated** — see Open Issues.

---

## Findings

| # | Finding |
|---|---|
| F1 | **Level linearity verified.** Slope 0.999–1.002 at every frequency, r² = 1.0000, residual RMS ≤0.03 dB, over 30–105 dB. The `20·log10` assumption the calibration rests on holds. |
| F2 | **Left-channel flatness: −0.40 to +0.80 dB**, 125–8000 Hz. Comfortably inside the ±2 dB criterion. |
| F3 | **Level-independence is near-perfect.** 15 of 22 frequency×ear cells show *exactly zero* residual spread across a 45 dB range. |
| F4 | **Spot-check correction feature ruled out.** Left ear yields no correctable frequencies. Deviations are smaller than or comparable to seating variance. Design question closed on evidence. |
| F5 | **Unit X right IR defect, 125–500 Hz.** −2.50 dB at 250 Hz, **+1.40 dB at 500 Hz**. Non-monotonic, so *not* a seal leak. Reproducible across 5 reseatings (mean −2.52, spread 0.50). Correct fix is IR regeneration, not a correction table. |
| F6 | **M11 quantified and sign-corrected.** Noise reads **quiet** by 0.6–0.8 dB, not loud by 1.3. Consistent across level. Bias differs slightly by ear (−0.92 L vs −0.74 R), which points at the inverse filters rather than the generator. |
| F7 | **Reseat variability**: within-seat 0.05 dB pooled; between-seat 0.19 pooled but strongly frequency-dependent (0.35 at 125 Hz, 0.00–0.10 mid). |
| F8 | **Anchor was stale by ~2 dB** and the two channels had drifted apart by 1.3 dB. Cause not established. |
| F9 | **B&K 1708 bandpass (22.4 Hz – 22.4 kHz) in vs out: no measurable difference** at 1 kHz. Configurations interchangeable. |
| F10 | **End-of-session drift check passed.** B&K 4231 read 93.9 against 94.0 nominal after ~2 h. Broadband (93.93) and 1/12-octave band readings agree to 0.03 dB, validating the RTA band method against the broadband meter. |
| F11 | **Room noise is infrasonic.** Peak at 2–3 Hz; below 20 dB SPL per band above 100 Hz. Z-weighted broadband readings were misleading because Z includes DC. Likely ground-borne (train station 100–200 m; construction). |

---

## Files modified

| File | Change |
|---|---|
| `utils/calibration_check.py` | **NEW** — analysis + plotting tool |
| `utils/measure_runner.py` | **NEW** — interactive bench driver |
| `docs/calibration_check_output_guide.md` | **NEW** — artifact reference |
| `tests/lab_2026-07-23_unit_X.csv` | **NEW** — 131 measurements, unit X, both ears |
| `tests/results/report_X.txt` | **NEW** — generated report |
| `tests/results/calibration_check_unit_X.png` | **NEW** — generated plots |
| `tests/results/corr_X.json` | **NEW** — candidate corrections (advisory only) |
| `calibration_data/calibration_config.json` | Unit X SPL anchor re-measured |

**Files NOT modified:** `adaptive_paradigm.py`, all `paradigm_*.py`, all
`test_*.py`, `level_validator.py`, `operator_gui.py`, `trial_player.py`,
`event_gen.py`, `calibration.py`, `DEFAULTS.py`, `paradigm_setup_dialog.py`,
`varspec.py`, `hl_converter.py`, `resource_logger.py`. No paradigm, GUI, or
audio-path code was touched this session.

---

## Key Signatures

Grep these to confirm project files are the current versions.

| File | Signature |
|---|---|
| `utils/calibration_check.py` | `def _level_dependent(slope, spread, tol):` |
| `utils/calibration_check.py` | `real but immaterial (< flat-tol/2)` |
| `utils/calibration_check.py` | `handlelength=4.0` |
| `utils/calibration_check.py` | `4a. Within-seat repeatability` |
| `utils/measure_runner.py` | `def parse_value(text, requested, guard):` |
| `utils/measure_runner.py` | `def sort_key(row):` |
| `utils/measure_runner.py` | `dB SPL from RTA cursor` |
| `calibration_config.json` | `"measured_spl_left": 101.3` |
| `calibration_config.json` | `"measured_spl_right": 100.6` |
| `docs/calibration_check_output_guide.md` | `Common pitfalls` |
| `tests/lab_2026-07-23_unit_X.csv` | `1.99 spot checks` |

---

## Anchor frequency proposal (background for N11/N12)

**Problem.** `measured_spl_left/right` is established from a single 1 kHz tone
at a single seating. Two things make that fragile, and together they explain the
shape of F8 -- an anchor error that differs between channels.

1. **The FIR residual has structure near 1 kHz.** Swept-sine analysis of the
   study units (2026-05-19, offline DAW measurement) puts unit A left's worst
   residual at **+2.38 dB @ 936 Hz** and unit B right's at **-1.26 dB @ 1057 Hz**
   -- both within ~60 Hz of the anchor frequency. A steep residual slope at the
   anchor means small measurement or seating changes translate directly into
   anchor error, and because the residual shape differs per channel, the
   resulting error is channel-asymmetric.
2. **1 kHz was the most seat-sensitive frequency measured today** (N9): 0.70 dB
   between seats, against 0.00-0.10 dB everywhere else.

Note the swept-sine data also independently corroborates the calibration: unit A
left goes 14.70 -> 3.52 dB flatness (mean |dev| 0.42 dB, 99.1% within +/-2 dB),
unit B right 15.79 -> 3.02 dB (mean |dev| 0.53 dB, 100% within +/-2 dB). Two
methods, same verdict as today's tone-by-tone result.

### Option 1 -- multi-seat averaging  (recommended first; free)

Average the anchor reading over 3 seatings. Attacks the *variance* term.
No schema change, no code change, no semantic change. Cuts seating noise by
~sqrt(3). Do this on the A/B spot check regardless of anything else.

### Option 2 -- multi-frequency mean anchor

Attacks the *FIR-residual* term. **No code change**: `spl_to_amplitude()` still
consumes one scalar per ear; only the procedure producing that scalar changes.

- Method: Step 7 placeholder trick, but repeated at 250 / 500 / 1000 / 2000 /
  4000 / 8000 Hz (the audiometric set already in `standard_frequencies.py` and
  the RETSPL table). Set `measured_spl_*` to the mean.
- **Average in the dB domain, not energy.** For a symmetric +/-2 dB ripple,
  energy averaging returns +0.45 dB instead of 0, because peaks dominate the
  power sum. dB-domain averaging lets peaks and dips cancel, which is the point.
- Schema: add `anchor_method` and `anchor_frequencies_hz` to `spl_calibration`,
  defaulting to `"single_1k"` so existing profiles are untouched. Without this,
  a profile's anchor convention becomes ambiguous once two schemes coexist.
- **Tradeoff:** no individual frequency gets more accurate. 1 kHz might read
  +0.4 dB off instead of 0.0. What improves is worst-case error across the
  range. That is the right trade because no paradigm privileges 1 kHz -- PTA
  spans 250-8000 Hz and IFMC/TMC use arbitrary probe frequencies. The current
  scheme makes 1 kHz exact for no reason anyone chose. It also improves dB HL
  across the board, since anchor error is common-mode across frequencies.
- Cost: 12 readings per profile, ~6 min.

### Option 3 -- band-limited noise anchor  (contingent on N3)

Elegant -- one measurement, inherently frequency-averaged -- but **only safe if
N3 resolves as acoustic.**

- If M11's bias is the FIR's average power gain differing from its 1 kHz gain,
  a noise anchor is simply a frequency-averaged tone measurement in one shot,
  and anchoring on it is legitimate.
- If M11's bias is a generator convention or crest-factor bug, a noise anchor
  imports that bug into every tone presented. **Do not do this before N3.**
- **Use pink, not white.** White noise has equal energy per Hz, so in log-
  frequency terms most of its energy sits in the top octave -- a white anchor
  would be dominated by 4-16 kHz and would give a fundamentally different number
  from Option 2. Pink noise has equal energy per octave, making it the true
  single-measurement equivalent of a log-spaced tone average.
- Requires N4 settled first: `reference_amplitude` is documented as *peak*. A
  sine at peak 0.0716 has RMS 3 dB down; noise at the same peak has RMS ~12 dB
  down, landing ~9 dB quieter. Either noise needs its own reference amplitude or
  the convention moves to RMS -- and that touches `event_gen`, not just config.
  Post-FIR peak headroom also needs checking, since noise at equal RMS peaks far
  higher than a sine.

### Sequencing

Options 1 and 2 are independent and multiply: Option 1 attacks seating variance,
Option 2 attacks FIR residual. Both together is ~18 readings and addresses both
candidate contributors to F8. **But run N12 first** -- if the anchor spread
across frequencies is small on A and B, none of this is worth doing for study
work.

---

## Open Issues / Next Steps

### New this session

| ID | Item | Priority |
|---|---|---|
| N1 | **`max_spl` for unit X not recomputed** after re-anchoring. Formula: `measured_spl + 20*log10(1/peak_after_FIR) - 3`, using the **quieter** ear — which has switched from left to right. Current 105 is conservative (corrected anchor needs *less* amplitude), so not urgent. | MED |
| N2 | **Profile `_description` not updated** for the re-anchor. Violates the doc-hygiene rule. Draft text was prepared in chat. | MED |
| N3 | **M11 root-cause diagnostic** — desk task, no hardware: load the unit X inverse-filter WAVs, compare the RMS-average of \|G(f)\| over the noise band against \|G(1 kHz)\|, per ear. If it matches −0.92 / −0.74, M11 is explained. Next suspect is the RMS normalisation in the noise generator. | MED |
| N4 | **Noise level convention undocumented** — whether `--type noise` targets broadband SPL or spectrum level (dB SPL/Hz) is not stated anywhere. Matters for maskers. | MED |
| N5 | **`calibration_check.py` section 6 seat-matching.** Tone term pools across seats while noise rows may exist at only one; cost 0.19 dB today (−0.83 same-seat vs −0.64 pooled). | LOW |
| N6 | **Unit X right IR defect (F5).** Regenerate the right inverse filter for unit X. Deferred: X is a toolbox-test unit only. | LOW |
| N7 | ~~Coupler identity unresolved.~~ **CLOSED.** All over-ear work uses the same mic, preamp and coupler, so today matches the 2026-06-23 IR session. Also ruled out on logic: a coupler difference acts on both channels, but F8 is channel-asymmetric (+2.1 L / +0.8 R). **Consequence: F8's cause is now genuinely open** -- see N11. | CLOSED |
| N8 | **A/B spot checks** in the audiology booth (floating floor — right answer for ground-borne train/construction noise). Shorter protocol: level-independence is established, so one level and more seatings. | MED |
| N9 | **1 kHz seating sensitivity.** Left ear showed 0.70 dB between-seat at 1 kHz vs 0.00–0.10 elsewhere. 1 kHz is the anchor frequency, so this matters. Only 3 seats — take more on A/B. | MED |
| N11 | **Anchor robustness -- see "Anchor frequency proposal" below.** Leading explanation for F8. Three independent measures, cheapest first: multi-seat averaging (free), multi-frequency mean anchor (config field + procedure), pink-noise anchor (contingent on N3). | MED |
| N12 | **Measure the anchor spread on A/B.** Play `reference_amplitude` at 250/500/1k/2k/4k/8k and record the spread of the resulting SPL readings. If it is under a few tenths on the units actually in rotation, N11 is moot for study work. Do this before investing in N11. | MED |
| N10 | **Adopt a 1 kHz seating gate**: after every remount, request 60 dB and expect within ~0.3 dB before starting a block. Would have caught two suspect mounts today at measurement zero. | LOW |

### Carried forward (see `prolactin_open_issues_2026-07-18.md` for full list)

- **M10** — dB HL numeric spot-check. Tooling now exists (`--retspl-config`).
- **M11** — noise-vs-tone bias. **Now quantified**; see N3 for root cause.
- **M15** — `spl_to_amplitude()` full-scale guard. 105 dB requests produced
  104.80 / 105.00 clean, no clipping, but the guard is still absent.
- **C3** — routing re-verification for remaining profiles. **Still open for A, B, K.**
  Today did not close it; X was already done.
- **L22** — 4157 mic cal file unverified (reused from the 4153 round). Interacts
  with N7.
- **L24** — ER-2 linearity re-measure. Deliberately skipped: the splitter
  migration will invalidate it.
- **L27** — ER-2 recalibration pending splitter.
- **L19**, **H4/T5**, **H5**, **H9**, **L2 (SL paradigm)** — unchanged.
- **RETSPL** still the ISO 389-8 HDA200 placeholder on circumaural DT250.
  Required before clinical use.

### Deliberately deferred today (not forgotten)

Blocks 2 (units A/B), 3 (ER-2), and 4 (M5 residual testing, H5 loopback,
H9 long run) were dropped for time. Block 1 on unit X was completed in full.
