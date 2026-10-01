# `calibration_check.py` — Guide to the Output Artifacts

*What each artifact contains, what each section answers, and how to read it.
Generic reference — no session-specific numbers.*

---

## Overview

`calibration_check.py` analyses coupler measurements collected in a flat CSV
(typically by `measure_runner.py`) and produces up to three artifacts:

| Artifact | Flag | Purpose |
|---|---|---|
| Text report | `--report PATH` (also always printed to stdout) | Full numeric analysis, 8 sections |
| PNG, one per unit | `--outdir DIR` | Four-panel visual summary |
| Candidate correction JSON | `--correction PATH` | Machine-readable verdict on per-frequency corrections |

The tool is read-only with respect to the CSV and tolerates blank
`measured_spl` rows, so it can be run repeatedly mid-session to watch the
picture fill in.

**Suggested reading order: section 4, then 3, then 7.** Section 4 tells you how
much measurement noise you are working against; section 3 tells you whether a
fixed per-frequency offset is even a valid model of the error; section 7 applies
both to reach a verdict. The other sections are supporting detail.

---

## 1. The text report

### Section 1 — Level linearity

**Question:** when you request 10 dB more, do you get 10 dB more?

Fits measured against requested SPL per `(unit, ear, frequency, stimulus)`,
reporting slope, intercept, r-squared and residual RMS. Requires at least three
distinct requested levels.

- **Slope** should be 1.000. Below 1 means compression (the chain gains less
  than asked as level rises); above 1 means expansion, and at the top of the
  range usually means clipping.
- **Intercept** is the frequency's offset in dB. A large uniform intercept
  across all frequencies points at a stale `measured_spl_*` anchor rather than
  anything wrong with the transducer.
- **Residual RMS** is scatter about the fit. Large values with a good slope
  mean noisy readings, not a nonlinear chain.

This section validates the `20*log10` relationship that the entire calibration
rests on. If it fails, nothing downstream is trustworthy.

### Section 2 — Frequency flatness

**Question:** at a fixed level, how far off is each frequency?

Reports `residual = measured - requested` per frequency, plus the same value
expressed relative to the 1 kHz anchor. Repeated readings at one frequency are
averaged and the count shown as `n`.

The **re-1 kHz** column is immune to anchor error, so if the absolute residuals
are all shifted by a constant, that column still shows the true response shape.

Default pass criterion is +/- `--flat-tol` (2.0 dB).

### Section 3 — Level-independence of the residual

**Question:** does each frequency's error stay put when the level changes?

This is the validity test for the whole idea of a per-frequency correction
table. A single dB offset per frequency can only represent an error that does
not move with level.

- With **3+ distinct levels**, reports the regression slope in dB of residual
  per 10 dB of level. Should be near zero.
- With **only 2 levels**, falls back to spread (max minus min), which is just
  the difference of two noisy readings and should not be over-read. Measure a
  third level to make this section meaningful.

A frequency whose residual slopes with level is flagged and excluded from
section 7 — no fixed offset can fix it.

### Section 4 — Repeatability and reseat variability

Split deliberately into two, because they answer different questions.

**4a, within-seat:** duplicate readings at the same mount. Measures the meter
and the toolbox only. This is your instrumentation noise floor.

**4b, between-seat:** collapses each seat to its mean first, then takes the SD
across seat means, so duplicate readings at one mount cannot masquerade as
seating spread. Adds the seal to the instrumentation noise.

**Only 4b feeds the correction floor**, because in real use the headphone is
reseated on every participant — seat-inclusive variance is the relevant one.
The number is computed **per frequency**, since seating sensitivity typically
varies several-fold across the range (low frequencies are far more sensitive to
seal quality), with the pooled value used only where a frequency has no repeated
seats.

**Comparing 4a and 4b is the diagnostic.** If 4b greatly exceeds 4a, the limit
is the seal and nothing in section 7 should be trusted until reseating improves.
If they are close, the measurement is as good as the method allows.

Requires the `seat` column to be incremented after every remount. Without that,
this section is silent and section 7 falls back to a conservative default.

### Section 5 — L/R asymmetry

Left minus right per frequency and level. Isolates channel differences from the
response shape both channels share.

**Caveat:** if both ears were anchored at the same frequency, the asymmetry
there is ~0 by construction and means nothing. The asymmetry at *other*
frequencies is the informative part — that is genuine transducer and inverse
filter difference.

A **monotonic** low-frequency deficit on one channel suggests a seal problem. A
**non-monotonic** pattern — a deficit at one frequency next to an excess at the
neighbouring one — cannot be a leak and indicates an inverse filter that failed
to invert a feature in the response.

### Section 6 — Noise vs tone bias

