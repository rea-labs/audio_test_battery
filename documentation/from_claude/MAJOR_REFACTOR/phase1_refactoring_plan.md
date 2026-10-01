# Phase 1 Refactoring Plan — Boilerplate Consolidation + Cleanup

*2026-03-29 (rev 3) | PROLACTIN codebase refactoring*

---

## Goal

Consolidate ~80% of duplicated paradigm subclass code into `AdaptiveParadigm`, reorganize it with clear internal structure, switch PTA to dB FS tracking, and fix known minor issues — all without changing runtime behavior.

**After Phase 1:**
- `AdaptiveParadigm` remains the single base class, reorganized into clearly separated sections (GUI, data, adaptive logic, template main)
- Generic default implementations for `adapt_difficulty()`, `initialize_adaptive_param()`, `reset_to_midpoint_value()`, `update_trial_params()`, `get_log_data()` handle both linear and multiplicative step modes
- Each paradigm subclass shrinks from ~300 lines to ~60-100 lines (just `__init__` + `prepare_trial()` + paradigm-specific overrides)
- PTA tracks `trial_level_dB` (dB FS) instead of linear amplitude — fits generic linear stepping, ready for CalibrationManager offset later
- `db2amp()`/`amp2db()` moved to shared utility module
- Package structure formalized with `__init__.py`

---

## Prerequisite: File Freshness

Before starting, ensure all project files are up to date from local working copies. Verify key signatures from `session_changelog_2026-03-26_session_02.md`.

---

## Step 1: Utilities + Package Structure

### 1a: Create `utils/audio_math.py`

Extract `db2amp()` and `amp2db()` from `TrialPlayer` into a shared module.

```python
# utils/audio_math.py
import numpy as np

def db2amp(db):
    """Convert dB to linear amplitude. 0 dB = 1.0."""
    return 10 ** (db / 20.0)

def amp2db(amp):
    """Convert linear amplitude to dB. 1.0 = 0 dB."""
    return 20.0 * np.log10(amp) if amp > 0 else -np.inf
```

Add backward-compatible aliases on `TrialPlayer`:
```python
# trial_player.py
from utils.audio_math import db2amp, amp2db

class TrialPlayer:
    # Keep static methods as aliases so existing code doesn't break
    db2amp = staticmethod(db2amp)
    amp2db = staticmethod(amp2db)
```

### 1b: Add `__init__.py` files

Create empty `paradigms/__init__.py` and `utils/__init__.py` to formalize package structure.

**Expected directory layout:**
```
project_root/
  paradigms/
    __init__.py
    adaptive_paradigm.py
    paradigm_am.py
    paradigm_dli.py
    paradigm_fm.py
    paradigm_gap.py
    paradigm_ifmc.py
    paradigm_ild.py
    paradigm_itd.py
    paradigm_ldl.py
    paradigm_pta.py
    paradigm_tmc.py
  utils/
    __init__.py
    varspec.py
    standard_frequencies.py
    paradigm_setup_dialog.py
    result_loader.py
    participant_id_helper.py
    audio_math.py             # NEW
    calibration.py            # Phase 4 (later)
  config/
    DEFAULTS.py
  test_am.py
  test_dli.py
  ...
  trial_player.py
  event_gen.py
  operator_gui.py
```

---

## Step 2: Reorganize `AdaptiveParadigm` Internal Structure

No behavior change — just reorder methods and add section headers for readability. The file currently intermixes GUI code, data code, adaptive logic, and the main loop. Reorganize into clearly labeled sections:

