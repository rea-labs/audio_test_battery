# PTA dB SPL Migration Plan

*Phase B Wave-2, paradigm 1 of 8. First migration; pattern will be reused.*

---

## Scope

Migrate PTA's adaptive parameter from **linear amplitude (effective dB FS)** to
**true dB SPL** via CalibrationManager. Reference for the pattern: IFMC/TMC
post-Phase-B-Step-6b. PTA-specific complications: **pan** (monoaural outer
var), **catch trials** (silence), and **downstream consumption**
(ResultLoader → IFMC/TMC probe levels).

---

## Current PTA state (inventory)

| Aspect | Value | Unit |
|---|---|---|
| Inner var name | `trial_amp` | linear amp internally |
| Adaptive logic operations | dB-space arithmetic, amp ↔ dB conversions | dB FS effectively |
| `start` default | 0.5 | linear amp = -6 dB FS |
| `min` default | 0.0001 | linear amp = -80 dB FS |
| `max` default | 1.0 | linear amp = 0 dB FS |
| Step sizes | -10/+10 (initial), -2/+2 (final) | dB |
| Catch trial | `amp = 0.0` | silence |
| TrialPlayer call | `tp.new_trial(... amp=amp ...)` | direct linear amp |
| `pan` outer var | -1, 0, +1 | passed through `tp.new_trial` |
| Logging | `trial_amp` column via `amp2db()` | dB FS |
| Fitted threshold | `threshold_dB` column (base class fit) | dB FS |
| Calibration | not wired | -- |

Test default freq set: `ULTRA_PTA_FREQS = [500]` (dev/debug).
Real audiometric set: `AUDIOMETRIC_FREQS = [250, 500, 1000, 2000, 4000, 8000]`.

---

## Migration approach

1. PTA operates in dB SPL throughout. Internal var `self.trial_amp` is
   reinterpreted as dB SPL (no rename, to minimize churn). Adaptive logic
   simplifies — no more amp ↔ dB conversions.
2. CalibrationManager required; raise RuntimeError if not attached
   (matches IFMC/TMC pattern).
3. TrialPlayer call uses `amp=1.0, per_channel_gain=(amp_L, amp_R)` from
   `cm.spl_to_amplitude(self.trial_amp)`. Pan still passed through; pan
   zeros the unused channel before per-channel gain is applied
   (verified in `prepare_sound`).
4. Catch trials: pass `amp=0.0, per_channel_gain=None`. Silence is silence
   regardless of calibration; gateway handles 0 amplitude cleanly.
5. CSV columns: `trial_amp` and `threshold_dB` keep names, but values are
   now dB SPL. Add two new columns: `level_units` (constant `"dB SPL"`) and
   `calibration_profile` (active profile name from CalibrationManager).
6. Downstream (`ResultLoader.get_*_probe_level`): switch from
   `db2amp(probe_db)` to `cm.spl_to_amplitude(probe_db_spl)` (averaged or
   left-only — see open Q below). ResultLoader gains an optional
   CalibrationManager kwarg.

---

## File-by-file changes

### `paradigm_pta.py`

**`initialize_adaptive_param`:** simplify. base_start, randomize, min, max
all in dB SPL directly. Remove all `amp2db`/`db2amp`. Pseudocode:

```python
base_start = self.inner_var.data.get('start', 60.0)  # dB SPL
step_down_initial = abs(self.inner_var.data.get('step_down_initial', -10))
randomize_dB = step_down_initial / 2.0
offset_dB = random.uniform(-randomize_dB, randomize_dB)
self.trial_amp = base_start + offset_dB  # dB SPL
min_level = self.inner_var.data.get('min', 0.0)
max_level = self.inner_var.data.get('max', 90.0)
self.trial_amp = max(min_level, min(max_level, self.trial_amp))
```

**`prepare_trial`:** add CalibrationManager guard (RuntimeError if missing
or `not spl_calibrated`). For catch trial, keep `amp=0.0`,
`per_channel_gain=None`. For normal trial:

```python
amp_L, amp_R = self.calibration.spl_to_amplitude(self.trial_amp)
self._last_amp_L = amp_L
self._last_amp_R = amp_R
self.tp.new_trial(
    wave_type="sin",
    durations=self.trial_dur,
    fc=self.fc,
    amp=1.0,
    per_channel_gain=(amp_L, amp_R),
    fade_time=self.fade_time,
    sample_accurate=self.sample_accurate,
    pan=self.pan,
    verbose=False
)
```

Track `last_two_levels` directly in dB SPL (no conversion).

**`adapt_difficulty`:** simplify to dB-space addition. No `db2amp`:

```python
if direction == "harder":
    self.trial_amp += step_down  # step_down is negative, e.g. -10
    self.trial_amp = max(self.trial_amp, min_level)
elif direction == "easier":
    self.trial_amp += step_up
    self.trial_amp = min(self.trial_amp, max_level)
```

**`reset_to_midpoint_amplitude`:** trivial in dB SPL space:

```python
midpoint = (self.last_two_levels[0] + self.last_two_levels[1]) / 2.0
self.trial_amp = midpoint
```

