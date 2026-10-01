# Session Changelog - 2026-07-01 (session 02)

## Session start protocol (next session)
1. Push all local working copies into the project BEFORE anything else.
2. Verify Key Signatures below (this session's + carried-forward) against uploaded files.
3. Review Open Issues / Next Steps.

## High-level summary
Implemented PRD `prd_2026-07-01_ifmc_tmc_outer_vars.md` (Approach 1, local /
correct-the-data-model). **Problem A:** demoted `probe_level` from an independent
outer var to a `probe_freq -> amplitude` lookup in IFMC + TMC, killing the
`itertools.product` cross-pairing that inflated config counts to `ratios x freq^2`
and fed mismatched probe amplitudes into playback. Config count is now
`ratios x freq` (IFMC) / `gaps x freq` (TMC). **Problem B:** exposed the remaining
outer var (`masker_freq_ratio` / `gap_duration`) as an editable field in
`ThresholdSetupDialog`, which previously only rendered it in `test_*.py`.
No base-class edits. Base `_setup_variable_looping` / `set_current_config` and the
other 9 paradigms untouched.

Two ordering bugs surfaced during live testing and were fixed (both are why the
first two hand-offs crashed):
- `_probe_level_by_freq` must be initialised BEFORE `super().__init__()` because
  `_setup_variable_looping()` runs inside super and calls `set_current_config(0)`.
- `main()` enters config 0 without re-calling `set_current_config` (the loop only
  re-selects on advance to config 1+). Config 0 was selected at construction with
  an empty map, so `set_probe_levels()` now derives `probe_level` for the
  already-selected config immediately after populating the map.

## Work completed

### paradigm_ifmc.py / paradigm_tmc.py (identical pattern)
- `__init__`: `self._probe_level_by_freq = {}` set **before** `super().__init__()`
  (mirrors the existing `self.paradigm_code` "CRITICAL before super" idiom).
- New `set_probe_levels(freq_to_amp)`: stores the map; **fail-fast** validation
  raises `ValueError` if any `probe_freq` in `unwrapped_params` lacks an entry
  (aborts at setup, not mid-session); then derives `probe_level` for the
  construction-selected config 0.
- New `set_current_config(ind)` override: `super()` then, if `probe_freq` set and
  map populated, `self.probe_level = self._probe_level_by_freq[self.probe_freq]`.
  Guard lets the construction-time `set_current_config(0)` (empty map) no-op.
- IFMC module `params` demo block: dropped `outer_3`; `__main__` now calls
  `ifmc.set_probe_levels({1000: 0.1})`.
- Docstrings / comments updated to describe `probe_level` as derived, not outer
  (incl. TMC module docstring and the stale `# amplitude from outer_3` comment).

### test_ifmc.py / test_tmc.py
- Dropped the `"outer_3"` VarSpec from `params`, the
  `params["outer_3"].data = probe_levels` assignment, and the now-dead
  `probe_levels` list.
- After re-instantiation, call
  `set_probe_levels({f: thresholds[f]["probe_amp"] for f in test_freqs})`.
- `outer_2` (probe_freq) still assigned from `test_freqs` as before.

### paradigm_setup_dialog.py (`ThresholdSetupDialog` only)
- `_build_ui`: added `self._build_extra_outer_var_editors(root)` after the
  threshold table.
- New `_build_extra_outer_var_editors`: renders an editable "Values" field for
  each outer var whose **name** is not in `("probe_freq", "probe_level")`
  (filter by name so it survives outer_N renumbering); populates
  `self._outer_entries`.
- `_on_accept`: reads back `self._outer_entries` into `self.params[key].data`
  (numeric-parse, str fallback, empty-list guard) — mirrors base
  `ParadigmSetupDialog` read-back. Base editor/`_on_accept` untouched.

## Files modified
| File | Change |
|------|--------|
| paradigm_ifmc.py | probe_level demoted to map; setter + set_current_config override; init-before-super; config-0 derivation; drop outer_3 demo param; docstrings |
| paradigm_tmc.py | same pattern (no `__main__` demo block); module + inline docstrings/comments |
| test_ifmc.py | drop outer_3 VarSpec/assignment/dead list; set_probe_levels(map) |
| test_tmc.py | same |
| paradigm_setup_dialog.py | ThresholdSetupDialog: `_build_extra_outer_var_editors` (name-filtered) + `_on_accept` read-back |

Files NOT modified: adaptive_paradigm.py (base looping/set_current_config
untouched), trial_player.py, calibration.py, calibration_config.json,
operator_gui.py, DEFAULTS.py, varspec.py, event_gen.py, hl_converter.py,
level_validator.py, result_loader.py, standard_frequencies.py, all other 9
`paradigm_*.py`, all other `test_*.py`.

## Key Signatures (this session)
paradigm_ifmc.py:
- `self._probe_level_by_freq = {}` appears BEFORE `super().__init__(` in `__init__`
- `def set_probe_levels(self, freq_to_amp):`
- `self.probe_level = self._probe_level_by_freq[self.probe_freq]` (x2: setter + override)
- NO `outer_3` anywhere in file

paradigm_tmc.py:
- `self._probe_level_by_freq = {}` BEFORE `super().__init__(` in `__init__`
- `def set_probe_levels(self, freq_to_amp):`
- `self.probe_level = self._probe_level_by_freq[self.probe_freq]` (x2)
- NO `outer_3` anywhere in file

test_ifmc.py / test_tmc.py:
- `set_probe_levels({f: thresholds[f]["probe_amp"] for f in test_freqs})`
- NO `params["outer_3"]`

paradigm_setup_dialog.py:
- `def _build_extra_outer_var_editors(self, parent`
- `and self.params[k].name not in ("probe_freq", "probe_level")`
- `self._build_extra_outer_var_editors(root)` in ThresholdSetupDialog `_build_ui`

## Verification done this session
- Headless harness (real extracted base + subclass method text vs stub):
  IFMC 14 configs (was 28), TMC 6 (was 12); no `probe_level` key in any config;
  every config's derived `probe_level == map[probe_freq]`; construction-time
  `set_current_config(0)` empty-map path safe; config-0 orphan reproduced and
  fixed; fail-fast raises on missing freq. Negative control confirms the harness
  fails when the config-0 fix is removed.
- Static AST check: `_probe_level_by_freq` init precedes `super().__init__()`.
- `ast.parse` clean on all 5; garbage/non-ASCII sweep clean (only pre-existing
  real-UTF-8 arrows/em-dashes in comments).
- Live (Eric, macOS): `test_ifmc.py` construction OK; `Total runs : 14
  (2 freq x 7 ratios)`; first trial plays. Full paradigm run + TMC live run
  still to confirm.

## Open Issues / Next Steps

### PRD #1 (this PRD) — DONE
IFMC/TMC outer-var demotion + dialog editor complete and live-smoke-tested for
IFMC config-count + first trial. Still worth a full IFMC run to completion and a
TMC live run when convenient.

### PRD #2 (next phase — new chat)
- **Catch-trial masker-only bug (H5)**.
- **IFMC high-config crash** root-cause (was partly masked by the cross-pairing;
  re-check now that config count is correct).
- **TMC gap-set vs MultiThreshold** reconciliation.

### Carried forward — high priority (pending team discussion)
- **Mulligan / config-rerun**: unbounded `scipy.curve_fit` in
  `fit_psychometric_function` drives theta extreme-negative + near-zero slope_k
  on unbracketed/near-separable staircases (P0007 configs 5/14/19). Auto-trigger
  vs manual rerun.
- **SPL reseat-averaging**: full remeasure (N>=5 placements/ear, energy-averaged);
  `calibration_config_local.json` override (load-time deep-merge).

### Carried forward — deferred
- Fail-fast validation in `set_probe_levels` is a deviation from PRD-literal
  (KeyError-only); kept as strictly-safer. Revert if undesired.
- Base class cannot express paired/zip outer vars (Approach 2 rejected) — log as
  LOW/MED footgun; revisit only if a future paradigm needs truly-independent
  paired vars.
- H4/T5 probe-level Path B (`db_above_threshold` 24 -> 10, `trial_dur=0.016`,
  `abs_threshold_16`) — orthogonal level-value question, untouched.
- per-channel SPL probe handling IFMC/TMC; centralized per-paradigm defaults
  (DEFAULTS.py; post_stim_pause candidate); PEQ-based calibration (9-band biquad);
  separate RME UCX II FR from headphone IR; RETSPL replacement (ISO 389-8 HDA200);
  Manual trial-redo; ExperimentController; MockParticipant/headless infra;
  TotalMix workspace templates.
- reaction_time_s live smoke-test + post_stim_pause click-test (prior session).

### Stale docs
- `code_audit_2026-02-19.md` sec 1.3 & 1.4 describe FM raw-beta bug as live -- RESOLVED (2026-05-31).

## Key Signatures (carried forward, unchanged this session)
- trial_player.py: `self.stim_end_time = now + max(self.bg_duration, max(self.end_times))`
- adaptive_paradigm.py: `import psychtoolbox as ptb`; `self.post_stim_pause = 0.1`;
  `self.reaction_time_s = np.nan`; `core.wait(self.post_stim_pause)`;
  `"reaction_time_s": getattr(self, "reaction_time_s", np.nan),`;
  `self.block_outer_var_name = "pan"`; `def _ear_block_label`;
  `self.catch_trial_rate = [0.2, 0.1, 0.5, 2.0, 0.1]`
- paradigm_pta.py / paradigm_ldl.py / paradigm_srt.py: `hl_reportable` = True / False / False
- demo_duration_attr present in AM,FM (trial_dur) and DLI,ILD,ITD (tone_dur)
- paradigm_ldl.py: LDL `start` default 60.0 dB SPL