```python
class AdaptiveParadigm:

    # ============================================================
    # CONSTRUCTOR
    # ============================================================
    def __init__(self, ...): ...

    # ============================================================
    # ABSTRACT / OVERRIDE METHODS (subclass contract)
    # ============================================================
    def prepare_trial(self): ...       # REQUIRED override
    # get_log_data() — now has a generic default, override optional
    # adapt_difficulty() — now has a generic default, override optional
    # initialize_adaptive_param() — now has a generic default, override optional

    # ============================================================
    # CONFIG + VARIABLE MANAGEMENT
    # ============================================================
    def _setup_variable_looping(self): ...
    def set_current_config(self, idx): ...

    # ============================================================
    # GENERIC ADAPTIVE DEFAULTS (step_mode dispatch)
    # ============================================================
    def initialize_adaptive_param(self): ...
    def adapt_difficulty(self, direction): ...
    def reset_to_midpoint_value(self): ...
    def get_log_data(self): ...

    # ============================================================
    # PARTICIPANT GUI
    # ============================================================
    def get_response(self, trial_playing): ...
    def update_gui_state(self, trial_playing): ...
    def show_false_positive_warning(self): ...

    # ============================================================
    # ADAPTIVE LOGIC (catch trials, streaks, reversals, fitting)
    # ============================================================
    def determine_catch_trial(self): ...
    def check_answer(self): ...
    def update_counters(self): ...
    def check_trial_conds(self): ...
    def update_trial_params(self): ...
    def check_paradigm_end_conds(self): ...
    def _clip_adaptive_param(self): ...
    def notify_wrv_limit(self): ...
    def fit_psychometric_function(self): ...
    def _reset_trial_state(self): ...
    def play_demo_trial(self): ...

    # ============================================================
    # DATA LOGGING
    # ============================================================
    def log_data(self): ...
    def write_data_to_disk(self): ...
    def _temp_data_path(self): ...
    def _write_temp_data(self): ...
    def _delete_temp_data(self): ...

    # ============================================================
    # AUDIO PLAYBACK
    # ============================================================
    def execute_trial(self): ...

    # ============================================================
    # MAIN LOOP
    # ============================================================
    def main(self): ...
```

This is purely organizational — no code changes, just method reordering and section comments.

---

## Step 3: Add Generic Defaults to `AdaptiveParadigm`

This is the core of the refactoring. Add `step_mode` dispatch so the five most-duplicated methods have working defaults in the base class. Subclasses only override when they genuinely need different behavior.

### Setup in `__init__()` (new lines):

```python
# Determine step mode and adaptive attribute name from inner var config
self._step_mode = 'linear'  # default
if isinstance(self.inner_var.data, dict):
    self._step_mode = self.inner_var.data.get('step_mode', 'linear')

# The attribute that gets adapted is always inner_var.name
# e.g., 'mod_ind', 'trial_level_dB', 'gap_duration', etc.
self._adaptive_attr = self.inner_var.name
self._last_two_levels = []
```

### Generic `initialize_adaptive_param()`:

```python
def initialize_adaptive_param(self):
    """
    Set initial adaptive parameter from inner var config.
    Handles both linear and multiplicative randomization.
    Subclasses can override if they need different initialization.
    """
    if not isinstance(self.inner_var.data, dict):
        return

    base_start = self.inner_var.data.get('start', 1.0)
    randomize_factor = self.inner_var.data.get('randomize_factor', None)
    min_val = self.inner_var.data.get('min', None)
    max_val = self.inner_var.data.get('max', None)

    if randomize_factor is not None and randomize_factor > 1.0:
        if self._step_mode == 'multiplicative':
            # Randomize in log space
            multiplier = random.uniform(1.0 / randomize_factor, randomize_factor)
            start_val = base_start * multiplier
        else:
            # Randomize in linear space
            offset = random.uniform(-randomize_factor, randomize_factor)
            start_val = base_start + offset
    else:
        start_val = base_start

    # Clip to range
    if min_val is not None:
        start_val = max(start_val, min_val)
    if max_val is not None:
        start_val = min(start_val, max_val)

    setattr(self, self._adaptive_attr, start_val)
    self._last_two_levels = []
```

### Generic `adapt_difficulty(direction)`:

