# Installation Checklist

## ✅ Complete Package - 24 Files Ready

### STEP 1: Download All Files ✓

**Documentation (9 files):**
- [ ] 00_START_HERE.md
- [ ] COMPLETE_FILE_LIST.md
- [ ] README.md
- [ ] INSTALLATION_GUIDE.md
- [ ] QUICK_REFERENCE.md
- [ ] MANUAL_ENTRY_GUIDE.md
- [ ] CHANGES_MADE.md
- [ ] IMPLEMENTATION_SUMMARY.md
- [ ] FILES_PROVIDED.md

**Paradigm Files (9 files):**
- [ ] adaptive_paradigm.py
- [ ] paradigm_pta.py
- [ ] paradigm_fm.py
- [ ] paradigm_am.py
- [ ] paradigm_gap.py
- [ ] paradigm_dli.py
- [ ] paradigm_ild.py
- [ ] paradigm_itd.py
- [ ] paradigm_ifmc.py

**Utils Files (4 files):**
- [ ] utils/__init__.py
- [ ] utils/result_loader.py
- [ ] utils/standard_frequencies.py
- [ ] utils/participant_id_helper.py

**Verification & Examples (2 files):**
- [ ] verify_changes.py
- [ ] COMPLETE_EXAMPLE_test_ifmc.py

---

### STEP 2: Backup Current Files ✓

```bash
mkdir backup_$(date +%Y%m%d)
cp adaptive_paradigm.py backup_$(date +%Y%m%d)/
cp paradigm_*.py backup_$(date +%Y%m%d)/
```

- [ ] Backup created
- [ ] Verified backup contents

---

### STEP 3: Install Files ✓

**Copy paradigm files:**
```bash
cp adaptive_paradigm.py /path/to/your/project/
cp paradigm_pta.py /path/to/your/project/
cp paradigm_fm.py /path/to/your/project/
cp paradigm_am.py /path/to/your/project/
cp paradigm_gap.py /path/to/your/project/
cp paradigm_dli.py /path/to/your/project/
cp paradigm_ild.py /path/to/your/project/
cp paradigm_itd.py /path/to/your/project/
cp paradigm_ifmc.py /path/to/your/project/
```

- [ ] All 9 paradigm files copied

**Create and populate utils directory:**
```bash
mkdir -p /path/to/your/project/utils
cp utils/__init__.py /path/to/your/project/utils/
cp utils/result_loader.py /path/to/your/project/utils/
cp utils/standard_frequencies.py /path/to/your/project/utils/
cp utils/participant_id_helper.py /path/to/your/project/utils/
```

- [ ] Utils directory created
- [ ] All 4 utils files copied

**Copy verification script:**
```bash
cp verify_changes.py /path/to/your/project/
```

- [ ] verify_changes.py copied

---

### STEP 4: Verify Installation ✓

```bash
cd /path/to/your/project
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
  ✓ participant_id set correctly

Testing filename format...
  ✓ Filename format correct
  ✓ Test file cleaned up

✓ ALL TESTS PASSED!
```

- [ ] All tests passed
- [ ] No errors reported

---

### STEP 5: Test Basic Functionality ✓

**Test 1: Participant ID prompt**
```python
from utils.participant_id_helper import get_participant_id

participant_id = get_participant_id()
print(f"Got: {participant_id}")
```

- [ ] Prompt appears
- [ ] ID returned correctly

**Test 2: Create paradigm with participant ID**
```python
from paradigms.paradigm_pta import ParadigmPTA
from utils.varspec import VarSpec

params = {
    "inner": VarSpec(name="trial_amp", data={'start': 0.5}),
    "outer_1": VarSpec(name="fc", data=[1000])
}

pta = ParadigmPTA(params, participant_id="TEST")
print(f"Paradigm code: {pta.paradigm_code}")
print(f"Participant ID: {pta.participant_id}")
```

- [ ] Creates without error
- [ ] paradigm_code = 'PTA'
- [ ] participant_id = 'TEST'

**Test 3: Import utilities**
```python
from utils.result_loader import ResultLoader
from utils.standard_frequencies import AUDIOMETRIC_FREQS

print("ResultLoader:", ResultLoader)
print("Frequencies:", AUDIOMETRIC_FREQS)
```

