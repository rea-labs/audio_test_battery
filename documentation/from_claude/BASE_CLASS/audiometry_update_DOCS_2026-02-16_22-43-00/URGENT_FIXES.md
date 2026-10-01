# URGENT FIXES - Issues Found in Testing

## Three Issues Fixed

### Issue 1: GAP Paradigm Crash ✅ FIXED
**Error:** `ValueError: all the input arrays must have same number of dimensions`

**Cause:** GAP paradigm didn't specify `pan` parameter, causing stereo/mono dimension mismatch

**Fix:** Added `pan=0` to GAP's `new_trial()` call

**File:** `paradigm_gap.py` (line 145)

```python
# BEFORE:
self.tp.new_trial(
    wave_type="white",
    del_times=[gap],
    durations=[self.noise_before_gap, self.noise_after_gap],
    amp=self.noise_level,
    fade_time=self.fade_time,
    sample_accurate=True,
    verbose=False
)

# AFTER:
self.tp.new_trial(
    wave_type="white",
    del_times=[gap],
    durations=[self.noise_before_gap, self.noise_after_gap],
    amp=self.noise_level,
    fade_time=self.fade_time,
    pan=0,  # Mono/center (prevents stereo dimension mismatch)
    sample_accurate=True,
    verbose=False
)
```

---

### Issue 2: No Participant ID Prompt ✅ FIXED
**Problem:** Participant ID always defaulted to "P000"

**Cause:** Your test scripts don't include the participant ID prompt

**Fix:** Created updated test scripts with participant ID prompts

**Files Updated:**
- `test_gap.py` - New version with participant ID prompt
- `test_ifmc.py` - New version with full workflow

**How to Use:**
```python
# Add this function to any test script:
def get_participant_id(default="P001"):
    """Prompt user for participant ID."""
    while True:
        pid = input(f"\nEnter Participant ID [{default}]: ").strip()
        if not pid:
            return default
        if len(pid) >= 2:
            return pid
        print("⚠ Participant ID too short.")

# Then use it:
participant_id = get_participant_id()
paradigm = ParadigmXXX(params, participant_id=participant_id)
```

---

### Issue 3: IFMC Didn't Load PTA ✅ FIXED
**Problem:** No GUI appeared, no PTA loading attempted

**Cause:** test_ifmc.py didn't include result loading code

**Fix:** Updated test_ifmc.py with complete workflow

**New test_ifmc.py includes:**
1. Participant ID prompt
2. ResultLoader to find PTA file
3. GUI file selection (if PTA exists)
4. Manual threshold entry option (if no PTA)
5. Safe probe level calculation
6. Full error handling

**Usage:**
```bash
python test_ifmc.py

# You'll see:
# 1. "Enter Participant ID [P001]: " ← Type participant ID
# 2. "Looking for PTA results..."
# 3. GUI file picker (if PTA file exists)
#    OR
#    "Enter thresholds manually?" dialog (if no PTA)
# 4. Test runs with calculated probe levels
```

---

## Files That Need Updating

### Replace These Files:
1. **paradigm_gap.py** - Fixed stereo/mono issue
2. **test_gap.py** - New version with participant ID
3. **test_ifmc.py** - New version with PTA loading

### All Other Test Scripts Need Similar Updates:
- test_pta.py
- test_fm.py
- test_am.py
- test_dli.py
- test_ild.py
- test_itd.py

Each should add:
```python
from utils.participant_id_helper import get_participant_id

participant_id = get_participant_id()
paradigm = ParadigmXXX(params, participant_id=participant_id)
```

---

## Quick Fix for All Your Test Scripts

Add these 3 lines to the top of each test script:

```python
def get_participant_id(default="P001"):
    """Prompt user for participant ID."""
    pid = input(f"\nEnter Participant ID [{default}]: ").strip()
    return pid if pid else default

# Then before creating paradigm:
participant_id = get_participant_id()

# Then when creating paradigm, add participant_id:
paradigm = ParadigmXXX(params, participant_id=participant_id)  # Add this parameter
```

---

## Testing the Fixes

### Test 1: GAP (should not crash now)
```bash
python test_gap.py
# Enter participant ID when prompted
# Should run without stereo/mono error
```

### Test 2: Participant ID (should save with correct name)
```bash
python test_gap.py
# Enter: P123
# Check file created: ls test_data/P123_GAP_*.csv
```

### Test 3: IFMC with PTA (should show GUI)
```bash
# First run PTA for participant
python test_pta.py  # Enter P001

# Then run IFMC
python test_ifmc.py  # Enter P001
# Should see:
#   1. "Looking for PTA results..."
#   2. GUI file picker showing P001_PTA_*.csv
#   3. Thresholds loaded
#   4. Test runs
```

### Test 4: IFMC without PTA (should prompt for manual entry)
```bash
python test_ifmc.py  # Enter P999 (non-existent)
# Should see:
#   1. "No PTA results found"
#   2. Dialog: "Enter thresholds manually?"
#   3. If Yes: Entry form appears
```

---

## Summary

✅ **paradigm_gap.py** - Added `pan=0` to fix stereo/mono crash  
✅ **test_gap.py** - Added participant ID prompt  
✅ **test_ifmc.py** - Complete workflow with PTA loading  

**All three files are updated and ready in outputs directory.**

**Action Items:**
1. Download the 3 updated files
2. Replace in your project
3. Update other test scripts with participant ID prompts
4. Test GAP - should not crash
5. Test IFMC - should load PTA with GUI

---

## Template for Updating Other Test Scripts

```python
"""
Test script for XXX paradigm
"""

from paradigms.paradigm_xxx import ParadigmXXX
from utils.varspec import VarSpec


def get_participant_id(default="P001"):
    """Prompt user for participant ID with validation."""
    while True:
        pid = input(f"\nEnter Participant ID [{default}]: ").strip()
        if not pid:
            print(f"Using default: {default}")
            return default
        if len(pid) >= 2:
            return pid
        print("⚠ Participant ID too short. Please use at least 2 characters.")


def main():
    print("=" * 70)
    print(" XXX PARADIGM TEST")
    print("=" * 70)
    
    # Get participant ID
    participant_id = get_participant_id()
    
    # Configuration
    params = {
        # ... your params ...
    }
    
    # Create paradigm WITH participant_id
    xxx = ParadigmXXX(params, participant_id=participant_id)
    
    print(f"\nRunning test for participant: {participant_id}")
    input("Press ENTER to start...")
    
    try:
        xxx.main()
        print(f"\n>>> Test completed!")
        print(f"Results saved: {participant_id}_XXX_*.csv")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
```

Use this template to update all your test scripts!