Compares broadband noise against a tone at the anchor frequency, at matched
requested levels. The tone term is restricted to the anchor frequency; pooling
all frequencies would fold the frequency-response spread into the bias estimate.

- **Constant bias across level** indicates a convention or crest-factor offset
  in the stimulus generator, or the inverse filter's average power gain across
  the noise band differing from its gain at the anchor frequency.
- **Bias that grows as level falls** usually means the low-level points are
  floor-limited: a broadband meter cannot reject room noise the way a
  narrow analysis band can, so low-level noise readings sit on top of the
  ambient floor and read high.
- **Bias differing between ears** points at the inverse filters (which differ
  per channel) rather than at the generator (which does not).

This matters for any paradigm using noise stimuli.

### Section 7 — Candidate correction table

**Question:** should per-frequency corrections be applied at all?

Three gates, in order. A frequency must clear all of them.

1. **Model validity** — rejected if section 3 shows the residual moves with
   level.
2. **Noise gate** — rejected if the deviation is within twice the between-seat
   SD *at that frequency*. Correcting below your own seating variance is
   fitting noise.
3. **Materiality gate** — rejected if the deviation is at or below
   `--materiality` (default `flat-tol / 2`). A deviation can be perfectly real
   and still not worth correcting if it sits well inside the tolerance you
   actually care about.

Verdicts: `LEVEL-DEPENDENT`, `within seating noise`, `real but immaterial`, or
`CORRECTABLE`.

**A sparse or empty result is the good outcome.** It means the inverse filter is
doing its job and no correction layer is warranted.

**A large correction that clears all three gates is usually not an argument for
a correction table — it is an argument for regenerating the inverse filter.** A
lookup table stacked on top of an FIR is two competing models of the same error.
A correction layer only earns its place when the residual is something the FIR
structurally cannot capture.

### Section 8 — dB HL spot-check

Only runs with `--retspl-config` and `--retspl-profile`.

Subtracts the profile's RETSPL table from the measured SPL and reports the
implied dB HL against what was requested. Frequencies absent from the table are
listed separately — worth knowing, since the converter must either interpolate
or refuse.

**This checks that the code applies the table correctly. It does not check that
the table is the right one for the transducer.** That is a separate question,
answered by standards work or behavioural calibration, not by this tool.

---

## 2. The PNG (one per unit)

### Top-left — Level linearity at the anchor frequency

Measured against requested, with a unity reference line.

- Points on the line: correct.
- Parallel offset: anchor error, correctable by editing `measured_spl_*`.
- Slope change or flattening at the top: compression or clipping.

### Top-right — Residual against frequency

**The most informative panel.** One trace per ear per level, with a shaded
+/- 2 dB band.

Encoding: **colour = level**, so a left/right pair at the same level shares a
colour. **Left is solid with circles, right is dashed with triangles.** Markers
are hollow so overlapping traces remain visible.

Two things to read:

1. **Vertical position** — how far from flat each frequency is.
2. **Whether traces of the same colour overlap** — overlap means the error is
   level-independent, which is section 3 rendered visually.

### Bottom-left — Channel asymmetry

Left minus right against frequency, one trace per level. Separates channel
mismatch from the shared response shape.

### Bottom-right — Residual by stimulus type

Boxplot per stimulus type. Catches a whole class of stimulus being
systematically off — where a noise-versus-tone bias shows up at a glance.

---

## 3. The correction JSON

```json
{
  "_note": "CANDIDATE ONLY -- not wired into CalibrationManager. ...",
  "corrections": {
    "<unit>/<ear>": { "<freq_hz>": <dB to ADD to the requested level> }
  }
}
```

Contains **only** frequencies that cleared all three gates in section 7. Values
are the negated mean residual — the offset you would add to the requested level
to land on target. Keys are per unit and ear, since channels diverge enough to
warrant separate tables.

**Nothing consumes this file.** It is evidence for or against building a
correction feature, not an input to `CalibrationManager`. If the numbers ever do
justify a correction layer, that is a PRD and a schema decision — where it lives
in `calibration_config.json`, the interpolation policy for arbitrary
frequencies, and whether broadband stimuli are excluded — not something to wire
up from a JSON dump.

---

## Common pitfalls

- **Forgetting to increment `seat` after a remount.** Readings from different
  mounts get pooled as duplicates, corrupting both 4a and the flatness means,
  and the correction floor falls back to a conservative default.
- **Doubled keystrokes** when typing readings (`5555.40` for `55.40`). Use
  `measure_runner.py`'s `--guard`.
- **Low-level broadband noise readings.** These sit on the ambient floor and
  read high. Use a narrow analysis band, or exclude them.
- **Reading section 5 at the anchor frequency.** Asymmetry there is ~0 by
  construction.
- **Treating section 8 as validation of the RETSPL table.** It validates the
  arithmetic, not the choice of standard.
