# AdaptiveParadigm Base Class - Updated Summary

## Recent Updates

### 1. ✅ **Explicit TP/FP/TN/FP Tracking**
Added counters to track participant performance across the paradigm:

```python
self.total_TP = 0   # True positives (heard when present)
self.total_FN = 0   # False negatives (missed when present)  
self.total_FP = 0   # False positives (heard when absent)
self.total_TN = 0   # True negatives (correct rejection)
```

These are:
- **Incremented** in `update_counters()` based on `self.correct_answer`
- **Reset** when starting a new config
- **Displayed** at end of paradigm in summary

### 2. ✅ **Configurable GUI System**
Complete rewrite of GUI to support paradigm-specific customization.

#### **How It Works:**

Pass a `gui_config` dict when creating the paradigm:

```python
gui_config = {
    'question': "Which interval had the gap?",
    'options': ['First', 'Second'],
    'keys': ['1', '2'],
    'allow_repeat': True,
    'window_title': "Gap Detection",
    'window_geometry': "600x200+100+100",
    'font_size': 16
}

paradigm = MyParadigm(params, gui_config=gui_config)
```

#### **Default Configuration:**
If no `gui_config` provided, uses sensible defaults:

```python
{
    'question': "Did you hear the stimulus?",
    'options': ['0 (No)', '1 (Yes)'],
    'keys': ['0', '1'],
    'allow_repeat': True,
    'window_title': "Audiology Test",
    'window_geometry': "500x200+100+100",
    'font_size': 14
}
```

#### **GUI Config Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `question` | str | Question text displayed | "Did you hear the stimulus?" |
| `options` | list[str] | Button labels | `['0 (No)', '1 (Yes)']` |
| `keys` | list[str] | Keyboard shortcuts | `['0', '1']` |
| `allow_repeat` | bool | Show repeat button | `True` |
| `window_title` | str | Window title | "Audiology Test" |
| `window_geometry` | str | Window size/position | "500x200+100+100" |
| `font_size` | int | Text font size | 14 |

#### **How Responses Work:**

The GUI returns an **integer index** (0, 1, 2, ...) corresponding to which option was selected:

```python
# If options = ['First', 'Second', 'Third']
user_input = 0  # means "First"
user_input = 1  # means "Second"  
user_input = 2  # means "Third"
```

**Default behavior** in `check_answer()`:
- `0` = "No/Not detected"
- `1` = "Yes/Detected"

**Override `check_answer()`** if you need different logic:

```python
class MyParadigm(AdaptiveParadigm):
    def check_answer(self):
        # Custom: option 0 = interval 1, option 1 = interval 2
        correct_interval = self.target_interval  # Set in prepare_trial()
        
        if self.test_cond == 1:  # Normal trial
            if self.user_input == correct_interval:
                self.correct_answer = "TP"
            else:
                self.correct_answer = "FN"
        elif self.test_cond == 0:  # Catch trial
            # Could implement different catch trial logic here
            ...
```

## Example Usage - Different Paradigms

### Example 1: PTA (Default)
```python
params = {...}  # VarSpec dict

# Use default GUI (works fine for PTA)
pta = ParadigmPTA(params, verbose=True)
pta.main()
```

### Example 2: GAP Detection (Custom Question)
```python
params = {...}

gui_config = {
    'question': "Did you hear a gap in the noise?",
    'options': ['No Gap', 'Heard Gap'],
    'keys': ['0', '1'],
    'window_title': "Gap Detection Test"
}

gap = ParadigmGAP(params, gui_config=gui_config)
gap.main()
```

### Example 3: FM/AM (Which Interval)
```python
params = {...}

gui_config = {
    'question': "Which tone was modulated?",
    'options': ['First', 'Second'],
    'keys': ['1', '2'],
    'window_title': "FM Detection Test",
    'font_size': 16
}

fm = ParadigmFM(params, gui_config=gui_config)
fm.main()
```

**Note:** For FM/AM, you'd need to override `check_answer()` because the logic is different (which interval, not yes/no detection).

### Example 4: DLI (Which Was Louder)
```python
params = {...}

gui_config = {
    'question': "Which tone was louder?",
    'options': ['First', 'Second', 'Same'],
    'keys': ['1', '2', '3'],
    'window_title': "Intensity Discrimination"
}

dli = ParadigmDLI(params, gui_config=gui_config)
dli.main()
```

## How GUI Adapts Automatically

The `get_response()` method now:

1. **Reads `gui_config`** to determine number of buttons and their labels
2. **Creates buttons dynamically** - works with 2, 3, 4+ options
3. **Maps keyboard shortcuts** - automatically binds keys from `keys` list
4. **Handles repeat button** - only shows if `allow_repeat=True`
5. **Returns index** - paradigm-agnostic (just an integer)

**Layout adapts automatically:**
```
2 options:  [Button0]  [Button1]  [Repeat]
3 options:  [Button0]  [Button1]  [Button2]  [Repeat]
4 options:  [Button0]  [Button1]  [Button2]  [Button3]  [Repeat]
```

## Performance Tracking

At end of paradigm, you'll see:

```
============================================================
PARADIGM COMPLETE
============================================================
Performance Summary:
  True Positives (TP):  45
  False Negatives (FN): 12
  False Positives (FP): 3
  True Negatives (TN):  8
============================================================

Results:
[DataFrame with all trial data]

Data saved to: test_data/results_2026-02-13_14-23-45.csv
```

**These counters help you:**
- Monitor participant reliability
- Calculate detection rates
- Identify if participant is guessing
- Track performance across configs

## Summary of Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Performance tracking** | None (deleted old counters) | Explicit TP/FN/FP/TN counts |
| **GUI question** | Hard-coded "Did you hear..." | Configurable via `gui_config` |
| **GUI buttons** | Always "0", "1", "Repeat" | Dynamic based on `options` list |
| **Response values** | Hard-coded 0/1 | Integer index (0, 1, 2, ...) |
| **Keyboard shortcuts** | Hard-coded '0', '1', 'r' | Configurable via `keys` list |
| **Window appearance** | Fixed size/title | Configurable geometry/title/font |
| **Paradigm-specific logic** | Mixed in check_answer() | Override check_answer() if needed |

## What This Enables

### ✅ Detection paradigms (PTA, GAP, Tinnitus Match)
- Default GUI works perfectly
- Question: "Did you hear X?"
- Options: "No", "Yes"

### ✅ Interval paradigms (FM, AM, DLI)
- Custom GUI question
- Options: "First", "Second" (or "Louder", "Softer")
- Override `check_answer()` to compare against correct interval

### ✅ Multi-option paradigms (future expansion)
- Options: "Interval 1", "Interval 2", "Interval 3", "Not sure"
- Automatically creates 4 buttons

### ✅ Custom workflows
- Disable repeat button if not needed
- Change window size for larger/smaller displays
- Adjust font for different viewing distances

## Next Steps

Ready to test! We should:
1. Create a simple PTA implementation to verify default behavior
2. Create a GAP implementation to test custom GUI config
3. Then tackle FM/AM which need custom `check_answer()` logic

Let me know if the GUI system makes sense or if you'd like different configurability!
