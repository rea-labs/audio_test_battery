# PROLACTIN Testing Plan v3

*2026-03-27 — covers human test protocols, automated test infrastructure, and implementation roadmap*

*v3 (2026-08-17): DLI inner-variable name corrected to `level_diff_dB` (was `delta_level`) to match the attribute used throughout `paradigm_dli.py` and the `_dB` suffix convention. No other changes from v2.*

---

## 1. Current State Summary

All 11 paradigms run without crashing. Core adaptive logic (reversals, catch trials, threshold estimation, operator GUI) is functional. Phases A1 and A2 are complete. No formal testing has been done.

**Key architectural constraint:** `AdaptiveParadigm.main()` currently couples adaptive logic, audio playback, GUI, and timing into a single blocking loop. This means automated tests require a `headless` mode (section 5) to bypass audio/GUI while preserving the logic path.

**What exists today:**

| Component | Status |
|-----------|--------|
| 11 paradigm classes | Functional, not formally validated |
| Adaptive logic (base class) | Implemented, needs edge-case testing |
| Operator GUI | Functional, label/display issues (S3) |
| Participant GUI | Functional (tkinter), eventual NiceGUI migration planned |
| Data logging (CSV) | Functional with temp crash recovery |
| ResultLoader | Functional, used by IFMC/TMC |
| Threshold estimation (psychometric fit) | Implemented, not validated against known data |
| Calibration | Not started (Phase B) |
| Experimental controller | Not started |
| Automated tests | None |

---

## 2. Testing Strategy Overview

Two parallel tracks, **human protocols first** (simpler, immediately useful):

**Track A — Human protocols (H1-H6):** Structured checklists your team runs manually. Covers audio quality, adaptive tracking, GUI/UX, and end-to-end validation. No code changes needed to run these.

**Track B — Automated tests (U/I/S tiers):** pytest-based tests requiring a `headless` mode addition and `MockParticipant` class. Covers logic correctness, CSV output, and stimulus math.

### Implementation order

| # | Task | Effort | Prereqs |
|---|------|--------|---------|
| 1 | Print and run **H1** (audio spot-check) for all paradigms | ~1 hr | None |
| 2 | Print and run **H2** (adaptive tracking) for PTA + 2 others | ~30 min | None |
| 3 | Print and run **H3** (participant GUI/UX) | ~30 min | None |
| 4 | Print and run **H4** (operator GUI/UX) | ~15 min | None |
| 5 | Implement `headless` mode in `AdaptiveParadigm` | ~2 hr | None |
| 6 | Build `MockParticipant` class | ~2 hr | Step 5 |
| 7 | Write **Tier 1** unit tests (U1-U8) | ~3 hr | Step 5 |
| 8 | Write **Tier 2** integration tests (I1-I6) | ~3 hr | Steps 5-6 |
| 9 | Write **Tier 3** stimulus tests (S1-S7) | ~2 hr | None (no headless needed) |
| 10 | Run **H5** (end-to-end validation) | ~1 hr | Phase B calibration |
| 11 | Run **H6** (cross-platform) | ~1 hr | Windows machine |

---

## 3. Paradigm Parameter Reference

For use during human testing and MockParticipant design.

### Step type summary

**Linear step paradigms** (add/subtract in native units):

| Paradigm | Adaptive param | Unit | Start | Initial steps | Final steps | Min | Max |
|----------|---------------|------|-------|---------------|-------------|-----|-----|
| PTA | trial_amp | amplitude | 0.5 | -10/+10 dB | -2/+2 dB | 0.0001 | 1.0 |
| GAP | gap_duration | seconds | 0.010 | -5/+5 ms | -1/+1 ms | 0.001 | 0.020 |
| IFMC | masker_level | dB | 20.0 | -10/+10 dB | -2/+2 dB | 0 | 100 |
| TMC | masker_level | dB | 10.0 | -10/+10 dB | -2/+2 dB | 0 | 100 |
| LDL | trial_amp | amplitude | 0.2 | +3 dB always | +3 dB always | 0.001 | 0.9 |

**Multiplicative step paradigms** (multiply factor in native units):