```python
def adapt_difficulty(self, direction):
    """
    Adjust adaptive parameter. Dispatches on step_mode.

    For multiplicative paradigms, step values are factors (e.g. 0.5, 2.0).
    Initial steps (before first reversal) are more aggressive than final
    steps (after first reversal):
      - step_down 0.5 -> 0.7 : halve -> 30% reduction  (coarse -> fine)
      - step_up   2.0 -> 1.4 : double -> 40% increase   (coarse -> fine)

    For linear paradigms, step values are added directly (e.g. -10, +10 dB).
    Same initial/final logic applies.

    Subclasses can override if they need fundamentally different stepping.
    """
    d = self.inner_var.data if isinstance(self.inner_var.data, dict) else {}
    val = getattr(self, self._adaptive_attr)

    if self.total_num_reversals == 0:
        step_down = d.get('step_down_initial',
                          0.5 if self._step_mode == 'multiplicative' else -10)
        step_up = d.get('step_up_initial',
                        2.0 if self._step_mode == 'multiplicative' else 10)
    else:
        step_down = d.get('step_down_final',
                          0.7 if self._step_mode == 'multiplicative' else -2)
        step_up = d.get('step_up_final',
                        1.4 if self._step_mode == 'multiplicative' else 2)

    if self._step_mode == 'multiplicative':
        if direction == "harder":
            val *= step_down
        elif direction == "easier":
            val *= step_up
    else:  # linear
        if direction == "harder":
            val += step_down  # negative for linear (e.g. -10 dB)
        elif direction == "easier":
            val += step_up

    # Clip to range
    min_val = d.get('min')
    max_val = d.get('max')
    if min_val is not None:
        val = max(val, min_val)
    if max_val is not None:
        val = min(val, max_val)

    setattr(self, self._adaptive_attr, val)
```

### Generic `reset_to_midpoint_value()`:

Replaces per-paradigm `reset_to_midpoint_amplitude()`, `reset_to_midpoint_mod_ind()`, etc.

```python
def reset_to_midpoint_value(self):
    """Reset adaptive param to midpoint of last two presented levels.
    Geometric mean for multiplicative, arithmetic mean for linear."""
    if len(self._last_two_levels) == 2:
        a, b = self._last_two_levels
        if self._step_mode == 'multiplicative':
            midpoint = np.sqrt(a * b)
        else:
            midpoint = (a + b) / 2.0
        setattr(self, self._adaptive_attr, midpoint)
```

### Generic `update_trial_params()`:

Replaces the per-paradigm overrides that all do the same midpoint-reset-then-super() pattern.

```python
def update_trial_params(self):
    """Handle midpoint reset + difficulty adjustment + config transitions."""
    if self.reset_to_midpoint:
        self.reset_to_midpoint_value()
        self.reset_to_midpoint = False
        self.make_harder = False
        self.make_easier = False

    if self.make_harder:
        self.adapt_difficulty("harder")
        self._clip_adaptive_param()
        if self._at_wrv_limit:
            self.notify_wrv_limit()
        self.make_harder = False

    elif self.make_easier:
        self.adapt_difficulty("easier")
        self._clip_adaptive_param()
        if self._at_wrv_limit:
            self.notify_wrv_limit()
        self.make_easier = False

    if self.end_config:
        # ... existing threshold estimation + config transition logic
        # (keep as-is for now, restructure in follow-up pass)
```

### Generic `get_log_data()`:

```python
def get_log_data(self):
    """
    Generic log: adaptive param + all outer var values.
    Subclasses can override to add paradigm-specific columns.
    """
    log_dict = {self._adaptive_attr: getattr(self, self._adaptive_attr)}

    for var in self.outer_vars:
        if hasattr(self, var.name):
            log_dict[var.name] = getattr(self, var.name)

    return log_dict
```

### Level tracking in `main()`:

Currently each paradigm manually tracks `last_two_levels` inside `prepare_trial()`. Move this to the main loop, right after `prepare_trial()`:

```python
# In main(), after self.prepare_trial():
if not self.is_catch_trial:
    val = getattr(self, self._adaptive_attr, None)
    if val is not None:
        self._last_two_levels.append(val)
        if len(self._last_two_levels) > 2:
            self._last_two_levels.pop(0)
```

This removes 5-6 duplicated lines from every paradigm's `prepare_trial()`.

### Bug F1 fix (duplicate snapshot):

The duplicate `last_trial_snapshot` block (lines 1216-1222 and 1230-1236) collapses to one copy in `main()`. No extra work — just don't copy the second block when reorganizing.

---

## Step 4: Switch PTA to dB FS Tracking

PTA currently stores `trial_amp` as linear amplitude (0.0-1.0) and applies dB steps via `db2amp()` conversion. This makes it a special case needing its own `adapt_difficulty()` override.

