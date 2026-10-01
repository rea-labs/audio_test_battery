# Complete List of Changes Made to Project Files

## Summary

Successfully implemented data management improvements including:
1. **Filename format**: `{participant_ID}_{paradigm}_{timestamp}.csv`
2. **paradigm_code requirement**: All paradigms must set this
3. **GUI file selection**: User-friendly file picker with most recent default
4. **Safe dB conversion**: Multiple safety checks for IFMC probe levels
5. **Standard frequencies**: Consistent frequency sets across paradigms

---

## Files Modified

### 1. `/mnt/project/adaptive_paradigm.py` ✅

**Changes:**
- Added `participant_id` parameter to `__init__()`
- Added `paradigm_code` attribute (initially None, subclass must set)
- Updated `write_data_to_disk()`:
  - Checks that `paradigm_code` is set (raises ValueError if not)
  - New filename format: `{participant_id}_{paradigm_code}_{timestamp}.csv`
  - Returns filename path

**Key code:**
```python
def __init__(self, ..., participant_id=None):
    self.participant_id = participant_id or "P000"
    if not hasattr(self, 'paradigm_code'):
        self.paradigm_code = None  # Subclass must set!

def write_data_to_disk(self):
    if self.paradigm_code is None:
        raise ValueError(...)
    filename = f"{self.participant_id}_{self.paradigm_code}_{timestamp}.csv"
```

---

### 2. `/mnt/project/paradigm_pta.py` ✅

**Changes:**
- Added `participant_id` parameter to `__init__()`
- Set `self.paradigm_code = 'PTA'` BEFORE `super().__init__()`
- Passed `participant_id` to parent

**Key code:**
```python
def __init__(self, params, verbose=False, gui_config=None, participant_id=None):
    # CRITICAL: Set paradigm code BEFORE calling super().__init__()
    self.paradigm_code = 'PTA'
    ...
    super().__init__(params, ..., participant_id=participant_id)
```

---

### 3. `/mnt/project/paradigm_fm.py` ✅

**Changes:**
- Added `participant_id` parameter
- Set `self.paradigm_code = 'FM'`
- Updated super() call

---

### 4. `/mnt/project/paradigm_am.py` ✅

**Changes:**
- Added `participant_id` parameter
- Set `self.paradigm_code = 'AM'`
- Updated super() call

---

### 5. `/mnt/project/paradigm_gap.py` ✅

**Changes:**
- Added `participant_id` parameter
- Set `self.paradigm_code = 'GAP'`
- Updated super() call

---

### 6. `/mnt/project/paradigm_dli.py` ✅

**Changes:**
- Added `participant_id` parameter
- Set `self.paradigm_code = 'DLI'`
- Updated super() call

---

### 7. `/mnt/project/paradigm_ild.py` ✅

**Changes:**
- Added `participant_id` parameter
- Set `self.paradigm_code = 'ILD'`
- Updated super() call

---

### 8. `/mnt/project/paradigm_itd.py` ✅

**Changes:**
- Added `participant_id` parameter
- Set `self.paradigm_code = 'ITD'`
- Updated super() call

---

### 9. `/mnt/project/paradigm_ifmc.py` ✅

**Changes:**
- Added `participant_id` parameter
- Set `self.paradigm_code = 'IFMC'`
- Updated super() call

---

## Files Created

### 10. `/mnt/project/utils/__init__.py` ✅ NEW

**Purpose:** Make utils a proper Python package

**Contents:**
```python
from .result_loader import ResultLoader, get_pta_threshold
from .standard_frequencies import *
```

---

### 11. `/mnt/project/utils/result_loader.py` ✅ NEW

**Purpose:** Load and access previous test results with GUI file selection

**Key features:**
- `ResultLoader` class
- `find_results()` - Find all files for participant/paradigm
- `select_file_gui()` - GUI window for file selection
- `load_results()` - Load CSV data
- `get_pta_thresholds()` - Extract PTA thresholds in dB
- `get_ifmc_probe_level()` - Calculate safe IFMC probe level

**Safety features:**
- Thresholds loaded in dB (as stored)
- Conversion to amplitude using `TrialPlayer.db2amp()`
- Maximum amplitude ceiling (default 0.7)
- Absolute ceiling (1.0)
- Multiple warnings if clamping

**Example usage:**
```python
from utils.result_loader import ResultLoader

loader = ResultLoader()
# Shows GUI to select PTA file for P001
thresholds = loader.get_pta_thresholds("P001", show_gui=True)
# Returns: {500: 20.5, 1000: 18.2, ...} in dB

# Calculate safe probe level for IFMC
probe_amp = loader.get_ifmc_probe_level("P001", 1000)
# Returns amplitude (0-1) with safety checks
```

**GUI Features:**
- Shows most recent file by default
- Lists other available files
- "Accept (Most Recent)" button (Enter key)
- "Browse Other Files..." button (if multiple files)
- "Cancel" button (Escape key)
- Centered window

---

### 12. `/mnt/project/utils/standard_frequencies.py` ✅ NEW

**Purpose:** Standard frequency definitions used across paradigms

**Contents:**
```python
AUDIOMETRIC_FREQS = [250, 500, 1000, 2000, 4000, 8000]
EXTENDED_FREQS = [250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
QUICK_TEST_FREQS = [500, 1000, 2000, 4000]
IFMC_PROBE_FREQS = [500, 1000, 2000, 4000, 6000]
IFMC_MASKER_RATIOS = [0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6]
TMC_GAPS = [20, 40, 50, 60, 80]
```

