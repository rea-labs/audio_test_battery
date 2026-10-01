# PROLACTIN Session Changelog

This file tracks changes made in each development session.
At the start of a new chat, cross-check project files against these entries.

---

## How to verify at session start

For each entry, check that the listed **key signature** is present in the project file.
If it's missing, the project file is out of date and needs to be replaced before starting work.

---

## Session 2026-03-21

### `trial_player.py`
- **Change:** Added `pan` parameter to `__init__()` and `new_trial()`; applied in `play_trial()` via stereo array rebuild
- **Key signature:** `def new_trial(self, ..., pan=None, ...)` and `self.pan = pan`

### `event_gen.py`
- **Change:** FM synthesis fixed — `mod_ind` (percent) now converted to β before synthesis
- **Key signature:** `delta_f = fc * mod_ind / 100.0` and `beta = delta_f / fm`
- **⚠️ TODO:** Review whether percent-deviation is the correct adaptive parameter for FM (see session_summary_2026-03-21.md)

### `paradigm_ild.py`
- **Change:** Replaced broken `pan`-based approach with direct stereo amplitude scaling (ITD pattern)
- **Key signature:** `self.ild_sound = sound.Sound(...)` in `prepare_trial()` and `def execute_trial(self):`

### `adaptive_paradigm.py`
- **Change 1:** FP warning no longer uses `messagebox` (caused segfault on macOS with PTB)
- **Key signature:** `def show_false_positive_warning(self):` contains `warning_label = tk.Label(` not `messagebox.showwarning(`
- **Change 2:** RNG fix — persistent `self._rng` instance instead of per-trial `default_rng()`
- **Key signature:** `self._rng = np.random.default_rng()` in `__init__()` and `rng = self._rng` in `determine_catch_trial()`

### `operator_gui.py`
- **Change:** Re-added current catch trial rate to catch trial stats block
- **Key signature:** `catch_rate = 100.0 * self.paradigm._current_catch_trial_rate` in `_build_status_text()`

### `test_pta.py`, `test_am.py`, `test_fm.py`, `test_gap.py`, `test_dli.py`, `test_ild.py`, `test_itd.py`, `test_ldl.py`
- **Change:** Replaced `get_participant_id()` + `input("Press ENTER...")` with `ParadigmSetupDialog`
- **Key signature:** `from utils.paradigm_setup_dialog import ParadigmSetupDialog` and `dialog = ParadigmSetupDialog(`

### `test_am.py`
- **Additional change:** Fixed `mod_ind` range from fraction (0–1) to percent (0–100)
- **Key signature:** `'start': 50.0` and `'max': 100.0` in inner VarSpec

### `test_itd.py`
- **Additional change:** Added `fc` as outer variable to prevent crash on sine trials
- **Key signature:** `"outer_2": VarSpec(name="fc", data=[1000])`

### `paradigm_am.py`, `paradigm_fm.py`
- **Change:** Added `hasattr` guards for `self.fc` and `self.fm` in `prepare_trial()`
- **Key signature:** `fc = self.fc if hasattr(self, 'fc') else 1000.0` in `prepare_trial()`

### `paradigm_gap.py`
- **Change:** Added `hasattr` guard for `self.noise_level` in `prepare_trial()`
- **Key signature:** `amp=self.noise_level if hasattr(self, 'noise_level') else 0.5`

### `paradigm_itd.py`
- **Change:** Added `hasattr` guard for `self.fc` in sine branch of `prepare_trial()`
- **Key signature:** `fc = self.fc if hasattr(self, 'fc') else 1000.0` inside `if signal_type == 'sin':`

---

## Known deprecated files (safe to delete from project)

These uppercase files are older standalone implementations superseded by the lowercase versions:
- `paradigm_PTA.py` → replaced by `paradigm_pta.py`
- `paradigm_AM.py`  → replaced by `paradigm_am.py`
- `paradigm_FM.py`  → replaced by `paradigm_fm.py`
- `paradigm_GAP.py` → replaced by `paradigm_gap.py`
- `paradigm_DLI.py` → replaced by `paradigm_dli.py`
- `test_AM.py`, `test_DLI.py`, `test_GAP.py`, `test_PTA.py`, `test_FM.py` → replaced by lowercase versions
- `paradigm_adaptive_PTA.py` → superseded by `adaptive_paradigm.py` + `paradigm_pta.py`
- `paradigm.py` → superseded by `adaptive_paradigm.py`

