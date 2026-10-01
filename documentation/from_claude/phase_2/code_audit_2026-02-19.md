# PROLACTIN Code Audit — 2026-02-19

Full audit of the codebase, implementation plan, and documentation alignment.

---

## 1. CRITICAL BUGS & CORRECTNESS ISSUES

### 1.1 IFMC and TMC have dead `update_streaks_and_difficulty()` methods

Both `paradigm_ifmc.py` (line 248) and `paradigm_tmc.py` (line 209) define `update_streaks_and_difficulty()`, but **this method is never called by the base class**. The base class uses `update_counters()` + `check_trial_conds()` + `adapt_difficulty()`. These dead methods contain alternative streak/difficulty logic (including resetting `current_streak = 0` on correct, which contradicts the base class behavior), but they never execute.

**Impact:** The IFMC/TMC adaptive tracking relies entirely on the base class's `update_counters()` and `check_trial_conds()`, which happen to produce identical behavior for the default 1-up/1-down case. But these dead methods suggest the original intent was different logic. If you ever change `target_streak_correct`, the dead methods would be out of sync and confusing.

**Fix:** Delete `update_streaks_and_difficulty()` from both files — they're unused and misleading.

### 1.2 IFMC/TMC `check_answer()` duplicates base class logic

Both IFMC (`paradigm_ifmc.py:170`) and TMC (`paradigm_tmc.py:179`) override `check_answer()` to do the *exact same thing* the base class already does (classify 0→No, 1→Yes into TP/FN/TN/FP). The only addition is `if self.user_input == "repeat": return`, which the base class doesn't have — but that check belongs in the base class anyway, not duplicated in subclasses.

**Fix:** Add the `repeat` guard to `AdaptiveParadigm.check_answer()` and remove the overrides.

### 1.3 FM `mod_ind` mismatch between paradigm and `event_gen`

`paradigm_fm.py` treats `mod_ind` as **percent frequency deviation** (e.g., 8% → `mod_ind=8.0`), and the docstring says `f(t) = fc + (fc * mod_ind/100) * sin(...)`. But `event_gen.py:105` uses `mod_ind` as the **raw modulation index in radians**: `wave = amp * sin(2π·fc·t + mod_ind * sin(2π·fm·t))`. There's no `/100` division, and the formula is phase modulation, not frequency deviation.

So when the paradigm passes `mod_ind=8.0` (meaning "8% frequency deviation"), event_gen interprets it as β=8.0 radians of phase modulation, which produces *massive* frequency excursions (way beyond 8%). These are two completely different quantities.

**Impact:** FM stimuli are probably wildly wrong. A `mod_ind` of 8 radians produces a frequency deviation of `8 × fm` Hz (e.g., 8 × 4 = 32 Hz deviation for fm=4 Hz carrier), which at fc=1000 Hz is 3.2%, not 8%. Worse, halving `mod_ind` to 4 radians doesn't halve the perceived deviation in a psychoacoustically meaningful way.

**Fix:** Either:
- (a) Change `event_gen.fm()` to use `mod_ind` as percent: `delta_f = fc * mod_ind/100`, then do proper FM synthesis with frequency integration, or
- (b) Add a `fm_percent_to_beta()` conversion in the paradigm's `prepare_trial()`.

### 1.4 `event_gen.py` imports from `config.DEFAULTS` but `trial_player.py` uses inline DEFAULTS

`event_gen.py:20` does `from config.DEFAULTS import DEFAULTS`, suggesting a `config/` package. But `trial_player.py:19` defines its own inline `DEFAULTS` dict. Meanwhile `DEFAULTS.py` exists at the project root (not inside `config/`). This means:
- `event_gen.py` will crash with `ModuleNotFoundError: No module named 'config'` unless you have a `config/` directory with `__init__.py` and `DEFAULTS.py`.
- Even if it works via path hacking, the two DEFAULTS dicts are different and could diverge.

**Fix:** Consolidate to a single `DEFAULTS.py` at project root, imported uniformly by both files.

### 1.5 Import paths are inconsistent and probably broken

- Paradigm files import `from paradigms.adaptive_paradigm import AdaptiveParadigm` — implies a `paradigms/` package directory.
- Test files import `from paradigms.paradigm_ifmc import ParadigmIFMC` and `from utils.varspec import VarSpec` — implies `utils/` package.
- But the project root shows `adaptive_paradigm.py`, `varspec.py`, etc. as flat files, not inside `paradigms/` or `utils/` directories.
- `trial_player.py` imports `import event_gen` (flat), while paradigm files import from `paradigms.` (packaged).