| Paradigm | Adaptive param | Unit | Start | Initial steps | Final steps | Min | Max |
|----------|---------------|------|-------|---------------|-------------|-----|-----|
| AM | mod_ind | % | 50.0 | x0.5 / x2.0 | x0.7 / x1.4 | 1.0 | 100.0 |
| FM | mod_ind | % | 8.0 | x0.5 / x2.0 | x0.7 / x1.4 | 0.1 | 20.0 |
| DLI | level_diff_dB | dB | 5.0 | x0.5 / x2.0 | x0.7 / x1.4 | 0.1 | 20.0 |
| ILD | ild_dB | dB | 15.0 | x0.5 / x2.0 | x0.7 / x1.4 | 0.5 | 32.0 |
| ITD | itd_ms | ms | 50.0 | x0.5 / x2.0 | x0.7 / x1.4 | 0.01 | 100.0 |

### Notes on step asymmetry

The multiplicative final steps (x0.7 down / x1.4 up) are *nearly* symmetric in log space (-3.1 dB / +2.9 dB) but not exactly. This is a ~0.2 dB bias toward larger values. For the precision level of these paradigms, this is probably acceptable, but worth flagging.

### Global adaptive settings

| Setting | Value | Source |
|---------|-------|--------|
| trials_after_reversal | 10 | adaptive_paradigm.py |
| target_streak_correct | 1 | 1-down/1-up by default |
| target_streak_wrong | 1 | |
| catch_trial_rate | [0.2, 0.1, 0.1, 0.5] | [start, min, step, max] |
| trial_ITI | 0.5 s | Between-trial pause |

---

## 4. Human Test Protocols (Track A)

### H1 — Audio Quality Spot-Check

**Goal:** Verify each paradigm produces correct, clean audio.
**Who:** Any team member with normal hearing.
**Time:** ~5 min per paradigm, ~1 hr total.
**Equipment:** Headphones connected to test machine.

**Procedure for each paradigm:**

Run the test script (e.g., `python test_pta.py`). In the setup dialog, use demo mode to preview stimuli at several parameter values.

**Checklist:**

```
Paradigm: ________    Tester: ________    Date: ________

[ ] No clicks or pops at stimulus onset/offset
[ ] Fades (ramp in/out) audible and smooth
[ ] Correct signal type:
    PTA:  pure tone
    GAP:  white noise with silent gap
    AM:   tone with amplitude fluctuation
    FM:   tone with pitch fluctuation
    DLI:  two sequential tones (one louder)
    ILD:  tone perceived to one side
    ITD:  tone/noise perceived to one side
    IFMC: masker tone → gap → probe tone
    TMC:  masker tone → gap → probe tone
    LDL:  pure tone (ascending volume)
[ ] Catch trial is silent (or masker-only for IFMC/TMC)
[ ] Demo at LOW parameter value: stimulus barely perceptible
[ ] Demo at HIGH parameter value: stimulus clearly perceptible
[ ] Demo at MID parameter value: somewhere between
[ ] Frequency changes sound correct when switching fc
[ ] Pan parameter works: left ear / right ear / both (where applicable)

Notes: _______________________________________________
Overall: [ ] PASS  [ ] FAIL  [ ] NEEDS FOLLOW-UP
```

**Paradigm-specific checks:**

| Paradigm | Extra check |
|----------|-------------|
| AM | At mod_ind=50%, fluctuation is very obvious; at mod_ind=5%, barely noticeable |
| FM | At mod_ind=8%, pitch wobble is audible; compare to AM to confirm it's pitch not volume |
| DLI | Both tones at same frequency; one is clearly louder; "Same" option works |
| IFMC | Masker → gap → probe structure audible; probe disappears on catch |
| TMC | Same as IFMC but gap duration varies |
| ITD | With noise: lateralization shifts; with tone: lateralization shifts |
| ILD | Clear left/right loudness difference |
| LDL | Gets progressively louder; stop if uncomfortable |

---

### H2 — Adaptive Tracking Verification

**Goal:** Verify the staircase logic works correctly by observing the operator display.
**Who:** Someone who understands the adaptive protocol.
**Time:** ~10 min per paradigm.
**Equipment:** Test machine with dual monitors (or large screen to see both windows).

**Procedure:**

Run a paradigm (start with PTA). Watch the operator display "Adaptive Track" plot.

**Phase 1: Forced descent** (~2 min)
Respond "Yes" (heard it) to every trial, including catch trials.

```
[ ] Track descends on each step
[ ] Steps are LARGE (10 dB or equivalent) before any reversal
[ ] Catch trial false positive: FP warning appears in participant GUI
[ ] Catch trial false positive: FP marker visible on operator display
[ ] Track does NOT change direction on FP (stays descending)
```

**Phase 2: Force first reversal** (~2 min)
After 5-8 "Yes" responses, respond "No" to the next normal trial.

