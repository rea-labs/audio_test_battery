# Phase 6 Refactoring Plan — Testing Infrastructure

*2026-03-29 | PROLACTIN codebase refactoring*

**Depends on:** Phases 1-3 complete (Phase 2 is critical — MockParticipantGUI enables headless mode). Phase 4 (CalibrationManager) and Phase 5 (ExperimentController) are helpful but not blocking.

**Reference:** `PROLACTIN_testing_plan_v2.md` and `PROLACTIN_human_test_checklists.md` contain the detailed test designs. This plan focuses on implementation — what to build and in what order — rather than re-specifying the tests.

---

## Goal

Build the automated testing infrastructure so all 11 paradigms can be validated without a human in the loop. This includes headless mode, MockParticipant classes, and a three-tier pytest suite covering logic, integration, and stimulus validation.

**After Phase 6:**
- Any paradigm can run headlessly by injecting `MockParticipantGUI`
- `MockParticipant` simulates a listener with a known threshold
- ~30 pytest tests cover adaptive logic, convergence, CSV output, and stimulus math
- Human test checklists (H1-H6) remain for audio quality and UX validation — no code needed for those

---

## How Phase 2 Makes Headless Mode Free

The testing plan v2 proposed adding `headless=True` flags (~30 lines across 4-5 methods). Post-Phase 2, this is unnecessary. Headless mode is just dependency injection:

```python
# Headless paradigm run — no flags, no conditional branches
mock_gui = MockParticipantGUI(response_fn=mock_participant)
data_manager = DataManager("TEST001", "PTA", output_dir=tmp_dir)

paradigm = ParadigmPTA(params, verbose=False,
                       participant_id="TEST001",
                       gui=mock_gui,
                       data_manager=data_manager,
                       show_operator_display=False)
paradigm.main()

# Assert on data_manager.data
```

The paradigm's `main()` runs the identical logic path — same catch trial determination, same reversals, same threshold estimation. The only difference is that `gui.get_response()` returns mock values instantly instead of blocking on Tk buttons, and `gui.show_playing()` / `gui.show_fp_warning()` are no-ops.

**One remaining issue: audio playback.** `execute_trial()` calls `self.tp.play_trial()` which plays actual audio via PsychoPy/PTB. In headless mode we want to skip this. Two options:

**(a) Skip in TrialPlayer:** Add `headless` flag to TrialPlayer that skips `Sound.play()` but still builds the numpy waveform (useful for Tier 3 stimulus tests that inspect waveforms).

**(b) Override `execute_trial()` in test fixtures:** The test creates a paradigm subclass (or monkey-patches) that overrides `execute_trial()` to be a no-op. Simpler, but you lose waveform access.

**(c) Skip `core.wait()` too:** The 0.5s pause after playback and the ITI pause between trials add up to ~1s per trial. A 200-trial run takes 200s in real time. For automated tests, these waits should be skipped.

**Recommendation:** Option (a) for TrialPlayer + skip `core.wait()` calls. Add a `headless` flag to `AdaptiveParadigm.__init__()` that:
- Passes `headless=True` to TrialPlayer (skips `Sound.play()` but builds waveform)
- Skips `core.wait()` calls in `main()`/`update_trial_params()`
- Does NOT affect any logic — catch trials, reversals, thresholds all run identically

This is ~15 lines of changes to `adaptive_paradigm.py` and ~5 lines to `trial_player.py`.

---

## Component 1: MockParticipantGUI (already stubbed in Phase 2)

Phase 2 creates the stub. Phase 6 fleshes it out:

```python
class MockParticipantGUI(ParticipantGUI):
    """Returns responses from a callable for headless testing."""

    def __init__(self, response_fn):
        """
        Args:
            response_fn: callable that receives the paradigm instance
                         and returns an int response.
        """
        self._response_fn = response_fn
        self._paradigm = None

    def attach_paradigm(self, paradigm):
        """Called before main loop so response_fn can read paradigm state."""
        self._paradigm = paradigm

    def get_response(self) -> int:
        return self._response_fn(self._paradigm)

    def show_playing(self): pass
    def show_waiting(self): pass
    def show_fp_warning(self): pass
    def show_message(self, text): pass
    def lift(self): pass
    def destroy(self): pass
```

