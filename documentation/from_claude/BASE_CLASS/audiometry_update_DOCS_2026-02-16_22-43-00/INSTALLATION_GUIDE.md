# Installation Guide - Data Management Updates

## 📦 Files Provided

### Modified Files (Replace in your project):
1. `adaptive_paradigm.py` - Base class with participant_id & paradigm_code
2. `paradigm_pta.py` - Added 'PTA' code
3. `paradigm_fm.py` - Added 'FM' code
4. `paradigm_am.py` - Added 'AM' code
5. `paradigm_gap.py` - Added 'GAP' code
6. `paradigm_dli.py` - Added 'DLI' code
7. `paradigm_ild.py` - Added 'ILD' code
8. `paradigm_itd.py` - Added 'ITD' code
9. `paradigm_ifmc.py` - Added 'IFMC' code

### New Files (Add to your project):
10. `utils/__init__.py` - Package initialization
11. `utils/result_loader.py` - Result loading with GUI
12. `utils/standard_frequencies.py` - Standard frequency definitions

### Documentation Files:
13. `CHANGES_MADE.md` - Complete changelog
14. `QUICK_REFERENCE.md` - Quick usage guide
15. `IMPLEMENTATION_SUMMARY.md` - Full implementation details
16. `verify_changes.py` - Automated verification script

---

## 🔧 Installation Steps

### Step 1: Backup Your Current Files
```bash
# Create backup directory
mkdir -p backup_$(date +%Y%m%d)

# Backup files that will be replaced
cp adaptive_paradigm.py backup_$(date +%Y%m%d)/
cp paradigm_*.py backup_$(date +%Y%m%d)/
```

### Step 2: Copy Modified Files
```bash
# Copy all modified paradigm files
cp /path/to/outputs/adaptive_paradigm.py .
cp /path/to/outputs/paradigm_pta.py .
cp /path/to/outputs/paradigm_fm.py .
cp /path/to/outputs/paradigm_am.py .
cp /path/to/outputs/paradigm_gap.py .
cp /path/to/outputs/paradigm_dli.py .
cp /path/to/outputs/paradigm_ild.py .
cp /path/to/outputs/paradigm_itd.py .
cp /path/to/outputs/paradigm_ifmc.py .
```

### Step 3: Create Utils Directory
```bash
# Create utils directory if it doesn't exist
mkdir -p utils

# Copy utils files
cp /path/to/outputs/utils/__init__.py utils/
cp /path/to/outputs/utils/result_loader.py utils/
cp /path/to/outputs/utils/standard_frequencies.py utils/
```

### Step 4: Copy Documentation
```bash
cp /path/to/outputs/CHANGES_MADE.md .
cp /path/to/outputs/QUICK_REFERENCE.md .
cp /path/to/outputs/IMPLEMENTATION_SUMMARY.md .
cp /path/to/outputs/verify_changes.py .
```

### Step 5: Verify Installation
```bash
# Run verification script
python verify_changes.py
```

**Expected output:**
```
Testing imports...
  ✓ ResultLoader imported
  ✓ Standard frequencies imported

Testing paradigm codes...
  ✓ ParadigmPTA: paradigm_code = 'PTA'
  ✓ ParadigmFM: paradigm_code = 'FM'
  ✓ ParadigmAM: paradigm_code = 'AM'
  ✓ ParadigmGAP: paradigm_code = 'GAP'
  ✓ ParadigmDLI: paradigm_code = 'DLI'
  ✓ ParadigmILD: paradigm_code = 'ILD'
  ✓ ParadigmITD: paradigm_code = 'ITD'
  ✓ ParadigmIFMC: paradigm_code = 'IFMC'

Testing participant_id parameter...
  ✓ participant_id set correctly: P999

Testing filename format...
  ✓ Filename format correct: PTEST_PTA_2026-02-16_15-30-45.csv
  ✓ Test file cleaned up

✓ ALL TESTS PASSED!
```

---

## ✅ What Changed

### Filename Format
**Before:**
```
results_2026-02-16_14-30-45.csv
```

**After:**
```
P001_PTA_2026-02-16_14-30-45.csv
```

### Paradigm Usage
**Before:**
```python
pta = ParadigmPTA(params)
pta.main()
```

**After:**
```python
pta = ParadigmPTA(params, participant_id="P001")
pta.main()
```

### New Capabilities
```python
# Load previous results
from utils.result_loader import ResultLoader

loader = ResultLoader()
data = loader.load_results("P001", "PTA", show_gui=True)

# Get thresholds
thresholds = loader.get_pta_thresholds("P001")

# Calculate IFMC probe levels
probe_amp = loader.get_ifmc_probe_level("P001", 1000)
```

---

## 📋 Directory Structure After Installation

