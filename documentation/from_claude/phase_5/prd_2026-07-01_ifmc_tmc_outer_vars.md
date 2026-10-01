# PRD 2026-07-01 — IFMC/TMC outer-var handling (Problem A + Problem B)

_Scope: IFMC + TMC only. No base-class `_setup_variable_looping` edit. Approach 1
(local, correct-the-data-model) confirmed by Eric 2026-07-01._

---

## Goal

1. **Problem A (correctness, HIGH):** kill the `itertools.product` cross-pairing of
   `probe_freq` x `probe_level`. `probe_level` is NOT an independent swept variable —
   it is `f(probe_freq) = threshold + db_above`. Demote it from an outer var to a
   freq->amp lookup, so config count is `ratios x freq` (IFMC) / `gaps x freq` (TMC),
   not `ratios x freq^2`. Prime suspect for the deviant-count inflation (14 vs 7,
   2:1) AND the high-config crash (crossed pair feeds a mismatched probe amplitude
   into playback).
2. **Problem B (GUI gap, MED):** `ThresholdSetupDialog` never renders the remaining
   outer var (`masker_freq_ratio` / `gap_duration`) as an editable field — currently
   only editable in `test_*.py`. Wire it in. (Simplified by A: after A, that is the
   ONLY outer var the threshold table doesn't already own.)

---

## Root cause (verified in code, 2026-07-01)

- `test_ifmc.py` L100-101 / `test_tmc.py` L101-102: `test_freqs` and `probe_levels`
  built as **index-aligned parallel lists** (`probe_levels[i]` is the level for
  `test_freqs[i]`), then assigned to `outer_2.data` / `outer_3.data`.
- `adaptive_paradigm._setup_variable_looping` L366: `itertools.product(*rest_data)`
  crosses ALL outer vars -> freq x level become an N x N grid, only the N diagonal
  cells valid. Total = `ratios x N x N` instead of `ratios x N`.
- `test_*.py` print (IFMC L119-120 / TMC L121-122) already reports the INTENDED
  `freq x ratios` count while the base builds N^2 -> the code contradicts itself.
  This becomes the post-fix assertion: `total_num_configs == that printed number`.
- `ThresholdSetupDialog._build_ui` (L742) overrides base and omits
  `_build_outer_var_editors`; `_on_accept` (L1233) is a full override that never
  reads `_outer_entries`. So outer_1 is invisible AND unreadable in the dialog.

---

## Implementation — Problem A (per file)

### paradigm_ifmc.py / paradigm_tmc.py (identical pattern in both)
- Remove `"outer_3"` (`probe_level`) from the module `params` demo block.
- Add instance map + setter (mirrors existing `set_calibration` / `set_session_metadata`
  setter pattern):
  ```python
  self._probe_level_by_freq = {}      # in __init__
  def set_probe_levels(self, freq_to_amp: dict):
      self._probe_level_by_freq = dict(freq_to_amp)
  ```
- Override `set_current_config` (subclass-only; base stays untouched):
  ```python
  def set_current_config(self, ind):
      super().set_current_config(ind)
      if getattr(self, "probe_freq", None) is not None and self._probe_level_by_freq:
          self.probe_level = self._probe_level_by_freq[self.probe_freq]
  ```
  Keeps `self.probe_level` valid for BOTH `prepare_trial` (IFMC L138 / TMC probe amp)
  and `get_log_data` (IFMC L309 `"probe_level"`), unchanged downstream.
- `__main__` demo: set a 1-entry map instead of the dummy `outer_3`.

### test_ifmc.py / test_tmc.py
- Drop the `"outer_3"` VarSpec from the base `params` dict (L70 / L71).
- Remove `params["outer_3"].data = probe_levels` (L111 / L113).
- Keep `test_freqs` + `probe_levels` derivation; pass as a map:
  ```python
  ifmc.set_probe_levels({f: thresholds[f]["probe_amp"] for f in test_freqs})
  ```
- Keep `params["outer_2"].data = test_freqs` (probe_freq stays a real outer var).

### No change
- `adaptive_paradigm.py` (`_setup_variable_looping`, `set_current_config`), the other
  9 paradigms, calibration, GUI logging columns. `probe_level` still logged, just
  sourced from the map not the product.

---

## Implementation — Problem B (per file)

### paradigm_setup_dialog.py (`ThresholdSetupDialog` only)
- `_build_ui`: after `_build_threshold_table`, call a filtered outer-var editor that
  renders ONLY outer vars the threshold table doesn't own — i.e. skip `probe_freq`
  (and `probe_level`, already gone post-A). Cleanest: a small helper
  `_build_extra_outer_var_editors(root)` that reuses base `_build_outer_var_editors`
  logic but filters `outer_keys` to `vs.name not in ("probe_freq", "probe_level")`.
  (Filter by name, not key, so it survives outer_N renumbering.)
- `_on_accept` (`ThresholdSetupDialog` override): before building `thresholds`, read
  back the rendered outer entries into `params` — mirror base L638-654 loop over
  `self._outer_entries` (only the rendered outer_1 is present there), numeric-parse,
  write `self.params[outer_key].data`. Empty-list guard as in base.

### No change
- Base `ParadigmSetupDialog` (the 9 paradigms keep the full-outer editor untouched).
- Threshold table, calibration, probe-arithmetic.

---

## Key signatures (new versions)

- paradigm_ifmc.py: `def set_probe_levels(self, freq_to_amp` AND
  `self.probe_level = self._probe_level_by_freq[self.probe_freq]` AND
  NO `"outer_3"` in module params
- paradigm_tmc.py: same two signatures; NO `"outer_3"` in module params
- test_ifmc.py / test_tmc.py: `set_probe_levels({f: thresholds[f]` AND
  NO `params["outer_3"]`
- paradigm_setup_dialog.py: `_build_extra_outer_var_editors` AND
  `vs.name not in ("probe_freq", "probe_level")`

## Post-fix assertions (headless, no PsychoPy)
- IFMC 7 ratios x 2 freq -> `total_num_configs == 14` (was 28).
- TMC gaps x 2 freq -> `total_num_configs == len(gaps)*2` (was `*4`).
- Every config's `probe_level` equals the map value for its `probe_freq`
  (no crossed pairs): iterate `unwrapped_params`, assert
  `cfg["probe_level"]` absent (now derived) and post-`set_current_config`
  `self.probe_level == map[self.probe_freq]`.
- `ast.parse` clean; garbage-char sweep clean on all touched files.

---

## Out of scope (explicit)
- Base-class paired/zip outer-var semantics (Approach 2) — REJECTED for this work;
  log as a separate LOW/MED "base class cannot express paired outer vars" footgun
  issue, close only if a future paradigm needs truly-independent paired vars.
- H4 / T5 probe-level Path B (`db_above_threshold` 24 -> 10, `trial_dur=0.016`) —
  untouched here; that is a level-value question, orthogonal to the pairing bug.
- Catch-trial masker-only bug (H5), IFMC high-config crash root-cause, TMC gap-set
  vs MT -> **PRD #2**.
- Mulligan step-up symmetry check -> deferred (Eric, 2026-07-01).
- M4 IFMC results-subplot plotting -> unchanged.

---

## Suggested order
| # | Step |
|---|------|
| 1 | Problem A in paradigm_ifmc.py (map + setter + set_current_config override; drop outer_3) |
| 2 | Mirror A in paradigm_tmc.py |
| 3 | test_ifmc.py + test_tmc.py: drop outer_3, pass map |
| 4 | Headless config-count + no-crossed-pair assertion (both) |
| 5 | Problem B: `_build_extra_outer_var_editors` + `_on_accept` read-back in ThresholdSetupDialog |
| 6 | ast.parse + garbage sweep on all 5 files; changelog |

---

## Open questions
1. **`set_probe_levels` timing.** Test calls it after construction, before `main()`.
   OK, or prefer passing the map through the constructor for symmetry with `params`?
   (Setter mirrors existing `set_calibration`; I lean setter.)
2. **Unknown-freq guard.** If `probe_freq` has no map entry (shouldn't happen, but
   e.g. a manually-edited freq list diverging from the threshold table), do we
   hard-fail (KeyError, loud) or fall back? I lean hard-fail — a missing probe level
   is a setup error, not something to paper over. Confirm.
3. **Problem B numeric parse.** `masker_freq_ratio` values are floats (0.5..1.6);
   `gap_duration` floats too. Base read-back tries float then falls back to str.
   Fine for both — confirm no ratio is meant to stay a string.
