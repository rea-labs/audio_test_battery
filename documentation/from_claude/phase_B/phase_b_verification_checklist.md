# Phase B6 — Hardware Verification Checklist

*Created: 2026-05-01 (session 02)*
*Purpose: Operator checklist for verifying calibrated PROLACTIN playback against the B&K 4153 artificial ear, before clinical use.*

---

## Prerequisites

Before starting:

- [ ] DT250 (or active calibration profile target) on B&K 4153 coupler
- [ ] Coupler seal verified (no L/R asymmetry from cable weight, etc.)
- [ ] B&K mic → RME UFX II line input
- [ ] RME UFX II HP output gain set to calibration setting (locked via TotalMix → Store → Lock Keys → ALL)
- [ ] Active calibration profile in `calibration_config.json` matches the headphones on the coupler
- [ ] Pistonphone calibrator available (94 dB SPL @ 1 kHz)
- [ ] Adobe Audition (or equivalent) for Total RMS measurement
- [ ] REW open and configured at 48 kHz sample rate for sweep measurements
- [ ] Audible smoke test (`tests/audible_smoke_test.py`) passes — sanity check before formal verification

---

## Test 1 — Pistonphone re-validation of SPL anchor

**Purpose:** Confirm the calibration's SPL anchor (`spl_at_ref_amp_dB_L`,
`..._R` in `calibration_config.json`) is still accurate. Drift here cascades
into all subsequent tests.

**Procedure:**
1. Place pistonphone on the B&K mic
2. Activate pistonphone (94 dB SPL @ 1 kHz)
3. Record 5-10 seconds in Audition
4. Compute Total RMS in dB FS via Window > Amplitude Statistics

**Expected:** Total RMS should match the value used during the original SPL
calibration procedure (recorded in calibration logs or
`session_changelog_2026-04-30.md`), within ±0.5 dB.

**Pass criterion:** ±0.5 dB
**Fail action:** SPL anchor drifted. Re-run pistonphone calibration before
proceeding. Update `calibration_config.json` with new anchor value.

- [ ] Test 1 passed (anchor measured = ___ dB FS, expected = ___ dB FS, delta = ___ dB)

---

## Test 2 — Frequency response flatness (calibrated white noise)

**Purpose:** Verify the FIR inverse filters flatten the headphone response
across the audiometric range.

**Procedure:**
1. Run a small Python script (or modify `audible_smoke_test.py`) that plays
   calibrated white noise at 65 dB SPL through the active profile
2. Record on coupler in REW (or capture in Audition then import to REW for
   spectrum analysis)
3. Apply 1/6 octave smoothing for visual comparison

**Expected:** Frequency response within ±2 dB across 100 Hz – 10 kHz on each
channel (matches the inverse filter design target range).

**Pass criterion:** ±2 dB across 100 Hz – 10 kHz, both channels
**Fail action:**
- Bumps/dips outside ±2 dB but within target range → IR may be stale (drift
  since measurement). Re-measure and regenerate IRs.
- Misbehavior outside target range (below 100 Hz or above 10 kHz) → expected;
  document but don't fail.
- Asymmetric L vs R outside ±2 dB → coupler seal issue or driver damage.
  Investigate hardware before re-running.

- [ ] Test 2 passed (L flatness ___ dB, R flatness ___ dB across 100 Hz – 10 kHz)

---

## Test 3 — Single-frequency level accuracy (1 kHz)

**Purpose:** Verify the calibration's SPL math produces the requested level at
the calibration anchor frequency.

**Procedure:** For each requested level in [40, 60, 80, 100] dB SPL:
1. Use a small Python script that calls
   `cm.spl_to_amplitude(target_spl)` and plays a 1 kHz sine through
   `cm.prepare_sound()`. (`audible_smoke_test.py` can be adapted, or write
   a new minimal script.)
2. Record 5-10 seconds in Audition (per ear, separately)
3. Compute Total RMS in dB FS (Audition Amplitude Statistics)
4. Convert to dB SPL using the pistonphone-anchored offset
5. Compare requested vs. measured

**Expected:** Measured ≤ ±1 dB from requested, both ears.

**Pass criterion:** ±1 dB at all four levels, both ears
**Fail action:**
- Bias of similar magnitude across all levels → SPL anchor or offset wrong.
  Re-do Test 1 first.
- Error grows with level → likely clipping or compressor in the signal chain.
  Reduce levels and re-test; investigate.