```
your_project/
├── adaptive_paradigm.py          # Modified
├── paradigm_pta.py                # Modified
├── paradigm_fm.py                 # Modified
├── paradigm_am.py                 # Modified
├── paradigm_gap.py                # Modified
├── paradigm_dli.py                # Modified
├── paradigm_ild.py                # Modified
├── paradigm_itd.py                # Modified
├── paradigm_ifmc.py               # Modified
├── utils/                         # New directory
│   ├── __init__.py               # New
│   ├── result_loader.py          # New
│   ├── standard_frequencies.py   # New
│   └── varspec.py                # Existing
├── test_data/                     # Will contain results
│   ├── P001_PTA_*.csv
│   ├── P001_IFMC_*.csv
│   └── ...
├── CHANGES_MADE.md                # Documentation
├── QUICK_REFERENCE.md             # Documentation
├── IMPLEMENTATION_SUMMARY.md      # Documentation
└── verify_changes.py              # Test script
```

---

## 🧪 Testing After Installation

### Test 1: Run a paradigm with participant ID
```python
from paradigms.paradigm_pta import ParadigmPTA
from utils.varspec import VarSpec

params = {
    "inner": VarSpec(name="trial_amp", data={'start': 0.5}),
    "outer_1": VarSpec(name="fc", data=[1000])
}

pta = ParadigmPTA(params, participant_id="P001")
# Don't need to run full test, just check it creates properly
print(f"Paradigm code: {pta.paradigm_code}")
print(f"Participant ID: {pta.participant_id}")
```

**Expected:**
```
Paradigm code: PTA
Participant ID: P001
```

### Test 2: Check imports
```python
from utils.result_loader import ResultLoader
from utils.standard_frequencies import AUDIOMETRIC_FREQS

print("ResultLoader:", ResultLoader)
print("Frequencies:", AUDIOMETRIC_FREQS)
```

**Expected:**
```
ResultLoader: <class 'utils.result_loader.ResultLoader'>
Frequencies: [250, 500, 1000, 2000, 4000, 8000]
```

### Test 3: Full workflow (if you have PTA data)
```bash
# Run PTA for a participant
python test_pta.py
# Enter: P001

# Check file created
ls test_data/P001_PTA_*.csv

# Try loading it
python -c "
from utils.result_loader import ResultLoader
loader = ResultLoader()
data = loader.load_results('P001', 'PTA', show_gui=False)
print('Loaded:', len(data), 'trials')
"
```

---

## 🆘 Troubleshooting

### Error: "No module named 'utils'"
**Problem:** utils directory not in Python path

**Solution:**
```python
# Add to top of script
import sys
sys.path.insert(0, '/path/to/your/project')
```

Or make sure you're running from the project directory:
```bash
cd /path/to/your/project
python test_pta.py
```

### Error: "Paradigm code not set!"
**Problem:** Paradigm file not updated correctly

**Solution:** Check that the paradigm's `__init__` has:
```python
def __init__(self, params, ..., participant_id=None):
    self.paradigm_code = 'XXX'  # BEFORE super().__init__()
    super().__init__(params, ..., participant_id=participant_id)
```

### Error: "Cannot import ResultLoader"
**Problem:** utils/__init__.py missing or incorrect

**Solution:** Verify utils/__init__.py exists and contains:
```python
from .result_loader import ResultLoader
```

### GUI window doesn't appear
**Problem:** tkinter not installed or display issues

**Solution:**
```bash
# Install tkinter (if needed)
# On Ubuntu/Debian:
sudo apt-get install python3-tk

# On macOS (usually pre-installed)
# On Windows (usually pre-installed)
```

Or use without GUI:
```python
loader = ResultLoader()
data = loader.load_results("P001", "PTA", show_gui=False)
```

---

## 📝 Next Steps

1. ✅ Install files (copy to project)
2. ✅ Run verification script
3. ✅ Test with one paradigm
4. Update test scripts to prompt for participant_id
5. Test PTA → IFMC workflow
6. Update any documentation specific to your lab

---

## 💡 Tips

**Participant ID conventions:**
- Use consistent format (e.g., P001, P002, etc.)
- Include leading zeros for sorting (P001 not P1)
- Can use letters for groups (PA01, PB01, etc.)

**File organization:**
- Files automatically organized by participant and paradigm
- Easy to grep: `ls test_data/P001_*.csv`
- Easy to find latest: `ls -t test_data/P001_PTA_*.csv | head -1`

**Best practices:**
- Run PTA first for each participant
- Use AUDIOMETRIC_FREQS for consistency
- Always verify with show_gui=True first time
- Keep backups before making changes

---

## ✅ Verification Checklist

- [ ] All 9 paradigm files copied
- [ ] utils/ directory created with 3 files
- [ ] Documentation files copied
- [ ] verify_changes.py runs successfully
- [ ] Can create paradigm with participant_id
- [ ] Filename format is correct
- [ ] Can import ResultLoader
- [ ] Can import standard frequencies

Once all checked, you're ready to use the new system! 🎉

---

**Questions or issues?** See:
- `QUICK_REFERENCE.md` for usage examples
- `CHANGES_MADE.md` for complete changelog
- `IMPLEMENTATION_SUMMARY.md` for detailed implementation