**Usage:**
```python
from utils.standard_frequencies import AUDIOMETRIC_FREQS, IFMC_PROBE_FREQS

# Use in paradigm configuration
params = {
    "outer_1": VarSpec(name="fc", data=AUDIOMETRIC_FREQS)
}
```

---

## Paradigm Code Standards

All paradigms now have these codes:

| Paradigm | Code | Filename Pattern |
|----------|------|------------------|
| Pure Tone Audiogram | `PTA` | `P001_PTA_*.csv` |
| Gap Detection | `GAP` | `P001_GAP_*.csv` |
| Frequency Modulation | `FM` | `P001_FM_*.csv` |
| Amplitude Modulation | `AM` | `P001_AM_*.csv` |
| Difference Limen Intensity | `DLI` | `P001_DLI_*.csv` |
| Interaural Level Difference | `ILD` | `P001_ILD_*.csv` |
| Interaural Time Difference | `ITD` | `P001_ITD_*.csv` |
| Iso-Forward Masking Contour | `IFMC` | `P001_IFMC_*.csv` |

---

## How to Use

### Running a Paradigm

```python
from paradigms.paradigm_pta import ParadigmPTA
from utils.varspec import VarSpec

params = {...}

# Create paradigm with participant ID
pta = ParadigmPTA(params, participant_id="P001")
pta.main()

# Data saved to: test_data/P001_PTA_2026-02-16_14-30-45.csv
```

### Loading Previous Results

```python
from utils.result_loader import ResultLoader

loader = ResultLoader()

# Load PTA results (shows GUI)
pta_data = loader.load_results("P001", "PTA", show_gui=True)

# Get thresholds
thresholds = loader.get_pta_thresholds("P001")
# → {500: 22.3, 1000: 18.7, ...} in dB
```

### IFMC with Auto Probe Levels

```python
from paradigms.paradigm_ifmc import ParadigmIFMC
from utils.result_loader import ResultLoader
from utils.standard_frequencies import IFMC_PROBE_FREQS, IFMC_MASKER_RATIOS

participant_id = "P001"

# Load PTA thresholds
loader = ResultLoader()
thresholds = loader.get_pta_thresholds(participant_id, IFMC_PROBE_FREQS, show_gui=True)

if thresholds:
    # Calculate safe probe levels
    probe_levels = [
        loader.get_ifmc_probe_level(participant_id, freq)
        for freq in IFMC_PROBE_FREQS
        if freq in thresholds
    ]
    test_freqs = [f for f in IFMC_PROBE_FREQS if f in thresholds]
    
    # Configure IFMC
    params = {
        "inner": VarSpec(...),
        "outer_1": VarSpec(name="masker_freq_ratio", data=IFMC_MASKER_RATIOS),
        "outer_2": VarSpec(name="probe_freq", data=test_freqs),
        "outer_3": VarSpec(name="probe_level", data=probe_levels)
    }
    
    ifmc = ParadigmIFMC(params, participant_id=participant_id)
    ifmc.main()
else:
    print("Please run PTA first!")
```

---

## Error Handling

### If paradigm_code not set:

```python
# Forgot to set paradigm_code
class MyParadigm(AdaptiveParadigm):
    def __init__(self, params, **kwargs):
        super().__init__(params, **kwargs)  # Oops!

# Error when writing data:
ValueError: Paradigm code not set! 
Subclass MyParadigm must set self.paradigm_code in __init__ 
BEFORE calling super().__init__(). 
Example codes: 'PTA', 'FM', 'AM', 'GAP', 'DLI', 'ILD', 'ITD', 'IFMC', etc.
```

### If PTA results not found:

```python
loader = ResultLoader()
thresholds = loader.get_pta_thresholds("P999")
# → Shows warning dialog: "No PTA results found for participant P999"
# → Returns None
```

---

## Testing Checklist

### 1. Test PTA with new filename
```bash
python test_pta.py
# Enter participant ID: P001
# Check: File saved as test_data/P001_PTA_YYYY-MM-DD_HH-MM-SS.csv
```

### 2. Test result loader GUI
```python
from utils.result_loader import ResultLoader
loader = ResultLoader()
data = loader.load_results("P001", "PTA", show_gui=True)
# GUI should appear showing most recent PTA file
```

### 3. Test IFMC with auto probe levels
```bash
# First run PTA for participant
python test_pta.py  # Enter P001

# Then run IFMC
python test_ifmc.py  # Enter P001
# Should auto-detect PTA results and calculate probe levels
```

### 4. Verify all paradigms have codes
```python
# Try each paradigm - should all work:
from paradigms.paradigm_pta import ParadigmPTA
from paradigms.paradigm_fm import ParadigmFM
from paradigms.paradigm_am import ParadigmAM
# etc.

# Each should save with proper code in filename
```

---

## Benefits

✅ **Organized data** - Easy to find specific results  
✅ **Participant tracking** - All data linked by ID  
✅ **Auto-configuration** - IFMC uses PTA thresholds  
✅ **Safe probe levels** - Multiple safety checks  
✅ **User-friendly** - GUI file selection  
✅ **Standardized** - Consistent frequencies  
✅ **Enforced** - paradigm_code requirement  
✅ **Backward compatible** - Amplitudes still (0-1)  

---

## Next Steps

1. ✅ All changes applied to project files
2. Test PTA with participant ID
3. Test result loader GUI
4. Test IFMC auto-loading workflow
5. Update any test scripts to prompt for participant ID

All implementation complete! 🎯