```
[ ] Reversal detected (marker on plot, "REVERSAL" in console)
[ ] Track resets to midpoint of last two levels
[ ] Steps switch to SMALL (2 dB or equivalent) after reversal
[ ] Trial countdown starts (visible in operator info panel)
```

**Phase 3: Oscillate** (~3 min)
Alternate between Yes and No responses.

```
[ ] Track oscillates around a stable level
[ ] Multiple reversals accumulate
[ ] Countdown decrements on each non-catch trial
[ ] Catch trials do NOT decrement countdown
```

**Phase 4: Completion** (~2 min)
Let countdown reach zero.

```
[ ] Config ends when countdown hits 0
[ ] Threshold estimate appears (console + operator display)
[ ] Next config starts automatically with fresh track
[ ] Previous threshold appears in "Previous Thresholds" plot
[ ] Psychometric function plot updates
```

**Repeat abbreviated version for:** GAP (linear steps), AM (multiplicative steps), DLI (3-response).

```
Paradigm: ________    Tester: ________    Date: ________
Overall: [ ] PASS  [ ] FAIL  [ ] NEEDS FOLLOW-UP
Notes: _______________________________________________
```

---

### H3 — Participant GUI/UX

**Goal:** Evaluate the participant experience for clarity and usability.
**Who:** Ideally someone unfamiliar with the project (naive user).
**Time:** ~5 min per paradigm, ~30 min for a representative subset.

**Procedure:**

Run 3-4 paradigms (PTA, GAP, DLI, LDL for variety). Act as a naive participant. Run each for at least 1 full config.

**Checklist (per paradigm):**

```
Paradigm: ________    Tester: ________    Date: ________

Setup dialog:
[ ] Participant ID field is clear and editable
[ ] Parameter summary is readable
[ ] Demo button works; stimulus plays
[ ] Accept / Cancel buttons work
[ ] Enter key confirms dialog; Escape cancels
[ ] Frequency set dropdown works (where applicable)

During test:
[ ] Question text is clear and appropriate for this paradigm
[ ] Button labels match the task (Yes/No, or Same/1st/2nd, etc.)
[ ] Buttons are large enough to click easily
[ ] Keyboard shortcuts work (0, 1, etc.)
[ ] "Playing stimulus..." shown during playback
[ ] Buttons DISABLED during playback (can't respond early)
[ ] Buttons ENABLED after playback finishes
[ ] Repeat button works (plays same trial again)
[ ] Response registers correctly (no double-clicks)

FP warning:
[ ] Respond "Yes" to a catch trial — warning appears
[ ] Warning text is readable
[ ] Warning clears after ~2 seconds
[ ] Test continues normally after warning

General:
[ ] Window stays on top / doesn't get lost behind other windows
[ ] No freezing or unresponsive periods
[ ] Font size readable at normal viewing distance

UX friction points (free text):
_______________________________________________

Overall: [ ] PASS  [ ] FAIL  [ ] NEEDS FOLLOW-UP
```

---

### H4 — Operator GUI/UX

**Goal:** Verify all 4 operator display panels update correctly.
**Who:** Someone familiar with the expected display behavior.
**Time:** ~15 min total (run 2-3 paradigms).

**Procedure:**

Run PTA through at least 2 configs with honest-ish responses. Observe operator window throughout.

**Checklist:**

```
Tester: ________    Date: ________    Paradigm(s): ________

Panel 1 — Stimulus Waveform:
[ ] Updates on each trial
[ ] Shows correct signal shape (tone, noise, masker+probe, etc.)
[ ] Catch trial shows flat line / silence
[ ] Axes labels present and correct

Panel 2 — Adaptive Track:
[ ] New point plotted each trial
[ ] Level values on Y-axis make sense for this paradigm
[ ] Reversal points marked
[ ] Midpoint reset visible after first reversal
[ ] Large steps visible before reversal, small steps after
[ ] Running threshold estimate shown (if implemented)

Panel 3 — Previous Thresholds:
[ ] Empty at start
[ ] Threshold point appears after first config completes
[ ] Accumulates across configs
[ ] Axis labels correct (frequency or config label on X)

Panel 4 — Psychometric Function:
[ ] Updates after config completes
[ ] Fitted curve visible
[ ] Data points (level vs. proportion correct) plotted
[ ] Theta and k values shown

Info Panel (text):
[ ] Paradigm name correct
[ ] Config N/M counter updates
[ ] Trial N counter updates
[ ] FP warning text appears on false positive
[ ] WRV limit warning appears if track hits min/max

Behavioral:
[ ] Window persists across config changes
[ ] No crashes during long runs
[ ] Plots don't accumulate rendering artifacts
[ ] Performance acceptable (no noticeable lag between trials)

Notes: _______________________________________________
Overall: [ ] PASS  [ ] FAIL  [ ] NEEDS FOLLOW-UP
```

