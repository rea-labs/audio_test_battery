# PROLACTIN Refactoring Plan — Combined Overview

*2026-03-29 | 6-phase plan for modular OOP architecture*

---

## Executive Summary

Transform the PROLACTIN codebase from a monolithic structure centered on `AdaptiveParadigm` (1250 lines, with ~300-line paradigm subclasses that are 80% copy-paste) into a modular, injectable, testable architecture — without breaking the 11 working paradigms.

**Current state:** All paradigms functional. Phases A1/A2 complete. No calibration, no automated tests, no session controller.

**End state:** Clean separation of concerns (paradigm logic / GUI / data / calibration / orchestration), 75% less paradigm code, automated test suite, single-script session management.

---

## Phase Summary

| Phase | Name | Key output | Effort | Depends on |
|---|---|---|---|---|
| 4 | CalibrationManager | `utils/calibration.py`, `prepare_sound()` gateway, TrialPlayer integration | Separate track | None |
| 1 | Boilerplate Consolidation | Generic `adapt_difficulty()`, paradigms shrink ~75%, PTA→dB FS | 10-12 hr | None (but account for Phase 4 file changes) |
| 2 | ParticipantGUI Extraction | Injectable GUI class, `wait_variable()` pattern, MockGUI stub | 7-8 hr | Phase 1 |
| 3 | DataManager Extraction | Injectable data class, `update_last_row()`, backward-compat `data` property | 4 hr | Phase 1 |
| 5 | ExperimentController | Session orchestration, paradigm registry, single Tk root, `run_session.py` | 12-15 hr | Phases 2, 3 |
| 6 | Testing Infrastructure | Headless mode, MockParticipant, 3-tier pytest suite (~50 tests) | 13-16 hr | Phase 2 |

**Total: ~47-55 hours** across phases 1-3 + 5-6 (Phase 4 is a separate track).

**Recommended order:** 4 → 1 → 2 → 3 → 5 → 6 (Phases 2 and 3 can be done in either order; Phase 6 can start after Phase 2 without waiting for Phase 5).

---

## Phase 4 — CalibrationManager (separate track)

Eric handles this before the other phases. See `phase_b_calibration_plan.md` (rev 2) for full details.

**Key outputs:**
- New `utils/calibration.py` with `CalibrationManager` class
- `prepare_sound()` gateway method — single audio intercept point
- TrialPlayer integration (accepts CalibrationManager, routes through gateway)
- ILD/ITD integration (they bypass TrialPlayer, call gateway directly)
- Delete fake `db_spl_to_amplitude()` from IFMC/TMC
- Identity IR placeholders for uncalibrated operation

**Files modified:** `trial_player.py`, `paradigm_ifmc.py`, `paradigm_tmc.py`, `paradigm_ild.py`, `paradigm_itd.py`, `adaptive_paradigm.py`. New files: `utils/calibration.py`, `calibration/calibration_config.json`, calibration utilities.

**Interaction with later phases:** Phase 1 must account for any structural changes to paradigm files made during Phase 4.

---

## Phase 1 — Boilerplate Consolidation + Cleanup

*Full plan: `phase1_refactoring_plan.md` (rev 3)*

**Goal:** Consolidate duplicated paradigm code into `AdaptiveParadigm` via `step_mode` dispatch. Switch PTA to dB FS tracking.

**Key changes:**
- Add `step_mode` (`'linear'` / `'multiplicative'`) to inner var config
- Generic `initialize_adaptive_param()`, `adapt_difficulty()`, `reset_to_midpoint_value()`, `update_trial_params()`, `get_log_data()` on AdaptiveParadigm
- Level tracking (`_last_two_levels`) moved from per-paradigm `prepare_trial()` to main loop
- PTA inner var becomes `trial_level_dB` (dB FS) — no special override needed
- `utils/audio_math.py` — shared `db2amp()`, `amp2db()`
- `paradigms/__init__.py`, `utils/__init__.py` for package structure
- Bug F1 fix (duplicate snapshot block)
- AM start value fix (50→16, pending team confirmation)

**After Phase 1:** Each paradigm is ~60-100 lines (down from ~300). Only `__init__()` + `prepare_trial()` + genuinely paradigm-specific overrides.

**Paradigms needing overrides:**

