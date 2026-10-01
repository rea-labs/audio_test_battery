# PROLACTIN Session Changelog - 2026-07-18 (session 02)

## Session start protocol (next session)
1. Push all local working copies into the project BEFORE anything else.
2. Verify the Key Signatures below against uploaded files (grep). Paradigm/dialog
   files are the usual stale-base hazards - check a signature, not just mtime.
3. Review Open Issues / Next Steps at the bottom.

## High-level summary
Implemented GitLab request "FM/AM: add individual threshold config for target
level": the carrier/tone level in AM and FM is now an individual per-carrier-
frequency value instead of one flat 60 dB for all frequencies. `tone_level_db`
was demoted from an outer variable to a per-fc target-level array (co-indexed
with `fc`, zipped by index, NOT crossed - avoids the documented `probe_level`
cross-pairing bug), exposed as an editable per-frequency table in the setup GUI,
defaulting to 60 dB. Plumbing mirrors IFMC `probe_level` and includes a
`set_target_levels()` hook for a future "load from another paradigm" path.

Two follow-on fixes surfaced during live testing:
- Setup dialog overflowed the screen (Start button unreachable). The base
  `ParadigmSetupDialog` now pins header + Start/Cancel and puts the variable
  sections in a scrollable canvas, height capped to screen, vertically resizable.
  A "Scroll down for more options" hint appears only while content overflows.
- Demoting `tone_level_db` removed the demo tone-level field (it was auto-shown
  as an outer var). Restored as a DEMO-ONLY override field for AM/FM.

Scope: AM + FM only. DLI/ILD/ITD `ref_level_db` (same flat-60 pattern) untouched.

## Work completed

### paradigm_am.py / paradigm_fm.py (identical plumbing)
- `tone_level_db` demoted from outer var to derived per-fc attribute.
- `_build_target_level_map(params)`: zips the `target_level` array with the fc
  outer var by index (fail-fast on length mismatch); all-60 when absent.
- `set_target_levels(freq_to_db)`: runtime override hook (fail-fast on missing
  fc), mirrors IFMC `set_probe_levels`. Future cross-paradigm load path.
- `_derive_dependent_params()`: sets `tone_level_db` from fc via the map after
  outer vars are set; honours a `_demo_tone_level` override (demo preview) when
  present; 60 dB fallback for unconfigured fc.
- `_demo_tone_level = None` instance attr (demo override; None on normal run).
- Docstrings/comments/`__main__` demo blocks updated; outer_3 removed from
  `__main__`.

### test_am.py / test_fm.py
- Removed `outer_3` (tone_level_db). Added dedicated `target_level` VarSpec:
  `data=[60.0]*len(AUDIOMETRIC_FREQS)`, NOT an outer_* slot.
- Config count unchanged (fc x fm). `tone_level_db` still logged (attribute-based).

### paradigm_setup_dialog.py (base ParadigmSetupDialog only; ThresholdSetupDialog untouched)
- `_build_target_level_editor()` + `_rebuild_target_rows()` + `_current_fc_list()`
  + `_fc_key()`: per-fc dB editor, rendered only when `target_level` present,
  live-rebuilt on fc-set change (edits preserved by freq), all fields required
  on OK; writes the fc-ordered array back to `params["target_level"].data`.
- Scrollable layout: `_build_ui` restructured (pinned header + bottom button bar,
  scrollable canvas middle, cross-platform mousewheel). `show()` now
  `resizable(False, True)`; new `_fit_to_screen()` caps window to screen height.
- `_update_scroll_hint()` + hint label: "Scroll down for more options" strip
  shown only while content extends below the viewport.
- Restored demo carrier-level field (AM/FM only, gated on `target_level`) writing
  the `_demo_tone_level` override key; independent of the per-fc map.

