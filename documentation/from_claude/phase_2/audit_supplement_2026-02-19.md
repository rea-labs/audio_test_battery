# PROLACTIN Audit Supplement — Issues from "Completing a Python audiology toolbox project" Chat + New Items

This covers: (A) issues from the previous chat that the Feb 19 audit missed or that remain unresolved, (B) diagnosis and fixes for the psychometric curve and waveform plot, and (C) a redesign proposal for the IFMC/TMC threshold import UX.

---

## A. Issues from Previous Chat Not Addressed in the Audit

### A.1 OperatorDisplay is Never Called from the Main Loop (ROOT CAUSE of plot issues)

**This is the most important finding.** The `OperatorDisplay` class exists in `operator_gui.py` with full plot update methods, but `adaptive_paradigm.py`'s `main()` loop **never instantiates or calls it**. There is no `import operator_gui` and no call to `update_display()` anywhere in `adaptive_paradigm.py`. The `main()` loop creates its own `tk.Tk()` for the participant GUI but never creates the operator display.

The singleton accessor `get_operator_display()` exists in `operator_gui.py` (line 711) but nothing calls it.

**This is why you never saw the psychometric curve or waveform plot** — the OperatorDisplay window was never created.

**Fix:** Add integration code to `adaptive_paradigm.py`:

```python
# In main(), before the trial loop:
from operator_gui import get_operator_display
self.operator_display = get_operator_display()
self.operator_display.attach_paradigm(self)

# In the trial loop, after check_paradigm_end_conds():
self.operator_display.update_display()
```

### A.2 Psychometric Curve — Why It Never Appeared

Two problems stacked:

1. **The display was never instantiated** (see A.1 above).

2. **Timing issue:** `threshold_dB` and `slope_k` are only computed at the END of each config (in `check_trial_conds()` around line 654). But `_update_psychometric_plot()` is designed to run after every trial. Since the threshold only exists after a config completes, the psychometric curve can only ever appear for the *completed* config — and by that point, the plot data has been cleared for the next config. 

**Fix approach:** The psychometric plot should use *running* data from the current config (all trials so far), not wait for the final threshold. The sigmoid fit should be attempted after each trial once there are enough data points (say >= 5 non-catch trials). Store the running fit parameters separately from the final threshold:

```python
# In _update_psychometric_plot(), compute the fit locally:
if len(levels) >= 5 and len(np.unique(responses)) == 2:  # Need both 0 and 1 responses
    try:
        from scipy.optimize import curve_fit
        def logistic(x, theta, k):
            return 1.0 / (1.0 + np.exp(-k * (x - theta)))
        popt, _ = curve_fit(logistic, levels, responses, 
                           p0=[np.mean(levels), 0.5], maxfev=1000)
        # Plot the curve using popt[0] (theta) and popt[1] (k)
    except:
        pass  # Not enough data or fit failed — just show dots
```

### A.3 Waveform Plot — Root Cause

The waveform timing diagram code (lines 294-353) correctly reads `tp.start_times`, `tp.end_times`, `tp.amp`, and `tp.fc`. These *are* populated by `TrialPlayer.new_trial()`. The issue was solely that the display was never instantiated (A.1).

However, there's a secondary issue: the y-axis range is hardcoded to `(-100, 5)` in dB, which is fine for PTA but will be wrong for IFMC/TMC where masker levels are in dB SPL (0-100). After calibration, you'll want the range to auto-scale.

**Additional improvement:** The rectangles use `TrialPlayer.amp2db()` which gives dB FS (negative values). Once calibration exists, add a flag to display dB SPL instead.

### A.4 Participant GUI Flicker (from Feb 14 audit, still present)

