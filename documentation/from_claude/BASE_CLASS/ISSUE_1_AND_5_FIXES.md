# Fixes for Issues #1 and #5

## Issue #1: Make Start Randomization Derive from Step Size

### Change in `paradigm_pta.py`, `initialize_adaptive_param()` method:

**Replace lines 63-80 with:**

```python
if isinstance(self.inner_var.data, dict):
    base_start = self.inner_var.data.get('start', 1.0)
    
    # Get initial step size to derive randomization range
    # Per MultiThreshold: randomize within +/- half of large step size
    step_down_initial = abs(self.inner_var.data.get('step_down_initial', -10))
    randomize_dB = step_down_initial / 2.0  # Half of initial step
    
    # Add random offset in dB space
    base_start_dB = TrialPlayer.amp2db(base_start)
    offset_dB = random.uniform(-randomize_dB, randomize_dB)
    randomized_start_dB = base_start_dB + offset_dB
    
    # Convert back to amplitude and clip to valid range
    self.trial_amp = TrialPlayer.db2amp(randomized_start_dB)
    min_amp = self.inner_var.data.get('min', 0.001)
    max_amp = self.inner_var.data.get('max', 1.0)
    self.trial_amp = max(min_amp, min(max_amp, self.trial_amp))
    
    if self.verbose:
        print(f"Initial amplitude: {self.trial_amp:.4f} ({TrialPlayer.amp2db(self.trial_amp):.1f} dB)")
        print(f"  (base: {base_start_dB:.1f} dB, offset: {offset_dB:+.1f} dB, range: +/-{randomize_dB:.1f} dB)")
```

**What changed:**
- Removed `randomize_start` parameter
- Now calculates `randomize_dB = step_down_initial / 2.0`
- If you change `step_down_initial` to -20, randomization automatically becomes +/-10 dB
- Added range to verbose output for verification

---

## Issue #5: Fix Catch Trial Rate Logic (Per-Run, Not Per-Trial)

### Change in `adaptive_paradigm.py`, `__init__()` method:

**Add after line 90 (after performance tracking variables):**

```python
# === CATCH TRIAL PER-RUN TRACKING ===
self._had_false_positive_this_run = False  # Track if FP occurred in current run
```

### Change in `adaptive_paradigm.py`, `update_counters()` method:

**Add after the FP counter increment (around line 448):**

```python
elif self.correct_answer == 'FP':
    self.total_FP += 1
    self._had_false_positive_this_run = True  # ADD THIS LINE
    # Don't change streak on false positive
```

### Change in `adaptive_paradigm.py`, `update_trial_params()` method:

**Replace lines 639-653 (the catch trial rate update section) with:**

```python
# Update catch trial rate PER-RUN (not per-trial)
# Only adjust at end of run (when moving to next config)
# This happens BEFORE the config reset, so we can check the flag
if self.end_config:
    # Adjust catch rate based on whether run had false positives
    if self._had_false_positive_this_run:
        # Increase rate if participant was caught out
        self._current_catch_trial_rate += self.catch_trial_rate[2]
        if self.verbose:
            print(f"  False positive detected - increasing catch rate")
    else:
        # Decrease rate if participant was NOT caught (perfect run)
        self._current_catch_trial_rate -= self.catch_trial_rate[2]
        if self.verbose:
            print(f"  No false positives - decreasing catch rate")
    
    # Clip to min/max
    self._current_catch_trial_rate = np.clip(
        self._current_catch_trial_rate,
        self.catch_trial_rate[1],  # min
        self.catch_trial_rate[3]   # max
    )
    
    if self.verbose:
        print(f"  New catch trial rate: {self._current_catch_trial_rate:.2f}")
```

### Change in `adaptive_paradigm.py`, config reset section:

**Add to the reset block (after line 627, after resetting catch rate):**

```python
self._current_catch_trial_rate = self.catch_trial_rate[0]
self._had_false_positive_this_run = False  # ADD THIS: Reset FP flag for new run
```

**What changed:**
- Added `_had_false_positive_this_run` flag to track if ANY false positives occurred during the run
- Moved catch rate adjustment from per-trial to per-run (only when `end_config` is True)
- Only decreases catch rate if ENTIRE run had NO false positives
- Only increases catch rate if run HAD false positives
- Resets flag at start of each new run

---

## Summary of Behavior Changes

### Issue #1:
**Before:** Randomization was +/-5 dB regardless of step size
**After:** Randomization is +/- half of initial step (e.g., +/-5 dB for -10 dB step, +/-10 dB for -20 dB step)

### Issue #5:
**Before:** Catch rate adjusted after every trial based on TP/TN
**After:** Catch rate adjusted once per run - increases if run had FP, decreases if run had no FPs

Both changes now match the MultiThreshold protocol exactly!