The `attach_paradigm()` call is needed because `MockParticipantGUI` is created before the paradigm, but the response function needs to read paradigm state (current adaptive parameter, catch trial flag). Wire this in `AdaptiveParadigm.main()`:

```python
# In main(), after GUI is set:
if hasattr(self.gui, 'attach_paradigm'):
    self.gui.attach_paradigm(self)
```

---

## Component 2: MockParticipant Response Functions

These simulate listeners with known thresholds. The design from `testing_plan_v2.md` (section 5.2) is already solid. Implementation:

### File: `tests/mock_participant.py`

```python
class MockParticipant:
    """
    Simulates a listener with a known threshold.
    Returns responses based on a psychometric function.
    """

    def __init__(self, threshold, slope=2.0, lapse_rate=0.05, seed=None):
        self.threshold = threshold
        self.slope = slope
        self.lapse_rate = lapse_rate
        self.rng = np.random.default_rng(seed)

    def _p_detect(self, stimulus_level):
        """Logistic psychometric function."""
        return 1.0 / (1.0 + np.exp(
            -self.slope * (stimulus_level - self.threshold)
        ))

    def _apply_lapse(self, p):
        return p * (1 - self.lapse_rate) + (1 - p) * self.lapse_rate

    def __call__(self, paradigm):
        # Catch trials: correct rejection with lapse_rate FP chance
        if paradigm.is_catch_trial:
            return 1 if self.rng.random() < self.lapse_rate else 0

        # Normal trials: probabilistic response
        attr_name = paradigm.inner_var.name
        current_val = getattr(paradigm, attr_name)
        p = self._apply_lapse(self._p_detect(current_val))
        return 1 if self.rng.random() < p else 0


class MockDLI(MockParticipant):
    """DLI: 3-alternative (same / 1st louder / 2nd louder)."""
    def __call__(self, paradigm):
        if paradigm.is_catch_trial:
            return 0  # "Same"
        current_val = getattr(paradigm, paradigm.inner_var.name)
        p = self._apply_lapse(self._p_detect(current_val))
        if self.rng.random() < p:
            return self.rng.choice([1, 2])  # detected, pick interval
        return 0  # "Same"


class MockLDL(MockParticipant):
    """LDL: ascending, 3 options (comfortable/loud/uncomfortable)."""
    def __call__(self, paradigm):
        current_val = getattr(paradigm, paradigm.inner_var.name)
        if current_val >= self.threshold:
            return 2  # Uncomfortable
        elif current_val >= self.threshold * 0.7:
            return 1  # Loud
        return 0  # Comfortable
```

---

## Component 3: Test Fixtures

### File: `tests/conftest.py`

```python
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def tmp_data_dir():
    """Temporary directory for test CSV output."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

@pytest.fixture
def pta_params():
    """Minimal PTA params for testing (single freq, single ear)."""
    return {
        "inner": VarSpec(name="trial_level_dB", data={
            'start': -6.0, 'step_mode': 'linear',
            'step_down_initial': -10, 'step_down_final': -2,
            'step_up_initial': 10, 'step_up_final': 2,
            'min': -80.0, 'max': 0.0,
        }),
        "outer_1": VarSpec(name="fc", data=[1000]),
        "outer_2": VarSpec(name="pan", data=[-1.0]),
    }

# Similar fixtures for each paradigm...

def make_headless_paradigm(cls, params, mock, tmp_dir,
                           participant_id="TEST001"):
    """Helper: create a headless paradigm with all dependencies injected."""
    mock_gui = MockParticipantGUI(response_fn=mock)
    dm = DataManager(participant_id, cls.paradigm_code,
                     output_dir=str(tmp_dir))
    paradigm = cls(params, verbose=False,
                   participant_id=participant_id,
                   gui=mock_gui, data_manager=dm,
                   show_operator_display=False, headless=True)
    mock_gui.attach_paradigm(paradigm)
    return paradigm
```

