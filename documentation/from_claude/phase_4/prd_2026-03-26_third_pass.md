# PROLACTIN — Development PRD
*Last updated: 2026-03-26 (rev 4)*

---

## Context

All 11 paradigms run without crashing. Core adaptive logic (reversals, catch trials, threshold estimation, operator GUI) is functional.

**Phase A1** and **Phase A2** are complete — all items implemented and committed across two sessions on 2026-03-26.

This document covers remaining short-term items, **Phase B** (calibration, requires hardware), and the long-term backlog.

---

## Remaining Short-Term Items

### S1 — Stereo panning audit (MEDIUM)
**Files:** `trial_player.py`, `paradigm_ild.py`, `paradigm_itd.py`, `test_pta.py`, `test_ldl.py`
**Problem:** Two related issues:
1. Pan is currently binary (`< 0` → left only, `> 0` → right only, `0` → both). Non-integer values like `-0.1` behave identically to `-1.0`. Continuous amplitude panning is not implemented.
2. `pan=0` (both channels at full amplitude) is perceived as significantly louder than `pan=±1` (single channel). Equal-power panning would fix this: `left = cos(θ) × signal`, `right = sin(θ) × signal` where θ ∈ [0, π/2].

**Questions to resolve with team:**
- Are non-integer pan values (continuous panning) actually needed for any paradigm?
- Should equal-power panning be implemented to equalize loudness across pan positions?

**Risk:** Low-medium. Contained to `trial_player.py` once design is decided. ILD and ITD paradigms build their own stereo signals and are unaffected.

---

### S2 — ITD signal type × frequency config structure (LOW)
**Files:** `test_itd.py`, `paradigm_itd.py`
**Problem:** `signal_type` and `fc` are separate outer vars, producing a cartesian product. When only `white` noise is selected, fc is irrelevant but still generates one config per frequency. Same potential issue for ILD if noise stimuli are added.
**Fix:** Pending team decision on whether sin and white noise conditions should run in the same session. If not, operator runs paradigm twice (one signal type per run) — no code change needed. If yes, requires restructuring params to avoid spurious configs.
**Status:** Deferred pending team decision.

---

### S3 — Operator GUI label fixes (LOW, ongoing)
**File:** `operator_gui.py`
**Problem:** Several plots and info panel fields show incorrect or generic labels (e.g. FP warning text not paradigm-aware).
**Fix:** Address incrementally as issues are identified during testing. At minimum, FP warning text should be paradigm-aware (each paradigm subclass provides its own string, defaulting to generic text).
**Status:** Ongoing — fix as encountered.

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

## Long-Term Backlog

- **MockParticipant testing framework** — automated validation across all paradigms (after calibration)
- **Priority 5 refactor** — base class boilerplate consolidation (dedicated Claude Code session)
- **New paradigms** — out of scope; implemented in separate 3D audio system

---

## Completed

### Phase A1 (2026-03-26, session 1)
All items complete: event_gen guard, dead method removal (IFMC/TMC), performance optimisation, verbose flag gating, config randomisation, WRV limits, garbage character cleanup.

### Phase A2 (2026-03-26, sessions 1–2)
| # | Task | Status |
|---|------|--------|
| A2.1 | Editable params in setup dialog | ✅ Complete |
| A2.2 | ITD click/truncation bug | ✅ Complete |
| A2.3 | Temp CSV logging | ✅ Complete |
| A2.4 | IFMC/TMC fade verification | ✅ Non-issue — audible click was caused by inaccurate PTA thresholds, not ramp duration |
| A2.5 | Garbage character cleanup | ✅ Complete |
| A2.6 | Operator GUI label fixes | 🔄 Ongoing — fix as encountered (see S3) |
| A2.7 | Keyboard nav in setup dialog | ✅ Complete (Enter/Tab) |
| A2.8 | Demo mode | ✅ Complete |
| A2.9 | ITD independent noise | ✅ Complete |