---

### H5 — End-to-End Validation Against Known Data

**Goal:** Compare PROLACTIN thresholds to reference values.
**Who:** 1-2 people with recent clinical audiograms.
**Time:** ~1 hr per person.
**Prereqs:** Phase B calibration complete (without calibration, results will be in dB FS, not dB HL/SPL — can still check relative pattern across frequencies).

**Procedure:**

1. Run full PTA at audiometric frequencies, both ears.
2. Run GAP detection.
3. Run IFMC at 1 kHz (requires PTA results for probe level).

**Comparison checklist:**

```
Participant: ________    Date: ________
Clinical audiogram date: ________

PTA (per frequency):
Freq (Hz) | Clinical (dB HL) | PROLACTIN (dB) | Diff (dB)
----------|------------------|----------------|----------
250       |                  |                |
500       |                  |                |
1000      |                  |                |
2000      |                  |                |
4000      |                  |                |
8000      |                  |                |

Expected: |diff| < 10 dB uncalibrated, < 5 dB calibrated.
Pattern across frequencies should match (both show same shape).

GAP threshold:
[ ] Normal hearing: < 5 ms
[ ] Result: _______ ms

IFMC depth at 1 kHz:
[ ] Normal hearing: ~20-30 dB (Lecluyse 2013)
[ ] Result: _______ dB

Notes: _______________________________________________
```

---

### H6 — Cross-Platform Verification

**Goal:** Confirm everything works on Windows.
**Who:** Anyone with access to a Windows machine.
**Time:** ~1 hr.
**Prereqs:** conda env set up from environment.yml on Windows.

**Checklist:**

```
Machine: ________    OS: ________    Date: ________

Environment:
[ ] conda env created successfully from environment.yml
[ ] PsychoPy imports without error
[ ] PTB audio backend initializes

Run PTA:
[ ] Setup dialog opens
[ ] Demo plays audio through headphones
[ ] Paradigm runs (at least 1 config)
[ ] Operator display opens and updates
[ ] CSV file written to test_data/
[ ] No path separator issues (backslash vs forward slash)

Run GAP:
[ ] Sample-accurate noise+gap plays correctly
[ ] No audio glitches or timing issues

Run AM:
[ ] Modulated tone sounds correct

Data files:
[ ] CSV readable by pandas on both platforms
[ ] Filenames use valid characters on both platforms
[ ] ResultLoader finds files correctly

Notes: _______________________________________________
Overall: [ ] PASS  [ ] FAIL  [ ] NEEDS FOLLOW-UP
```

---

## 5. Automated Test Infrastructure (Track B)

### 5.1 — Headless Mode Design

Add a `headless` kwarg to `AdaptiveParadigm.__init__()` and a `response_source` callable. When `headless=True`:

- Skip `tk.Tk()` creation in `main()`
- Skip `core.wait()` calls
- Skip operator display
- `execute_trial()` becomes a no-op (no audio)
- `get_response()` calls `self.response_source(self)` instead of blocking on GUI

**Minimal code change in `adaptive_paradigm.py`:**

```python
# In __init__():
self.headless = kwargs.get('headless', False)
self.response_source = kwargs.get('response_source', None)

# In main():
if not self.headless:
    self.root = tk.Tk()
    # ... existing GUI setup ...
else:
    self.root = None

# In execute_trial():
def execute_trial(self):
    self.trial_repeats += 1
    if not self.headless:
        self.tp.play_trial()

# In get_response():
def get_response(self, trial_playing=True):
    if self.headless and self.response_source is not None:
        return self.response_source(self)
    # ... existing GUI code ...

# In update_gui_state():
def update_gui_state(self, trial_playing=True):
    if self.headless or self.root is None:
        return
    # ... existing code ...

# Gate core.wait() calls:
if not self.headless:
    core.wait(0.5)
```

The key design principle: **same logic path, just no I/O**. The catch trial determination, reversal detection, step adaptation, threshold estimation, and data logging all execute identically.

**Estimated change:** ~30 lines across 4-5 methods, all in `adaptive_paradigm.py`. No paradigm subclass changes needed.

