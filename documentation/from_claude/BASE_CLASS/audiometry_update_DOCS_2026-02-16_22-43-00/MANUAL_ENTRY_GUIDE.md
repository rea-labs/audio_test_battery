# Participant ID and Manual Threshold Entry - User Guide

## Overview

Two new features added to make the system more flexible:

1. **Participant ID Prompt** - Helper function to get participant ID from user
2. **Manual Threshold Entry** - Enter thresholds manually if no PTA file exists

---

## Feature 1: Participant ID Prompt

### Helper Function

Add this to your test scripts:

```python
def get_participant_id(default="P001"):
    """Prompt user for participant ID with validation."""
    while True:
        pid = input(f"\nEnter Participant ID [{default}]: ").strip()
        
        if not pid:
            pid = default
            print(f"Using default: {pid}")
            return pid
        
        # Basic validation
        if len(pid) < 2:
            print("⚠ Participant ID too short. Please use at least 2 characters.")
            continue
        
        return pid
```

### Usage in Test Script

```python
# At the start of your test script
participant_id = get_participant_id(default="P001")

# Then pass to paradigm
pta = ParadigmPTA(params, participant_id=participant_id)
pta.main()
```

### User Experience

```
Enter Participant ID [P001]: P005
Running test for participant: P005
...
Data saved to: test_data/P005_PTA_2026-02-16_14-30-45.csv
```

Or press Enter for default:
```
Enter Participant ID [P001]: ← (just press Enter)
Using default: P001
```

---

## Feature 2: Manual Threshold Entry

### When It Activates

Automatically offered when:
1. `get_pta_thresholds()` is called
2. No PTA file found for the participant
3. `allow_manual_entry=True` (default)

### How It Works

**Step 1: Initial Dialog**
```
┌─────────────────────────────────────────┐
│         No PTA Results Found             │
│                                          │
│ No PTA results found for participant    │
│ P002.                                    │
│                                          │
│ Would you like to enter thresholds      │
│ manually?                                │
│                                          │
│ You will be prompted to enter threshold │
│ (in dB) for each frequency:             │
│ 500, 1000, 2000, 4000, 6000 Hz         │
│                                          │
│           [Yes]        [No]              │
└─────────────────────────────────────────┘
```

**Step 2: Threshold Entry Form** (if Yes)
```
┌─────────────────────────────────────────┐
│    Enter PTA Thresholds - P002          │
├─────────────────────────────────────────┤
│ Enter threshold in dB for each          │
│ frequency:                               │
│ (Typical range: 0-80 dB)                │
│                                          │
│   500 Hz:  [  25  ] dB                  │
│  1000 Hz:  [  20  ] dB                  │
│  2000 Hz:  [  18  ] dB                  │
│  4000 Hz:  [  30  ] dB                  │
│  6000 Hz:  [  35  ] dB                  │
│                                          │
│     [✓ Submit]       [Cancel]           │
└─────────────────────────────────────────┘
```

### Code Example

```python
from utils.result_loader import ResultLoader

loader = ResultLoader()

# With manual entry option (default)
thresholds = loader.get_pta_thresholds(
    "P002",
    [500, 1000, 2000, 4000, 6000],
    show_gui=True,           # Show file picker if files exist
    allow_manual_entry=True  # Offer manual entry if no files
)

# Result (from manual entry):
# {500: 25.0, 1000: 20.0, 2000: 18.0, 4000: 30.0, 6000: 35.0}
```

### Validation

**Missing values:**
- All fields required
- Error shown if any field empty

**Invalid numbers:**
- Must be valid float
- Error shown for non-numeric input

**Unusual values:**
- Warning if threshold < -20 or > 120 dB
- User can accept or re-enter

**Example validation:**
```
You entered: 150 dB at 1000 Hz

┌─────────────────────────────────────────┐
│           Unusual Value                  │
│                                          │
│ Threshold at 1000 Hz seems unusual:     │
│ 150 dB                                   │
│                                          │
│ Typical range: 0-80 dB                  │
│                                          │
│ Accept this value anyway?               │
│                                          │
│           [Yes]        [No]              │
└─────────────────────────────────────────┘
```

---