- L/R differ by > 0.5 dB → per-ear sensitivity correction in CalibrationManager
  may have a bug. Check `spl_to_amplitude()` returns asymmetric values.

| Requested SPL | Measured L (dB SPL) | Measured R (dB SPL) | L delta | R delta | Pass? |
|---------------|---------------------|---------------------|---------|---------|-------|
| 40 | ___ | ___ | ___ | ___ | [ ] |
| 60 | ___ | ___ | ___ | ___ | [ ] |
| 80 | ___ | ___ | ___ | ___ | [ ] |
| 100 | ___ | ___ | ___ | ___ | [ ] |

---

## Test 4 — Multi-frequency level equality

**Purpose:** Verify that the inverse filter and SPL math compose correctly
across frequencies — i.e., a request for "60 dB SPL" produces the same SPL
regardless of frequency.

**Procedure:** For each frequency in [250, 500, 1000, 2000, 4000, 8000] Hz:
1. Play calibrated 60 dB SPL sine via `cm.prepare_sound()`
2. Record on coupler
3. Compute Total RMS → convert to dB SPL

**Expected:** All measurements within ±2 dB of each other (the FIR inverse
filter target tolerance).

**Pass criterion:** ±2 dB across all six frequencies, both ears
**Fail action:**
- Frequency-specific bias > 2 dB → IR magnitude error at that frequency.
  Cross-check against REW's IR verification trace (1/A × original = flat).
- Systematic high-frequency rolloff → coupler high-frequency limitations
  may dominate above 8 kHz; document but don't necessarily fail.

| Frequency | Measured L | Measured R | Delta from 1k L | Delta from 1k R | Pass? |
|-----------|-----------|-----------|-----------------|-----------------|-------|
| 250 Hz | ___ | ___ | ___ | ___ | [ ] |
| 500 Hz | ___ | ___ | ___ | ___ | [ ] |
| 1000 Hz | ___ | ___ | ___ | ___ | [ ] |
| 2000 Hz | ___ | ___ | ___ | ___ | [ ] |
| 4000 Hz | ___ | ___ | ___ | ___ | [ ] |
| 8000 Hz | ___ | ___ | ___ | ___ | [ ] |

---

## Test 5 — Clipping check at safety ceiling

**Purpose:** Verify that requesting the maximum allowed SPL (105 dB SPL) does
not produce digital clipping or audible distortion.

**Procedure:**
1. Play calibrated 1 kHz sine at 105 dB SPL via `cm.prepare_sound()`
2. Record on coupler
3. Inspect waveform in Audition — should be clean sinusoid
4. Compute Total RMS and peak — peak should be ≤ -1 dB FS (some headroom)
5. Listen briefly (with caution) — should sound clean, no harshness or distortion

**Expected:**
- Digital peak ≤ -1 dB FS (ideally close to -1 dB FS — cleanly approaching
  but not at maximum)
- Acoustic SPL within ±1 dB of 105 dB SPL
- Clean sinusoid in waveform view

**Pass criterion:** No digital clipping; acoustic SPL within ±2 dB of 105;
clean sinusoid
**Fail action:**
- Digital clipping → headphone less sensitive than expected; either lower
  `max_spl` in calibration_config or accept that 105 isn't achievable on
  this profile.
- Acoustic SPL well below 105 → headphone less sensitive than expected
  (similar action).
- Distortion without digital clipping → headphone driver excursion
  limit; lower `max_spl`.

- [ ] Test 5 passed (peak = ___ dB FS, measured SPL = ___ dB SPL)

---

## Test 6 — Safety guard verification

**Purpose:** Verify that `CalibrationManager` refuses requests above
`max_spl` instead of silently clipping.

**Procedure:**
1. In a Python REPL with the calibration loaded, call
   `cm.spl_to_amplitude(110)` (5 dB above max_spl=105)
2. Observe behavior

**Expected:** Should either raise an exception OR log a warning AND clamp
to max_spl. Behavior should be documented and consistent.

**Pass criterion:** Behavior matches the documented safety contract in
`calibration.py`; no silent overshoot
**Fail action:** Update `spl_to_amplitude()` to enforce the ceiling; ensure
documentation matches behavior.

- [ ] Test 6 passed (observed behavior: ___________)

---

## Test 7 — End-to-end paradigm playback (calibration-active)

**Purpose:** Verify that calibrated playback works end-to-end through
TrialPlayer-routed paradigms (no buffer truncation, no clicks at boundaries,
correct levels).