**Change:** PTA's inner var becomes `trial_level_dB` (dB FS), with plain linear dB steps. The `db2amp()` conversion moves to `prepare_trial()`.

**Why this works pre-calibration:** dB FS is well-defined (0 dB FS = full scale digital). PTA thresholds in dB FS are meaningful relative values. When CalibrationManager arrives, dB SPL = dB FS + calibrated offset.

**Updated `test_pta.py` inner var:**
```python
"inner": VarSpec(
    name="trial_level_dB",
    data={
        'start': -6.0,             # dB FS (approx 0.5 amplitude)
        'step_mode': 'linear',
        'step_down_initial': -10,
        'step_down_final': -2,
        'step_up_initial': 10,
        'step_up_final': 2,
        'min': -80.0,              # dB FS (approx 0.0001 amplitude)
        'max': 0.0,                # dB FS (full scale)
    }
)
```

**Updated `paradigm_pta.py` `prepare_trial()`:**
```python
def prepare_trial(self):
    self.trial_num += 1
    if self.is_catch_trial:
        amp = 0.0
    else:
        amp = db2amp(self.trial_level_dB)  # convert dB FS -> linear for audio

    fc = getattr(self, 'fc', 1000.0)
    pan = getattr(self, 'pan', 0)
    self.tp.new_trial(
        wave_type="sin", fc=fc, amp=amp,
        durations=self.trial_dur, fade_time=self.fade_time,
        pan=pan, sample_accurate=False, verbose=False
    )
```

**Result:** PTA uses the generic linear `adapt_difficulty()`. No override needed. All 10 adaptive paradigms share the same implementation.

**CSV output change:** Column changes from `trial_amp` (linear) to `trial_level_dB` (dB FS). Existing CSV data uses the old format — note this in changelog.

**Impact on other code:**
- `ResultLoader` — reads `threshold_dB` from PTA CSVs for IFMC/TMC. The psychometric fit already operates in dB, so values should be consistent. **Must verify.**
- `operator_gui.py` — y-axis on adaptive track plot should pick up inner var name dynamically. Verify it reads `trial_level_dB` for PTA.

---

## Step 5: Slim Down Paradigm Subclasses

Remove boilerplate from each paradigm. After this step, each file contains only:
- `__init__()` — gui_config, paradigm_code, paradigm-specific defaults
- `prepare_trial()` — stimulus construction (always paradigm-specific)
- Overrides only where genuinely needed

### What gets deleted from each multiplicative paradigm (AM, FM, DLI, ILD, ITD):

- `initialize_adaptive_param()` — replaced by generic
- `adapt_difficulty()` — replaced by generic
- `reset_to_midpoint_*()` — replaced by `reset_to_midpoint_value()`
- `update_trial_params()` — replaced by generic (did same thing: midpoint reset + super())
- `get_log_data()` — replaced by generic (logged inner var + outer vars)
- `last_two_levels` tracking in `prepare_trial()` — now in main loop

### What gets deleted from each linear paradigm (PTA, GAP, IFMC, TMC):

- Same five methods (where they exist as overrides)
- PTA additionally loses `adapt_difficulty()` override thanks to dB FS switch

### Paradigms needing special overrides after consolidation:

| Paradigm | Override | Reason |
|---|---|---|
| DLI | `check_answer()` | 3-alternative response format (louder was 1st, 2nd, or same) |
| ILD | `execute_trial()` | Bypasses TrialPlayer, builds stereo array directly |
| ITD | `execute_trial()` | Bypasses TrialPlayer, builds stereo array + delay methods |
| LDL | `check_answer()` | 3-option response (comfortable/loud/uncomfortable) |
| IFMC | (none beyond `prepare_trial()`) | Complex stimulus but generic adaptive logic works |
| TMC | (none beyond `prepare_trial()`) | Same as IFMC |

### Minimal subclass example (AM after consolidation):