**Open question:** `prepare_trial()` calls `self.tp.new_trial(...)` which constructs PsychoPy Sound objects. In headless mode, do we want to (a) skip `new_trial()` entirely, (b) let it build the numpy waveform but skip the Sound object, or (c) let it run fully? Option (a) is simplest but means Tier 3 stimulus tests can't run through `prepare_trial()`. Option (b) requires a small `TrialPlayer` change. Option (c) requires PsychoPy installed even for CI. **Recommendation: option (a)** for now — Tier 3 tests call `EventGen` directly anyway. Can revisit if needed.

### 5.2 — MockParticipant Design

A callable that simulates a participant with a known threshold, returning responses based on a psychometric function with added noise.

```python
class MockParticipant:
    """
    Simulates participant responses based on a psychometric function.
    
    Usage:
        mock = MockParticipant(threshold=0.01, slope=4.0, lapse_rate=0.05)
        paradigm = ParadigmGAP(params, headless=True, response_source=mock)
        paradigm.main()
    
    The __call__ signature takes the paradigm instance, reads the current
    adaptive parameter value, and returns a response integer.
    """
    
    def __init__(self, threshold, slope=2.0, lapse_rate=0.05, seed=None):
        """
        Args:
            threshold: Ground-truth threshold in paradigm-native units.
                       For PTA: amplitude (e.g. 0.01).
                       For GAP: gap duration in seconds (e.g. 0.003).
                       For AM/FM: mod_ind in % (e.g. 8.0).
                       For DLI/ILD: dB difference (e.g. 1.5).
                       For ITD: delay in ms (e.g. 0.05).
                       For LDL: amplitude at which "uncomfortable" (e.g. 0.7).
            slope: Psychometric function slope. Higher = sharper transition.
            lapse_rate: Probability of random incorrect response.
            seed: RNG seed for reproducibility.
        """
        self.threshold = threshold
        self.slope = slope
        self.lapse_rate = lapse_rate
        self.rng = np.random.default_rng(seed)
    
    def _p_detect(self, stimulus_level):
        """
        Probability of detection via logistic function.
        p(x) = 1 / (1 + exp(-slope * (x - threshold)))
        
        For "harder = lower value" paradigms (PTA, AM, FM, DLI, ILD, ITD):
            Higher stimulus value -> more detectable -> p closer to 1
        For "harder = higher value" paradigms (GAP only):
            sign is inverted - shorter gap is harder
        """
        return 1.0 / (1.0 + np.exp(-self.slope * (stimulus_level - self.threshold)))
    
    def _apply_lapse(self, p):
        """Add lapse rate: small chance of random wrong answer."""
        return p * (1 - self.lapse_rate) + (1 - p) * self.lapse_rate
    
    def __call__(self, paradigm):
        """
        Return response for current trial.
        
        Reads the adaptive parameter from the paradigm instance,
        computes detection probability, returns response.
        """
        # Handle catch trials: never say "yes" on a catch (ideal observer)
        # ... with lapse_rate chance of false positive
        if paradigm.is_catch_trial:
            if self.rng.random() < self.lapse_rate:
                return 1  # False positive (lapse)
            return 0  # Correct rejection
        
        # Read current adaptive parameter value
        attr_name = paradigm.inner_var.name
        current_val = getattr(paradigm, attr_name)
        
        p = self._p_detect(current_val)
        p = self._apply_lapse(p)
        
        if self.rng.random() < p:
            return 1  # Detected
        else:
            return 0  # Not detected
```

**Paradigm-specific subclasses needed:**

| Paradigm | Why special |
|----------|-------------|
| DLI | 3-alternative: return 0 (same) when level_diff_dB < threshold, else return 1 or 2 (randomly choose which interval was louder) |
| LDL | 3-option: return 0 (comfortable) or 1 (loud) when level < threshold, return 2 (uncomfortable) when level >= threshold |
| GAP | Inverted direction: shorter gap = harder. `_p_detect` needs sign flip. |
| IFMC/TMC | Mock needs to respond based on masker level exceeding masking threshold at that frequency/gap |

