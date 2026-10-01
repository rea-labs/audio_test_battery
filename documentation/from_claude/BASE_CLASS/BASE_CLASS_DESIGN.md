# AdaptiveParadigm Base Class - Design Summary

## Overview

I've extracted and cleaned up the base class from `paradigm_adaptive_PTA.py`. The new `AdaptiveParadigm` class is:
- ✅ **Generic** - no PTA-specific logic
- ✅ **Well-documented** - extensive docstrings
- ✅ **Clean** - removed all deprecated attributes
- ✅ **Fixed** - GUI initialization issue resolved
- ✅ **Extensible** - clear extension points for subclasses

## Key Improvements from Original

### 1. **Removed Deprecated Attributes**
❌ Deleted:
- `total_num_correct`, `total_num_wrong` (unused)
- `dec_amp`, `inc_amp` (replaced with `inc_difficulty`, `dec_difficulty`)
- `next_freq` (merged into `end_config`)
- `trial_active` (unused)
- `max_reversals` (not used in new logic)
- `_this_is_a_test`, `__and_so_is_this` (test junk)

✅ Kept only what's necessary for adaptive logic

### 2. **Fixed GUI Initialization**
**Problem:** Original created `self.root = tk.Tk()` on every `get_response()` call

**Solution:** 
- Create `self.root` once in `main()`
- Clear/rebuild widgets each time rather than recreating window
- Properly destroy when paradigm ends

### 3. **Made Paradigm-Agnostic**
Moved paradigm-specific logic to **abstract methods** that subclasses must implement:

```python
# MUST implement:
def prepare_trial(self):
    """Configure trial and call TrialPlayer"""
    
def adapt_difficulty(self, direction):
    """Adjust adaptive parameter ("increase" or "decrease")"""
    
def get_log_data(self):
    """Return dict of paradigm-specific CSV columns"""
```

### 4. **Enhanced Logging**
- Base class handles common columns: `unix_time`, `config_num`, `trial_num`, `correct_answer`, `trial_repeats`, `is_catch_trial`
- Paradigms add their own via `get_log_data()` (e.g., `freq`, `amplitude` for PTA)
- Automatically merges base + paradigm data

### 5. **Better Code Organization**
Grouped methods into logical sections:
- **Abstract methods** - must override
- **Optional methods** - can override
- **Core adaptive logic** - shouldn't override
- **Main loop** - entry point

## Abstract Methods (Subclasses MUST Implement)

### `prepare_trial()`
**Purpose:** Set up the next trial

**Must do:**
1. Increment `self.trial_num`
2. Check `self.is_catch_trial` to determine catch vs. normal
3. Set `self.test_cond` (0=catch, 1=normal)
4. Configure parameters based on adaptive variable
5. Call `self.tp.new_trial(...)`

**Example (PTA):**
```python
def prepare_trial(self):
    self.trial_num += 1
    
    if self.is_catch_trial:
        amp = 0.0
        self.test_cond = 0
    else:
        amp = self.trial_amp
        self.test_cond = 1
    
    self.tp.new_trial(
        wave_type="sin",
        fc=self.fc,
        amp=amp,
        durations=self.trial_dur,
        fade_time=self.fade_time
    )
```

### `adapt_difficulty(direction)`
**Purpose:** Adjust the adaptive parameter

**Args:** `direction` = `"increase"` or `"decrease"`

**Example (PTA - amplitude):**
```python
def adapt_difficulty(self, direction):
    if direction == "increase":
        # Quieter = harder
        self.trial_amp *= TrialPlayer.db2amp(-10)
    elif direction == "decrease":
        # Louder = easier
        self.trial_amp *= TrialPlayer.db2amp(5)
        self.trial_amp = min(self.trial_amp, 1.0)
```

**Example (GAP - gap duration):**
```python
def adapt_difficulty(self, direction):
    if direction == "increase":
        # Shorter gap = harder
        self.gap_duration *= 0.5
    elif direction == "decrease":
        # Longer gap = easier
        self.gap_duration *= 2.0
```