**`get_log_data`:** remove `amp2db()` call. `trial_amp` is already dB SPL.
Add `level_units` and `calibration_profile`:

```python
return {
    "trial_amp": self.trial_amp,
    "fc": self.fc,
    "trial_dur": self.trial_dur,
    "level_units": "dB SPL",
    "calibration_profile": self.calibration.active_profile,
    "amp_L": getattr(self, "_last_amp_L", None),
    "amp_R": getattr(self, "_last_amp_R", None),
}
```

**Module docstring + class docstring:** update to reflect dB SPL semantics
(line 7 already aspirational; will become accurate).

**`__main__` block:** update example params to dB SPL defaults.

### `test_pta.py`

Same shape as `test_ifmc.py` / `test_tmc.py`:

- Add `from utils.calibration import CalibrationManager`
- Add module-level `CALIBRATION_CONFIG_PATH = "../../calibration_data/calibration_config.json"`
- In `main()`, load CalibrationManager up top with three pre-flight
  checks (config exists, SPL data populated, FIR loaded). Abort gracefully
  on first two; warn and continue on third.
- Update default `params`:
  - `start: 60.0` (dB SPL)
  - `min: 0.0` (dB SPL)
  - `max: 90.0` (dB SPL — paradigm operator soft cap; `max_spl=105`
    in calibration is the hard ceiling)
- Both `ParadigmPTA(...)` constructions (pre-dialog and post-dialog)
  followed by `paradigm.set_calibration(calibration)`
- Optional: revert `ULTRA_PTA_FREQS` → `AUDIOMETRIC_FREQS` import
  (the current `ULTRA` is dev/debug; first real PTA run wants the full
  set). Flagged as small change — can stay as is if Eric wants.

### `result_loader.py`

`get_pta_thresholds()` keeps reading `threshold_dB`. Values are now dB
SPL; semantic change documented but no code change in this method.

`get_ifmc_probe_level()` and `get_tmc_probe_level()` need calibration
to convert dB SPL → linear amp. Smallest change:

```python
def get_ifmc_probe_level(self, participant_id, probe_freq,
                         db_above_threshold=10.0,
                         calibration=None,  # NEW kwarg
                         show_gui=True,
                         max_amplitude=0.7):
    ...
    threshold_db = thresholds[probe_freq]      # now dB SPL
    probe_db = threshold_db + db_above_threshold
    if calibration is not None:
        amp_L, amp_R = calibration.spl_to_amplitude(probe_db)
        probe_amp = (amp_L + amp_R) / 2.0      # diotic average
                                                # (see open Q below)
    else:
        # legacy/uncalibrated path: kept for old test scripts that
        # don't pass a CalibrationManager. Emits warning.
        warnings.warn(
            "ResultLoader: probe_db treated as dB FS (legacy). Pass a "
            "CalibrationManager to get true dB SPL conversion."
        )
        probe_amp = TrialPlayer.db2amp(probe_db)
    ...
```

Symmetric change to `get_tmc_probe_level`. Module-level convenience
wrappers `get_pta_threshold()` / `get_tmc_probe_level()` get the same
new optional kwarg.

`max_amplitude=0.7` clamp stays for now (transitional safety; redundant
with `cm.max_spl` once we trust calibration).

### `test_ifmc.py` / `test_tmc.py`

Where ResultLoader's probe-level helpers are called, pass the existing
CalibrationManager. Two-line change. Strictly speaking required for
correctness post-PTA-migration since stored thresholds are no longer
dB FS.

### Files NOT touched in this migration

`adaptive_paradigm.py` (psychometric fit operates on dB-anything;
unit-agnostic), `trial_player.py`, `calibration.py`, `event_gen.py`,
`paradigm_setup_dialog.py`, all other paradigms, `operator_gui.py`.

`paradigm_setup_dialog.py` may need a small label tweak ("amplitude" →
"level (dB SPL)") in the parameter summary panel — TBD, depends on
what's currently displayed. Flagged for inventory during implementation.

---

## CSV format change (annotated)

Old PTA CSV columns (per-trial rows): `trial_amp` (dB FS), `fc`, `trial_dur`,
`threshold_dB` (dB FS, last row of each config), `slope_k`, etc.

New PTA CSV columns: `trial_amp` (dB SPL), `fc`, `trial_dur`, `level_units`
(constant `"dB SPL"`), `calibration_profile` (e.g. `"akg_k271_mkii_ufx2"`),
`amp_L`, `amp_R`, `threshold_dB` (dB SPL), `slope_k`, etc.

`level_units` and `calibration_profile` are added by PTA's `get_log_data`
on every row. The base class threshold-fit row inherits them (the fit's
`threshold_dB` is in the same units as the per-trial levels it was
derived from).

**Old CSVs become non-comparable to new ones.** ResultLoader currently
has no version detection. Two options:
- (a) Trust user to not mix datasets across the migration boundary;
  document in changelog.
- (b) Add a version-detection check in ResultLoader: if `level_units`
  column missing, treat as legacy dB FS and emit warning.

Recommend (b) for safety. Small addition.

---

## Catch-trial handling

Catch trial passes `amp=0.0, per_channel_gain=None`. Verify silence
behavior with calibration:

