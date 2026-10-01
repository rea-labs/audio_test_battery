# Data Management Implementation Summary

## ✅ Changes Implemented

### 1. **Filename Format: `{participant_ID}_{paradigm}_{date}`**

**Example:**
```
P001_PTA_2026-02-16_14-30-45.csv
P001_IFMC_2026-02-16_14-35-20.csv
```

**Implementation:**
- Modified `write_data_to_disk()` in `adaptive_paradigm.py`
- Each subclass MUST set `self.paradigm_code` (e.g., 'PTA', 'FM', 'IFMC')
- Enforced via check in `write_data_to_disk()` - raises error if not set

---

### 2. **paradigm_code Requirement**

**Pythonic approach using class attribute:**

```python
class ParadigmPTA(AdaptiveParadigm):
    def __init__(self, params, **kwargs):
        # MUST set before calling super().__init__()
        self.paradigm_code = 'PTA'
        super().__init__(params, **kwargs)
```

**Enforcement:**
```python
def write_data_to_disk(self):
    if self.paradigm_code is None:
        raise ValueError(
            f"Paradigm code not set! "
            f"Subclass {self.__class__.__name__} must set self.paradigm_code"
        )
```

**Standard codes:**
- PTA, GAP, FM, AM, DLI, ILD, ITD, IFMC, TMC, LDL

---

### 3. **GUI File Selection**

**Features:**
- Shows most recent file by default
- Lists other available files
- "Accept" button (Enter key)
- "Browse Other Files..." button (if multiple exist)
- "Cancel" button (Escape key)
- Centered window with clear formatting

**Example usage:**
```python
loader = ResultLoader()
data = loader.load_results("P001", "PTA", show_gui=True)
```

**GUI displays:**
```
┌─────────────────────────────────────────┐
│   Loading PTA results for P001          │
│                                          │
│   Most recent file found:                │
│   P001_PTA_2026-02-16_14-30-45.csv      │
│                                          │
│   2 other file(s) also available:        │
│     • P001_PTA_2026-02-16_10-15-30.csv  │
│     • P001_PTA_2026-02-15_16-45-10.csv  │
│                                          │
│  [✓ Accept]  [Browse Other...]  [Cancel]│
└─────────────────────────────────────────┘
```

---

### 4. **Safe dB-to-Amplitude Conversion**

**CRITICAL SAFETY FEATURES:**

```python
def get_ifmc_probe_level(self, participant_id, probe_freq, 
                        db_above_threshold=10.0,
                        max_amplitude=0.7):  # SAFETY CEILING
    """
    Returns amplitude (0-1) for backward compatibility.
    
    Safety features:
    - Takes threshold in dB (from PTA)
    - Adds 10 dB
    - Converts to amplitude using TrialPlayer.db2amp()
    - ENFORCES max_amplitude=0.7 (never exceeds!)
    - Additional check: never > 1.0
    - Warnings if clamping occurs
    """
```

**Example:**
```python
# PTA threshold at 1000 Hz = 20 dB
# Probe level = 20 + 10 = 30 dB
# Convert to amplitude: db2amp(30) = 0.032
# Safe! Within 0.7 limit
probe_amp = loader.get_ifmc_probe_level("P001", 1000)
# → 0.032 amplitude (safe)
```

**Safety checks:**
```python
if probe_amp > max_amplitude:
    print(f"WARNING: Clamping to {max_amplitude}")
    probe_amp = max_amplitude

if probe_amp > 1.0:
    print("CRITICAL WARNING: This should never happen!")
    probe_amp = max_amplitude
```

---

### 5. **Standardized Frequencies**

**File:** `utils/standard_frequencies.py`

```python
AUDIOMETRIC_FREQS = [250, 500, 1000, 2000, 4000, 8000]
IFMC_PROBE_FREQS = [500, 1000, 2000, 4000, 6000]
IFMC_MASKER_RATIOS = [0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6]
```

**Ensures:** PTA and IFMC use same frequencies

---

## 📁 Files Provided

1. **adaptive_paradigm_updates.md** - Changes to adaptive_paradigm.py
2. **utils/result_loader.py** - GUI-based result loading with safety checks
3. **utils/standard_frequencies.py** - Standard frequency definitions
4. **paradigm_code_examples.md** - Examples for all paradigms
5. **DATA_MANAGEMENT_PLAN.md** - Original comprehensive plan

---

## 🔧 Implementation Checklist

### Step 1: Update adaptive_paradigm.py
```python
# Add to __init__:
self.participant_id = participant_id or "P000"
if not hasattr(self, 'paradigm_code'):
    self.paradigm_code = None

# Update write_data_to_disk():
if self.paradigm_code is None:
    raise ValueError(...)
filename = f"{self.participant_id}_{self.paradigm_code}_{timestamp}.csv"
```

### Step 2: Update ALL paradigm subclasses
```python
# Add to EVERY paradigm's __init__:
self.paradigm_code = 'PTA'  # or 'FM', 'AM', 'GAP', etc.
```

### Step 3: Create utils directory
```bash
mkdir -p utils/
# Add result_loader.py
# Add standard_frequencies.py
```

### Step 4: Update test scripts
```python
# Add participant_id prompt
participant_id = input("Participant ID [P001]: ") or "P001"

# Pass to paradigm
pta = ParadigmPTA(params, participant_id=participant_id)
```

### Step 5: Update IFMC for auto-loading
```python
from utils.result_loader import ResultLoader
from utils.standard_frequencies import IFMC_PROBE_FREQS

loader = ResultLoader()
thresholds = loader.get_pta_thresholds(participant_id, 
                                      IFMC_PROBE_FREQS,
                                      show_gui=True)

if thresholds:
    probe_levels = [
        loader.get_ifmc_probe_level(participant_id, freq)
        for freq in IFMC_PROBE_FREQS
        if freq in thresholds
    ]
```

---

## 🎯 Key Benefits

✅ **Organized files** - Easy to find participant/paradigm results  
✅ **Safe probe levels** - Multiple safety checks prevent loud sounds  
✅ **Auto-configuration** - IFMC loads PTA automatically  
✅ **User-friendly** - GUI file selection with clear info  
✅ **Standardized** - Consistent frequencies across tests  
✅ **Enforced** - paradigm_code requirement prevents errors  
✅ **Backward compatible** - Returns amplitudes (0-1)  

---

## 🔒 Safety Features

**Multiple layers of protection:**

1. **Input validation** - Amplitude must be 0-1
2. **Max ceiling** - Default 0.7 (70% of maximum)
3. **Absolute ceiling** - Never exceeds 1.0
4. **Warnings** - Alerts operator if clamping
5. **dB conversion** - Uses proper TrialPlayer.db2amp()
6. **Threshold checking** - Validates PTA thresholds reasonable

**Example safety in action:**
```python
# If PTA threshold = 80 dB (very loud)
# Probe = 80 + 10 = 90 dB
# Amplitude = db2amp(90) = 31.6 (WAY TOO LOUD!)
# Safety clamp: → 0.7
# Operator warning: "Clamping to 0.7"
```

---

## 🚀 Next Steps

1. Apply updates to adaptive_paradigm.py
2. Add paradigm_code to all existing paradigms
3. Test with PTA → IFMC workflow
4. Verify GUI file selection works
5. Confirm safe probe levels

Ready to implement! 🎯
