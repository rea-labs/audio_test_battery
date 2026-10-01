# PROLACTIN Session Changelog — 2026-04-30 (Phase B Calibration)

## How to verify at session start

For each entry, check that the listed **key signature** is present in the project file.
If it's missing, the project file is out of date and needs to be replaced before starting work.

---

## Session scope

This session implemented Phase B Steps 1-7 of `phase_b_calibration_plan.md`:
headphone calibration via FIR inverse filter convolution + per-ear dB SPL
mapping. B3 (the actual measurements) was completed by Eric outside this
session using REW + Reaper + Adobe Audition + B&K 4153 coupler. Step 8
(end-to-end regression pass on real hardware) is deferred to Eric's manual
testing after this session.

See "Session Addenda (2026-04-30)" at the end of `phase_b_calibration_plan.md`
for design decisions that diverged from the original plan.

---

## Files created

### `utils/calibration.py` — CalibrationManager class
- New class encapsulating FIR inverse filter convolution + dB SPL mapping
- **Key signature:** `class CalibrationManager:`
- **Key signature:** `def prepare_sound(self,`  (the gateway method; routes mono/stereo audio through stereo conversion -> per-channel gain -> FIR convolution -> safety clip -> PsychoPy Sound wrap)
- **Key signature:** `def spl_to_amplitude(self, db_spl: float) -> Tuple[float, float]:`
- **Key signature:** `def amplitude_to_spl(self, amplitude: float, channel: str) -> float:`
- Two independent flags: `fir_calibrated` and `spl_calibrated` (props), plus convenience `is_calibrated`
- **Key signature:** `def fir_calibrated(self) -> bool:`
- **Key signature:** `def spl_calibrated(self) -> bool:`
- **Key signature:** `def ringout_seconds(self) -> float:`  (added in Step 5 for ILD/ITD wait-time bumps)
- Lazy `psychopy.sound.Sound` import so the class is usable offline (unit tests, IR generation utilities)
- FIR convolution uses **`mode='full'` with full-length output (N + M - 1 samples)**, NOT `mode='same'`. See addendum for rationale.
- **Key signature:** `mode="full"`  (in prepare_sound)

### `calibration_data/calibration_config.json` — multi-profile calibration config
- Active profile: `akg_k271_mkii_ufx2` (DT250 deferred pending hardware return)
- Self-documenting via `_description` fields per profile (REW export settings, SPL measurement procedure, HP gain lock method)
- Reference: 1 kHz sine at peak amp 0.0272 -> 94.0 dB SPL (L) / 94.1 dB SPL (R)
- IR WAVs: `AKG_K271_MkII_IR_LEFT_2026-04-16-48k.wav` / `AKG_K271_MkII_IR_RIGHT_2026-04-16-48k.wav`
- Schema versioning: `_schema_version: 1`
- **Lives outside the toolbox folder** at `../../calibration_data/` (will be moved into `audiology_toolbox/calibration_data/` later)

### `tests/audible_smoke_test.py` — manual sanity-check script
- CLI script: builds a tone, runs through `prepare_sound()`, verifies 10 numerical sanity checks (no NaN/Inf, no clicks, no clipping, correct stereo shape, ear-zero check, envelope/amp ratio sanity), writes WAV for offline inspection, optionally plays via PsychoPy/PTB
- Used for end-to-end "Test B" verification (the no-hardware path was used in this session; `--play` mode requires hardware setup)
- **Key signature:** `def build_tone(fs: int, freq: float, duration: float,`
- Args: `--config`, `--profile`, `--freq`, `--duration`, `--level`, `--ear {left,right,both}`, `--play/--no-play`, `--out`

---

## Files edited