`update_gui_state()` in the main loop destroys all children and rebuilds every call. This was flagged in the Feb 14 audit (#13) and is still present. The fix is to create the buttons once and just toggle `state=tk.NORMAL`/`state=tk.DISABLED`.

### A.5 Performance Summary Still Commented Out

Lines 992-997 of `adaptive_paradigm.py` show the end-of-paradigm performance summary is commented out. The per-config summary was discussed as working, but the overall summary at paradigm end is dead code.

### A.6 Two Separate Tk Root Windows

`adaptive_paradigm.py:main()` creates `self.root = tk.Tk()` for the participant GUI. If OperatorDisplay is instantiated, it creates its OWN `self.root = tk.Tk()`. Running two `Tk()` instances simultaneously is technically unsupported by tkinter and can cause subtle issues (event loop conflicts, window focus problems).

**Fix:** Either:
- Make OperatorDisplay use `tk.Toplevel()` (child of the main root), or
- Pass the paradigm's root to OperatorDisplay

### A.7 `update_gui_state` Focus Stealing

The code tries to force focus back after OperatorDisplay updates (line 288-291):
```python
try:
    self.paradigm.root.focus_force()
except:
    pass
```
This is a workaround for the dual-Tk problem (A.6). Using `Toplevel()` would eliminate the need for focus hacking.

---

## B. Psychometric Curve and Waveform Plot — Complete Fix Plan

### B.1 Integration into Main Loop

Add to `adaptive_paradigm.py`:

**At the top of `main()`** (after creating participant GUI):
```python
# Operator display (separate monitoring window)
from operator_gui import get_operator_display
self.op_display = get_operator_display()
self.op_display.attach_paradigm(self)
```

**After `self.check_paradigm_end_conds()`** in the trial loop:
```python
# Update operator display after each trial
if hasattr(self, 'op_display'):
    self.op_display.update_display()
    self.op_display.root.update_idletasks()
```

**At end-of-config** (in `check_trial_conds`, after threshold estimation):
```python
# Store threshold for history plot
if hasattr(self, 'op_display') and not np.isnan(self.threshold_dB):
    self.op_display.threshold_history.append(
        (self.config_num, self.threshold_dB))
```

### B.2 Fix Dual Tk Issue

Change `OperatorDisplay.__init__()` to accept an optional parent:
```python
def __init__(self, title="Operator Display", parent=None):
    if parent:
        self.root = tk.Toplevel(parent)
    else:
        self.root = tk.Tk()
```

Then in `main()`:
```python
self.op_display = OperatorDisplay(parent=self.root)
```

### B.3 Live Psychometric Fit

Replace the current approach (which waits for final `threshold_dB`) with a running fit computed locally in the plot method. See the code snippet in A.2 above.

### B.4 Waveform Auto-Scale

Replace the hardcoded `ylim(-100, 5)` with:
```python
if len(tp.amp) > 0:
    db_values = [TrialPlayer.amp2db(a) if a > 0 else -100 for a in tp.amp]
    self.ax_waveform.set_ylim(min(db_values) - 10, max(db_values) + 10)
```

---

## C. IFMC/TMC Threshold Data Import — Redesign Proposal

### C.1 Current State

`ResultLoader` has:
- `get_pta_thresholds()` — loads PTA CSV, extracts threshold_dB per frequency
- `get_ifmc_probe_level()` — takes PTA threshold + 10 dB SL → amplitude
- `get_tmc_probe_level()` — identical logic to IFMC version
- `select_file_gui()` — shows "Accept most recent / Browse / Cancel"
- `_manual_threshold_entry()` — fallback if no PTA file found

### C.2 Problems with Current UX

1. **No verification of loaded values.** The file selector shows a filename but doesn't display what thresholds were actually loaded. If there's a bad value or the wrong file, you only discover it mid-paradigm.

2. **Can't edit individual values.** If one threshold looks wrong, you must cancel and either re-run PTA for that frequency or manually enter ALL thresholds from scratch.

3. **Separate code paths for "load" vs "manual".** File load returns thresholds directly; manual entry has its own dialog. There's no unified "review and edit" step.

4. **IFMC and TMC both call `get_pta_thresholds()` separately**, which means the user sees the file-selection GUI twice if running both tests.

5. **get_tmc_probe_level() is a copy-paste of get_ifmc_probe_level().** These are identical functions.

### C.3 Proposed Redesign: "Threshold Review & Edit" GUI

Replace the current load-or-manual flow with a single unified GUI:

```
┌──────────────────────────────────────────────────────────┐
│         PTA Thresholds for P001 — Review & Edit          │
│                                                          │
│  Source: P001_PTA_2026-02-16_10-00-00.csv                │
│  (2 other files available)                               │
│                                                          │
│  ┌──────────┬────────────┬──────────────┬──────────────┐ │
│  │ Freq (Hz)│ Loaded (dB)│ Probe dB SL  │ Probe Amp    │ │
│  ├──────────┼────────────┼──────────────┼──────────────┤ │
│  │   500    │ [  22.3  ] │    32.3      │   0.041      │ │
│  │  1000    │ [  18.7  ] │    28.7      │   0.027      │ │
│  │  2000    │ [  25.1  ] │    35.1      │   0.057      │ │
│  │  4000    │ [  31.4  ] │    41.4      │   0.117      │ │
│  │  6000    │ [  ----  ] │    ---       │   ---        │ │
│  └──────────┴────────────┴──────────────┴──────────────┘ │
│                                                          │
│  Note: Probe level = threshold + 10 dB SL                │
│  ⚠ 6000 Hz: No threshold found (skipped in test)        │
│                                                          │
│  [Accept]  [Load Different File]  [Enter Manually]       │
│                       [Cancel]                           │
└──────────────────────────────────────────────────────────┘
```

**Key features:**
- Shows ALL loaded thresholds at once with computed probe levels
- Editable threshold fields — user can adjust individual values
- Probe level and amplitude update dynamically as thresholds change
- Missing frequencies clearly flagged
- Safety warnings for unusual values (highlighted in red/orange)
- Single "Accept" button that returns the final (possibly edited) thresholds

### C.4 Implementation Plan

**New class: `ThresholdReviewDialog`** (in `result_loader.py` or separate file)

```python
class ThresholdReviewDialog:
    """
    Unified GUI for loading, reviewing, and editing PTA thresholds
    before using them in IFMC/TMC paradigms.
    """
    
    def __init__(self, participant_id, frequencies, 
                 loaded_thresholds=None, source_file=None,
                 db_above_threshold=10.0, max_amplitude=0.7):
        ...
    
    def show(self):
        """Show dialog and return final thresholds dict, or None if cancelled."""
        ...
```

**Modified flow in ResultLoader:**

```python
def get_probe_thresholds(self, participant_id, frequencies,
                         db_above_threshold=10.0, paradigm="IFMC"):
    """
    Unified method replacing get_ifmc_probe_level and get_tmc_probe_level.
    Returns dict {freq: {'threshold_dB': x, 'probe_dB': y, 'probe_amp': z}}
    """
    # 1. Try to auto-load most recent PTA file
    files = self.find_results(participant_id, "PTA")
    loaded = None
    source = None
    if files:
        source = files[0]
        loaded = self._extract_thresholds(source, frequencies)
    
    # 2. Show review dialog (always, even if auto-loaded)
    dialog = ThresholdReviewDialog(
        participant_id, frequencies,
        loaded_thresholds=loaded,
        source_file=source,
        db_above_threshold=db_above_threshold
    )
    result = dialog.show()
    
    if result is None:
        return None
    
    return result  # {freq: {'threshold_dB': ..., 'probe_amp': ...}}
```

**Usage in test scripts:**
```python
loader = ResultLoader()
probes = loader.get_probe_thresholds("P001", IFMC_PROBE_FREQS)
if probes:
    test_freqs = list(probes.keys())
    probe_levels = [probes[f]['probe_amp'] for f in test_freqs]
    # ... configure paradigm
```

### C.5 Benefits

- **One method** instead of three (`get_pta_thresholds` + `get_ifmc_probe_level` + `get_tmc_probe_level`)
- **Always shows review step** — no more silent acceptance of potentially wrong values
- **Editable** — fix one bad frequency without re-entering everything
- **Transparent** — user sees exactly what probe levels will be used
- **Reusable** — same dialog works for IFMC and TMC (and any future paradigm needing PTA input)

### C.6 Caching to Avoid Double-Loading

If IFMC and TMC run in sequence, the second paradigm shouldn't re-prompt. Add a simple cache:

```python
class ResultLoader:
    _threshold_cache = {}  # {participant_id: {freq: threshold_dB}}
    
    def get_probe_thresholds(self, ...):
        cache_key = (participant_id, tuple(sorted(frequencies)))
        if cache_key in self._threshold_cache:
            use_cached = messagebox.askyesno(
                "Use Previous Thresholds?",
                f"PTA thresholds for {participant_id} were already loaded.\n"
                "Use the same values?"
            )
            if use_cached:
                return self._threshold_cache[cache_key]
        
        # ... normal flow ...
        self._threshold_cache[cache_key] = result
        return result
```

---

## D. Summary of All Unresolved Issues (Combined)

### From the Feb 19 audit (unchanged):
- FM mod_ind mismatch (BLOCKER)
- ILD pan not supported (BLOCKER) 
- Import paths inconsistent (BLOCKER)
- event_gen.py config.DEFAULTS import (BLOCKER)
- Dead update_streaks_and_difficulty methods (HIGH)
- Amplitude scale mismatch IFMC/TMC (HIGH)
- Module-level EventGen (HIGH)
- Paradigm boilerplate (MEDIUM)
- No config shuffling (MEDIUM)
- No WRV limits/abort (MEDIUM)
- O(n²) DataFrame concat (MEDIUM)

### From this supplement (NEW):
- **OperatorDisplay never called from main loop** (HIGH — root cause of all plot issues)
- **Dual Tk root windows** (MEDIUM — causes focus/event issues)
- **Participant GUI flicker** (LOW — still rebuilds every trial)
- **Performance summary commented out** (LOW)
- **Threshold import UX needs redesign** (MEDIUM — proposal in section C)
- **get_tmc_probe_level duplicates get_ifmc_probe_level** (LOW — consolidate)