**Impact:** The code as uploaded cannot run without a specific directory layout that isn't represented in the project files. There's likely a local directory structure with `paradigms/` and `utils/` subdirectories containing these files or symlinks, but it's not documented.

**Fix:** Document the expected directory layout, or better yet, consolidate imports to work with a flat structure during development.

### 1.6 `event_gen.py` line 174: module-level instantiation

`eg = EventGen()` at module level means **every import of event_gen triggers PsychoPy audio initialization**. This is problematic because:
- It slows down all imports.
- It can fail on machines without audio devices.
- It makes the module impossible to import for testing without PsychoPy configured.

**Fix:** Move this inside an `if __name__ == "__main__":` guard.

---

## 2. PROTOCOL DEVIATIONS (vs. MultiThreshold / Lecluyse)

### 2.1 Previous audit items (from 2026-02-14) — status check

The Feb 14 audit identified several issues. Current status:

| Issue | Status | Notes |
|-------|--------|-------|
| #1 Start randomization | **Fixed** | Now derives from step size in PTA |
| #2 First reversal definition | **Partially addressed** | Reversal detection uses `abs(last - current) > 1`, still doesn't enforce initial descending direction |
| #3 Trial counting start | **Fixed** | `trials_remaining = trials_after_reversal - 1` on line 558 |
| #4 Config transition off-by-one | **Still present** | `config_num` dual use as 0-based index and 1-based display number |
| #5 Catch trial rate per-run | **Fixed** | Now adjusts per-run via `_had_false_positive_this_run` flag |
| #6 Threshold estimation | **Fixed** | Psychometric function fitting implemented |
| #7 WRV limits / abort logic | **NOT implemented** | Still clips to min/max without aborting |
| #8 Continue vs stop on FP | **NOT implemented** | Always continues (UZH behavior only) |

### 2.2 No config shuffling/randomization

The MultiThreshold manual discusses presentation order options (box [23]: "fixed sequence" vs randomized). The current code always presents outer variable combinations in `itertools.product` order (i.e., deterministic). For IFMC, this means masker ratios always go 0.5 → 0.7 → 0.9 → ... which could introduce order effects.

**Fix:** Add an `order` parameter: `"sequential"`, `"random"`, `"counterbalanced"`.

### 2.3 IFMC probe level: amplitude vs dB SPL confusion

`paradigm_ifmc.py:116` says `probe_amp = self.probe_level` where `probe_level` comes from the outer variable. The test script `test_ifmc.py:49` gets this from `loader.get_ifmc_probe_level()`, which converts PTA threshold dB → amplitude via `TrialPlayer.db2amp()`. But `db2amp()` just does `10^(dB/20)`, which maps negative dB to tiny numbers and 0 dB to 1.0. Since PTA thresholds are typically stored as dB FS (negative numbers like -40 dB), the probe amplitude would be something like `10^(-30/20) = 0.032`.

Meanwhile, `db_spl_to_amplitude()` on line 152 does a **linear** mapping `dB_SPL / 100`. These are two completely incompatible scales being used in the same paradigm. The masker uses `db_spl_to_amplitude()` (linear 0-100 mapping) while the probe uses raw `db2amp()` (exponential dB mapping).

**Impact:** Masker and probe levels are on different scales, so the masking thresholds will be meaningless until calibration is implemented.

### 2.4 IFMC masker frequency ratios missing 0.8 ratio

The PROLACTIN plan CSV specifies `maskerRelativeFrequency: 0.7, 0.9, 1, 1.1, 1.3`. `standard_frequencies.py` has `[0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6]`. This doesn't match either Lecluyse 2013 (which uses a different set) or the PROLACTIN plan exactly. Not necessarily wrong, but worth confirming which set you actually want.

### 2.5 TMC timing from Lecluyse vs PROLACTIN plan mismatch

`standard_frequencies.py` defines both `TMC_GAPS = [20, 40, 50, 60, 80]` (from Lecluyse 2013) and `TMC_PROLACTIN_GAPS = [0.030, 0.050, 0.070]` (from PROLACTIN plan). The test script uses PROLACTIN gaps. This is fine but should be explicitly documented which source wins for your deployment.

### 2.6 LDL doesn't inherit from `AdaptiveParadigm`

`paradigm_ldl.py` is a standalone class, not inheriting from `AdaptiveParadigm`. This makes sense since LDL isn't adaptive, but it means LDL has its own separate GUI code, data logging, and file-writing logic. This creates maintenance burden — any changes to the GUI or logging patterns need to be duplicated.

**Suggestion:** Consider a lighter base class (e.g., `BaseParadigm`) that handles GUI + logging but not adaptive logic, with `AdaptiveParadigm` inheriting from it.

---