### `trial_player.py`
- Added `calibration` and `per_channel_gain` kwargs to `__init__` and `new_trial`
- **Key signature:** `def __init__(self, wave_type=None, del_times=None, durations=None, fc=None, fm=None, mod_ind=None, amp=None, bg=None, fs=None, fade_time=None, sample_accurate=None, pan=None, play_now=False, verbose=None, calibration=None, per_channel_gain=None):`
- **Key signature:** `def new_trial(self, wave_type=None, del_times=None, durations=None, fc=None, fm=None, mod_ind=None, amp=None, bg=None, fs=None, fade_time=None, sample_accurate=None, pan=None, play_now=False, verbose=None, per_channel_gain=None):`
- Added `wave_list` parallel to `sound_list` to capture raw mono samples per event (needed for both calibration and sample_accurate concat)
- **Key signature:** `wave_list = [None] * self.num_events`
- Per-event branch routes through `prepare_sound()` when calibration is set; preserves original pan rebuild as `elif`
- **Key signature:** `pcg_list = self._normalize_per_channel_gain(self.per_channel_gain)`
- `sample_accurate` path: concats raw mono `wave_list[i]` (not `sound_list[i].sound`) so timing is preserved when calibration is applied to the full concat
- bg_sound path: switched to `return_dict=True`, routed through calibration if set
- New helper: `_normalize_per_channel_gain()` — validates and per-event-expands the kwarg
- **Key signature:** `def _normalize_per_channel_gain(self, pcg):`
- `per_channel_gain` is incompatible with `sample_accurate=True` (raises ValueError)

### `adaptive_paradigm.py`
- Added `calibration=None` kwarg to `__init__`; stored as `self.calibration`; passed to `TrialPlayer(verbose=False, calibration=calibration)`
- **Key signature:** `def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None, show_operator_display=True, randomize_config_order=True, calibration=None):`
- New method: `set_calibration(calibration)` — sets both `self.calibration` and `self.tp.calibration`
- **Key signature:** `def set_calibration(self, calibration):`
- **Subclasses NOT modified.** Test scripts wire calibration via `paradigm.set_calibration(cm)` after construction.

### `paradigm_ild.py`
- `prepare_trial`: routes stereo through `prepare_sound()` if calibration set, else original `Sound()` ctor
- **Key signature:** `if self.calibration is not None:\n            # Gateway handles FIR convolution and Sound wrapping.`  (in prepare_trial)
- `execute_trial`: bumps `time.sleep` by `cm.ringout_seconds` to absorb FIR ringout
- **Key signature:** `ringout_pad = self.calibration.ringout_seconds if self.calibration else 0.0`

### `paradigm_itd.py`
- Same pattern as ILD. Both `signal_type='sin'` and `signal_type='white'` paths share one calibration branch (after `stereo_wave` is built)
- **Key signature:** `if self.calibration is not None:\n            # Gateway handles FIR convolution and Sound wrapping.`  (in prepare_trial)
- **Key signature:** `ringout_pad = self.calibration.ringout_seconds if self.calibration else 0.0`

### `paradigm_ifmc.py`
- Deleted fake `db_spl_to_amplitude()` stub (the old `db_spl / 100.0` math is gone)
- `prepare_trial`: requires CalibrationManager (raises RuntimeError if not attached); calls `cm.spl_to_amplitude(masker_level)` -> `(amp_L, amp_R)`; passes to TrialPlayer via `amp=1.0, per_channel_gain=(amp_L, amp_R)` (not `amp=amp_L`)
- **Key signature:** `raise RuntimeError(\n                "IFMC requires a CalibrationManager with valid SPL calibration "`
- **Key signature:** `amp_L, amp_R = self.calibration.spl_to_amplitude(self.masker_level)`
- **Key signature:** `per_channel_gain=(amp_L, amp_R),`  (catch trial)
- **Key signature:** `per_channel_gain=[(amp_L, amp_R), None],`  (normal trial: per-event list, None for probe)
- Stores `self._last_masker_amp_L` / `_R` for logging
- `get_log_data()` now includes `masker_amp_L` / `masker_amp_R` columns
- **Key signature:** `"masker_amp_L": getattr(self, "_last_masker_amp_L", None),`

### `paradigm_tmc.py`
- Deleted fake `_db_to_amp()` stub
- Same pattern as IFMC for `prepare_trial` and `get_log_data`
- **Key signature:** `raise RuntimeError(\n                "TMC requires a CalibrationManager with valid SPL calibration "`
- **Key signature:** `amp_L, amp_R = self.calibration.spl_to_amplitude(self.masker_level)`
- **Key signature:** `per_channel_gain=(amp_L, amp_R),`
- **Key signature:** `per_channel_gain=[(amp_L, amp_R), None],`
- **Key signature:** `"masker_amp_L": getattr(self, "_last_masker_amp_L", None),`

