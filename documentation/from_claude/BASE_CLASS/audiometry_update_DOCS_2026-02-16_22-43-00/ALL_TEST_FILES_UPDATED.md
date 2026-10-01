# All Test Files Updated with Participant ID Prompts

## ✅ Complete Set of Test Scripts

All 8 test files now include participant ID prompts and proper file naming.

---

## Files Provided

1. **test_pta.py** - Pure Tone Audiogram
2. **test_fm.py** - Frequency Modulation
3. **test_am.py** - Amplitude Modulation
4. **test_gap.py** - Gap Detection
5. **test_dli.py** - Difference Limen Intensity
6. **test_ild.py** - Interaural Level Difference
7. **test_itd.py** - Interaural Time Difference
8. **test_ifmc.py** - Iso-Forward Masking Contour (with PTA loading)

---

## Features in All Test Files

### Participant ID Prompt
Every test file includes:
```python
def get_participant_id(default="P001"):
    """Prompt user for participant ID."""
    while True:
        pid = input(f"\nEnter Participant ID [{default}]: ").strip()
        if not pid:
            print(f"Using default: {default}")
            return default
        if len(pid) >= 2:
            return pid
        print("⚠ Participant ID too short.")
```

### Proper File Naming
Results automatically saved as:
```
{participant_id}_{paradigm}_{timestamp}.csv

Examples:
P001_PTA_2026-02-16_14-30-45.csv
P001_FM_2026-02-16_14-35-20.csv
P001_GAP_2026-02-16_14-40-15.csv
```

### Standard Frequencies
PTA, FM, AM, DLI use standard audiometric frequencies:
```python
from utils.standard_frequencies import AUDIOMETRIC_FREQS
# [250, 500, 1000, 2000, 4000, 8000] Hz
```

### Error Handling
All test files include try/except blocks with traceback

---

## Special Features

### test_ifmc.py - Complete Workflow

Includes full PTA integration:

1. **Participant ID prompt**
2. **Search for PTA file**
   - Shows GUI file picker if PTA exists
   - Offers manual threshold entry if no PTA
3. **Safe probe level calculation**
   - Loads thresholds in dB
   - Converts with safety ceiling (0.7 max)
4. **Automatic configuration**
   - Only tests frequencies with valid thresholds
   - Uses standard IFMC parameters

**Usage:**
```bash
# First run PTA
python test_pta.py
# Enter: P001

# Then run IFMC
python test_ifmc.py
# Enter: P001
# GUI appears showing PTA file
# Thresholds loaded automatically
# Test runs with calculated probe levels
```

---

## Usage Examples

### Basic Usage (PTA, FM, AM, GAP, DLI)
```bash
python test_pta.py

Enter Participant ID [P001]: P123

Participant: P123
Frequencies: [250, 500, 1000, 2000, 4000, 8000] Hz

Press ENTER to start...
# Test runs...
>>> Results saved: P123_PTA_2026-02-16_14-30-45.csv
```

### Spatial Tests (ILD, ITD)
```bash
python test_ild.py

Enter Participant ID [P001]: P456

Participant: P456

Press ENTER to start...
# Test runs...
>>> Results saved: P456_ILD_2026-02-16_15-00-00.csv
```

### IFMC with PTA Loading
```bash
# Run PTA first
python test_pta.py
Enter Participant ID [P001]: P789
# ... test completes ...

# Run IFMC
python test_ifmc.py
Enter Participant ID [P001]: P789

Looking for PTA results...
# GUI shows: P789_PTA_2026-02-16_14-30-45.csv
# Click "Accept"

✓ Thresholds available for 5 frequencies
  500 Hz: 22.3 dB → 0.041 amplitude
  1000 Hz: 18.7 dB → 0.027 amplitude
  2000 Hz: 20.1 dB → 0.032 amplitude
  4000 Hz: 25.6 dB → 0.061 amplitude
  6000 Hz: 30.2 dB → 0.103 amplitude

Testing 5 frequencies × 7 ratios
# ... test runs ...
>>> Results saved: P789_IFMC_2026-02-16_15-15-30.csv
```

---

## File Organization

After running tests for participant P001:
```
test_data/
├── P001_PTA_2026-02-16_10-00-00.csv
├── P001_FM_2026-02-16_10-30-00.csv
├── P001_AM_2026-02-16_11-00-00.csv
├── P001_GAP_2026-02-16_11-30-00.csv
├── P001_DLI_2026-02-16_12-00-00.csv
├── P001_ILD_2026-02-16_12-30-00.csv
├── P001_ITD_2026-02-16_13-00-00.csv
└── P001_IFMC_2026-02-16_13-30-00.csv
```

Easy to find all tests for one participant:
```bash
ls test_data/P001_*.csv
```

---

## Installation

Simply copy all 8 test files to your project directory.

**Replace your existing test files with these new versions.**

---

## What's Different from Your Old Test Files

### OLD (your current files):
```python
# No participant ID prompt
# Default ID always "P000"
# Files named: results_timestamp.csv

from paradigm_PTA import ParadigmPTA
pta = ParadigmPTA(params)  # No participant_id
pta.main()
# Saves: results_2026-02-16_14-30-45.csv
```

### NEW (these files):
```python
# Prompts for participant ID
# Custom ID for each run
# Files named: {ID}_{paradigm}_{timestamp}.csv

from paradigms.paradigm_pta import ParadigmPTA
participant_id = get_participant_id()
pta = ParadigmPTA(params, participant_id=participant_id)
pta.main()
# Saves: P001_PTA_2026-02-16_14-30-45.csv
```

---

## Summary

✅ **8 test files** - All paradigms covered  
✅ **Participant ID prompts** - User enters ID each time  
✅ **Proper file naming** - Easy to organize and find  
✅ **Standard frequencies** - Consistent across tests  
✅ **IFMC integration** - Auto-loads PTA thresholds  
✅ **Error handling** - Graceful error messages  
✅ **Ready to use** - Just copy and run!  

All files provided above. Download and replace your existing test files! 🎯