| Paradigm | Override | Reason |
|---|---|---|
| DLI | `check_answer()` | 3-AFC response |
| ILD | `execute_trial()` | Bypasses TrialPlayer |
| ITD | `execute_trial()`, stereo methods | Bypasses TrialPlayer |
| LDL | `check_answer()` | 3-option response |

All others: only `__init__()` + `prepare_trial()`.

---

## Phase 2 — ParticipantGUI Extraction

*Full plan: `phase2_participant_gui_plan.md`*

**Goal:** Extract Tkinter GUI code from AdaptiveParadigm into injectable `ParticipantGUI` class.

**Key changes:**
- New `utils/participant_gui.py` with `ParticipantGUI` interface, `TkParticipantGUI`, `MockParticipantGUI` stub
- `TkParticipantGUI` receives `gui_config` dict + optional `parent` Tk widget
- `get_response()` switches from `mainloop()`/`quit()` to `wait_variable()` — essential for Phase 5 (shared Tk root)
- AdaptiveParadigm accepts `gui=` param, delegates all GUI calls
- `self.root` removed from AdaptiveParadigm entirely
- `operator_gui.py` coupling fixed: `paradigm.root` → `paradigm.gui.lift()`

**Enables:** Headless mode (inject MockGUI), NiceGUI migration (inject WebGUI), ExperimentController (inject GUI with parent).

---

## Phase 3 — DataManager Extraction

*Full plan: `phase3_data_manager_plan.md`*

**Goal:** Extract data logging from AdaptiveParadigm into injectable `DataManager` class.

**Key changes:**
- New `utils/data_manager.py` with `DataManager` class
- `log_trial()`, `save()`, `write_temp()`, `delete_temp()`, `update_last_row()`, `get_config_data()`
- AdaptiveParadigm accepts `data_manager=` param, delegates storage calls
- Backward-compatible `data` property on AdaptiveParadigm (operator GUI reads `paradigm.data` unchanged)
- `log_data()` stays on AdaptiveParadigm (assembles row dict from `get_log_data()` + trial metadata), then calls `data_manager.log_trial()`

**Blast radius:** Two files only — new `data_manager.py` + edits to `adaptive_paradigm.py`. Zero changes to operator GUI, paradigm subclasses, or test scripts.

---

## Phase 5 — ExperimentController

*Full plan: `phase5_experiment_controller_plan.md`*

**Goal:** Top-level orchestrator for entire test sessions.

**Key changes:**
- New `experiment_controller.py` — owns Tk root, operator display, CalibrationManager
- New `paradigm_registry.py` — declarative paradigm configs (source of truth, replacing `test_*.py` param dicts)
- New `session_setup_dialog.py` — participant ID + paradigm selection
- New `run_session.py` — entry point
- Single hidden `tk.Tk()` persists entire session; everything else is `Toplevel` children
- `operator_gui.py` extended with session management view, accepts `parent=` param
- `paradigm_setup_dialog.py` accepts `parent=` param, uses `wait_window()` when parented
- Between-paradigm screen with continue/skip/abort options
- Session output directory with `session_log.json`
- Paradigm dependency enforcement (PTA before IFMC/TMC)

**`test_*.py` scripts** remain functional for standalone development but import params from registry instead of defining them inline.

---

## Phase 6 — Testing Infrastructure

*Full plan: `phase6_testing_infrastructure_plan.md`*

**Goal:** Automated test suite for all 11 paradigms.

**Key changes:**
- `headless` flag on AdaptiveParadigm (skips audio playback + `core.wait()` calls)
- `MockParticipantGUI` fleshed out (attach_paradigm hook for state access)
- `MockParticipant` + subclasses (DLI, LDL, GAP) — simulate listeners with known thresholds
- 3-tier pytest suite:
  - **Tier 1 (Unit):** 7 files, ~15 tests — reversal detection, catch trials, step sizing, midpoint, psych fit, config unwrap, WRV limits
  - **Tier 2 (Integration):** 6 files, ~20 tests — convergence to known thresholds, CSV format, crash recovery, multi-config, ResultLoader, threshold import
  - **Tier 3 (Stimulus):** 7 files, ~15 tests — waveform math verification (FFT, envelope, cross-correlation)
- Human test checklists (H1-H6) already complete in `PROLACTIN_human_test_checklists.md` — no code needed

---