### `test_ifmc.py`
- Added `from utils.calibration import CalibrationManager`
- Added module-level constant `CALIBRATION_CONFIG_PATH = "../../calibration_data/calibration_config.json"`
- **Key signature:** `CALIBRATION_CONFIG_PATH = "../../calibration_data/calibration_config.json"`
- `main()`: loads CalibrationManager at top, with three pre-flight checks (config exists, SPL data populated, FIR loaded). Aborts gracefully on first two, warns and continues on third.
- **Key signature:** `calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)`
- Both `ParadigmIFMC(...)` constructions (pre-dialog and post-dialog) followed by `paradigm.set_calibration(calibration)`
- **Key signature:** `ifmc.set_calibration(calibration)`  (TWO occurrences in the file)

### `test_tmc.py`
- Symmetric to test_ifmc.py
- **Key signature:** `CALIBRATION_CONFIG_PATH = "../../calibration_data/calibration_config.json"`
- **Key signature:** `calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)`
- **Key signature:** `tmc.set_calibration(calibration)`  (TWO occurrences in the file)

### `phase_b_calibration_plan.md`
- Inline warning above the obsolete `mode='same'` snippet pointing to the addendum
- **Key signature:** `!!! IMPORTANT: the mode='same' snippet below is OBSOLETE and WRONG.`
- Appended **Session Addenda (2026-04-30)** section covering:
  - Convolution mode correction (with empirical gap-detection numbers)
  - Per-channel SPL plumbing rationale (Step 6 -> Step 6b)
  - File/directory layout deviations
  - Per-trial logging additions
  - Plan deliverables NOT created (`calibrate_spl.py`, `generate_inverse_ir.py`, `verify_calibration.py`)
  - Untested code paths (ILD/ITD with calibration on hardware; calibrated bg_sound; dt250 profile)
  - What's still TODO post-session
- **Key signature:** `## Session Addenda (2026-04-30)`

---

## Phase B implementation status vs plan

| Plan step | Status |
|-----------|--------|
| B1a — CalibrationManager class | [OK] Implemented (with extensions: `ringout_seconds`, `summary()`, `per_channel_gain` kwarg) |
| B2a — TrialPlayer integration | [OK] Implemented (with extension: `per_channel_gain` plumbing through `new_trial`) |
| B2b — ILD/ITD direct-Sound integration | [OK] Implemented |
| B3 — SPL calibration measurement | [OK] Done by Eric outside this session (REW + Reaper + Audition workflow) |
| Step 6 — IFMC/TMC dB SPL wiring | [OK] Implemented (true per-ear SPL via per_channel_gain) |
| Step 7 — test scripts wired up | [OK] Implemented for `test_ifmc.py` and `test_tmc.py` |
| Step 8 — manual regression pass | DEFERRED to Eric outside session |

### Plan deliverables NOT created

These were listed in the plan's "Files That Will Be Modified" table but
were not implemented this session:

- `calibrate_spl.py` — interactive SPL measurement helper. NOT NEEDED: B3 was performed via REW + Audition + manual measurement.
- `generate_inverse_ir.py` — Python IR inversion utility. NOT NEEDED: REW handles min-phase inverse FIR generation.
- `verify_calibration.py` — automated verification test. PARTIALLY REPLACED by `tests/audible_smoke_test.py` (manual sanity-check, not automated).

### Untested code paths

- ILD/ITD with calibration on real hardware. Numerical smoke tests pass but actual playback of FIR-extended buffer in those paradigms not yet exercised end-to-end.
- Calibrated `bg_sound`. Has unit-level coverage but no end-to-end paradigm uses it yet.
- `dt250_ufx2` profile. Placeholder only; never loaded.

---

## Open questions (still pending team input)

1. **Maximum SPL safety ceiling.** Currently 105 dB SPL in the AKG profile, pending team confirmation. Eric flagged this for confirmation today.
2. **dB HL conversion methodology for PTA.** RETSPL values not published for AKG K271 MkII; multiple options under discussion. Out of scope for Phase B.
3. **Per-frequency L/R asymmetry.** Calibration measures asymmetry at 1 kHz only (0.1 dB). Asymmetry at other frequencies is uncharacterized. Worth measuring at all test frequencies if observed asymmetries grow beyond ~0.5 dB.

---

## Next session

- Step 8 manual regression pass (Eric, outside session) is the immediate next item.
- After regression pass: Wave 2 dB migration — convert PTA, AM, FM, GAP, DLI, LDL, ILD, ITD user-facing levels to true dB SPL via the same calibration pathway. Each paradigm needs a defined reference level for its carrier.
- Once new DT250 arrives: populate `dt250_ufx2` profile and cross-validate against AKG measurements at common frequencies.
- Possibly add operator-facing "Verify Calibration" check in setup dialog.