- `amp=0.0` → `eg.sin()` produces all-zero waveform.
- `per_channel_gain=None` → no per-channel scaling.
- `prepare_sound` runs FIR convolution on zeros → zeros (math).
- Peak safety check passes (0 < 1.0).
- Result: silent stereo Sound object of correct duration.

No special-casing needed. Worth confirming with a quick smoke test.

---

## Pan + per_channel_gain (verified)

`prepare_sound` handles both: pan zeros the unused channel during
mono → stereo conversion, then per_channel_gain multiplies. For
`pan=-1` (left only): right channel is zeros, `gain_R * 0 = 0`. Left
channel gets `gain_L`. Result: target dB SPL on left ear, silence
on right. Correct.

---

## Implementation order

1. Update `paradigm_pta.py` (all changes above).
2. Update `test_pta.py` (CalibrationManager wiring + new defaults).
3. Update `result_loader.py` (calibration-aware probe-level helpers
   + legacy version detection).
4. Update `test_ifmc.py` + `test_tmc.py` to pass calibration to
   ResultLoader probe-level helpers.
5. Smoke test: run `test_pta.py` headless or with verbose, verify
   no exceptions and CSV format.
6. Manual hardware test (Eric): run PTA at 60 dB SPL, 1 kHz, verify
   on coupler that produced SPL is 60 ± 1 dB.

---

## Test checklist

- [ ] PTA runs to completion without calibration → RuntimeError (correct)
- [ ] PTA runs to completion with calibration → CSV contains
      `level_units`, `calibration_profile`, `amp_L`, `amp_R` columns
- [ ] Threshold values look plausible (e.g. for self-test, normal hearing
      should yield ~0–20 dB SPL across 500–4k Hz)
- [ ] Catch trials are silent (no audible signal)
- [ ] Pan = -1 → audible left only; pan = +1 → audible right only
- [ ] Pan = 0 → diotic; SPL at each ear matches request to ~0.1 dB
- [ ] Adaptive steps work in dB SPL (e.g. -10 dB drop produces ~half
      perceived loudness)
- [ ] Midpoint reset between two consecutive levels gives the expected
      midpoint in dB
- [ ] Old PTA CSVs still loadable by ResultLoader, with warning about
      legacy units (if option (b) implemented)
- [ ] IFMC/TMC consume new PTA threshold correctly (probe SPL on
      coupler matches `threshold + db_above_threshold`)

---

## Open questions

1. **Probe diotic-amp policy.** `cm.spl_to_amplitude()` returns
   `(amp_L, amp_R)`. ResultLoader's `get_*_probe_level()` historically
   returns a single scalar. Three options:
   - (a) Return mean of L/R (proposed default; ~0.05 dB error per ear).
   - (b) Return only `amp_L` (matches IFMC/TMC's first-pass shortcut
     before Step 6b; ~0.1 dB R-ear bias).
   - (c) Return tuple, change IFMC/TMC probe handling to accept and
     plumb `per_channel_gain` for the probe too. Cleanest, but expands
     scope significantly.
   - I lean toward (a) for this migration; (c) is a separate future task.
2. **`ULTRA_PTA_FREQS` revert.** Currently `test_pta.py` uses the
   single-frequency dev set. Revert to `AUDIOMETRIC_FREQS` for the first
   real PTA run? Or leave as-is and revert manually when ready?
3. **`max` paradigm soft-cap.** Proposed `max=90` dB SPL in PTA params.
   Calibration's `max_spl=105` is the hard ceiling. Are 90 dB and 105 dB
   the right values, or should PTA's per-paradigm soft-cap be lower?
   (Convention varies; clinical PTA usually maxes at 110 dB HL ≈ 117 dB
   SPL at 1 kHz, but PROLACTIN's own ceiling can be conservative.)
4. **Legacy CSV detection.** Implement option (b) version detection in
   ResultLoader — yes/no?
5. **Setup-dialog label updates.** `ParadigmSetupDialog` likely shows a
   parameter summary that includes inner-variable name and start value.
   Worth a quick check during implementation; if it shows "0.5" with no
   unit, change to "60.0 dB SPL". Flagged for inventory.
6. **PTA min level.** `min=0.0` dB SPL means 0 dB SPL floor — for many
   normal-hearing listeners this is below threshold and the test will
   bottom out. Is this OK (tracker will clip), or should `min=-10` to
   allow exploration below 0 dB SPL? `cm.spl_to_amplitude` doesn't
   prevent negative dB SPL — it just produces small linear amps.

---

## Deferred (post-PTA-migration, before batching the rest)

- **B6 verification suite** — multi-frequency level check on coupler
  to confirm the FIR + SPL pipeline produces flat dB SPL across the
  audiometric range. Should happen *before* trusting PTA output
  clinically. The PTA migration itself can land first; the
  verification gates clinical use, not feature merge.
- **Per-frequency L/R asymmetry characterization** — currently 1 kHz
  only. PTA exercises the full audiometric range, so this becomes
  more relevant.
- **dB HL conversion** — methodology decision deferred (see main
  Phase B plan, Open Q #2).
