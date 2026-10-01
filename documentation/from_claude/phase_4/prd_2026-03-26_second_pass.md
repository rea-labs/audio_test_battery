# PROLACTIN — Development PRD
*Last updated: 2026-03-26 (rev 3)*

---

## Context

All 11 paradigms run without crashing. Core adaptive logic (reversals, catch trials, threshold estimation, operator GUI) is functional.

**Phase A1** (previous PRD) is complete — all items A1–A6 implemented and committed.

This document now covers three phases: **Phase A2** (next round of fixes and features), **Phase B** (calibration, requires hardware), and a **low-priority backlog**.

---

## Phase A2 — Next Round of Fixes & Features

### A2.1 — Editable params in paradigm setup dialog (HIGH)
**File:** `paradigm_setup_dialog.py`, all `test_*.py`  
**Problem:** The setup dialog shows a read-only summary of inner/outer params. Operators cannot adjust values before running — requiring code edits for any change.  
**Fix:**
- Replace the read-only param summary with an editable section
- **Inner var (`data` dict):** render each key/value pair as an editable field (start, step_down_initial, step_down_final, step_up_initial, step_up_final, min, max). Changes update the `params` dict before paradigm construction.
- **Outer vars:** for frequency-type vars, provide a dropdown of named frequency sets (reuse existing `FREQUENCY_SETS` from `standard_frequencies.py`). Once a set is selected, values are shown as an editable free-form list (comma-separated). Other outer vars (pan, duration, etc.) are shown as editable free-form lists directly.
- All changes feed back into the `params` dict before the paradigm is constructed — no re-instantiation needed, the test script just reads the (now-modified) params after `dialog.show()` returns.
- No sanity checks required initially; add later.
- `ThresholdSetupDialog` (IFMC/TMC) already handles frequency editing — ensure new approach is consistent or extends it rather than duplicating.

**Risk:** Medium-high. Touches the dialog and every test script's param-handling flow. Implement and test one paradigm (PTA) first, then roll out.

---

### A2.2 — ITD stimulus click / truncation bug (HIGH)
**File:** `paradigm_itd.py`, `event_gen.py`  
**Problem:** For sin signal type, the second stimulus is sometimes truncated with an audible click. Likely cause: the inter-stimulus delay pushes the total stimulus duration past the allocated buffer length, cutting off the tail before the fade-out completes.  
**Fix:**
- Audit ITD stimulus generation: compute worst-case total duration (base duration + max possible delay) and ensure the buffer is allocated accordingly.
- Ensure fade-out is applied to the end of the *actual* signal, not the end of the buffer.
- Confirm fix for both sin and noise signal types.

**Note (low priority, separate task):** For ITD with noise stimuli, consider generating two independent pink noise signals (one per ear) rather than delaying a copy of the same signal. Currently, zero-delay noise is identical in both ears, making it trivially easy to detect — this is not a valid psychoacoustic stimulus.

**Risk:** Low-medium. Contained to ITD paradigm and event_gen.

---

### A2.3 — Temporary CSV logging after each config (MEDIUM)
**File:** `adaptive_paradigm.py`  
**Problem:** A mid-run crash loses all data since `write_data_to_disk()` only runs at paradigm end.  
**Fix:** At the end of each config (in the config-completion block of `update_trial_params()`), write a temp file: `{participant_id}_{paradigm_code}_temp.csv`. Overwrite on each config completion. Delete on clean paradigm completion.  
**Note:** Resume-from-crash (loading temp file to restore state) is a separate, more complex feature — deferred to later.

**Risk:** Low.

---

### A2.4 — IFMC/TMC fade time verification (MEDIUM)
**File:** `paradigm_ifmc.py`, `paradigm_tmc.py`  
**Problem:** Current ramp duration is 4 ms (`ramp_dur = 0.004`). There may be an audible click at the end of the second stimulus, potentially acting as an unintended cue.  
**Fix:** Compare ramp durations against the MATLAB MultiThreshold reference implementation. Adjust if needed.  
**Status:** Deferred until MATLAB MT code can be checked. Log current values here for reference:
- `masker_dur = 108 ms`, `gap_dur = 10 ms`, `probe_dur = 16 ms`, `ramp_dur = 4 ms`

**Risk:** Low (once verified against reference).

---

### A2.5 — Fix garbage characters in comments/strings (MEDIUM)
**Files:** Multiple (scope to be determined by grep at task time)  
**Problem:** Encoding artifacts (e.g. `Ã¢â€ â€™` instead of `→`) appear in comments, docstrings, and possibly some GUI labels/plot titles. No known runtime impact yet, but at least one instance in a GUI-visible string has been suspected.  
**Fix:** Run a grep for common garbage character patterns across all `.py` files. Replace with correct UTF-8 characters or ASCII equivalents. Pay special attention to any string that appears in a GUI label, plot title, or printed output.

**Risk:** None for comments. Low for GUI strings — verify after fix.

---

### A2.6 — Operator GUI mislabeled plots and info text (MEDIUM)
**File:** `operator_gui.py`  
**Problem:** Several plots and info panel fields show incorrect or generic labels that don't reflect the current paradigm (e.g. FP warning text says "please only respond if you heard the stimulus" even in paradigms like ITD where the question is about lateralisation, not detection).  
**Fix:** To be specified in detail after a closer review of the GUI output across paradigms. At minimum: FP warning text should be paradigm-aware (each paradigm subclass should be able to provide its own FP warning string, defaulting to the current generic text).  
**Status:** Deferred pending detailed review. Placeholder for now.

**Risk:** Low-medium depending on scope.

---