## Cross-Phase File Impact Matrix

| File | Ph1 | Ph2 | Ph3 | Ph4 | Ph5 | Ph6 |
|---|---|---|---|---|---|---|
| `adaptive_paradigm.py` | Major | Major | Medium | Minor | Minor | Minor |
| `paradigm_*.py` (all 10) | Major | — | — | IFMC/TMC | — | — |
| `trial_player.py` | Minor | — | — | Major | — | Minor |
| `operator_gui.py` | Minor | Minor | — | — | Medium | — |
| `paradigm_setup_dialog.py` | — | — | — | — | Medium | — |
| `test_*.py` (all 10) | Medium | — | — | — | Optional | — |
| `event_gen.py` | — | — | — | — | — | — |
| `utils/audio_math.py` | **NEW** | — | — | — | — | — |
| `utils/participant_gui.py` | — | **NEW** | — | — | — | Medium |
| `utils/data_manager.py` | — | — | **NEW** | — | — | — |
| `utils/calibration.py` | — | — | — | **NEW** | — | — |
| `experiment_controller.py` | — | — | — | — | **NEW** | — |
| `paradigm_registry.py` | — | — | — | — | **NEW** | — |
| `tests/*` | — | — | — | — | — | **NEW** |

---

## Adversarial Review — Potential Issues

### 1. ILD/ITD in Headless Mode — PsychoPy Hard Dependency

**Severity: HIGH**

ILD and ITD both import `from psychopy import sound` at module level and create `sound.Sound()` objects directly in `prepare_trial()` (lines 152 and 273 respectively). They also override `execute_trial()` with their own `time.sleep()` calls.