```python
class ParadigmAM(AdaptiveParadigm):
    paradigm_code = "AM"

    def __init__(self, params, verbose=False, gui_config=None, participant_id=None):
        if gui_config is None:
            gui_config = {
                'question': "Did you hear AMPLITUDE MODULATION (tremolo/pulsing)?",
                'options': ['No AM (0)', 'Heard AM (1)'],
                'keys': ['0', '1'],
                'window_title': "AM Detection Test",
                'font_size': 16
            }
        super().__init__(params, verbose=verbose, gui_config=gui_config,
                         participant_id=participant_id)
        self.fade_time = 0.05
        self.trial_dur = 2.0

    def prepare_trial(self):
        """Configure AM trial. Catch = pure tone (no modulation)."""
        self.trial_num += 1
        if self.is_catch_trial:
            mod_ind = 0.0
        else:
            mod_ind = self.mod_ind

        tone_amp = getattr(self, 'tone_amp', 0.5)
        fc = getattr(self, 'fc', 1000.0)
        fm = getattr(self, 'fm', 8.0)
        self.tp.new_trial(
            wave_type="am", durations=self.trial_dur,
            fc=fc, fm=fm, mod_ind=mod_ind, amp=tone_amp,
            fade_time=self.fade_time, sample_accurate=False, verbose=False
        )
```

Compare with current AM at ~312 lines.

### Paradigm size summary after consolidation:

| Paradigm | Key contents | Approx lines |
|---|---|---|
| PTA | gui_config, dB FS -> linear in prepare_trial | ~60 |
| AM | gui_config, catch=pure tone | ~60 |
| FM | gui_config, catch=pure tone | ~60 |
| DLI | gui_config, two sequential tones, check_answer override | ~80 |
| GAP | gui_config, noise with gap | ~60 |
| ILD | gui_config, stereo array, execute_trial override | ~100 |
| ITD | gui_config, stereo + delay, execute_trial, ITD-specific methods | ~150 |
| IFMC | gui_config, masker+probe, ResultLoader integration | ~100 |
| TMC | gui_config, masker+probe, ResultLoader integration | ~100 |
| LDL | gui_config, ascending tone, check_answer override | ~80 |

**Total paradigm code: ~850 lines (down from ~3,500).** ~75% reduction.

---

## Step 6: Update `test_*.py` Scripts

Add `'step_mode'` key to all inner var dicts. Fix AM start value.

**Multiplicative paradigms (AM, FM, DLI, ILD, ITD):**
```python
"inner": VarSpec(
    name="mod_ind",
    data={
        'start': 16.0,                        # AM: changed from 50.0
        'step_mode': 'multiplicative',         # NEW
        'step_down_initial': 0.5,
        'step_down_final': 0.7,
        'step_up_initial': 2.0,
        'step_up_final': 1.4,
        'min': 1.0,
        'max': 100.0,
        'randomize_factor': 1.2
    }
)
```

**Linear paradigms (GAP, IFMC, TMC, LDL) — add `step_mode`:**
```python
'step_mode': 'linear',                 # NEW (default, but explicit for clarity)
```

**PTA — updated to dB FS (see Step 4)**

### AM start value discrepancy

`test_am.py` has `start=50.0`, `paradigm_am.py` `__main__` uses `start=16.0`. Prague convention is 16%. **Recommend `start=16.0`.** With `randomize_factor=1.2`, actual start ranges ~13-19%. **Confirm with team.**

---

## Step 7: Update `operator_gui.py`

Minimal changes:
- Verify y-axis label on adaptive track picks up inner var name dynamically (should already work)
- Confirm it displays `trial_level_dB` for PTA instead of `trial_amp`
- No structural changes needed

---

## Implementation Order