- [ ] Imports successfully
- [ ] No errors

---

### STEP 6: Test Complete Workflow ✓

**Run a full PTA test:**
```python
from paradigms.paradigm_pta import ParadigmPTA
from utils.participant_id_helper import get_participant_id
from utils.standard_frequencies import AUDIOMETRIC_FREQS

participant_id = get_participant_id()

params = {
    "inner": VarSpec(name="trial_amp", data={'start': 0.5}),
    "outer_1": VarSpec(name="fc", data=AUDIOMETRIC_FREQS)
}

pta = ParadigmPTA(params, participant_id=participant_id)
pta.main()
```

- [ ] Prompts for participant ID
- [ ] Test runs
- [ ] File saved with correct name: `{ID}_PTA_{timestamp}.csv`

**Test result loading:**
```python
from utils.result_loader import ResultLoader

loader = ResultLoader()
data = loader.load_results(participant_id, "PTA", show_gui=True)
```

- [ ] GUI appears (if PTA file exists)
- [ ] Data loads successfully

**Test manual threshold entry:**
```python
thresholds = loader.get_pta_thresholds(
    "NEWID",  # Non-existent participant
    [500, 1000, 2000, 4000],
    allow_manual_entry=True
)
```

- [ ] Prompt appears: "Enter thresholds manually?"
- [ ] Entry form appears (if Yes clicked)
- [ ] Validation works
- [ ] Thresholds returned correctly

---

### STEP 7: File Organization Check ✓

**Verify directory structure:**
```
your_project/
├── adaptive_paradigm.py          ✓
├── paradigm_pta.py                ✓
├── paradigm_fm.py                 ✓
├── paradigm_am.py                 ✓
├── paradigm_gap.py                ✓
├── paradigm_dli.py                ✓
├── paradigm_ild.py                ✓
├── paradigm_itd.py                ✓
├── paradigm_ifmc.py               ✓
├── utils/                         ✓
│   ├── __init__.py               ✓
│   ├── result_loader.py          ✓
│   ├── standard_frequencies.py   ✓
│   └── participant_id_helper.py  ✓
├── verify_changes.py              ✓
└── test_data/                     (will be created)
```

- [ ] All files in correct locations
- [ ] utils/ is a directory (not file)
- [ ] verify_changes.py executable

---

### STEP 8: Documentation Review ✓

**Read in order:**
1. [ ] 00_START_HERE.md - Overview
2. [ ] README.md - Package summary
3. [ ] INSTALLATION_GUIDE.md - Install steps
4. [ ] QUICK_REFERENCE.md - Usage examples
5. [ ] MANUAL_ENTRY_GUIDE.md - New features

**Optional reading:**
- [ ] CHANGES_MADE.md - Detailed changelog
- [ ] IMPLEMENTATION_SUMMARY.md - Technical details

---

## ✅ Final Verification

### All checks passed:
- [ ] All 24 files downloaded
- [ ] Backup created
- [ ] Files copied to correct locations
- [ ] verify_changes.py passes all tests
- [ ] Participant ID prompt works
- [ ] Paradigm creates with participant_id
- [ ] Utilities import successfully
- [ ] Full workflow tested (PTA run)
- [ ] File naming correct
- [ ] Result loading works
- [ ] Manual entry works
- [ ] Directory structure correct
- [ ] Documentation reviewed

### Ready for production:
- [ ] Team trained on new features
- [ ] Test scripts updated with participant ID prompts
- [ ] Standard frequencies in use
- [ ] Backup procedure established

---

## 🎉 Installation Complete!

**You can now:**
✅ Track participants by ID
✅ Organized file management
✅ Load previous results with GUI
✅ Enter thresholds manually if needed
✅ Use standard frequencies across tests
✅ Safe probe level calculation
✅ Auto-load PTA for IFMC

**Next steps:**
1. Update your test scripts to use participant ID prompts
2. Run PTA for a test participant
3. Run IFMC and watch it auto-load PTA thresholds
4. Enjoy your professional test battery!

---

**Questions?** See documentation files or review INSTALLATION_GUIDE.md troubleshooting section.

**Success!** 🚀