### File: `tests/test_params.py`

Canonical test parameter dicts for each paradigm — single-config versions (one frequency, one ear) for fast test runs. Imported by test files and conftest fixtures. These mirror the paradigm registry configs but stripped to minimal configs.

---

## Component 4: Test Tiers

### Tier 1 — Unit Tests (pure logic)

These test individual methods on `AdaptiveParadigm` by constructing minimal paradigm instances and calling methods directly. No full `main()` run needed.

| Test file | What it tests |
|---|---|
| `test_unit_reversals.py` | Reversal detection from streak sequences. FP doesn't trigger reversal. |
| `test_unit_catch_trials.py` | Trial 0 never catch, trial 1 always catch, subsequent probabilistic. Rate adaptation after FP. |
| `test_unit_step_sizes.py` | Pre-reversal steps (coarse) vs post-reversal (fine). Linear vs multiplicative dispatch. |
| `test_unit_midpoint.py` | Arithmetic midpoint for linear, geometric for multiplicative. |
| `test_unit_psych_fit.py` | Recovers known threshold from synthetic logistic data. Handles edge cases (all-yes, all-no, <3 points). |
| `test_unit_config_unwrap.py` | Cartesian product of outer vars. Randomization produces different order. Single outer var. No outer vars. |
| `test_unit_wrv_limits.py` | Boundary detection at min/max. Flag set correctly. |

**Key design: `make_minimal_paradigm()` helper.** Creates a paradigm with enough state to call individual methods, without running `main()`:

```python
def make_minimal_paradigm(**overrides):
    """Build a PTA paradigm with minimal config for unit testing."""
    params = {
        "inner": VarSpec(name="trial_level_dB", data={
            'start': -6.0, 'step_mode': 'linear',
            'step_down_initial': -10, 'step_down_final': -2,
            'step_up_initial': 10, 'step_up_final': 2,
            'min': -80.0, 'max': 0.0,
        }),
        "outer_1": VarSpec(name="fc", data=[1000]),
    }
    p = ParadigmPTA(params, verbose=False,
                    show_operator_display=False)
    # Apply overrides
    for k, v in overrides.items():
        setattr(p, k, v)
    return p
```

**Estimated: 7 test files, ~200 lines total, ~15 test functions.**

### Tier 2 — Integration Tests (headless full runs)

These run complete paradigms headlessly with MockParticipant and assert on the output data.

| Test file | What it tests |
|---|---|
| `test_integration_convergence.py` | Each paradigm converges to mock threshold (±tolerance). Parametrized across all 11. |
| `test_integration_csv_output.py` | CSV has required columns. Threshold on last row only. Correct answer classifications. |
| `test_integration_crash_recovery.py` | Temp CSV exists mid-run. Deleted on clean completion. |
| `test_integration_multi_config.py` | Multi-config run produces correct number of configs. Config randomization changes order. |
| `test_integration_result_loader.py` | Write PTA CSV, load via ResultLoader, thresholds match. |
| `test_integration_threshold_import.py` | Write fake PTA CSV, verify IFMC/TMC ResultLoader picks up correct thresholds. |

**The convergence test is the most important.** It validates the entire adaptive pipeline end-to-end. Expected tolerances:

| Paradigm | Mock threshold | Tolerance | Notes |
|---|---|---|---|
| PTA | -30.0 dB FS | ±5 dB | Linear stepping, 2 dB final steps |
| AM | 10.0 % | ±factor of 2 | Multiplicative, log-space comparison |
| FM | 4.0 % | ±factor of 2 | Same as AM |
| GAP | 0.004 s | ±factor of 2 | Multiplicative |
| DLI | 2.0 dB | ±factor of 2 | Multiplicative |
| ILD | 3.0 dB | ±factor of 2 | Multiplicative |
| ITD | 0.1 ms | ±factor of 2 | Multiplicative |
| IFMC | 40.0 dB | ±5 dB | Linear |
| TMC | 30.0 dB | ±5 dB | Linear |
| LDL | -3.0 dB FS | ±3 dB | Ascending only, first "uncomfortable" |