The Phase 6 headless approach skips `execute_trial()` at the call site (`if not self.headless: self.execute_trial()`). But `prepare_trial()` still runs and still creates Sound objects. This means:
- Headless ILD/ITD tests require PsychoPy audio backend initialized (fine on Eric's machine, fails on CI)
- The `time.sleep()` in their `execute_trial()` overrides won't be skipped by the base class's headless check — if execute_trial is called, those sleeps happen even in headless mode

**Fix options:**
- **(a)** Guard Sound creation in ILD/ITD's `prepare_trial()`: `if not self.headless: self.ild_sound = sound.Sound(...)`
- **(b)** Skip `prepare_trial()` entirely in headless mode for Tier 2 tests (we only need the adaptive logic, not the audio). But then the paradigm can't read its own adaptive parameter because `prepare_trial()` is where `self.trial_num` is incremented.
- **(c)** Make `execute_trial()` skip happen at the call site in the main loop (`if not self.headless: self.execute_trial()`), which already handles base class paradigms. But ILD/ITD's execute_trial would still sleep if somehow called.

**Recommendation:** Option (a) for ILD/ITD. Also move `self.trial_num += 1` out of `prepare_trial()` into the main loop (it's duplicated in every paradigm's `prepare_trial()` — another piece of boilerplate that belongs in the base). Then headless mode can skip `prepare_trial()` for Tier 2 tests if needed, though option (a) is sufficient.

### 2. Dynamic Attribute Access (`setattr`/`getattr`) — Fragility

**Severity: MEDIUM**

The Phase 1 generic `adapt_difficulty()` uses `setattr(self, self._adaptive_attr, val)` where `_adaptive_attr` is derived from `inner_var.name`. This is clean but fragile:
- Typo in `inner_var.name` (e.g., `'mod_indd'`) silently creates a new attribute instead of updating the intended one
- IDE autocomplete and static analysis tools can't track these dynamic attributes
- Debugging is harder — stack traces show `setattr` not the attribute name

**Mitigation:** Add a validation check in `__init__()` that confirms `hasattr(self, self._adaptive_attr)` after `initialize_adaptive_param()` runs. If the attribute doesn't exist, raise a clear error. This catches typos at startup rather than mid-run.

### 3. Phase 4 → Phase 1 Merge Conflict Risk

**Severity: MEDIUM**

Phase 4 (calibration) modifies `paradigm_ifmc.py`, `paradigm_tmc.py`, `trial_player.py`, and `adaptive_paradigm.py`. Phase 1 also modifies all of these (boilerplate removal from paradigm files, reorganization of adaptive_paradigm). If Phase 4 is done first (planned), Phase 1 must work with the post-Phase-4 versions of these files.

**Specific risk:** Phase 4 deletes `db_spl_to_amplitude()` from IFMC/TMC and adds CalibrationManager integration. Phase 1 then tries to slim these files further. If Phase 1's plan was written against the pre-Phase-4 code (which it was), the line numbers and method references may be wrong.

**Mitigation:** After Phase 4, do a quick re-audit of the affected files before starting Phase 1. Update the Phase 1 plan's file-specific notes as needed. The structural changes (boilerplate consolidation) are independent of calibration changes, so the conflict is logistical, not architectural.

### 4. `wait_variable()` macOS Risk

**Severity: MEDIUM**

Phase 2 switches `get_response()` from `mainloop()`/`quit()` to `wait_variable()`. Tk's `wait_variable()` is theoretically equivalent but less commonly used. On macOS with Apple Silicon + PTB audio:
- PsychoPy/PTB creates its own audio threads
- Tkinter's event loop is single-threaded and not fully thread-safe on macOS
- The existing `mainloop()`/`quit()` pattern has been tested and works
- `wait_variable()` has not been tested in this specific environment

**Mitigation:** Test `wait_variable()` on macOS early in Phase 2 (Step 2v). If it causes issues (crashes, unresponsive GUI, focus problems), fall back to `mainloop()`/`quit()` for now. Phase 5 may then need to use a different mechanism (e.g., `after()` callbacks instead of blocking) but that bridge can be crossed later.

### 5. No Pre-Refactor Baseline Data

**Severity: MEDIUM**

The verification strategy for Phase 1 says "compare CSV output with pre-refactor baseline." But no baseline exists yet. If Phase 1 introduces a subtle bug in adaptive logic (e.g., geometric vs arithmetic midpoint applied to the wrong paradigm), the only way to detect it is noticing that thresholds are different — which requires knowing what they were before.

**Mitigation:** Before starting Phase 1, run each of the 11 paradigms for one short session (1-2 configs, fixed seed if possible) and save the CSV output as reference data. This takes ~30 minutes with a human clicking through and provides a concrete baseline for comparison.

### 6. `data` Property Before `main()` Runs

**Severity: LOW**

Phase 3's backward-compatible `data` property returns `data_manager.data` if the data manager exists, or an empty DataFrame if it doesn't. But `data_manager` is created inside `main()`. Code that accesses `self.data` during `__init__()` or between construction and `main()` (e.g., the operator display checking data length) will silently get empty data instead of raising an error.

**Mitigation:** Currently no code accesses `self.data` before `main()` runs — the operator display only reads data inside `update_display()` which is called from the trial loop. But document this constraint: "DataManager is available only after main() starts."

### 7. Paradigm Registry / Test Script Divergence During Transition

**Severity: LOW**

Phase 5 creates `paradigm_registry.py` as the source of truth for paradigm configs. During the transition period, both the registry and `test_*.py` scripts contain param definitions. If someone edits `test_pta.py` without updating the registry (or vice versa), configs diverge silently.

**Mitigation:** Once the registry exists, immediately update `test_*.py` scripts to import from it (`from paradigm_registry import PARADIGM_REGISTRY; params = PARADIGM_REGISTRY['PTA']['default_params']`). Don't maintain two copies.

### 8. `update_trial_params()` Scope in Phase 1

**Severity: MEDIUM**

The current `update_trial_params()` in AdaptiveParadigm does three things: (1) per-trial flag resets, (2) difficulty adjustment, (3) end-of-config handling (threshold estimation, config transition, catch rate adjustment, ITI timing). The Phase 1 plan shows a generic version that handles the midpoint reset + difficulty adjustment, but the full ~150-line method also contains the end-of-config block and ITI timing.

The per-paradigm overrides (AM, FM, DLI, etc.) only override the midpoint reset part — they call `super().update_trial_params()` for everything else. So the generic version must preserve the complete behavior of the current base class method, not just the midpoint + difficulty parts.

**Mitigation:** Phase 1's generic `update_trial_params()` should be the complete current method with the midpoint-reset section made generic (dispatch on `step_mode`). Don't accidentally truncate the end-of-config or ITI logic. The plan's code snippets are abbreviated — the actual implementation must include the full method.

### 9. `trial_num += 1` Duplication

**Severity: LOW (but contributes to fragility)**

Every paradigm's `prepare_trial()` starts with `self.trial_num += 1`. This is boilerplate that could be in the main loop instead. Phase 1 moves `_last_two_levels` tracking to the main loop but doesn't address `trial_num`. If a subclass forgets to increment `trial_num`, trial counting breaks silently.

**Mitigation:** Move `self.trial_num += 1` to the main loop, before `prepare_trial()`. This is a small Phase 1 addition (one line in the loop, remove one line from each of the 10 `prepare_trial()` methods). Worth doing for consistency and to prevent future bugs.

### 10. Tk Root Conflicts Between Controller and OperatorDisplay Singleton

**Severity: LOW**

`operator_gui.py` has a module-level `_tk_hidden_root` singleton that creates a hidden `tk.Tk()` for the operator display's Toplevel. Phase 5's ExperimentController also creates `tk.Tk()` as the session root. If both execute, there are two Tk roots — which can cause instability, especially on macOS.

**Mitigation:** When the controller exists, it passes `parent=self.root` to OperatorDisplay, bypassing the hidden root entirely. The singleton pattern should detect this: if `parent` is provided, don't create `_tk_hidden_root`. When running standalone via `test_*.py` (no controller), the existing singleton path works as before.

### 11. Tier 2 Test Speed

**Severity: LOW**

Even with `headless=True` skipping audio and waits, each paradigm run still executes `prepare_trial()` (builds numpy waveforms), manages DataFrames, and runs psychometric fitting. A single-config PTA run is ~20-30 trials. With 11 paradigms × 3 seeds in convergence tests = 33 test runs. Each run takes ~1-2 seconds of pure Python. Total: ~30-60 seconds for Tier 2 alone.

This is acceptable for local testing but slow for rapid iteration. If it becomes a problem, adding a `max_trials` cap to headless mode (e.g., force end after 30 trials) would help.

### 12. MockParticipant Threshold Units Post-PTA dB Switch

**Severity: LOW**

After Phase 1, PTA's inner var is `trial_level_dB` in dB FS. MockParticipant's threshold must also be in dB FS (e.g., `-30.0`). For multiplicative paradigms (AM), the threshold is in native units (e.g., `10.0` percent). The `_p_detect()` logistic function compares `stimulus_level` to `threshold` — these must be in the same units.

This is already handled correctly in the Phase 6 tolerance table, but it's an easy mistake when writing new tests. Someone might set a PTA MockParticipant threshold to `0.01` (the old linear amplitude convention) instead of `-40.0` (dB FS equivalent).

**Mitigation:** Document the expected units clearly in MockParticipant's docstring and in test_params.py. Add a comment next to each threshold value: `threshold=-30.0  # dB FS`.

---

## Summary of Adversarial Findings

| # | Issue | Severity | Action needed |
|---|---|---|---|
| 1 | ILD/ITD PsychoPy hard dependency in headless mode | HIGH | Guard Sound creation in prepare_trial with headless check |
| 2 | Dynamic setattr/getattr fragility | MEDIUM | Add attribute existence validation in __init__ |
| 3 | Phase 4→1 merge conflict risk | MEDIUM | Re-audit affected files after Phase 4 completes |
| 4 | wait_variable() macOS risk | MEDIUM | Test early in Phase 2, have fallback plan |
| 5 | No pre-refactor baseline data | MEDIUM | Run all paradigms once and save CSVs before Phase 1 |
| 6 | data property before main() | LOW | Document constraint |
| 7 | Registry/test script divergence | LOW | Import from registry immediately |
| 8 | update_trial_params() full scope | MEDIUM | Don't truncate — preserve complete method |
| 9 | trial_num += 1 duplication | LOW | Move to main loop in Phase 1 |
| 10 | Tk root conflicts | LOW | Controller passes parent, singleton detects |
| 11 | Tier 2 test speed | LOW | Accept for now, add max_trials if needed |
| 12 | MockParticipant threshold units | LOW | Document expected units clearly |

**Highest priority actions before starting Phase 1:**
1. Save pre-refactor baseline CSV data (issue #5)
2. Plan for Phase 4 file change accounting (issue #3)
3. Decide whether to move `trial_num += 1` to main loop (issue #9 — small but affects all paradigm files, best done as part of Phase 1 boilerplate removal)