```python
class MockDLI(MockParticipant):
    """DLI: 3-alternative (same / 1st louder / 2nd louder)."""
    def __call__(self, paradigm):
        if paradigm.is_catch_trial:
            return 0  # "Same" is correct for catch
        current_val = getattr(paradigm, paradigm.inner_var.name)
        p = self._apply_lapse(self._p_detect(current_val))
        if self.rng.random() < p:
            # Detected difference; randomly guess which interval
            # DLI assigns louder interval randomly each trial
            return self.rng.choice([1, 2])
        else:
            return 0  # "Same" — didn't detect difference

class MockLDL(MockParticipant):
    """LDL: ascending only, 3 options (comfortable/loud/uncomfortable)."""
    def __call__(self, paradigm):
        current_val = getattr(paradigm, paradigm.inner_var.name)
        if current_val >= self.threshold:
            return 2  # Uncomfortable
        elif current_val >= self.threshold * 0.7:
            return 1  # Loud
        else:
            return 0  # Comfortable

class MockGAP(MockParticipant):
    """GAP: inverted direction (shorter = harder)."""
    def _p_detect(self, stimulus_level):
        # Longer gap -> easier to detect (positive relationship)
        # But threshold is the MINIMUM detectable gap
        # So we want p -> 1 when gap >> threshold, p -> 0 when gap << threshold
        return 1.0 / (1.0 + np.exp(-self.slope * (stimulus_level - self.threshold)))
        # Actually this is the same formula. The sign works out because
        # larger gap_duration = higher stimulus_level = more detectable.
        # The adapt_difficulty inverts the direction (harder = shorter gap).
```

### 5.3 — Test Tiers

#### Tier 1: Unit Tests (pure logic, no paradigm instantiation needed)

```
tests/
  test_unit_reversals.py       # U1: reversal detection from streak sequences
  test_unit_catch_trials.py    # U2: scheduling, rate adaptation
  test_unit_step_sizes.py      # U4: pre/post reversal step switching
  test_unit_midpoint.py        # U5: arithmetic vs geometric midpoint
  test_unit_psych_fit.py       # U6: psychometric function fitting
  test_unit_config_unwrap.py   # U7: Cartesian product, randomization
  test_unit_wrv_limits.py      # U8: boundary detection
```

Each test file is standalone, imports only `adaptive_paradigm.py` (and maybe numpy), and tests a single method or behavior by constructing minimal scenarios.

**Example — U1 (reversal detection):**

```python
def test_reversal_on_direction_change():
    """Streak going +1,+2 then to -1 should trigger a reversal."""
    p = make_minimal_paradigm()  # helper that builds headless paradigm
    p.current_streak = 2
    p.last_current_streak = 2
    
    # Simulate a FN response
    p.correct_answer = 'FN'
    p.is_catch_trial = False
    p.update_counters()
    
    assert p.total_num_reversals == 1
    assert p.trials_remaining == 9  # trials_after_reversal - 1
    assert p.reset_to_midpoint == True

def test_no_reversal_on_catch_fp():
    """False positive on catch trial should NOT trigger reversal."""
    p = make_minimal_paradigm()
    p.current_streak = 2
    p.last_current_streak = 1
    
    p.correct_answer = 'FP'
    p.is_catch_trial = True
    p.update_counters()
    
    assert p.total_num_reversals == 0  # No reversal from FP
```

**Example — U6 (psychometric fit):**

```python
def test_psych_fit_recovers_known_threshold():
    """Fitting synthetic data at theta=30 should recover theta ~30."""
    p = make_minimal_paradigm()
    
    # Generate synthetic data: logistic with theta=30, k=0.5
    levels = np.arange(20, 40, 1.0)
    true_p = 1 / (1 + np.exp(-0.5 * (levels - 30)))
    rng = np.random.default_rng(42)
    responses = (rng.random(len(levels)) < true_p).astype(int)
    
    result = p.fit_psychometric_function(levels, responses)
    
    assert result['success']
    assert abs(result['threshold_dB'] - 30.0) < 3.0  # within 3 dB
```

#### Tier 2: Integration Tests (headless full paradigm runs)

```
tests/
  test_integration_convergence.py  # I1: all paradigms converge to mock threshold
  test_integration_csv_output.py   # I2: CSV format validation
  test_integration_crash_recovery.py # I3: temp CSV exists mid-run
  test_integration_multi_config.py  # I4: multi-config sequencing
  test_integration_result_loader.py # I5: ResultLoader round-trip
  test_integration_threshold_import.py # I6: IFMC/TMC loads PTA data
```

**Example — I1 (convergence):**