Tolerances are deliberately loose — we're testing that the adaptive machinery converges in the right direction, not that it hits exact thresholds. Precision depends on step sizes and trial count, which are protocol decisions, not bugs.

**Estimated: 6 test files, ~300 lines total, ~20 test functions.**

### Tier 3 — Stimulus Validation (numerical waveform checks)

These import `EventGen` directly, generate raw numpy waveforms, and verify mathematical properties. They do NOT require headless paradigm runs.

| Test file | What it tests |
|---|---|
| `test_stimulus_tone.py` | FFT peak at requested frequency ±2 Hz |
| `test_stimulus_am.py` | Hilbert envelope modulation depth matches mod_ind ±5% |
| `test_stimulus_fm.py` | Instantaneous frequency deviation matches expected range |
| `test_stimulus_gap.py` | Silent region at correct position and duration ±1 sample |
| `test_stimulus_fades.py` | Onset/offset ramps: first/last samples near zero, no clicks |
| `test_stimulus_ild.py` | Channel amplitude ratio matches requested ILD ±0.5 dB |
| `test_stimulus_itd.py` | Cross-correlation peak offset matches requested ITD ±1 sample |

**PsychoPy dependency:** `EventGen.__init__` imports PsychoPy (for Sound objects). Tier 3 tests use `return_dict=True` to get raw numpy arrays, but PsychoPy must be installed. This is acceptable since tests run on Eric's machine. Long-term, EventGen could be refactored to separate numpy waveform generation from Sound object creation, but that's out of scope here.

**Estimated: 7 test files, ~250 lines total, ~15 test functions.**

---

## Component 5: Headless Flags

Minimal additions to support skipping audio and waits:

### `adaptive_paradigm.py` — add `headless` param:

```python
def __init__(self, ..., headless=False):
    ...
    self.headless = headless

# In main() / run_trial_loop():
if not self.headless:
    core.wait(0.5)   # skip in headless

# In execute_trial():
def execute_trial(self):
    self.trial_repeats += 1
    if not self.headless:
        self.tp.play_trial()

# In update_trial_params() ITI:
if not self.headless:
    core.wait(iti_pre)
    # ... gui state update ...
    core.wait(iti_post)
```

### `trial_player.py` — optional waveform-only mode:

Not strictly needed for Phase 6 (since `execute_trial()` is skipped entirely in headless mode). But useful if we later want Tier 3 tests to run through `prepare_trial()`:

```python
class TrialPlayer:
    def __init__(self, ..., headless=False):
        self.headless = headless

    def play_trial(self):
        if self.headless:
            return  # waveforms built by new_trial(), just don't play
        # ... existing playback code ...
```

---

## File Structure

```
project_root/
  tests/
    __init__.py
    conftest.py                    # fixtures, make_headless_paradigm helper
    mock_participant.py            # MockParticipant + subclasses
    test_params.py                 # canonical minimal param dicts

    # Tier 1
    test_unit_reversals.py
    test_unit_catch_trials.py
    test_unit_step_sizes.py
    test_unit_midpoint.py
    test_unit_psych_fit.py
    test_unit_config_unwrap.py
    test_unit_wrv_limits.py

    # Tier 2
    test_integration_convergence.py
    test_integration_csv_output.py
    test_integration_crash_recovery.py
    test_integration_multi_config.py
    test_integration_result_loader.py
    test_integration_threshold_import.py

    # Tier 3
    test_stimulus_tone.py
    test_stimulus_am.py
    test_stimulus_fm.py
    test_stimulus_gap.py
    test_stimulus_fades.py
    test_stimulus_ild.py
    test_stimulus_itd.py

  test_data_automated/             # gitignored, output from automated tests
```

---

## Implementation Order

