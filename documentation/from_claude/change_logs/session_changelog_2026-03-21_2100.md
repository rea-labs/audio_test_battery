# PROLACTIN Session Changelog — 2026-03-21 (evening session)

## How to verify at session start

For each entry, check that the listed **key signature** is present in the project file.
If it's missing, the project file is out of date and needs to be replaced before starting work.

---

## Changes from previous session (2026-03-21 1700)

All changes from the previous changelog still apply. This file adds the following.

---

## Session 2026-03-21 (evening)

### `adaptive_paradigm.py`
- **Change 1:** Repeat button moved to second row (below response buttons)
- **Key signature:** `repeat_btn.grid(row=1, column=0, columnspan=num_options` (appears twice)
- **Change 2:** Default window geometry widened
- **Key signature:** `'window_geometry': "600x250+100+100"`

### `paradigm_dli.py`
- **Change:** `get_log_data()` now keys adaptive parameter by `self.inner_var.name` so operator GUI plots work
- **Key signature:** `self.inner_var.name: self.level_diff_dB` in `get_log_data()`

### `paradigm_ild.py`
- **Change:** Added `self.fs = 48000` (was missing from local copy — use project version)
- **Key signature:** `self.fs = 48000  # Hz — must match TrialPlayer/PTB sample rate`

### `paradigm_itd.py`
- **Change 1:** Added `self.fs = 48000` (was missing from local copy — use project version)
- **Key signature:** `self.fs = 48000  # Hz`
- **Change 2:** `hasattr` guard added for `self.fc` in sine branch of `prepare_trial`
- **Key signature:** `fc = self.fc if hasattr(self, 'fc') else 1000.0` inside `if signal_type == 'sin':`

### `paradigm_ldl.py` — MAJOR REFACTOR
- **Change:** Rewritten to inherit from `AdaptiveParadigm` (was standalone)
- **Key signatures:**
  - `class ParadigmLDL(AdaptiveParadigm):`
  - `self.trials_after_reversal = 1`
  - `self.catch_trial_rate = [0, 0, 0, 0]`
  - `self.reset_to_midpoint = False` in `update_trial_params()`
  - `def determine_catch_trial(self):` override (always False)
  - `def check_trial_conds(self):` override (end config on FN)
  - Response mapping: `if response in (0, 1): self.correct_answer = 'TP'`

### `paradigm_am.py`, `paradigm_fm.py`
- **Change:** `hasattr` guards added for `self.fc` and `self.fm` in `prepare_trial`
- **Key signature:** `fc = self.fc if hasattr(self, 'fc') else 1000.0` in `prepare_trial()`

### `paradigm_gap.py`
- **Change:** `hasattr` guard added for `self.noise_level` in `prepare_trial`
- **Key signature:** `amp=self.noise_level if hasattr(self, 'noise_level') else 0.5`

### `test_itd.py`
- **Change 1:** `signal_type` values corrected from `"tone"/"noise"` to `"sin"/"white"`
- **Key signature:** `"outer_1": VarSpec(name="signal_type", data=["sin", "white"])`
- **Change 2:** `fc` added as outer variable
- **Key signature:** `"outer_2": VarSpec(name="fc", data=[1000])`

### `test_ldl.py`
- **Change:** Rewritten to use standard params/VarSpec pattern with `pan` as outer var
- **Key signature:** `"outer_2": VarSpec(name="pan", data=[-1.0, 1.0])`

### `test_am.py`
- **Change:** `mod_ind` range corrected from 0-1 fraction to 0-100 percent
- **Key signature:** `'start': 50.0` and `'max': 100.0`

---

## Files changed this session (need to be re-uploaded to project)

| File | Status |
|------|--------|
| `adaptive_paradigm.py` | Modified |
| `paradigm_dli.py` | Modified |
| `paradigm_ild.py` | Use project version (local was stale) |
| `paradigm_itd.py` | Modified |
| `paradigm_ldl.py` | Major rewrite |
| `paradigm_am.py` | Modified |
| `paradigm_fm.py` | Modified |
| `paradigm_gap.py` | Modified |
| `test_itd.py` | Modified |
| `test_ldl.py` | Rewritten |
| `test_am.py` | Modified |

---

## Documentation added this session

- `ldl_refactor_2026-03-21.md` — detailed documentation of LDL refactor

