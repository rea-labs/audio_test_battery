# IFMC/TMC Setup Dialog Overhaul
**Date:** 2026-03-20  
**Scope:** Pre-paradigm operator GUI for IFMC and TMC; foundation for all paradigms

---

## What Changed and Why

### Problem with the old flow

`test_ifmc.py` and `test_tmc.py` previously:
- Collected participant ID via terminal `input()`
- Called `ResultLoader.get_pta_thresholds()` which popped up a file-selector GUI *once per frequency* (causing the "click Accept several times" issue)
- Triggered a `WARNING: Unusual threshold` print for negative dB values (dBFS artefact, not a real clinical warning)
- Ended with `input("Press ENTER to start...")` which could conflict with Tkinter's event loop on macOS, causing the apparent hang / spinning pinwheel

### New flow

Both `test_ifmc.py` and `test_tmc.py` now:
1. Define default `params` (with empty `outer_2`/`outer_3` lists as placeholders)
2. Instantiate `ThresholdSetupDialog` and call `.show()` — **one blocking window, one click to start**
3. Receive `(participant_id, thresholds)` back from the dialog
4. Populate `params["outer_2"].data` and `params["outer_3"].data` from the dialog output
5. Construct the paradigm object and call `.main()`

No terminal prompts, no multiple GUI popups, no `input()` after Tkinter.

---

## New / Modified Files

### New: `utils/paradigm_setup_dialog.py`

Contains two classes:

#### `ParadigmSetupDialog`  (base — all paradigms)

| Feature | Detail |
|---|---|
| Participant ID entry | Numeric input, e.g. `18` → `P0018`. Formats with `P` + 4 zero-padded digits. |
| Live preview | Shows formatted ID next to entry field as user types |
| Parameter summary | Read-only `Courier` text block showing all inner/outer VarSpec keys and values |
| Return value | `participant_id` string, or `None` if cancelled |
| Keyboard | Escape = Cancel |

**Intended future use:** Called from `AdaptiveParadigm.__init__()` or `ExperimentController` for all paradigms — operator always sees this window before a test begins.

#### `ThresholdSetupDialog(ParadigmSetupDialog)`  (IFMC / TMC)

Extends the base with a threshold loading and preview section.

| Feature | Detail |
|---|---|
| Frequency set dropdown | Lists all named sets from `FREQUENCY_SETS` in `standard_frequencies.py`. Pre-selects the paradigm-specific default. Changing the set rebuilds the table immediately. |
| Participant load field | Separate entry for loading PTA data (defaults to main participant field if left blank). Enter key triggers load. |
| Load Most Recent button | Searches `test_data/` for most recent `{PID}_PTA_*.csv`, populates table |
| Load from CSV… button | Opens file dialog filtered to `*.csv`, starting in `test_data/` |
| Frequency mismatch warning | Non-blocking popup if loaded file has different frequencies than the selected set. User can proceed. |
| Threshold table | One editable row per frequency. Columns: Freq (Hz) · Threshold (dB) · Probe dB SL · Probe Amp · Status |
| Live computed columns | Probe dB SL and Probe Amp update on every threshold edit and whenever `db_above_threshold` or `max_amplitude` fields change |
| Status column | `ok` (green) / `unusual ⚠` (orange, outside −20…120 dB) / `clamped ⚠` (orange, amp > max) / `missing` / `no data` / `invalid` |
| Editable probe params | `db_above_threshold` (default 10.0 dB) and `max_amplitude` (default 0.7) are both editable fields |
| Return value | `(participant_id, thresholds_dict)` or `(None, None)` if cancelled |

`thresholds_dict` format:
```python
{
    500:  {"threshold_dB": 22.3, "probe_amp": 0.041},
    1000: {"threshold_dB": 18.7, "probe_amp": 0.027},
    ...
}
```

#### `format_participant_id(raw)` helper

Standalone function (importable) that handles all these inputs:
```
"18"    -> "P0018"
"p18"   -> "P0018"
"P18"   -> "P0018"
"P0018" -> "P0018"
""      -> None
"abc"   -> None
```

---

### Modified: `utils/standard_frequencies.py`

Added:

```python
FREQUENCY_SETS = {
    "IFMC — Lecluyse 2013":       IFMC_PROBE_FREQS,
    "TMC — PROLACTIN":            TMC_PROLACTIN_FREQS,
    "Audiometric — ISO 389":      AUDIOMETRIC_FREQS,
    "Extended audiometric":       EXTENDED_FREQS,
    "Quick test (4 freqs)":       QUICK_TEST_FREQS,
    "Ultra-fast (500 Hz only)":   ULTRA_IFMC_PROBE_FREQS,
}

IFMC_DEFAULT_FREQ_SET = "IFMC — Lecluyse 2013"
TMC_DEFAULT_FREQ_SET  = "TMC — PROLACTIN"
```

All existing constants (`IFMC_PROBE_FREQS`, `TMC_PROLACTIN_FREQS`, etc.) are unchanged.

> **TODO (future):** Consider merging `FREQUENCY_SETS` and paradigm defaults into `DEFAULTS.py` as part of a broader paradigm-configuration dictionary once calibration is implemented.

---

### Modified: `test_ifmc.py`

- Removed `get_participant_id()` function
- Removed all `ResultLoader` calls
- Removed `input("Press ENTER to start...")`
- Replaced with single `ThresholdSetupDialog(...).show()` call
- `params["outer_2"].data` and `params["outer_3"].data` populated from dialog output before paradigm construction

### Modified: `test_tmc.py`

Same changes as `test_ifmc.py`.

---

## Files NOT Changed

| File | Reason |
|---|---|
| `paradigms/paradigm_ifmc.py` | No changes needed — receives the same `params` structure as before |
| `paradigms/paradigm_tmc.py` | Same |
| `paradigms/adaptive_paradigm.py` | Dialog not yet integrated here — see Roadmap below |
| `utils/result_loader.py` | Old methods kept for backward compatibility; no longer called by test_ifmc/tmc |
| `operator_gui.py` | Separate concern, unchanged |

---

## Bugs Fixed

| Bug | Fix |
|---|---|
| "Click Accept several times" | Old flow called `get_ifmc_probe_level()` once *per frequency*, each call showing a separate GUI. New dialog loads all frequencies in one pass. |
| Apparent hang / spinning pinwheel after GUI closes | Caused by `input()` after `root.mainloop()` on macOS. Removed entirely — dialog's Accept button is the start trigger. |
| Participant ID required full `P001` format | New dialog accepts bare numbers; `format_participant_id()` handles padding. |
| `WARNING: Unusual threshold` for negative dBFS values | Warning still shown in status column (orange) but no longer a terminal print blocking the flow. Will be revisited when dBFS → dBSPL calibration is implemented. |

---

## Architecture Roadmap

This work is Step 1 of a larger pre-paradigm setup architecture:

```
Current state (this PR):
  test_ifmc.py / test_tmc.py
      └── ThresholdSetupDialog.show()
              └── returns (participant_id, thresholds)
      └── ParadigmIFMC / ParadigmTMC constructed with result

Near future:
  test_*.py (all paradigms)
      └── ParadigmSetupDialog.show()    ← base class only
              └── returns participant_id
      └── Paradigm constructed with result

Long-term goal:
  ExperimentController
      └── selects paradigm from menu
      └── calls appropriate dialog (base or threshold variant)
      └── constructs and runs paradigm
      └── logs results, advances to next test
  (test_*.py scripts become thin wrappers or are removed)
```

The `ParadigmSetupDialog` base class is already implemented and ready to be
wired into the other test scripts (`test_pta.py`, `test_gap.py`, etc.) at any time.
