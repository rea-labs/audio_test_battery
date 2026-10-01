# PROLACTIN — Project Status & Context
*Last updated: 2026-02-23*

---

## What Is This

PROLACTIN is a Python audiology toolbox for psychoacoustic research testing. It implements 11 paradigms (PTA, GAP, AM, FM, DLI, IFMC, TMC, ILD, ITD, LDL, adaptive_PTA) following the MultiThreshold MATLAB toolbox protocol and Lecluyse 2009/2013 standards. Target platform: Mac + Windows, PsychoPy audio backend, tkinter GUI.

---

## Architecture Overview

```
test_xxx.py          → configures and launches a paradigm
paradigm_xxx.py      → paradigm-specific subclass (VarSpec, prepare_trial)
adaptive_paradigm.py → base class: trial loop, adaptive logic, data logging
trial_player.py      → audio playback via PsychoPy
event_gen.py         → stimulus waveform synthesis
operator_gui.py      → operator monitoring window (matplotlib + tkinter)
result_loader.py     → load PTA results for IFMC/TMC probe level computation
standard_frequencies.py → shared freq/timing constants
DEFAULTS.py          → shared audio defaults
varspec.py           → variable specification container
```

### Adaptive Logic (MultiThreshold pattern)
- 1-up/1-down tracking (default), configurable to N-up/M-down
- Reversal detection: direction change after initial descending phase
- Trial counting starts after first reversal (trials_after_reversal)
- Threshold = arithmetic mean of post-criterion reversals (or psychometric fit)
- Per-run catch trial rate adaptation (reduces if false positives occur)
- Outer variables (frequency, duration, etc.) define configs; each config is an independent adaptive run

---

## Current Status (as of 2026-02-23)

### Priority 1 — Operator GUI: ~70% done
- `operator_gui.py` has 4-panel matplotlib display: waveform, adaptive track, threshold history, psychometric function
- **ROOT CAUSE BUG**: OperatorDisplay is NEVER instantiated from `adaptive_paradigm.py:main()` — no import, no call. Plots never appear.
- Fix is documented in audit_supplement A.1/B.1 (straightforward integration, ~20 lines)
- Dual-Tk issue: OperatorDisplay must use `tk.Toplevel(parent)` not `tk.Tk()` (documented in audit_supplement A.6/B.2)
- Psychometric plot needs live fitting during config, not just at end (audit_supplement A.2/B.3)
- Remaining polish: participant GUI flicker (rebuilds every trial), hardcoded y-axis limits, performance summary commented out

### Priority 2 — Calibration: NOT STARTED
- `TrialPlayer.db2amp()` is uncalibrated (maps dB FS → amplitude with no SPL offset)
- IFMC/TMC have amplitude scale mismatch: masker uses linear dB_SPL/100, probe uses 10^(dB/20) — these are incompatible
- Plan: inverse filter convolution (REW-generated FIR) + SPL offset per channel
- Blocker for meaningful IFMC/TMC data

### Priority 3 — Testing & Tuning: NOT STARTED
- Separate testing plan document exists (PROLACTIN_testing_plan.md)
- Depends on calibration for IFMC/TMC threshold validity

### Priority 4 — HID Input: NOT STARTED
- NiceGUI (web-based) preferred for tablet participant response
- Can be developed in parallel with Priorities 1-2

### Priority 5 — Refactoring: NOT STARTED
- Do after Priorities 1-3 stabilize
- Target: extract ParticipantGUI, DataManager, IOManager from AdaptiveParadigm

---

## Confirmed Bugs (must fix before testing)