| # | Task | Effort |
|---|------|--------|
| 1 | Add `headless` flag to `AdaptiveParadigm` (skip audio, skip waits) | 30 min |
| 2 | Flesh out `MockParticipantGUI` (attach_paradigm hook) | 30 min |
| 3 | Create `tests/mock_participant.py` (MockParticipant + DLI/LDL/GAP subclasses) | 1 hr |
| 4 | Create `tests/conftest.py` + `tests/test_params.py` (fixtures, minimal param dicts) | 1 hr |
| 4v | **Verify:** Run one headless PTA paradigm from a pytest test. Confirm it completes, produces data, no Tk or audio. | 30 min |
| 5 | Write Tier 1 unit tests (7 files, ~15 tests) | 3 hr |
| 6 | Write Tier 2 integration tests (6 files, ~20 tests) | 3-4 hr |
| 7 | Write Tier 3 stimulus tests (7 files, ~15 tests) | 2-3 hr |
| 8 | **Verify:** `pytest tests/` — all green. Fix any failures. | 1-2 hr |

**Total estimate:** ~13-16 hours across 2-3 sessions.

---

## Verification Strategy

- **Step 4v (headless smoke test):** The single most important check. Create a PTA paradigm with MockParticipant (threshold=-30 dB), run `paradigm.main()` in a pytest test. Assert: no Tk window appears, no audio plays, data has >10 trials, threshold_dB is populated and within ±10 dB of -30. If this works, everything else is just writing more tests.
- **Step 8 (full suite):** `pytest tests/ -v`. All tests should pass. Convergence tests may need tolerance tuning based on actual results — run with a fixed seed first, then add a few different seeds to catch edge cases.

---

## Open Questions

1. **PsychoPy import for Tier 3.** `EventGen` imports PsychoPy at module level. Tier 3 tests need EventGen but not PsychoPy's audio backend. For now, accept that PsychoPy must be installed to run Tier 3 tests. Long-term, refactoring EventGen to separate waveform generation (numpy-only) from Sound object wrapping would remove this dependency. Not in scope for Phase 6.

2. **`prepare_trial()` in headless mode.** With `headless=True` and `execute_trial()` skipped, `prepare_trial()` still calls `self.tp.new_trial(...)` which builds numpy waveforms and PsychoPy Sound objects. This is wasted work in Tier 2 tests (we don't inspect waveforms). Options: (a) accept the overhead — it's fast enough for ~200 trials; (b) add a `headless` flag to TrialPlayer that skips Sound object creation. **Recommend (a)** for now. If tests are slow, add (b) later.

3. **Convergence test seeds.** Using `seed=42` makes tests deterministic but only validates one random path. Using multiple seeds (e.g., parametrize over `[42, 123, 456]`) increases coverage but triples test time. **Recommend single seed for CI, multi-seed for pre-release validation.**

4. **Human test checklists (H1-H6).** These are already complete in `PROLACTIN_human_test_checklists.md`. No code changes needed — print and run. The team should run H1 (audio spot-check) and H2 (adaptive tracking) before trusting automated test results, since the automated tests don't verify audio quality.

5. **FM mod_ind formula.** The testing plan flagged this as Q4: the FM implementation might be wrong (phase modulation vs frequency deviation). Tier 3's `test_stimulus_fm.py` should verify the frequency deviation range, which will either confirm or definitively identify the bug. This is a good candidate for the first Tier 3 test to write.

---

## Interaction with Other Phases

**Phase 1 (boilerplate consolidation):** Generic `adapt_difficulty()` and `get_log_data()` means test fixtures don't need per-paradigm setup — the same `make_headless_paradigm()` helper works for all 11.

**Phase 2 (ParticipantGUI):** Enables headless mode via injection. Without Phase 2, headless mode requires the `headless=True` flag approach from the original testing plan (~30 lines of conditionals). With Phase 2, it's clean injection with zero conditionals in paradigm code.

**Phase 3 (DataManager):** Tests inject `DataManager(output_dir=tmp_dir)` so test output goes to a temporary directory. Assert on `data_manager.data` in-memory rather than reading CSVs from disk.

**Phase 5 (ExperimentController):** Full integration tests can create an ExperimentController with MockParticipantGUI, run a multi-paradigm session headlessly, and verify session log + CSV output. This is the capstone test but depends on Phase 5 being complete.
