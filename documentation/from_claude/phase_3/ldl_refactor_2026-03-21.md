# LDL Paradigm Refactor — 2026-03-21

## Summary

`paradigm_ldl.py` was rewritten to inherit from `AdaptiveParadigm` instead of
being a standalone class. This gives LDL the operator GUI, standard data logging,
and future ExperimentController compatibility for free.

`test_ldl.py` was rewritten to use the standard `params`/`VarSpec` pattern,
adding `pan` (L/R ear) as a second outer variable.

---

## What changed

### `paradigm_ldl.py`

**Before:** Standalone class with its own Tk GUI, `TrialPlayer` instance,
data storage (`trial_rows`, `ldl_results`), and `write_data_to_disk()`.

**After:** Inherits from `AdaptiveParadigm`. All GUI, logging, and data writing
is handled by the base class. LDL only implements the paradigm-specific methods:
`initialize_adaptive_param`, `adapt_difficulty`, `prepare_trial`,
`check_answer`, `update_trial_params`, `get_log_data`, `get_trial_description`.

### `test_ldl.py`

**Before:** Called `ParadigmLDL(frequencies=[...], start_amp=..., step_dB=..., ...)`
with a custom constructor and a synthetic `_DISPLAY_PARAMS` dict for the setup dialog.

**After:** Standard `params`/`VarSpec` pattern. Inner var is `trial_amp`,
outer vars are `fc` (5 frequencies) and `pan` (L/R). Total runs: 10.

---

## Protocol mapping

LDL's ascending-level protocol is mapped onto `AdaptiveParadigm` as follows:

| LDL response    | AdaptiveParadigm class | Effect                        |
|-----------------|------------------------|-------------------------------|
| Comfortable (1) | TP                     | `adapt_difficulty("harder")`  |
| Loud (2)        | TP                     | `adapt_difficulty("harder")`  |
| Uncomfortable (3)| FN                    | Reversal detected → end config |

### Key parameter overrides (set in `__init__`)

| Parameter               | Value        | Reason                                      |
|-------------------------|--------------|---------------------------------------------|
| `trials_after_reversal` | `1`          | Config ends immediately on first reversal   |
| `catch_trial_rate`      | `[0,0,0,0]`  | No catch trials for LDL                     |
| `_current_catch_trial_rate` | `0.0`    | Ensure catch logic is fully disabled        |

### Why `trials_after_reversal = 1`

In `AdaptiveParadigm.check_trial_conds()`, the countdown starts at
`trials_after_reversal - 1` after the first reversal. With `trials_after_reversal = 1`,
the countdown starts at 0, which immediately satisfies `trials_remaining < 1`,
setting `end_config = True`. The config ends on the same trial as the reversal.

### Midpoint reset suppression

`AdaptiveParadigm` normally resets the adaptive parameter to the midpoint of
the last two levels after the first reversal. For LDL this is unwanted (the
config ends immediately). `update_trial_params()` is overridden to set
`self.reset_to_midpoint = False` before calling `super()`.

---

## Outer variables

| Variable | Values              | Notes                              |
|----------|---------------------|------------------------------------|
| `fc`     | 500, 1000, 2000, 4000, 8000 Hz | Per PROLACTIN plan       |
| `pan`    | -1.0, 1.0           | -1.0 = left ear, +1.0 = right ear  |

Total configs: 10 (5 frequencies × 2 ears), presented in order:
(500, L), (500, R), (1000, L), (1000, R), ... via `itertools.product`.

---

## Data logging

`get_log_data()` logs:

| Column           | Content                                |
|------------------|----------------------------------------|
| `trial_amp`      | Current amplitude in dB (rel FS)       |
| `trial_amp_linear` | Current amplitude (linear 0–1)       |
| `response_label` | "Comfortable/Loud" or "Uncomfortable" |
| `fc`             | Carrier frequency (Hz)                 |
| `pan`            | Pan value (-1.0 or 1.0)               |

Note: The column name for the adaptive parameter matches `inner_var.name`
(`"trial_amp"`) so the operator GUI adaptive track plot works correctly.

---

## What was removed

The following are no longer needed and have been deleted from `paradigm_ldl.py`:

- `_open_gui()`, `_close_gui()`, `_update_gui_playing()`,
  `_update_gui_waiting()`, `_update_gui_get_ready()`, `_get_response()`,
  `_register_response()` — replaced by `AdaptiveParadigm`'s GUI system
- `_run_frequency()` — replaced by `AdaptiveParadigm.main()` loop
- `write_data_to_disk()` — handled by base class
- `_print_summary()` — handled by base class
- `trial_rows`, `ldl_results` dicts — replaced by base class `self.data` DataFrame
- Module-level `COMFORTABLE`, `LOUD`, `UNCOMFORTABLE` constants

---

## Key signatures (for session changelog verification)

- `class ParadigmLDL(AdaptiveParadigm):` in `paradigm_ldl.py`
- `self.trials_after_reversal = 1` in `paradigm_ldl.py`
- `self.catch_trial_rate = [0, 0, 0, 0]` in `paradigm_ldl.py`
- `self.reset_to_midpoint = False` in `update_trial_params()` in `paradigm_ldl.py`
- `"outer_2": VarSpec(name="pan", data=[-1.0, 1.0])` in `test_ldl.py`
