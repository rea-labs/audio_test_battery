# File Organization & Setup Instructions

## Directory Structure

Create the following directory structure for your project:

```
audiology_toolbox/
├── paradigms/
│   ├── __init__.py                    (empty file)
│   ├── adaptive_paradigm.py           (NEW - base class)
│   └── paradigm_pta.py                (NEW - PTA implementation)
├── utils/
│   ├── __init__.py                    (empty file)
│   └── varspec.py                     (EXISTING - from your project)
├── config/
│   ├── __init__.py                    (empty file)
│   └── DEFAULTS.py                    (EXISTING - from your project)
├── trial_player.py                    (EXISTING - from your project)
├── event_gen.py                       (EXISTING - from your project)
├── test_data/                         (created automatically)
│   └── results_YYYY-MM-DD_HH-MM-SS.csv
└── test_pta.py                        (NEW - test script)
```

---

## Files to Copy/Create

### ✅ **NEW FILES** (from outputs)

1. **`paradigms/adaptive_paradigm.py`**
   - Source: `/mnt/user-data/outputs/adaptive_paradigm.py`
   - This is the new base class
   - Copy to: `audiology_toolbox/paradigms/adaptive_paradigm.py`

2. **`paradigms/paradigm_pta.py`**
   - Source: Create from the code above
   - PTA implementation inheriting from base class
   - Copy to: `audiology_toolbox/paradigms/paradigm_pta.py`

3. **`test_pta.py`**
   - Source: Create from the code above
   - Test script to run PTA
   - Copy to: `audiology_toolbox/test_pta.py`

### ✅ **EXISTING FILES** (from your project)

4. **`trial_player.py`**
   - Source: `/mnt/project/trial_player.py`
   - Already working - no changes needed
   - Copy to: `audiology_toolbox/trial_player.py`

5. **`event_gen.py`**
   - Source: `/mnt/project/event_gen.py`
   - Already working - no changes needed
   - Copy to: `audiology_toolbox/event_gen.py`

6. **`utils/varspec.py`**
   - Source: `/mnt/project/varspec.py`
   - Already working - no changes needed
   - Copy to: `audiology_toolbox/utils/varspec.py`

7. **`config/DEFAULTS.py`**
   - Source: `/mnt/project/DEFAULTS.py`
   - Already exists - no changes needed
   - Copy to: `audiology_toolbox/config/DEFAULTS.py`

### ✅ **FILES TO CREATE** (empty __init__.py)

8. **`paradigms/__init__.py`**
   - Create empty file (makes it a Python package)

9. **`utils/__init__.py`**
   - Create empty file (makes it a Python package)

10. **`config/__init__.py`**
    - Create empty file (makes it a Python package)

---

## Step-by-Step Setup

### **Step 1: Create Directory Structure**

```bash
mkdir -p audiology_toolbox/paradigms
mkdir -p audiology_toolbox/utils
mkdir -p audiology_toolbox/config
```

### **Step 2: Create Empty __init__.py Files**

```bash
touch audiology_toolbox/paradigms/__init__.py
touch audiology_toolbox/utils/__init__.py
touch audiology_toolbox/config/__init__.py
```

### **Step 3: Copy Existing Files**

From your project directory:

```bash
# Copy existing working files
cp trial_player.py audiology_toolbox/
cp event_gen.py audiology_toolbox/
cp varspec.py audiology_toolbox/utils/
cp DEFAULTS.py audiology_toolbox/config/
```

### **Step 4: Copy New Files**

From the outputs:

```bash
# Copy new base class
cp adaptive_paradigm.py audiology_toolbox/paradigms/

# Copy new PTA implementation
cp paradigm_pta.py audiology_toolbox/paradigms/

# Copy test script
cp test_pta.py audiology_toolbox/
```

---

## Import Path Updates Needed

### **In `adaptive_paradigm.py`:**

The imports should be:
```python
from trial_player import TrialPlayer
from utils.varspec import VarSpec
```

These will work when running from the `audiology_toolbox/` directory.

### **In `paradigm_pta.py`:**

The imports should be:
```python
from paradigms.adaptive_paradigm import AdaptiveParadigm
from trial_player import TrialPlayer
from utils.varspec import VarSpec
```

### **In `test_pta.py`:**

The imports should be:
```python
from paradigms.paradigm_pta import ParadigmPTA
from utils.varspec import VarSpec
```

---

## Dependencies

Make sure your environment has these packages:

```bash
# Check your environment.yml or install:
pip install --break-system-packages psychopy psychtoolbox pandas numpy
```

Or use your existing conda environment:
```bash
conda activate psychopy  # or whatever your env is called
```

---

## Running the Test

### **From the `audiology_toolbox/` directory:**

```bash
cd audiology_toolbox
python test_pta.py
```

### **Expected Behavior:**

1. Prints test configuration
2. Asks you to press ENTER to start
3. Opens tkinter window with question: "Did you hear a tone?"
4. First trial: You should hear a loud tone (say "Yes")
5. Second trial: Silence/catch trial (say "No")
6. Subsequent trials: Adaptive difficulty
7. When complete, saves to `test_data/results_YYYY-MM-DD_HH-MM-SS.csv`

---

## Quick Visual Check

Your directory should look like this:

```
audiology_toolbox/
├── paradigms/
│   ├── __init__.py              ← Empty file
│   ├── adaptive_paradigm.py     ← NEW base class
│   └── paradigm_pta.py          ← NEW PTA implementation
├── utils/
│   ├── __init__.py              ← Empty file
│   └── varspec.py               ← EXISTING from project
├── config/
│   ├── __init__.py              ← Empty file
│   └── DEFAULTS.py              ← EXISTING from project
├── trial_player.py              ← EXISTING from project
├── event_gen.py                 ← EXISTING from project
└── test_pta.py                  ← NEW test script
```

---

## Troubleshooting

### **Import Errors?**

If you get `ModuleNotFoundError`:

1. Make sure you're running from the `audiology_toolbox/` directory
2. Check that `__init__.py` files exist in subdirectories
3. Verify file names match exactly (case-sensitive!)

### **PsychoPy/PTB Errors?**

If audio doesn't work:

1. Check your `environment.yml` matches your setup
2. Make sure PTB audio is properly configured
3. Try running a simple `trial_player.py` test first to verify audio works

### **GUI Doesn't Appear?**

On Mac, you may need to:
```bash
pythonw test_pta.py  # Instead of python
```

Or check that tkinter is properly installed.

---

## Next Steps After Testing

Once the PTA test works:

1. ✅ Verify data is saved correctly to CSV
2. ✅ Check that adaptive behavior makes sense (gets quieter when you detect)
3. ✅ Confirm catch trials work (get warning if you say "yes" to silence)
4. ✅ Review logged data structure

Then we can:
- Refactor GAP paradigm using the same pattern
- Create remaining paradigms (FM, AM, DLI, etc.)
- Build the full test battery

---

## Files Summary

| File | Status | Location | Purpose |
|------|--------|----------|---------|
| `adaptive_paradigm.py` | NEW | `paradigms/` | Base class with adaptive logic |
| `paradigm_pta.py` | NEW | `paradigms/` | PTA implementation |
| `test_pta.py` | NEW | `./` | Test script |
| `trial_player.py` | EXISTING | `./` | Trial assembly |
| `event_gen.py` | EXISTING | `./` | Sound generation |
| `varspec.py` | EXISTING | `utils/` | Parameter specs |
| `DEFAULTS.py` | EXISTING | `config/` | Default configs |

Ready to test! Let me know if you hit any issues.
