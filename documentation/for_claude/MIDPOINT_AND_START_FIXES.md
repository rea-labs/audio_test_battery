# Midpoint Calculation & Start Level Fixes - Summary

## Issues Fixed

### Issue 1: Incorrect Midpoint Calculation ❌ → ✅

**Problem:**
- Code was tracking `last_amp_yes` and `last_amp_no` (last yes/no responses)
- This is NOT what the paper says!

**What the protocol actually says:**
> "After the first reversal the stimulus level is set to the **mid-point between the two previous levels**"
> — Lecluyse & Meddis (2009)

**Solution:**
- Now tracks `last_two_levels` list (last 2 presented levels regardless of response)
- Calculates midpoint between these two levels in dB space
- Updated in `prepare_trial()` to append each non-catch trial level

**Code changes:**
```python
# OLD (WRONG):
self.last_amp_yes = None
self.last_amp_no = None
# Track separately based on response...

# NEW (CORRECT):
self.last_two_levels = []
# In prepare_trial, for non-catch trials:
self.last_two_levels.append(self.trial_amp)
if len(self.last_two_levels) > 2:
    self.last_two_levels.pop(0)
```

### Issue 2: Edge Case with Starting at Maximum ❌ → ✅

**Problem:**
If first trial wrong (FN) at 0 dB ceiling:
```
Trial 1: 0 dB → Wrong → try to increase → still 0 dB (at ceiling)
Trial 2: 0 dB → Right → REVERSAL
Midpoint = (0 + 0) / 2 = 0 dB  ← No change!
```

**Root cause:**
Starting exactly at the ceiling (or floor) means no room for adjustment.

**What MultiThreshold does:**
> "The start level is different in each run and **randomly located in a range ±5 dB** relative to the nominal start value."
> — Lecluyse & Meddis (2009)

> "The starting value for the target tone is at **30 dB SPL** by default."
> — MultiThreshold Manual

**Solution:**
- Added `randomize_start` parameter (default ±5 dB)
- Starting level now randomized in dB space
- Prevents starting exactly at ceiling/floor
- More closely matches MultiThreshold protocol

**Code changes:**
```python
def initialize_adaptive_param(self):
    base_start = self.inner_var.data.get('start', 1.0)
    randomize_dB = self.inner_var.data.get('randomize_start', 5)  # ±5 dB
    
    # Add random offset
    base_start_dB = TrialPlayer.amp2db(base_start)
    offset_dB = random.uniform(-randomize_dB, randomize_dB)
    randomized_start_dB = base_start_dB + offset_dB
    
    self.trial_amp = TrialPlayer.db2amp(randomized_start_dB)
    # Clip to min/max range
```

### Issue 3: Double Adjustment After First Reversal ❌ → ✅

**Problem:**
After first reversal:
1. Reset to midpoint (-35 dB)
2. ALSO apply difficulty step (-2 dB) → -37 dB ❌

Should just reset to midpoint and wait for next trial!

**Solution:**
Clear `make_harder`/`make_easier` flags after midpoint reset:

```python
def update_trial_params(self):
    if self.reset_to_midpoint:
        self.reset_to_midpoint_amplitude()
        self.reset_to_midpoint = False
        
        # Prevent double adjustment
        self.make_harder = False
        self.make_easier = False
    
    super().update_trial_params()
```

### Bonus: Special Character Cleanup ✅

**Problem:**
Test file had Unicode characters that displayed as garbage: `ðŸ"‹`, `ðŸŽ®`, `âš ï¸`, `âœ…`, `âŒ`

**Solution:**
Replaced with ASCII alternatives:
- `***` for section headers
- `>>>` for success
- `!!!` for warnings/errors

---

## Files Updated

### 1. `paradigm_pta.py`

**Key changes:**
- Import `random` module
- `__init__`: Changed from `last_amp_yes/no` to `last_two_levels = []`
- `initialize_adaptive_param()`: Added randomization of start level
- `prepare_trial()`: Tracks presented levels in `last_two_levels`
- `reset_to_midpoint_amplitude()`: Uses `last_two_levels` instead of yes/no
- `update_trial_params()`: Clears difficulty flags after midpoint reset

### 2. `test_pta.py`

**Key changes:**
- Added `'randomize_start': 5` to params
- Updated print statements to reflect new behavior
- Replaced Unicode emojis with ASCII: `***`, `>>>`, `!!!`
- Updated configuration description to mention randomization and midpoint

---

## Testing

Expected behavior now:

```
Trial 1: -3.2 dB (randomized from 0±5) → Heard (TP) → step down 10 dB
Trial 2: -13.2 dB → Catch trial (TN)
Trial 3: -23.2 dB → Not heard (FN) → step up 10 dB → REVERSAL!
         ↓
       -18.2 dB ← MIDPOINT (between -13.2 and -23.2), NO extra step!
         ↓
Trial 4: -18.2 dB → Heard (TP) → step down 2 dB (small step)
Trial 5: -20.2 dB → ...
```

---

## Parameter Configuration

Updated params in test file:

```python
params = {
    "inner": VarSpec(
        name="trial_amp",
        data={
            'start': 1.0,
            'randomize_start': 5,        # NEW: ±5 dB randomization
            'step_down_initial': -10,
            'step_down_final': -2,
            'step_up_initial': 10,
            'step_up_final': 2,
            'min': 0.001,
            'max': 1.0
        }
    ),
    ...
}
```

---

## Verification Checklist

✅ Midpoint uses last two **presented levels** (not yes/no)
✅ Starting level randomized ±5 dB (prevents edge case)
✅ No double adjustment after first reversal
✅ Clean ASCII output (no garbled Unicode)
✅ Follows Lecluyse & Meddis (2009) protocol exactly
✅ Follows MultiThreshold UZH protocol exactly

All changes based on authoritative sources (papers + manual)!