| # | Severity | Issue | File(s) |
|---|----------|-------|---------|
| 1 | BLOCKER | OperatorDisplay never called from main() | adaptive_paradigm.py |
| 2 | BLOCKER | FM mod_ind = phase mod index (radians) ≠ % freq deviation | event_gen.py, paradigm_fm.py |
| 3 | BLOCKER | ILD pan param not accepted by TrialPlayer → no lateralization | paradigm_ild.py, trial_player.py |
| 4 | BLOCKER | Import paths inconsistent (flat files vs paradigms/ utils/ packages) | all files |
| 5 | BLOCKER | event_gen.py imports from config.DEFAULTS (no such package) | event_gen.py:20 |
| 6 | HIGH | IFMC/TMC amplitude scale mismatch (masker vs probe) | paradigm_ifmc.py, paradigm_tmc.py |
| 7 | HIGH | Dead update_streaks_and_difficulty() methods (never called) | paradigm_ifmc.py, paradigm_tmc.py |
| 8 | HIGH | Module-level EventGen() instantiation triggers PsychoPy on import | event_gen.py:174 |
| 9 | MEDIUM | Dual Tk() root windows (operator + participant) → event conflicts | adaptive_paradigm.py, operator_gui.py |
| 10 | MEDIUM | No WRV limits / abort on non-convergence | adaptive_paradigm.py |
| 11 | MEDIUM | No config presentation order randomization | adaptive_paradigm.py |
| 12 | MEDIUM | O(n²) DataFrame concat in trial logging | adaptive_paradigm.py:892 |

---

## Protocol Deviations (open)

- First reversal logic doesn't strictly enforce initial descending direction (partial fix only)
- Config transition off-by-one: config_num used as both 0-based index and 1-based display
- "Continue vs stop on false positive" not implemented (always continues; UZH behavior only)
- IFMC masker frequency ratios: plan CSV vs standard_frequencies.py vs Lecluyse not fully reconciled
- TMC gaps: two sets defined (Lecluyse vs PROLACTIN plan) — need to pick one explicitly

---

## Threshold Import for IFMC/TMC

Current flow: ResultLoader loads PTA CSV → computes probe amplitude → passes to paradigm. Problems: no verification UI, can't edit individual values, IFMC+TMC both prompt separately, get_tmc_probe_level duplicates get_ifmc_probe_level.

Proposed fix: `ThresholdReviewDialog` — unified editable table GUI (see audit_supplement C). Not yet implemented.

---

## Key Design Decisions (settled)

- Single persistent operator window (not per-paradigm)
- Tkinter + Matplotlib for GUI (not NiceGUI yet)
- Psychometric fitting: Boltzmann sigmoid (Lecluyse), always computed at config end, live fit in plot
- Config order: add `order` param ("sequential"/"random"/"counterbalanced"), default sequential for now
- IFMC masker frequencies: confirm with team (0.7, 0.9, 1.0, 1.1, 1.3 per PROLACTIN plan)
- TMC gaps: use PROLACTIN plan values (30, 50, 70 ms) not Lecluyse (20, 40, 50, 60, 80 ms)

---

## Open Questions

1. Import path structure: do you have a `paradigms/` and `utils/` directory locally? Or is everything flat? Need to resolve before any integration testing.
2. Calibration: Has REW measurement been done? What headphone model? Do you have an inverse filter WAV already?
3. IFMC masker frequencies: confirm final set (see 2.4 in audit)
4. WRV abort: should non-convergence abort config or just flag in output?
5. Session controller: automated PTA → IFMC → TMC sequence needed?

---

## Immediate Next Steps (recommended order)

1. **Resolve import paths** (bug #4, #5) — nothing runs without this
2. **Fix OperatorDisplay integration** (bug #1) — audit_supplement B.1/B.2, ~30 lines
3. **Fix FM stimulus** (bug #2) — single formula change in event_gen.py
4. **Fix ILD panning** (bug #3) — add stereo support to TrialPlayer or bypass like ITD
5. **Implement ThresholdReviewDialog** for IFMC/TMC (audit_supplement C)
6. **Calibration** (Priority 2)
7. **Testing** (Priority 3 — see testing plan)

---

## Reference Documents

- `code_audit_2026-02-19.md` — comprehensive bug/issue list with line numbers
- `audit_supplement_2026-02-19.md` — OperatorDisplay integration fix, psychometric plot fix, ThresholdReviewDialog proposal
- `implementation_plan_5_priorities.md` — full implementation plan with code sketches
- `Documentation_multiThreshold_UZH_UPDATE.docx` — MultiThreshold manual (primary protocol reference)
- `Lecluyse2013IJAprofiles.pdf` — IFMC/TMC protocol reference
- `PROLACTIN_miro_block_diagrams.pdf` — architecture diagrams
- `PROLACTIN_paradigm_plan_overview.csv` — parameter specs per paradigm

---

## How to Use This Document

At the start of each new chat: paste this file + relevant source files. After completing a major item, ask Claude to update the "Current Status" and "Confirmed Bugs" sections and regenerate this file.
