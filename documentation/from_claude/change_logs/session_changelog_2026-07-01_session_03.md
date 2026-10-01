# Session Changelog - 2026-07-01 (session 03)

## Session start protocol (next session)
1. Push all local working copies into the project BEFORE anything else.
2. Verify Key Signatures below (this session's + carried-forward) against uploaded files.
3. Review Open Issues / Next Steps.

## High-level summary
Implemented PRD `prd_2026-07-01_ifmc_tmc_catch_gaps.md`, Phase 1 (instrumentation)
+ the TMC gap-set data change. This is an INVESTIGATION PRD: no speculative fixes
were written. Phase 2 (H5 fix / crash) is deferred until the lab verbose run
identifies a cause.

- **H5 catch-audibility probe** added to the catch branch of both IFMC and TMC:
  the existing bare `-> Catch trial (no probe)` verbose line was REPLACED (not
  duplicated) with a richer diagnostic dumping `config_num`, masker freq (+ratio
  for IFMC / gap for TMC), `masker_level` with its config `min`, and `amp_L/amp_R`.
  Lets the next run distinguish (a) zero gain, (b) degenerate freq, (c) masker
  pinned at floor (expected-quiet, NOT a bug) as the source of reported silence.
  Verbose-gated, console-only, no CSV column, no audio-path change.
- **Crash try/except state-dump: NOT added** (Eric, this session). The crash was
  most likely the pre-PRD-#1 crossed-product artifact and is probably already
  A-fixed. Revisit only if the config sweep actually crashes.
- **TMC gap set corrected** to the confirmed UZH source
  (`paradigm_tinnoice_TMC.m`, `betweenRuns.variableList1`):
  `[0.005, 0.010, 0.020, 0.040]` s (5/10/20/40 ms, FOUR gaps). Was the shipped
  `[0.030, 0.050, 0.070]` (30/50/70 ms, three). Resolves open Q1
  ("team said 0.04" = largest gap; "M13 four gaps"). TMC config count is now
  `4 gaps x freq` (was `3 x freq`).

No base-class edits. Only IFMC/TMC catch branches + one data constant touched.

## Work completed

### standard_frequencies.py
- `TMC_PROLACTIN_GAPS` -> `[0.005, 0.010, 0.020, 0.040]`; added a source-provenance
  comment pointing at `paradigm_tinnoice_TMC.m`. `TMC_GAPS` (Lecluyse original
  5-gap set) untouched.

### paradigm_ifmc.py
- Catch branch (`prepare_trial`): replaced the one-line verbose catch print with a
  multi-field H5 diagnostic (`config_num`, `masker_freq_ratio`, `masker_freq`,
  `masker_level` + config `min`, `amp_L`, `amp_R`). `min` read inline from
  `inner_var.data` with the same `isinstance(..., dict)` guard the rest of the file
  uses. No change to `new_trial` call, audio, or the normal branch.

### paradigm_tmc.py
- Catch branch (`prepare_trial`): same H5 diagnostic (gap + freq instead of ratio;
  masker = probe freq). No audio-path change.
- Docstring: gap-example (module L17) and PROLACTIN-plan reference (L32) updated
  to 5/10/20/40 ms to match the new constant. Frequencies left as-is (out of scope;
  see Open Issues note re MATLAB single-freq).

## Files modified
| File | Change |
|------|--------|
| standard_frequencies.py | `TMC_PROLACTIN_GAPS` -> `[0.005,0.010,0.020,0.040]`; provenance comment |
| paradigm_ifmc.py | catch-branch verbose print -> H5 audibility diagnostic |
| paradigm_tmc.py | catch-branch verbose print -> H5 diagnostic; docstring gap refs (L17,L32) |

Files NOT modified: adaptive_paradigm.py, trial_player.py, calibration.py,
calibration_config.json, operator_gui.py, paradigm_setup_dialog.py, DEFAULTS.py,
varspec.py, event_gen.py, hl_converter.py, level_validator.py, result_loader.py,
test_ifmc.py, test_tmc.py, all other 9 `paradigm_*.py`, all other `test_*.py`.
No base-class edit. No crash try/except wrapper (deliberately deferred).

## Key Signatures (this session)
standard_frequencies.py:
- `TMC_PROLACTIN_GAPS     = [0.005, 0.010, 0.020, 0.040]`

paradigm_ifmc.py:
- `# H5 catch-audibility probe: a silent catch shows here as`
- `f"masker_level={self.masker_level:.1f} dB (min={_min_lvl:.1f}), "` (catch branch)

paradigm_tmc.py:
- `# H5 catch-audibility probe: silent catch shows as amp ~0`
- `f"masker_level={self.masker_level:.1f} dB (min={_min_lvl:.1f}), "` (catch branch)
- docstring `(gaps: 5, 10, 20, 40 ms; frequencies: 500, 1000 Hz)`

## Verification done this session
- Tier 1 (desk, Eric): PASS. `TMC_PROLACTIN_GAPS == [0.005,0.010,0.020,0.040]`,
  len 4; TMC config count == `len(freqs) x 4`; matches the `test_tmc.py` print line.
- `ast.parse` clean on all 3 files.
- Garbage-char sweep clean: all non-ASCII is pre-existing legitimate `->`(arrow)/`--`(em-dash)
  in comments; none in edited lines; TMC fully ASCII; no mojibake.
- Tier 2 (lab, by ear) NOT yet done -- handed to team / deferred by Eric. This is
  the actual H5 reproduction step.

## Open Issues / Next Steps

### PRD `prd_2026-07-01_ifmc_tmc_catch_gaps.md` -- Phase 1 DONE, Phase 2 PENDING LAB
- **H5 root cause**: awaiting Tier-2 verbose IFMC run. Watch the **ratio=1.3**
  catch lines (durable ID; silence was reported there pre-reindex). Outcomes:
  amps ~0 -> gain-floor guard; degenerate freq -> freq bug; masker at `min` +
  sane amps + audible -> NOT a bug, close H5.
- **Q2 (decide after run)**: keep the verbose H5 print permanently, or strip it
  once diagnosed? Lean keep (lightweight).
- **IFMC high-config crash**: no wrapper added; re-run the previously-crashing
  sweep. Clean across all configs -> close as A-fixed (PRD #1 removed the crossed
  product that most likely caused it). Only add try/except if it still crashes.
- **TMC gap change is a real behavior shift**: 5/10/20/40 ms is much tighter than
  old 30/50/70. One perceptual sanity-listen on the 5 ms-gap NORMAL trial (masker
  108 -> gap 5 -> probe 16; mechanically fine) recommended.
- **TMC frequency list mismatch (new, minor)**: MATLAB source has
  `targetFrequency=[1000]` (single); PROLACTIN plan / `TMC_PROLACTIN_FREQS` =
  `[500, 1000]`. Left untouched (out of PRD scope). Reconcile if the team wants
  MATLAB parity.

### Carried forward -- high priority (pending team discussion)
- **Mulligan / config-rerun**: unbounded `scipy.curve_fit` in
  `fit_psychometric_function` drives theta extreme-negative + near-zero slope_k on
  unbracketed/near-separable staircases (P0007 configs 5/14/19). Auto-trigger vs
  manual rerun.
- **SPL reseat-averaging**: full remeasure (N>=5 placements/ear, energy-averaged);
  `calibration_config_local.json` override (load-time deep-merge).

### Carried forward -- deferred
- IFMC/TMC `set_probe_levels` fail-fast (ValueError) is stricter than PRD-literal
  (KeyError-only); kept as strictly-safer. Revert if undesired.
- Base class cannot express paired/zip outer vars (Approach 2 rejected) -- LOW/MED
  footgun; revisit only if a future paradigm needs truly-independent paired vars.
- H4/T5 probe-level Path B (`db_above_threshold` 24 -> 10, `trial_dur=0.016`,
  `abs_threshold_16`) -- orthogonal level-value question, untouched.
- per-channel SPL probe handling IFMC/TMC; centralized per-paradigm defaults
  (DEFAULTS.py; post_stim_pause candidate); PEQ-based calibration (9-band biquad);
  separate RME UCX II FR from headphone IR; RETSPL replacement (ISO 389-8 HDA200);
  Manual trial-redo; ExperimentController; MockParticipant/headless infra;
  TotalMix workspace templates.
- reaction_time_s live smoke-test + post_stim_pause click-test (prior session).

### Stale docs
- `code_audit_2026-02-19.md` sec 1.3 & 1.4 describe FM raw-beta bug as live -- RESOLVED (2026-05-31).

## Key Signatures (carried forward, unchanged this session)
- PRD #1 (session 02) signatures still hold -- paradigm_ifmc/tmc.py
  `set_probe_levels`, `_probe_level_by_freq` before super, NO `outer_3`;
  test_ifmc/tmc.py `set_probe_levels({f: thresholds...})`;
  paradigm_setup_dialog.py `_build_extra_outer_var_editors`.
- trial_player.py: `self.stim_end_time = now + max(self.bg_duration, max(self.end_times))`
- adaptive_paradigm.py: `import psychtoolbox as ptb`; `self.post_stim_pause = 0.1`;
  `self.reaction_time_s = np.nan`; `self.block_outer_var_name = "pan"`;
  `def _ear_block_label`; `self.catch_trial_rate = [0.2, 0.1, 0.5, 2.0, 0.1]`
- paradigm_pta.py / paradigm_ldl.py / paradigm_srt.py: `hl_reportable` = True / False / False
- demo_duration_attr present in AM,FM (trial_dur) and DLI,ILD,ITD (tone_dur)
- paradigm_ldl.py: LDL `start` default 60.0 dB SPL