```python
@pytest.mark.parametrize("paradigm_class,mock_cls,threshold,params", [
    (ParadigmPTA, MockParticipant, 0.01, PTA_TEST_PARAMS),
    (ParadigmGAP, MockGAP, 0.004, GAP_TEST_PARAMS),
    (ParadigmAM, MockParticipant, 10.0, AM_TEST_PARAMS),
    # ... etc for each paradigm
])
def test_convergence(paradigm_class, mock_cls, threshold, params):
    mock = mock_cls(threshold=threshold, slope=2.0, seed=42)
    p = paradigm_class(params, headless=True, response_source=mock)
    p.main()
    
    # Check that estimated threshold is within tolerance of ground truth
    config_data = p.data[p.data['config_num'] == 1]
    last_row = config_data.iloc[-1]
    estimated = last_row['threshold_dB']
    
    assert not np.isnan(estimated), "Threshold estimation failed"
    # Tolerance depends on paradigm precision
    assert abs(estimated - threshold) < tolerance
```

**Example — I2 (CSV format):**

```python
def test_csv_has_required_columns():
    mock = MockParticipant(threshold=0.01, seed=42)
    p = ParadigmPTA(PTA_SINGLE_FREQ_PARAMS, headless=True,
                     response_source=mock, participant_id="TEST001")
    p.main()
    
    df = p.data
    required = ['unix_time', 'config_num', 'trial_num', 'correct_answer',
                'trial_repeats', 'is_catch_trial', 'threshold_dB', 'slope_k']
    for col in required:
        assert col in df.columns, f"Missing column: {col}"
    
    # Threshold filled only on last trial of each config
    for config_num in df['config_num'].unique():
        config = df[df['config_num'] == config_num]
        non_last = config.iloc[:-1]
        last = config.iloc[-1]
        assert non_last['threshold_dB'].isna().all()
        # last row may or may not have threshold depending on fit success
```

**Example — I6 (IFMC threshold import):**

```python
def test_ifmc_loads_pta_thresholds():
    """Write fake PTA CSV, verify IFMC ResultLoader picks it up."""
    # Create fake PTA data with known thresholds
    fake_data = pd.DataFrame({
        'config_num': [1, 1, 2, 2],
        'trial_num': [9, 10, 9, 10],
        'fc': [1000, 1000, 2000, 2000],
        'threshold_dB': [np.nan, -20.0, np.nan, -15.0],
        # ... other required columns
    })
    
    test_dir = Path('test_data_automated')
    test_dir.mkdir(exist_ok=True)
    fake_path = test_dir / 'TEST001_PTA_2026-01-01_00-00-00.csv'
    fake_data.to_csv(fake_path, index=False)
    
    loader = ResultLoader(data_dir=str(test_dir))
    thresholds = loader.get_thresholds('TEST001', 'PTA')
    
    assert 1000 in thresholds
    assert thresholds[1000] == pytest.approx(-20.0)
```

#### Tier 3: Stimulus Validation (numerical waveform checks)

```
tests/
  test_stimulus_am.py    # S1
  test_stimulus_fm.py    # S2
  test_stimulus_gap.py   # S3
  test_stimulus_tone.py  # S4
  test_stimulus_fades.py # S5
  test_stimulus_ild.py   # S6
  test_stimulus_itd.py   # S7
```

These import `EventGen` directly, generate raw numpy waveforms (no Sound objects), and verify mathematical properties. They do NOT require PsychoPy audio backends.

**Problem: `EventGen.__init__` imports PsychoPy at module level** (for Sound objects). Options:
1. Refactor EventGen to separate waveform generation (numpy-only) from Sound object creation
2. Add a `raw=True` parameter to EventGen methods that returns numpy array without creating Sound
3. Accept that Tier 3 tests require PsychoPy installed (fine since Eric runs locally)

**Recommendation: option 3** for now. EventGen already has `return_dict=True` which returns the raw waveform alongside the Sound object. Tests can use that.

**Example — S1 (AM envelope):**

```python
def test_am_modulation_depth():
    """Verify AM envelope matches requested mod_ind."""
    eg = EventGen(fs=48000)
    _, data = eg.am(duration=0.5, fc=1000, fm=8, mod_ind=50.0,
                     amp=1.0, return_dict=True)
    wave = data['values']
    
    # Extract envelope via Hilbert transform
    from scipy.signal import hilbert
    envelope = np.abs(hilbert(wave))
    
    # Remove fade regions
    fade_samples = int(0.05 * 48000)
    env_trimmed = envelope[fade_samples:-fade_samples]
    
    # Modulation depth = (max - min) / (max + min)
    m = (env_trimmed.max() - env_trimmed.min()) / (env_trimmed.max() + env_trimmed.min())
    
    # mod_ind=50 means 50% depth -> m should be ~0.5
    assert abs(m - 0.50) < 0.05  # within 5% tolerance (Hilbert not exact)
```

**Example — S4 (tone frequency):**