## 3. CODE QUALITY & EFFICIENCY

### 3.1 Massive boilerplate duplication across paradigms

AM, FM, DLI, ILD all have nearly identical code for:
- `initialize_adaptive_param()` — randomize start with factor
- `adapt_difficulty()` — multiplicative steps
- `reset_to_midpoint_*()` — geometric mean
- `update_trial_params()` — midpoint reset + super()
- `get_log_data()` — hasattr checks for outer vars

The pattern differs only in:
- Variable name (`mod_ind`, `level_diff_dB`, `ild_dB`, `itd_ms`)
- Step type (multiplicative vs linear)
- Midpoint type (geometric vs arithmetic)

**This is the single biggest code quality problem.** ~80% of each paradigm file is copy-pasted from another paradigm with variable names changed.

**Fix:** The base class should handle all of this parametrically:
```python
# In AdaptiveParadigm.__init__():
self.step_mode = inner_var.data.get('step_mode', 'linear')  # or 'multiplicative'
```
Then `adapt_difficulty()`, `reset_to_midpoint()`, and `initialize_adaptive_param()` can all live in the base class with step_mode dispatching. Each paradigm would only need to implement `prepare_trial()`, `get_log_data()`, and optionally `check_answer()`.

### 3.2 `last_two_levels` tracked in every subclass

Every paradigm (PTA, GAP, AM, FM, DLI, ILD, ITD) manually maintains `self.last_two_levels` and has its own midpoint reset method. This should be in the base class since the logic is identical except for arithmetic vs geometric mean (which depends on `step_mode`).

### 3.3 `get_log_data()` uses `hasattr` checks defensively

Every paradigm's `get_log_data()` does `if hasattr(self, 'fc')` etc. Since outer variables are always set by `set_current_config()` in the base class, these checks are unnecessary — the variables will always exist after `_setup_variable_looping()`. This is defensive coding against a scenario that can't happen.

### 3.4 `operator_gui.py` has extreme plot formatting repetition

The `clear_display()` method (lines 645-685) repeats axis formatting code identically for all 4 subplots. Each plot update method also repeats the same axis styling. This should be a helper: `_style_axis(ax, xlabel, ylabel, title)`.

### 3.5 `trial_player.py` has legacy structure

- The `len` parameter name on `vec_expand` (line 196) shadows the Python builtin.
- `play_trial()` prints "Begin trial..." and "Trial finished..." unconditionally — should be gated by `verbose`.
- The inline DEFAULTS dict duplicates `bg` key with conflicting definitions (lines 28 vs 31-36).
- Sample-accurate mode (line 154) creates a `Sound` with `stereo=True` from a 1D array, which PsychoPy may handle by duplicating to both channels, but this is implicit.

### 3.6 `pd.concat` in a loop for data logging

`adaptive_paradigm.py:892` creates a new DataFrame each trial and concatenates. This is O(n²) — for long paradigms with many configs, this will get progressively slower. Better to append dicts to a list and create DataFrame once at the end.

---

## 4. IMPLEMENTATION PLAN ASSESSMENT

### 4.1 Plan accuracy

The 5-priority plan is generally solid. A few notes:

- **Priority 1 (Operator GUI):** Largely implemented. The `operator_gui.py` file has all 4 panels, text stats, and singleton pattern. Main remaining work is integration testing and polish.

- **Priority 2 (Calibration):** Not started. The plan is sound (inverse filter convolution + SPL offset), but the `db_spl_to_amplitude()` placeholder in IFMC/TMC is a blocker for meaningful masking data. This should probably be priority 1 now that the GUI exists.

- **Priority 3 (Testing & Tuning):** Not started. The `MockParticipant` idea from the plan is excellent and would catch many of the issues identified here.

- **Priority 4 (HID Input):** Not started. Low priority until core paradigms work.

- **Priority 5 (Refactoring):** The plan identifies the right concerns. I'd argue the boilerplate reduction (section 3.1 above) should happen sooner rather than later since it affects every paradigm change.

### 4.2 Revised priority recommendation

Given the current state:

1. **Fix FM `mod_ind` mismatch** (section 1.3) — FM paradigm is producing wrong stimuli
2. **Fix import paths** (section 1.5) — nothing runs without this
3. **Consolidate paradigm boilerplate** (section 3.1) — dramatically simplifies every subsequent change
4. **Implement calibration** (Priority 2) — needed for IFMC/TMC to produce meaningful data
5. **Add config randomization** (section 2.2) — simple but important for valid data
6. **Build MockParticipant** and run simulations (Priority 3)
7. **Add WRV limits/abort** (section 2.1, #7)

---

## 5. PARADIGM-SPECIFIC NOTES

### 5.1 PTA
Working correctly per the MultiThreshold protocol. Uses linear dB steps, arithmetic midpoint. The only concern is that `trial_dur` (from outer var) creates a Cartesian product with frequency — if you specify `data=[0.5, 1.0]`, you get 2× the number of configs. Check if that's intentional.

### 5.2 GAP
Sound implementation is correct (sample-accurate white noise with gap). Uses linear ms steps. Gap of 0.0 for catch trials is handled correctly by creating continuous noise.

### 5.3 AM
Stimulus generation in `event_gen.am()` is correct: `amp * (1 + mod_ind/100 * sin(2π·fm·t)) * sin(2π·fc·t)`. The `/100` division properly converts percent to fraction. This contrasts with FM where the conversion is missing.

### 5.4 FM
**Broken** — see section 1.3. The `event_gen.fm()` formula is phase modulation, not frequency deviation percentage. The modulation index β in radians ≠ percent frequency deviation.

### 5.5 DLI
Correct 3-response paradigm (same/1st/2nd). One concern: the louder tone is randomly assigned each trial, but the catch trial presents both tones at the *same* level, so the participant has three choices but only one is "correct" for catch trials (0="Same"). This is fine per the design.

### 5.6 IFMC
Structurally correct. Key issue is the amplitude scale mismatch (section 2.3). Also, the IFMC catch trial presents masker-only with no gap or probe — but in the real paradigm, should the participant hear the gap + silence-where-probe-would-be? Currently they just hear a masker tone, which may sound different enough from normal trials to be obvious.

### 5.7 TMC
Nearly identical to IFMC (on-frequency masking, variable gap instead of variable masker frequency). Same amplitude scale concern. Same catch trial design question.

### 5.8 ITD
Bypasses `TrialPlayer` entirely for stereo rendering — `prepare_trial()` generates audio directly and `execute_trial()` plays it. This works but breaks the TrialPlayer abstraction. When calibration is added, it won't apply to ITD stimuli unless the bypass is refactored.

### 5.9 ILD
Uses `pan` parameter in `TrialPlayer.new_trial()`, but `TrialPlayer` doesn't accept a `pan` parameter — it's not in the constructor, `new_trial()`, or `DEFAULTS`. This means ILD trials will silently ignore the pan and play center-panned audio.

**Impact:** ILD paradigm plays equal-level tones to both ears regardless of `ild_dB` value. The test produces meaningless data.

**Fix:** Add stereo panning support to `TrialPlayer`, or use sample-accurate stereo generation like ITD does.

### 5.10 LDL
Clean standalone implementation. The `step_mult` calculation from `db2amp(step_dB)` is correct for multiplicative amplitude stepping. The safety ceiling (`max_amp < 1.0`) is appropriate.

---

## 6. SUMMARY OF ACTION ITEMS (by priority)

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | **BLOCKER** | FM mod_ind mismatch (wrong stimuli) | event_gen.py / paradigm_fm.py |
| 2 | **BLOCKER** | ILD pan parameter not supported (no lateralization) | paradigm_ild.py / trial_player.py |
| 3 | **BLOCKER** | Import paths broken (can't run) | All paradigm + test files |
| 4 | **BLOCKER** | event_gen.py config.DEFAULTS import | event_gen.py line 20 |
| 5 | **HIGH** | Dead `update_streaks_and_difficulty()` methods | paradigm_ifmc.py, paradigm_tmc.py |
| 6 | **HIGH** | Amplitude scale mismatch in IFMC/TMC | paradigm_ifmc.py, paradigm_tmc.py |
| 7 | **HIGH** | Module-level EventGen instantiation | event_gen.py line 174 |
| 8 | **MEDIUM** | Paradigm boilerplate duplication | All paradigm_*.py |
| 9 | **MEDIUM** | No config shuffling | adaptive_paradigm.py |
| 10 | **MEDIUM** | No WRV limits / abort on non-convergence | adaptive_paradigm.py |
| 11 | **MEDIUM** | O(n²) DataFrame concatenation | adaptive_paradigm.py line 892 |
| 12 | **LOW** | `last_two_levels` duplicated in all subclasses | All paradigm_*.py |
| 13 | **LOW** | Operator GUI plot formatting repetition | operator_gui.py |
| 14 | **LOW** | `trial_player.py` builtin shadowing (`len`) | trial_player.py line 196 |
| 15 | **LOW** | Unconditional print statements in trial_player | trial_player.py lines 165, 178 |
| 16 | **LOW** | `direction` attribute unused | adaptive_paradigm.py |
| 17 | **LOW** | VarSpec type annotation (list vs dict) | varspec.py |