## Complete Workflow Examples

### Example 1: Normal Workflow (PTA file exists)

```python
# test_ifmc.py
participant_id = get_participant_id()  # User enters: P001

loader = ResultLoader()
thresholds = loader.get_pta_thresholds(
    participant_id,
    IFMC_PROBE_FREQS,
    allow_manual_entry=True
)

# → GUI shows: "P001_PTA_2026-02-16_10-00-00.csv"
# → User clicks: "Accept"
# → Thresholds loaded from file ✓
```

### Example 2: No PTA File - Manual Entry

```python
participant_id = get_participant_id()  # User enters: P002

loader = ResultLoader()
thresholds = loader.get_pta_thresholds(
    participant_id,
    IFMC_PROBE_FREQS,
    allow_manual_entry=True
)

# → No file found
# → Dialog: "Enter thresholds manually?"
# → User clicks: "Yes"
# → Entry form appears
# → User enters thresholds
# → User clicks: "Submit"
# → Thresholds returned ✓
```

### Example 3: Decline Manual Entry

```python
participant_id = get_participant_id()  # User enters: P003

loader = ResultLoader()
thresholds = loader.get_pta_thresholds(
    participant_id,
    IFMC_PROBE_FREQS,
    allow_manual_entry=True
)

# → No file found
# → Dialog: "Enter thresholds manually?"
# → User clicks: "No"
# → thresholds = None
# → Program should handle gracefully
```

### Example 4: Disable Manual Entry

```python
# Force file loading only (no manual entry option)
thresholds = loader.get_pta_thresholds(
    participant_id,
    IFMC_PROBE_FREQS,
    allow_manual_entry=False  # No manual entry
)

# → No file found
# → No dialog shown
# → thresholds = None immediately
```

---

## Integration with IFMC

```python
from utils.standard_frequencies import IFMC_PROBE_FREQS
from utils.result_loader import ResultLoader

# Get participant ID
participant_id = get_participant_id()

# Load or enter thresholds
loader = ResultLoader()
thresholds = loader.get_pta_thresholds(
    participant_id,
    IFMC_PROBE_FREQS,
    allow_manual_entry=True
)

if thresholds:
    # Calculate probe levels
    probe_levels = [
        loader.get_ifmc_probe_level(participant_id, freq)
        for freq in IFMC_PROBE_FREQS
        if freq in thresholds
    ]
    
    test_freqs = [f for f in IFMC_PROBE_FREQS if f in thresholds]
    
    # Configure IFMC
    params = {
        "outer_2": VarSpec(name="probe_freq", data=test_freqs),
        "outer_3": VarSpec(name="probe_level", data=probe_levels)
    }
    
    ifmc = ParadigmIFMC(params, participant_id=participant_id)
    ifmc.main()
else:
    print("Cannot run IFMC without thresholds")
    print("Please run PTA first or enter thresholds manually")
```

---

## Keyboard Shortcuts

**Threshold Entry Dialog:**
- `Tab` - Move to next field
- `Shift+Tab` - Move to previous field
- `Enter` - Submit (when on last field)
- `Escape` - Cancel

---

## Tips

1. **Keep PTA files** - Faster than manual entry
2. **Verify manual entries** - Double-check your values
3. **Typical thresholds:**
   - Normal hearing: 0-25 dB
   - Mild loss: 25-40 dB
   - Moderate loss: 40-70 dB
   - Severe loss: 70+ dB

4. **Validation ranges:**
   - Acceptable: -20 to 120 dB
   - Typical: 0 to 80 dB
   - Warning for values outside typical range

---

## Files Provided

1. `utils/participant_id_helper.py` - Helper function
2. `utils/result_loader.py` - Updated with manual entry
3. `COMPLETE_EXAMPLE_test_ifmc.py` - Full example

---

## Summary

✅ **Participant ID**: Simple prompt with validation  
✅ **Manual Entry**: GUI form for thresholds when no file  
✅ **Validation**: Checks for missing/invalid/unusual values  
✅ **Flexible**: Can enable/disable manual entry option  
✅ **User-Friendly**: Clear dialogs and error messages  

Both features make the system more flexible for different testing scenarios! 🎯
