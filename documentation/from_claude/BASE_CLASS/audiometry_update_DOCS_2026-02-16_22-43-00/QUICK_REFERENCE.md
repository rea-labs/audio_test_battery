# Quick Reference: What Changed

## ✅ All Files Updated

### Modified Files (9 total):
1. `adaptive_paradigm.py` - Base class updates
2. `paradigm_pta.py` - Added PTA code
3. `paradigm_fm.py` - Added FM code
4. `paradigm_am.py` - Added AM code
5. `paradigm_gap.py` - Added GAP code
6. `paradigm_dli.py` - Added DLI code
7. `paradigm_ild.py` - Added ILD code
8. `paradigm_itd.py` - Added ITD code
9. `paradigm_ifmc.py` - Added IFMC code

### New Files (3 total):
10. `utils/__init__.py` - Package initialization
11. `utils/result_loader.py` - Result loading with GUI
12. `utils/standard_frequencies.py` - Standard frequency definitions

---

## Key Changes

### 1. Filename Format Changed
**Before:**
```
results_2026-02-16_14-30-45.csv
```

**After:**
```
P001_PTA_2026-02-16_14-30-45.csv
```

**Pattern:** `{participant_ID}_{paradigm}_{timestamp}.csv`

---

### 2. Each Paradigm Now Has Code

**Every paradigm's `__init__` now includes:**
```python
def __init__(self, params, verbose=False, gui_config=None, participant_id=None):
    # MUST set BEFORE super().__init__()
    self.paradigm_code = 'PTA'  # or 'FM', 'AM', etc.
    
    super().__init__(params, ..., participant_id=participant_id)
```

**Codes assigned:**
- PTA, FM, AM, GAP, DLI, ILD, ITD, IFMC

---

### 3. How to Run Paradigms Now

**Option 1: Pass participant_id directly**
```python
pta = ParadigmPTA(params, participant_id="P001")
pta.main()
```

**Option 2: Update test scripts to prompt**
```python
participant_id = input("Participant ID [P001]: ") or "P001"
pta = ParadigmPTA(params, participant_id=participant_id)
pta.main()
```

**Result:**
```
Data saved to: test_data/P001_PTA_2026-02-16_14-30-45.csv
```

---

### 4. Loading Previous Results

**New utility available:**
```python
from utils.result_loader import ResultLoader

loader = ResultLoader()

# Load with GUI (shows file selection window)
data = loader.load_results("P001", "PTA", show_gui=True)

# Get PTA thresholds in dB
thresholds = loader.get_pta_thresholds("P001")
# Returns: {500: 22.3, 1000: 18.7, ...}

# Calculate IFMC probe level (with safety checks)
probe_amp = loader.get_ifmc_probe_level("P001", 1000)
# Returns: 0.032 (safe amplitude)
```

---

### 5. Standard Frequencies Available

**New module:**
```python
from utils.standard_frequencies import AUDIOMETRIC_FREQS, IFMC_PROBE_FREQS

# Use in paradigms
params = {
    "outer_1": VarSpec(name="fc", data=AUDIOMETRIC_FREQS)
}
```

**Definitions:**
- `AUDIOMETRIC_FREQS = [250, 500, 1000, 2000, 4000, 8000]`
- `IFMC_PROBE_FREQS = [500, 1000, 2000, 4000, 6000]`
- `IFMC_MASKER_RATIOS = [0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6]`

---

## Example Workflow: PTA → IFMC

### Step 1: Run PTA
```python
from paradigms.paradigm_pta import ParadigmPTA

params = {...}
pta = ParadigmPTA(params, participant_id="P001")
pta.main()
# Saves: test_data/P001_PTA_2026-02-16_10-00-00.csv
```

### Step 2: Run IFMC (auto-loads PTA)
```python
from paradigms.paradigm_ifmc import ParadigmIFMC
from utils.result_loader import ResultLoader
from utils.standard_frequencies import IFMC_PROBE_FREQS, IFMC_MASKER_RATIOS

loader = ResultLoader()

# Load PTA thresholds (GUI shows file selection)
thresholds = loader.get_pta_thresholds("P001", IFMC_PROBE_FREQS, show_gui=True)

# Calculate safe probe levels
probe_levels = [
    loader.get_ifmc_probe_level("P001", freq)
    for freq in IFMC_PROBE_FREQS if freq in thresholds
]

test_freqs = [f for f in IFMC_PROBE_FREQS if f in thresholds]

# Configure IFMC with auto-calculated levels
params = {
    "inner": VarSpec(...),
    "outer_1": VarSpec(name="masker_freq_ratio", data=IFMC_MASKER_RATIOS),
    "outer_2": VarSpec(name="probe_freq", data=test_freqs),
    "outer_3": VarSpec(name="probe_level", data=probe_levels)
}

ifmc = ParadigmIFMC(params, participant_id="P001")
ifmc.main()
# Saves: test_data/P001_IFMC_2026-02-16_10-30-00.csv
```

---

## Safety Features

### IFMC Probe Level Safety
1. **Thresholds in dB** - Stored and loaded properly
2. **dB to amplitude** - Uses `TrialPlayer.db2amp()`
3. **Max ceiling** - Default 0.7 (70%)
4. **Absolute ceiling** - Never exceeds 1.0
5. **Warnings** - Alerts if clamping needed

**Example:**
```python
# PTA threshold at 1kHz = 20 dB
# Probe = 20 + 10 = 30 dB
# Amplitude = db2amp(30) = 0.032 ✓ Safe!

# If threshold was 80 dB (very loud)
# Probe = 80 + 10 = 90 dB
# Amplitude = db2amp(90) = 31.6 ✗ Too loud!
# Clamped to: 0.7 ✓ Safe!
# Warning: "Clamping to 0.7"
```

---

## Error Messages

### If forgot paradigm_code:
```
ValueError: Paradigm code not set! 
Subclass MyParadigm must set self.paradigm_code in __init__ 
BEFORE calling super().__init__(). 
Example codes: 'PTA', 'FM', 'AM', 'GAP', 'DLI', 'ILD', 'ITD', 'IFMC', etc.
```

**Fix:** Add to paradigm's `__init__`:
```python
self.paradigm_code = 'XXX'  # Before super().__init__()
```

---

## Testing

### Quick Test
```bash
# Run a paradigm
python test_pta.py

# When prompted, enter:
Participant ID: P001

# Check file created:
ls test_data/P001_PTA_*.csv
```

### Test Result Loader
```python
from utils.result_loader import ResultLoader

loader = ResultLoader()
data = loader.load_results("P001", "PTA", show_gui=True)
# GUI window should appear
```

---

## File Organization

```
test_data/
├── P001_PTA_2026-02-16_10-00-00.csv
├── P001_PTA_2026-02-16_10-15-30.csv
├── P001_FM_2026-02-16_10-30-00.csv
├── P001_AM_2026-02-16_10-45-00.csv
├── P001_IFMC_2026-02-16_11-00-00.csv
├── P002_PTA_2026-02-16_14-00-00.csv
└── P002_FM_2026-02-16_14-15-00.csv
```

Easy to:
- Find all tests for P001
- Find specific paradigm results
- Track chronological order
- Auto-load related data

---

## Summary

✅ All 12 files updated/created  
✅ Filename format: `{participant}_{paradigm}_{timestamp}`  
✅ All paradigms have codes  
✅ GUI file selection  
✅ Safe probe level calculation  
✅ Standard frequencies defined  
✅ Ready to test!

See `CHANGES_MADE.md` for complete details.
