# PROLACTIN Testing Plan
*Priority 3 — Validation of control flow, parameters, and output data*

---

## Approach

Two-phase testing:
1. **Simulation testing** — `MockParticipant` auto-responds; validates logic without human
2. **Human pilot testing** — real runs; validates UX, timing, output data quality

All tests should log results to CSV and be inspectable post-hoc. Tests should cover: starting values, step sizes, reversal detection, trial counting, threshold estimation, catch trial logic, config sequencing, and data output format.

---

## MockParticipant Design

### Concept

`MockParticipant` replaces the human participant with a simulated responder driven by a logistic psychometric function. The key parameters are the true threshold (50% detection point) and slope (steepness). With these, you can predict what a "perfect" participant with a known threshold would respond, run the adaptive procedure, and verify that the estimated threshold converges to the known true threshold.

The slope parameter `k` is in paradigm-native units (dB⁻¹, ms⁻¹, etc.). The Lecluyse paper uses a Boltzmann sigmoid — the implementation below matches that convention. A slope of `k=0.5` in dB units gives a "normal" psychometric function width of ~4 dB between 25% and 75% detection.

### Implementation

```python
import random
import math

class MockParticipant:
    """
    Simulates participant responses for automated testing.
    Uses a Boltzmann sigmoid psychometric function (per Lecluyse & Meddis 2009).
    
    The paradigm's adaptive_param_value is passed to respond().
    Units must match the paradigm (dB for PTA/IFMC/TMC, ms for GAP, % for AM/FM, etc.)
    """
    def __init__(self, true_threshold, slope=0.5, false_positive_rate=0.05):
        """
        Args:
            true_threshold: 50% detection point in paradigm-native units
                            PTA: dB HL (e.g., 20.0)
                            GAP: ms (e.g., 5.0)
                            AM/FM: % modulation (e.g., 5.0)
                            IFMC/TMC: dB SPL masker level (e.g., 50.0)
                            DLI: dB level difference (e.g., 3.0)
                            ILD: dB (e.g., 5.0)
                            ITD: microseconds (e.g., 30.0)
            slope: Psychometric slope k (steeper = more precise listener)
                   Typical values: 0.3-1.0 for dB-based paradigms
            false_positive_rate: p(respond=1 | catch trial), typically 0.0-0.1
        """
        self.threshold = true_threshold
        self.slope = slope
        self.fp_rate = false_positive_rate
    
    def p_detect(self, level):
        """Boltzmann sigmoid: p(detect) = 1 / (1 + exp(-k*(x - theta)))"""
        return 1.0 / (1.0 + math.exp(-self.slope * (level - self.threshold)))
    
    def respond(self, level, is_catch=False):
        """
        Return 1 (detected) or 0 (not detected).
        
        Args:
            level: Current adaptive parameter value (same units as true_threshold)
            is_catch: If True, respond based on false_positive_rate only
        Returns:
            int: 1 = "yes I heard it", 0 = "no"
        """
        if is_catch:
            return 1 if random.random() < self.fp_rate else 0
        return 1 if random.random() < self.p_detect(level) else 0
```

### Integration with AdaptiveParadigm

The cleanest integration is to subclass the paradigm and override `get_response()`. This avoids modifying production code:

```python
class MockParadigmPTA(ParadigmPTA):
    """PTA paradigm with simulated participant responses."""
    
    def __init__(self, params, mock_participant, **kwargs):
        self.mock = mock_participant
        kwargs.setdefault('verbose', False)
        super().__init__(params, **kwargs)
    
    def get_response(self):
        """Return simulated response instead of waiting for GUI input."""
        # self.trial_amp is the current adaptive parameter for PTA
        level_db = TrialPlayer.amp2db(self.trial_amp)
        return self.mock.respond(level_db, is_catch=self.is_catch_trial)
    
    def setup_gui(self):
        """Skip GUI creation entirely."""
        pass  # No tkinter window needed
```

You need a `MockParadigm` variant for each paradigm type because the adaptive parameter name differs (`self.trial_amp` for PTA, `self.gap_duration` for GAP, `self.mod_ind` for AM/FM, etc.). A shared base helps:

```python
class MockAdaptiveParadigm:
    """Mixin — override in each paradigm subclass."""
    
    def __init_subclass__(cls, adaptive_attr=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._adaptive_attr = adaptive_attr  # e.g. 'trial_amp', 'gap_duration'
    
    def get_response(self):
        level = getattr(self, self._adaptive_attr)
        # Convert to dB if needed (paradigm-specific)
        return self.mock.respond(level, is_catch=self.is_catch_trial)
    
    def setup_gui(self):
        pass
```

### Running simulations