```python
def test_tone_frequency():
    """Verify generated tone has correct frequency."""
    eg = EventGen(fs=48000)
    _, data = eg.sin(duration=0.5, fc=1000, amp=1.0, return_dict=True)
    wave = data['values']
    
    # FFT, find peak
    fft = np.abs(np.fft.rfft(wave))
    freqs = np.fft.rfftfreq(len(wave), 1/48000)
    peak_freq = freqs[np.argmax(fft)]
    
    assert abs(peak_freq - 1000) < 2.0  # within 2 Hz
```

**Example — S7 (ITD delay):**

```python
def test_itd_delay():
    """Verify ITD introduces correct interaural delay."""
    # This requires accessing paradigm_itd.create_itd_stereo()
    # or building the stereo signal manually
    
    from paradigms.paradigm_itd import ParadigmITD
    # ... setup paradigm, call create_itd_stereo with known delay
    # Cross-correlate L and R channels
    # Verify peak offset matches requested ITD ± 1 sample
```

### 5.4 — File Structure

```
project_root/
  tests/
    conftest.py               # Shared fixtures: make_minimal_paradigm(), test params
    mock_participant.py        # MockParticipant + subclasses
    test_params.py             # Canonical test parameter dicts for each paradigm
    
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
    test_stimulus_am.py
    test_stimulus_fm.py
    test_stimulus_gap.py
    test_stimulus_tone.py
    test_stimulus_fades.py
    test_stimulus_ild.py
    test_stimulus_itd.py
  
  test_data_automated/        # Output from automated tests (gitignored)
```

---

## 6. Open Questions / Blockers

### Must resolve before automated tests

| # | Question | Impact | Suggested resolution |
|---|----------|--------|---------------------|
| Q1 | `prepare_trial()` creates PsychoPy Sound objects. In headless mode, should this be skipped entirely? | Tier 2 tests will fail or be slow if Sound objects are created | Skip `new_trial()` in headless mode via flag on TrialPlayer (option a) |
| Q2 | EventGen imports PsychoPy at module level. Tier 3 tests need waveforms but not Sound objects. | Tests crash if PsychoPy not installed | Acceptable for now since Eric runs locally; long-term refactor to separate numpy and PsychoPy layers |
| Q3 | How should MockParticipant handle the `randomize_factor` on start values? | Mock sees the randomized start, not the configured start — this is correct behavior but may confuse initial threshold comparisons | Mock should be set to the TRUE threshold, not the start value; the test tolerance accounts for convergence error |

### Must resolve before human tests

| # | Question | Impact | Suggested resolution |
|---|----------|--------|---------------------|
| Q4 | FM mod_ind: is the current implementation correct or broken? | H1 will flag if FM sounds wrong vs. AM, but tester needs to know what "correct" sounds like | Compare aurally to Prague toolbox if accessible; write S2 test to at least verify frequency deviation range |
| Q5 | ILD: does panning work correctly after the A2 changes? | H1 will reveal immediately | Run test_ild.py and listen |
| Q6 | IFMC/TMC catch trial: masker-only (current) vs. masker + gap + silence. Which is correct? | H1 tester needs to know expected behavior | Check MultiThreshold manual; current implementation may be too obviously different from normal trials |

### Can defer

| # | Question | Notes |
|---|----------|-------|
| Q7 | Multiplicative step asymmetry (x0.7/x1.4): intentional or oversight? | ~0.2 dB bias, probably negligible |
| Q8 | trials_after_reversal=10 gives ~1.6 dB precision — sufficient? | Fine for clinical screening, might need more for research |
| Q9 | Experimental controller design — when to tackle? | After testing validates current paradigms |
| Q10 | NiceGUI migration timeline for participant GUI | After core validation, probably after experimental controller |

---

## 7. Issues Found During This Review

| # | File | Issue | Severity |
|---|------|-------|----------|
| F1 | adaptive_paradigm.py:1216-1236 | `last_trial_snapshot` is saved TWICE (lines 1216-1222 and 1230-1236) — identical code block duplicated | Low (harmless but wasteful) |
| F2 | test_am.py vs paradigm_am.py | test_am uses `start=50.0` but paradigm_am's `__main__` block uses `start=16.0` — different units/values | Medium — which is correct? |
| F3 | All multiplicative paradigms | Final steps x0.7/x1.4 not exactly symmetric in log space | Low — ~0.2 dB bias |
| F4 | GAP test params | `max=0.020` (20 ms) seems low for impaired listeners who may need gaps up to 50-100 ms | Medium — check plan CSV |