### A2.7 — Keyboard navigation in operator setup dialog (MEDIUM)
**File:** `paradigm_setup_dialog.py`  
**Problem:** Operator cannot tab between fields or confirm with Enter/Space — mouse required throughout.  
**Fix:**
- Tab order set explicitly through all editable fields
- Enter/Space confirm the default action (Accept button) when focus is not in a text field
- Applies to `ParadigmSetupDialog` and `ThresholdSetupDialog`

**Risk:** Low.

---

### A2.8 — Demo mode (LOW)
**Files:** `adaptive_paradigm.py`, all `test_*.py`  
**Problem:** No way for the operator to play a sample trial to familiarise the participant without triggering data logging.  
**Fix:** Add a `demo_mode` flag to `AdaptiveParadigm`. When set, run one trial (no catch trial, stimulus at a comfortable level), then pause for the participant to respond — but skip all data logging, threshold estimation, and file writing. Accessible from the setup dialog via a "Play demo trial" button.

**Risk:** Low. Contained change.

---

### A2.9 — ITD noise: independent per-ear signals (LOW)
**File:** `paradigm_itd.py`, `event_gen.py`  
**Problem:** For noise stimuli, the same noise signal is used for both ears (only one is delayed). At zero delay, both ears receive an identical signal, making lateralisation trivially easy and scientifically invalid.  
**Fix:** Generate two independent noise signals (one per ear). Apply delay to one. This preserves the ITD cue while eliminating the identical-signal artifact at zero delay.

**Risk:** Low-medium. Requires changes to noise generation in event_gen and ITD stimulus construction.

---

### Phase A2 — Suggested implementation order

| # | Task | Priority | Effort | Risk |
|---|------|----------|--------|------|
| A2.1 | Editable setup dialog | High | 2–3 hr | Medium-high |
| A2.2 | ITD click/truncation bug | High | 1 hr | Low-medium |
| A2.3 | Temp CSV logging | Medium | 30 min | Low |
| A2.5 | Garbage character cleanup | Medium | 30 min | None |
| A2.4 | IFMC/TMC fade verification | Medium | defer | Low |
| A2.6 | Operator GUI label fixes | Medium | defer | Low |
| A2.7 | Keyboard nav in setup dialog | Medium | 1 hr | Low |
| A2.8 | Demo mode | Low | 1–2 hr | Low |
| A2.9 | ITD independent noise | Low | 1 hr | Low-medium |

---

## Phase B — Headphone Calibration

> **Prerequisite:** Access to calibration setup (calibrated mic or HATS, REW). Steps B1a, B2a, B2b are code-only and can be done now. Measurement steps require hardware.

**Target hardware:** Beyerdynamic DT250 (250 Ω).

---

### B1 — Inverse filter convolution (frequency response correction)

**Goal:** Flatten headphone frequency response so equal digital amplitude → equal SPL across frequencies. This is headphone EQ correction only — not HRTF/binaural encoding.

**Implementation:**
- New class `CalibrationManager` in `calibration.py`
- Loads per-channel FIR impulse response WAVs (`headphone_L_inverse.wav`, `headphone_R_inverse.wav`)
- Resamples to system sample rate if needed
- Exposes `apply(signal_L, signal_R) → (signal_L_cal, signal_R_cal)` via `scipy.signal.fftconvolve`
- Applied in `TrialPlayer` just before audio output
- If no calibration files present: runs uncalibrated with console warning (graceful degradation)

**Default:** Start with identity IRs (flat = no correction). Real IRs dropped in later without code changes.

**Integration point:** `trial_player.py` — optional injectable dependency; paradigm code does not change.

**REW workflow (deferred until hardware available):**
1. Play log swept sine through headphones, measure with calibrated mic (one per ear)
2. Export minimum-phase FIR inverse filter as WAV
3. Drop WAVs into `calibration/` folder, update `calibration_config.json`

---

### B2 — SPL offset calibration (dB FS → dB SPL mapping)

**Goal:** Map digital amplitudes to absolute SPL so IFMC/TMC masker/probe levels are physically meaningful.

**Implementation:**
1. Play 1 kHz sine at known digital amplitude (e.g., -20 dB FS), measure SPL with calibrated mic
2. Compute: `SPL_offset = measured_SPL - reference_dBFS`
3. Update `TrialPlayer.db_spl_to_amplitude()`: `amp = 10^((dB_SPL - SPL_offset) / 20)`
4. Store offset + headphone model in `calibration_config.json`

**Config file structure (`calibration_config.json`):**
```json
{
  "headphone_model": "Beyerdynamic DT250 250ohm",
  "spl_offset_dB": null,
  "ir_left":  "calibration/headphone_L_inverse.wav",
  "ir_right": "calibration/headphone_R_inverse.wav"
}
```
`null` values → uncalibrated mode with warning.

---

### B3 — REW workflow (deferred)

To be addressed in a dedicated session once hardware access is confirmed. Key questions to resolve: mic calibration chain, IR export settings (minimum-phase FIR), per-ear measurement procedure, absolute SPL reference.

---

### Phase B — Suggested implementation order

| # | Task | Prerequisite |
|---|------|-------------|
| B1a | `CalibrationManager` class + identity IR placeholder | None (code only) |
| B2a | `db_spl_to_amplitude()` update with offset param | None (code only) |
| B2b | JSON calibration config loader | B2a |
| B3 | REW measurement + IR export | Hardware access |
| B1b | Integrate real IRs, verify flat response | B3 + B1a |
| B2c | Measure SPL offset, populate config | B3 + B2b |

---

## Out of scope for these phases

- MockParticipant testing framework (after calibration)
- Base class boilerplate consolidation / Priority 5 refactor (Claude Code session)
- SRT, SiN, Chopper, Pitch/loudness match, MML, RI paradigms (separate design discussions)