```python
import numpy as np

def run_simulation(paradigm_class, params, true_threshold, n_runs=50, slope=0.5):
    """
    Run n_runs adaptive threshold measurements with a MockParticipant.
    Returns list of estimated thresholds.
    """
    estimates = []
    for i in range(n_runs):
        mock = MockParticipant(true_threshold, slope=slope)
        p = paradigm_class(params, mock_participant=mock, participant_id="SIM")
        p.main()
        # Extract final threshold estimates from data
        thresholds = p.data[p.data['threshold_dB'].notna()]['threshold_dB'].tolist()
        estimates.extend(thresholds)
    return estimates

estimates = run_simulation(MockParadigmPTA, pta_params, true_threshold=25.0)
print(f"True threshold: 25.0 dB")
print(f"Mean estimate:  {np.mean(estimates):.1f} dB  (bias: {np.mean(estimates)-25:.1f} dB)")
print(f"Std deviation:  {np.std(estimates):.1f} dB")
```

### Practical notes

- Start with PTA since it's the simplest (linear dB steps, amplitude-only adaptive param). Get the simulation working there before extending to other paradigms.
- AM and FM use multiplicative steps and the adaptive parameter is in % — make sure the `level` passed to `respond()` and `true_threshold` are in the same units. For AM, `mod_ind` in % is the natural unit; threshold might be ~5% for a normal listener.
- GAP: `gap_duration` is in seconds internally. Pass `level * 1000` (ms) to `respond()` and set `true_threshold` in ms (e.g., 3.0 ms for a normal listener).
- For IFMC/TMC, the adaptive parameter is masker level in dB SPL. Set `true_threshold` to a plausible masker threshold (e.g., 50 dB SPL on-frequency).
- DLI uses a 3-alternative response (0/1/2). The MockParticipant above only handles binary yes/no. For DLI, the correct response is the interval with the louder tone; the mock needs to know which interval was louder. Simplest approach: have `MockParadigmDLI.get_response()` check `self.louder_interval` (or equivalent) and respond with probability based on `self.level_diff_dB`.
- Disable GUI creation in mock subclasses (override `setup_gui()` to no-op) so simulations run headlessly without requiring a display.

---

---

## Test Suite

### T1 — Adaptive Tracking Logic

**Goal:** Confirm step sizes, reversal detection, trial counting match protocol.

**Method:** Run MockParticipant at known threshold for each paradigm. Inspect CSV output.