### `get_log_data()`
**Purpose:** Return paradigm-specific data for CSV

**Returns:** Dictionary with column names as keys

**Example (PTA):**
```python
def get_log_data(self):
    return {
        "freq": self.fc,
        "amplitude_dB": TrialPlayer.amp2db(self.trial_amp)
    }
```

**Example (GAP):**
```python
def get_log_data(self):
    return {
        "gap_duration_ms": self.gap_duration * 1000
    }
```

## Optional Methods (Can Override)

### `initialize_adaptive_param()`
Set the starting value for your adaptive parameter

**Example (PTA):**
```python
def initialize_adaptive_param(self):
    # inner_var.data should be a dict with 'start' key
    self.trial_amp = self.inner_var.data.get('start', 1.0)
```

### `reset_adaptive_param()`
Reset adaptive parameter when starting a new config
**Default:** Calls `initialize_adaptive_param()`

### `get_trial_description()`
Return string for GUI display
**Default:** `"Config {config_num}/{total}, Trial {trial_num}"`

## How to Use

### 1. **Create a VarSpec config:**
```python
from utils.varspec import VarSpec

params = {
    "inner": VarSpec(
        name="trial_amp",
        data={
            'start': 1.0,
            'step_down': -10,  # dB
            'step_up': 5,       # dB
            'min': 0.001,
            'max': 1.0
        }
    ),
    "outer_1": VarSpec(name="fc", data=[250, 500, 1000, 2000, 4000]),
    "outer_2": VarSpec(name="trial_dur", data=[0.5, 1.0])
}
```

### 2. **Create a subclass:**
```python
from adaptive_paradigm import AdaptiveParadigm
from trial_player import TrialPlayer

class ParadigmPTA(AdaptiveParadigm):
    def prepare_trial(self):
        self.trial_num += 1
        
        if self.is_catch_trial:
            amp = 0.0
            self.test_cond = 0
        else:
            amp = self.trial_amp
            self.test_cond = 1
        
        self.tp.new_trial(
            wave_type="sin",
            fc=self.fc,
            amp=amp,
            durations=self.trial_dur,
            fade_time=0.05
        )
    
    def adapt_difficulty(self, direction):
        if direction == "increase":
            self.trial_amp *= TrialPlayer.db2amp(-10)
        elif direction == "decrease":
            self.trial_amp *= TrialPlayer.db2amp(5)
            self.trial_amp = min(self.trial_amp, 1.0)
    
    def get_log_data(self):
        return {
            "freq": self.fc,
            "amplitude_dB": TrialPlayer.amp2db(self.trial_amp)
        }
    
    def initialize_adaptive_param(self):
        self.trial_amp = 1.0  # Start at max amplitude
```

### 3. **Run it:**
```python
pta = ParadigmPTA(params, verbose=True)
pta.main()
```

## What's Different from paradigm_adaptive_PTA.py

| Aspect | Old (adaptive_PTA) | New (AdaptiveParadigm) |
|--------|-------------------|------------------------|
| **Specificity** | PTA-specific (amplitude adaptation) | Generic (subclass defines adaptation) |
| **GUI Init** | Creates window every response | Creates once in main() |
| **Deprecated vars** | Many unused attributes | Cleaned up |
| **Documentation** | Minimal comments | Extensive docstrings |
| **Logging** | Fixed columns | Extensible via get_log_data() |
| **Adaptive param** | Hard-coded `trial_amp` | Abstract `adapt_difficulty()` |

## Next Steps

1. **Test the base class** - Create a simple PTA subclass to verify it works
2. **Migrate GAP** - First full paradigm refactor as proof-of-concept
3. **Add inner variable support** - Enhance VarSpec to support adaptive param config
4. **Create remaining paradigms** - AM, FM, DLI, etc.

## Questions?

The base class is ready for review. Let me know if you'd like me to:
- Adjust any of the abstract methods
- Change the default behavior
- Add/remove functionality
- Create a test PTA implementation to verify it works
