# CRITICAL FIX - GAP Still Crashing

## Root Cause Found

The issue is in **trial_player.py**, not paradigm_gap.py!

### The Problem

When `sample_accurate=True`, trial_player.py concatenates stereo sounds but initializes with:
```python
tmp_snd = []  # This is 1D (empty list)
```

Then tries to concatenate stereo sounds (NÃ—2 arrays):
```python
tmp_snd = np.concatenate((tmp_snd, sound_list[i].sound))  # ERROR!
# Can't concatenate 1D [] with 2D stereo array
```

### The Fix

**File:** `trial_player.py` (lines 192-199)

**BEFORE:**
```python
if self.sample_accurate:
    tmp_snd = []  # ← WRONG: 1D empty list
    del_array = np.concatenate((self.del_times*self.fs, [0]))
    del_array = np.int32(del_array)
    for i in range(self.num_events):
        tmp_snd = np.concatenate((tmp_snd, sound_list[i].sound))
        tmp_snd = np.concatenate((tmp_snd, np.zeros(del_array[i])))  # ← WRONG: 1D zeros
    new_t = np.linspace(0, np.size(tmp_snd)/self.fs, np.size(tmp_snd))
```

**AFTER:**
```python
if self.sample_accurate:
    tmp_snd = np.zeros((0, 2))  # ✓ CORRECT: Stereo empty array (0Ã—2 shape)
    del_array = np.concatenate((self.del_times*self.fs, [0]))
    del_array = np.int32(del_array)
    for i in range(self.num_events):
        tmp_snd = np.concatenate((tmp_snd, sound_list[i].sound))
        if del_array[i] > 0:
            tmp_snd = np.concatenate((tmp_snd, np.zeros((del_array[i], 2))))  # ✓ CORRECT: Stereo zeros
    new_t = np.linspace(0, np.size(tmp_snd, axis=0)/self.fs, np.size(tmp_snd, axis=0))
```

### Key Changes:

1. **Initialize as stereo:** `np.zeros((0, 2))` instead of `[]`
   - Creates empty stereo array with shape (0, 2)
   - Matches the stereo sounds being concatenated

2. **Add stereo silence:** `np.zeros((del_array[i], 2))` instead of `np.zeros(del_array[i])`
   - Creates stereo silence with shape (N, 2)
   - Matches the stereo waveform shape

3. **Use axis parameter:** `np.size(tmp_snd, axis=0)` instead of `np.size(tmp_snd)`
   - Gets number of samples (rows) not total elements
   - Correctly handles stereo arrays

---

## Files to Update

**CRITICAL - Replace this file:**
- **trial_player.py** ← This is the actual fix!

**Also update (from previous fixes):**
- paradigm_gap.py (has pan=0 which is still needed)
- test_gap.py (has participant ID prompt)
- test_ifmc.py (has PTA loading)

---

## Why This Wasn't Caught Earlier

The stereo panning feature added `_make_stereo_from_pan()` which creates stereo sounds (NÃ—2 arrays).

Previously, when all sounds were mono (1D arrays), concatenating with an empty list `[]` worked fine.

Now with stereo sounds, the empty list initialization fails because you can't concatenate:
- 1D array: `[]`
- with 2D array: `[[L1, R1], [L2, R2], ...]`

---

## Test After Fix

```bash
python test_gap.py
# Should work now without stereo/mono error
```

The error should be completely gone!

---

## Summary

✅ **trial_player.py** - Fixed sample_accurate stereo concatenation  
✅ **paradigm_gap.py** - Already has pan=0 (still needed)  
✅ **test_gap.py** - Has participant ID prompt  
✅ **test_ifmc.py** - Has PTA loading workflow  

**Download and replace trial_player.py - this is the critical fix!**