**Procedure:** Run a few-trial demo of each paradigm in `verbose=True` mode
with calibration loaded:

- [ ] **PTA** — 60 dB SPL, 1 kHz, both ears: audible, no clicks, CSV header
      shows `level_units: dB SPL`
- [ ] **LDL** — starts at 50 dB SPL, ascends 3 dB/trial, audible at 50 and
      louder above
- [ ] **AM** — 60 dB SPL carrier, fc=1k, fm=8, mod_ind=50%: audible tremolo,
      no clipping warnings
- [ ] **FM** — 60 dB SPL carrier, fc=1k, fm=4, mod_ind=8%: audible warble,
      no clipping warnings
- [ ] **GAP** — 65 dB SPL noise, 10 ms gap: audible gap, no clicks
- [ ] **DLI** — 60 dB SPL ref, 5 dB diff, 1 kHz: audible level difference
- [ ] **ILD** — 60 dB SPL ref, 1 kHz, 10 dB ILD: clearly lateralized,
      mean loudness balanced across center vs. lateralized trials
- [ ] **ITD (sin)** — 60 dB SPL ref, 1 kHz, 10 ms ITD: clearly lateralized,
      both ears equal-loudness perceptually
- [ ] **ITD (white)** — 60 dB SPL ref, 1 ms ITD, white noise: clearly
      lateralized, perceptually diffuse (independent noise → IACC ≈ 0)
- [ ] **IFMC** — masker level adapts in dB SPL, probe audible (post band-aid
      adjustment), CSV header shows `masker_level_units: dB SPL`
- [ ] **TMC** — same shape as IFMC

For each: confirm CSV file is produced with correct header metadata
(`prolactin_version`, `calibration_profile`, `level_units`, etc.) and that
per-row `amp_L`/`amp_R` columns are populated.

**Pass criterion:** All paradigms run to completion. No clipping warnings.
No audible clicks/glitches at trial boundaries. CSV headers and per-row
audit columns correct.

---

## Test 8 — Long-trial ringout sanity

**Purpose:** Verify the recently added ringout-aware `core.wait` in
TrialPlayer doesn't cause noticeable lag between trials, AND verify no
buffer truncation at trial end.

**Procedure:**
1. Run a 10-trial PTA config in calibrated verbose mode
2. Time the inter-trial gap (subjective is fine — should feel natural,
   not noticeably slower than uncalibrated runs)
3. Record one trial's audio output via loopback or coupler
4. Inspect the recorded audio: should show clean fade-out, no abrupt
   truncation at end (ringout properly captured)

**Pass criterion:** Inter-trial gap subjectively normal; recorded audio
shows clean fade-out without truncation
**Fail action:** If truncation observed, increase the slack constant in
`trial_player.py`'s `play_trial` (currently `+ 0.1`) — or investigate
whether `ringout_seconds` is being computed correctly.

- [ ] Test 8 passed

---

## Final sign-off

- [ ] All Tests 1-8 passed
- [ ] Date of verification: ___________
- [ ] Operator: ___________
- [ ] Active profile: ___________
- [ ] Calibration anchor (pistonphone Total RMS): ___ dB FS
- [ ] `max_spl` in calibration_config.json: ___ dB SPL
- [ ] Notes / deviations: ___________________________________________

Once all tests pass, **Phase B is complete**. The calibration setup is
clinically validated for use with PROLACTIN paradigms.

---

## Appendix: Failure mode triage

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| All measurements biased by same dB amount | SPL anchor drift | Re-do pistonphone calibration |
| Bias grows with level | Clipping or compressor in chain | Reduce gain; investigate signal chain |
| L/R differ by > 0.5 dB at same frequency | Coupler seal or driver damage | Re-seat headphone; inspect drivers |
| Frequency-specific bias > 2 dB | IR error at that frequency | Re-verify IR in REW; regenerate if needed |
| Inter-trial gap noticeably long | Ringout slack too generous | Reduce slack constant in `play_trial` |
| Audible click at trial end | Ringout slack too tight (truncation) | Increase slack constant |
| Audible click at trial start | Onset issue (not ringout-related) | Verify fade-in via FIR — see session_changelog_2026-04-30 mode='full' fix |
| Calibrated playback silent | Calibration not attached, or `spl_calibrated=False` | Check pre-flight checks in test script; verify config JSON populated |