**Checks:**
- [ ] Starting level is correct (PTA: 40 dB HL; GAP: 16 ms; AM/FM: starting mod depth per plan)
- [ ] Step sizes: verify large step before 1st reversal, small step after (paradigm-specific)
- [ ] Reversal #1 triggered only after direction change from initial descent
- [ ] Trial count begins at reversal #1 (not trial #1)
- [ ] Config ends after `trials_after_reversal` trials post-reversal-#1
- [ ] Threshold = arithmetic mean of post-criterion reversal values (not midpoint of last two levels unless that's the implementation choice — confirm which)
- [ ] `config_num` increments correctly; 0-based/1-based consistent throughout

**Paradigms to test:** PTA, GAP, AM, FM (after fix), IFMC, TMC

---

### T2 — Catch Trial Logic

**Goal:** Confirm catch trial rate starts at protocol value and adapts correctly.

**Method:** Run with MockParticipant with known false positive rate (e.g., 5%).

**Checks:**
- [ ] Initial catch trial rate matches spec (check PROLACTIN plan CSV per paradigm)
- [ ] Catch trials randomly interleaved (not periodic)
- [ ] After a false positive in a run: catch rate reduces in NEXT run (not same run)
- [ ] `_had_false_positive_this_run` resets between runs
- [ ] Catch trial response = 0 → TN; response = 1 → FP; FP counted correctly
- [ ] FP rate reported in output CSV

---

### T3 — Starting Level & Step Size Per Paradigm

Values drawn from `test_xxx.py` and `paradigm_xxx.py`. Step mode: **Add** = linear additive; **Mult** = multiplicative (step is a ratio: ×0.5 = halve, ×2.0 = double). All values need to be cross-checked against the PROLACTIN plan CSV and team expectations.

| Paradigm | Adaptive param | Start | Large step (down/up) | Small step (down/up) | Min | Max | Step mode |
|----------|---------------|-------|---------------------|---------------------|-----|-----|-----------|
| PTA | `trial_amp` (dB) | 0.5 amp (~−6 dB FS) | −10 / +10 dB | −2 / +2 dB | 0.001 amp | 1.0 amp | Add (dB) |
| GAP | `gap_duration` (s) | 0.010 s (10 ms) | −5 / +5 ms | −1 / +1 ms | 0.001 s (1 ms) | 0.020 s (20 ms) | Add (ms) |
| AM | `mod_ind` (%) | 0.5% (=50% if as fraction? — ⚠ verify units) | ×0.5 / ×2.0 | ×0.7 / ×1.4 | 0.01% | 1.0% | Mult |
| FM | `mod_ind` (%) | 8% | ×0.5 / ×2.0 | ×0.7 / ×1.4 | 0.1% | 20% | Mult |
| DLI | `level_diff_dB` (dB) | 5.0 dB | ×0.5 / ×2.0 | ×0.7 / ×1.4 | 0.1 dB | 20 dB | Mult |
| IFMC | `masker_level` (dB SPL) | 20 dB SPL | −10 / +10 dB | −2 / +2 dB | 0 dB SPL | 100 dB SPL | Add (dB) |
| TMC | `masker_level` (dB SPL) | 10 dB SPL | −10 / +10 dB | −2 / +2 dB | 0 dB SPL | 100 dB SPL | Add (dB) |
| ILD | `ild_dB` (dB) | 15 dB | ×0.5 / ×2.0 | ×0.7 / ×1.4 | 0.5 dB | 32 dB | Mult |
| ITD | `itd_us` (μs) | 50 μs | ×0.5 / ×2.0 | ×0.7 / ×1.4 | 0.01 μs | 100 μs | Mult |
| LDL | `amp` (linear) | 0.2 amp | +3 dB/trial | — (no reversal) | — | 0.9 amp | Add (dB), ascending only |

**Flags and questions to resolve:**

- **PTA start**: Code starts at `amp=0.5` (≈ −6 dB FS), which with randomization (±half of 10 dB large step = ±5 dB) gives ~1 dB FS to −11 dB FS. Confirm this is appropriate — it's not "40 dB HL" until calibration maps dB FS → dB SPL → dB HL.
- **GAP max**: Currently 20 ms. This is quite short — Lecluyse uses up to 200+ ms for some TMC conditions. Confirm 20 ms max is intentional for GAP detection (not TMC).
- **AM start**: `start=0.5` in test_am.py. The paradigm uses this as a fraction (0–1), so 0.5 = 50% modulation depth. This is a reasonable starting point for detection but may be too high — confirm with team. Prague protocol uses 16% start (per paradigm_am.py `__main__`).
- **AM/FM small step**: ×0.7 / ×1.4 is an asymmetric multiplicative step (~−3.1 dB / +2.9 dB in log space). MultiThreshold uses equal steps. Intended?
- **IFMC/TMC start**: IFMC starts at 20 dB SPL, TMC at 10 dB SPL. Both very low — participant hears probe easily at start, then masker level tracks up until probe is masked. This is the correct direction. Verify these are reasonable given your probe level calibration.
- **LDL**: Not adaptive in the reversal sense — just ascending until participant reports discomfort. No reversal logic, no threshold estimation via sigmoid. Check that 0.2 start and 3 dB step don't go too loud too fast (0.2 amp → 0.9 amp = ~13 dB, so 4–5 trials max before hitting ceiling).
- **ILD/ITD**: Both broken currently (ILD: no panning; ITD: works but bypasses TrialPlayer). Don't test parameters until fixes are in.
- **Global**: `trials_after_reversal = 10` (set in `adaptive_paradigm.py:121`). This applies to all paradigms. Lecluyse 2009 (Eq. 3) suggests n=26 trials for 1 dB accuracy at k=0.5. 10 trials gives ~1.6 dB accuracy — acceptable for clinical screening but not high-precision research. Confirm this is intentional.
- **Global catch trial rate**: Starts at 20%, adapts to min 10% if false positives occur (step −10%, max rebound to 50%). Verify initial 20% matches PROLACTIN plan.

**Check:** For each paradigm, verify values in `test_xxx.py` match the PROLACTIN plan CSV column by column.

---

### T4 — Config Sequencing

**Goal:** All configs (outer variable combinations) run exactly once.

**Checks:**
- [ ] N configs created = product of all outer variable list lengths
- [ ] Each config runs independently (adaptive state resets between configs)
- [ ] Config metadata (freq, duration, etc.) logged correctly per trial in CSV
- [ ] Paradigm ends after last config, not before

---

### T5 — Output Data Format

**Goal:** CSV output contains all required columns with correct values.

**Required columns (minimum):**
`participant_id, paradigm_code, config_num, trial_num, adaptive_param_value, response, correct_response, outcome (TP/FN/TN/FP), is_catch, reversal_num, threshold_dB, timestamp`

**Checks:**
- [ ] All columns present
- [ ] No NaN values in non-optional fields
- [ ] `outcome` is one of {TP, FN, TN, FP} for every trial
- [ ] `threshold_dB` populated at config end, NaN during config (or running estimate)
- [ ] File writes correctly on Mac and Windows (path separators, line endings)
- [ ] File not overwritten if re-run (timestamp suffix or error)

---

### T6 — Stimulus Validation (Acoustic)

**Goal:** Confirm synthesized stimuli are perceptually and numerically correct. Requires audio analysis.

**Method:** Generate stimuli at known parameters, analyze with scipy/librosa or export and inspect in Audacity/REW.

**Checks by paradigm:**

**PTA:**
- [ ] Pure tone at specified frequency (FFT peak at correct freq)
- [ ] Level scales correctly with dB parameter (20 dB step → ~10× amplitude ratio)
- [ ] Silence segments have expected duration

**GAP:**
- [ ] White noise with gap at correct position
- [ ] Gap duration matches parameter (sample-accurate)
- [ ] Catch trial (gap=0) is continuous noise

**AM:**
- [ ] Carrier at fc, modulation sidebands at fc±fm
- [ ] Modulation depth = mod_ind% (verify with AM demodulation)
- [ ] Catch trial (mod_ind=0) is unmodulated tone

**FM (after fix):**
- [ ] Frequency deviation = fc * mod_ind/100 Hz at peak
- [ ] Sidebands at expected Bessel function amplitudes (for small mod_ind)
- [ ] Verify after fix that deviation matches parameter

**IFMC/TMC:**
- [ ] Masker and probe at independently specified levels
- [ ] Gap between masker and probe matches parameter
- [ ] Probe level = PTA threshold + 10 dB SL (verify against loaded thresholds)

**ILD (after fix):**
- [ ] Left/right channel level difference matches ild_dB parameter
- [ ] Verify with channel-separated analysis

**ITD:**
- [ ] Interaural time delay = itd_us microseconds
- [ ] Verify with cross-correlation of left/right channels

---

### T7 — Threshold Estimation Accuracy

**Goal:** Confirm estimated threshold is close to MockParticipant's true threshold.

**Method:** Run 20+ simulated sessions at each of 3 known thresholds. Compare estimated vs true.

**Checks:**
- [ ] Mean estimated threshold within ±2 dB (or equivalent units) of true threshold
- [ ] Standard deviation of estimates < 5 dB across sessions
- [ ] Psychometric function fit parameters (theta, k) logged to CSV
- [ ] Running estimate in operator GUI converges toward final estimate

---

### T8 — Operator GUI Integration

**Goal:** Operator display shows correct real-time data.

**Method:** Run paradigm with MockParticipant, visually inspect GUI.

**Checks:**
- [ ] Window appears on paradigm start
- [ ] Adaptive track plot updates after each trial
- [ ] TP/FN/TN/FP color coding correct (green/red/gray)
- [ ] Threshold history updates after each config completes
- [ ] Psychometric curve appears and updates during config (not just at end)
- [ ] Text stats (trial num, streak, reversals, threshold estimate) match CSV data
- [ ] No focus stealing from participant GUI
- [ ] No crash when paradigm ends

---

### T9 — Multi-Paradigm Session

**Goal:** Confirm IFMC and TMC correctly load PTA thresholds and compute probe levels.

**Method:** Run PTA → save results → run IFMC with ResultLoader.

**Checks:**
- [ ] ThresholdReviewDialog shows correct loaded values
- [ ] Probe level = loaded threshold + 10 dB SL (verify against manual calculation)
- [ ] Safety warning shown for unusual threshold values (< 0 dB HL or > 80 dB HL)
- [ ] Editing a threshold in the dialog updates probe level in real time
- [ ] Cancelling dialog stops paradigm gracefully

---

### T10 — Human Pilot Tests

Run each paradigm with a real participant (team member). Focus on:

- [ ] Instructions are clear; participant understands task
- [ ] Response buttons work; no missed or double responses
- [ ] Audio levels are appropriate (not too loud/soft before calibration)
- [ ] Paradigm duration is reasonable (flag if any config takes > 10 min)
- [ ] Operator GUI readable from typical monitoring distance
- [ ] Data file written and openable after session

**Recommended order:** PTA → GAP → AM → DLI → FM → IFMC → TMC → ITD → ILD → LDL

---

## Test Infrastructure

### File structure
```
tests/
  mock_participant.py       # MockParticipant class
  test_adaptive_logic.py    # T1, T2, T4
  test_parameters.py        # T3
  test_output_format.py     # T5
  test_stimuli.py           # T6 (generates WAVs for inspection)
  test_threshold_accuracy.py # T7
  test_gui_integration.py   # T8 (requires display, run manually)
  run_all_simulations.py    # runs T1-T7 headlessly, outputs pass/fail report
```

### Pass/fail reporting
Each test should print: `[PASS]` / `[FAIL: reason]` per check. Final summary: N passed, M failed.

---

## Pre-Testing Blockers (must fix first)

1. Import path resolution (audit #4, #5)
2. FM mod_ind fix (audit #1.3)
3. ILD pan fix (audit #5.9)
4. OperatorDisplay integration (supplement A.1)
5. Calibration (Priority 2) — required for T6 level checks to be meaningful