## Files modified
| File | Change |
|------|--------|
| paradigm_am.py | tone_level_db -> per-fc map; set_target_levels; derive + demo override |
| paradigm_fm.py | identical to AM |
| paradigm_setup_dialog.py | per-fc target editor; scrollable layout + scroll hint; demo tone-level field |
| test_am.py | outer_3 -> target_level array |
| test_fm.py | outer_3 -> target_level array |

**Files NOT modified:** adaptive_paradigm.py (base core - unchanged; only relied
on existing `_derive_dependent_params` hook + `set_current_config` ordering),
paradigm_dli/ild/itd/gap/pta/ldl/srt.py, paradigm_ifmc/tmc.py, ThresholdSetupDialog
(overrides show/_build_ui, so untouched by the scroll change), calibration.py,
calibration_config.json, DEFAULTS.py, event_gen.py, trial_player.py, all other
test_*.py, varspec.py, operator_gui.py.

## Key Signatures (grep targets for next start-check)
- paradigm_am.py / paradigm_fm.py:
  - `self._target_level_by_freq = self._build_target_level_map(params)`
  - `def set_target_levels(self, freq_to_db):`
  - `self._demo_tone_level = None`
  - `demo_level = getattr(self, "_demo_tone_level", None)`
- paradigm_setup_dialog.py:
  - `def _build_target_level_editor(self`
  - `def _fit_to_screen(self)`
  - `def _update_scroll_hint(self`
  - `text="\u25bc  Scroll down for more options  \u25bc"`
  - `self._demo_entries["_demo_tone_level"] = var`
  - `self._root.resizable(False, True)`
- test_am.py / test_fm.py:
  - `"target_level": VarSpec(name="tone_level_db"` present
  - zero hits for `outer_3` + `tone_level_db` together

## Verification done this session
- ast.parse clean on all 5 delivered files; garbage sweep clean (0 mojibake;
  dialog's 13 non-ASCII are pre-existing em-dash/arrow; new code uses \u escapes).
- Map builder: default-60 / zip-by-index / length-mismatch raise.
- Derive/override: config-supplied array, default-60, set_target_levels load path,
  missing-freq fail-fast, demo-freq fallback, demo override wins / None->map /
  garbage->map fallback.
- Dialog (real methods, tk stubbed): co-indexing, live add/remove preservation,
  accept-array in fc order, empty-field rejection; scroll layout builds + height
  cap engages; scroll-hint toggle; demo field present for AM/FM, absent for PTA.
- Config count invariant (fc x fm); tone_level_db still in CSV; no config-builder
  inflation (target_level ignored by outer_* product; benign self.target_level attr).

## Open Issues / Next Steps
- **Real-hardware validation (AM/FM):** confirm on Mac that Start is reachable,
  scroll + hint feel right, per-fc editor + demo tone-level field behave; then a
  Windows pass. Scrollable layout + hint now affect ALL base-dialog paradigms -
  quick visual check of other setup dialogs (PTA/LDL/DLI/etc.) worth doing.
- **Demo tone level = independent override (design choice).** Alternative is
  WYSIWYG (demo mirrors per-fc map value for the demo fc, no separate field).
  Revisit if team prefers WYSIWYG.
- **DLI/ILD/ITD `ref_level_db`** still flat 60 across freqs. If team wants the
  same per-fc treatment there, the AM/FM plumbing is the template (candidate for
  base-class lift if extending to >2 paradigms).
- Standing backlog unchanged - see `prolactin_open_issues_2026-07-18.md`
  (Mulligan config-rerun / unbounded curve_fit; core.wait -> time.sleep thermal
  fix + IFMC crash campaign; RETSPL replacement before clinical use;
  spl_to_amplitude full-scale guard; IFMC/TMC probe-level path B; ExperimentController;
  MockParticipant/headless infra; etc.).

## Files to re-upload into the project
- paradigm_am.py
- paradigm_fm.py
- paradigm_setup_dialog.py
- test_am.py
- test_fm.py
- session_changelog_2026-07-18_session_02.md (this file)
- (optional) prd_2026-07-18_amfm_target_level.md