| # | Task | Files touched | Risk | Effort |
|---|------|--------------|------|--------|
| 1 | Create `utils/audio_math.py`; add aliases on TrialPlayer | `audio_math.py` (new), `trial_player.py` | Very low | 15 min |
| 2 | Create `paradigms/__init__.py`, `utils/__init__.py` | New files | Very low | 5 min |
| 3 | Reorganize `AdaptiveParadigm` sections (no behavior change) | `adaptive_paradigm.py` | Low | 1 hr |
| 4 | Add `step_mode` dispatch + generic defaults to `AdaptiveParadigm` (`initialize_adaptive_param`, `adapt_difficulty`, `reset_to_midpoint_value`, `update_trial_params`, `get_log_data`); add level tracking + fix snapshot duplication in `main()` | `adaptive_paradigm.py` | Medium | 2-3 hr |
| 4v | **Verify:** Run PTA + AM + LDL. Confirm adaptive tracking, midpoint resets, threshold estimation match pre-refactor behavior. | — | — | 30 min |
| 5 | Switch PTA to dB FS tracking | `paradigm_pta.py`, `test_pta.py` | Low-medium | 1 hr |
| 5v | **Verify:** Run PTA. Check CSV has `trial_level_dB`. Run IFMC/TMC to verify ResultLoader still loads thresholds correctly. | — | — | 30 min |
| 6 | Slim down all paradigm subclasses | All `paradigm_*.py` | Medium | 3-4 hr |
| 7 | Update `test_*.py` — add `step_mode`, fix AM start | All `test_*.py` | Low | 1 hr |
| 8 | **Verify:** Run all 11 paradigms (short runs, 3-5 configs). Compare CSV output with pre-refactor baseline. | — | — | 1-2 hr |

**Total estimate:** ~10-12 hours across 2-3 focused sessions.

---

## Verification Strategy

- **Steps 1-3:** No behavior change. Quick import/run check.
- **Step 4 (generic defaults):** Run PTA (linear), AM (multiplicative), LDL (ascending-only). Verify adaptive tracking, midpoint resets, threshold estimation produce identical results to pre-refactor.
- **Step 5 (PTA dB FS):** Run PTA. Confirm CSV column is `trial_level_dB`, thresholds in dB FS, operator display y-axis correct. Run IFMC or TMC to verify ResultLoader compatibility.
- **Steps 6-7 (slim subclasses):** Run all 11 paradigms, short runs. Compare CSV output structure column-for-column.

---

## Open Questions (resolve during implementation)

1. **ResultLoader + PTA dB switch** — ResultLoader reads `threshold_dB` from PTA CSVs for IFMC/TMC probe levels. The psychometric fit already works in dB internally, so threshold values should be consistent after the switch. **Must verify during Step 5v.**

2. **AM `start` value** — `test_am.py` has `start=50.0`, Prague convention is `16.0`. Recommend 16.0. **Confirm with team.**

3. **Config transition logic in `update_trial_params()`** — the `end_config` block (~80 lines) mixes threshold fitting with config management. Keep as-is for now. Restructure in a later pass.

4. **`play_demo_trial()`** — stays on AdaptiveParadigm. Uses `_reset_trial_state()`. The setup dialog calls `paradigm.play_demo_trial(demo_vals)` without needing to know the concrete type.

5. **LDL** — fits the generic linear pattern. `step_down=-3` is never triggered. No special handling beyond existing `check_answer()` override.

---

## What This Does NOT Cover (deferred)

- **Phase 2:** ParticipantGUI extraction (separate class, injectable for NiceGUI migration + headless mode)
- **Phase 3:** DataManager extraction (separate class)
- **Phase 4:** CalibrationManager + TrialPlayer integration — **Eric plans to do this before Phase 1; changes to `trial_player.py`, `paradigm_ifmc.py`, `paradigm_tmc.py`, and new `utils/calibration.py` will need to be accounted for**
- **Phase 5:** ExperimentController (top-level orchestrator, owns Tk mainloop)
- **Phase 6:** Headless mode / MockParticipant / automated tests
- NiceGUI migration
- FM mod_ind formula fix (team review needed)

---

## Appendix: Step Config Audit (2026-03-29)

All inner var configs verified across `test_*.py` files:

**Multiplicative paradigms** (AM, FM, DLI, ILD, ITD):
- All use identical step pattern: 0.5x/2.0x initial, 0.7x/1.4x final
- Initial steps are more aggressive (halve/double), final steps are finer (30%/40% change)
- Note: the *number* increases from 0.5 to 0.7 for step_down, but the *change magnitude* decreases — this is correct but unintuitive; warrants a comment in the code

**Linear paradigms** (PTA, IFMC, TMC):
- All use +/-10 dB initial, +/-2 dB final

**GAP** — linear in seconds: +/-5 ms initial, +/-1 ms final

**LDL** — ascending only: +3 dB always, step_down=-3 dB (never triggered)

**No inconsistencies found** except the AM start value discrepancy (50 vs 16).
