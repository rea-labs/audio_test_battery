# PRD - Pan/ear config blocking (single-ear paradigms)

Date: 2026-06-30
Status: approved (Q1-Q4 answered) -> implementing this session.

## Goal
Single-ear paradigms (PTA, LDL) must run ALL configs for one ear before the
other, instead of interleaving ears. `pan` leaves the global config shuffle and
becomes a BLOCKING outer var: one block per pan value, internally randomized,
block (ear) order randomized for counterbalancing. Diotic paradigms unchanged.

## Decisions (from team / Eric)
- Q1 ear order: RANDOMIZED (which ear leads varies per run).
- Q2 trigger: default base attr `block_outer_var_name="pan"`; no-op when the var
  is absent or single-valued. No per-paradigm opt-in.
- Q3 scope: PTA + LDL only (current pan-multivalue launchers). No other param
  will be de-randomized. Confirmed with team.
- Q4 ear message: include a "Beginning LEFT/RIGHT ear" line at each block start
  (low complexity; reuses existing pause screen).

## Implementation - adaptive_paradigm.py (base only; no paradigm/launcher edits)

1. `__init__` (~L183, by `self.pan`): add
   `self.block_outer_var_name = "pan"` with explanatory comment.

2. `_setup_variable_looping` (replace L323-341 build+shuffle block):
   - Detect blocking var = outer var whose `.name == block_outer_var_name`
     AND `len(data) > 1`. Else None.
   - `rest_vars` = all other outer vars.
   - Helper `_build_block(assignment)`: product of rest_vars, shuffle within
     block when `randomize_config_order`, merge `assignment` (e.g. {"pan":-1.0})
     into each config.
   - block_var None  -> single implicit block = full product (preserves old
     behavior incl. flat within-block shuffle).
   - block_var set   -> randomize block-value order (ear counterbalancing), then
     concatenate one `_build_block` per value.
   - Build parallel `self._ear_block_start` (bool per config; True at first
     config of each block) and `self._blocking_active` (bool).
   - Keep existing tail: `set_current_config(0)` + `initialize_adaptive_param()`.

3. `_show_pause` (~L776) + new helper `_ear_block_label`:
   - Helper returns "Beginning LEFT ear" / "Beginning RIGHT ear" when
     `_blocking_active`, the upcoming config is a block start, the blocking var
     is "pan", and pan resolves lateralized (<0 / >0). Else "" (centre/diotic/
     headless/out-of-range -> no line).
   - In `_show_pause`, after the subline label, add a bold `tk.Label` with that
     text if non-empty. Fires for the pre-first pause too (announces ear 1).

## Out of scope (explicit fence)
- No edits to any `paradigm_*.py`, `test_*.py`, `operator_gui.py`,
  `paradigm_setup_dialog.py`, `calibration*`, `DEFAULTS.py`, `event_gen.py`.
- No change to within-config trial/staircase/catch logic, threshold fit,
  logging schema, or calibration path.
- No outer-var GUI-exposure / product-vs-zip audit work (Problem A/B). Tracked
  separately; only vocabulary kept aligned (blocking var = 2nd "special" outer
  var category alongside latent paired/zip category).
- No change to `inter_config_pause` duration or the global shuffle for
  non-blocking paradigms.

## Behavior matrix
| Paradigm | pan outer var | Result |
|---|---|---|
| PTA, LDL | [-1.0, 1.0] | 2 ear blocks, ear order randomized, within-ear randomized |
| SRT | [0.0] | 1 block (centre), no ear label -> unchanged |
| AM/FM/GAP/DLI/ILD/ITD/IFMC/TMC | no pan outer var | 1 implicit block = full product + flat shuffle -> unchanged |

## Key signatures (for session-cleanup changelog)
- `self.block_outer_var_name = "pan"`
- `# all configs for one of its values are presented before moving to the next`
- `def _ear_block_label(self, upcoming_config_num):`
- `self._ear_block_start` (presence)

## Verification
- `ast.parse` clean; garbage-char/emoji sweep clean.
- Headless unit test of the real `_setup_variable_looping` (ast-extracted, run
  on a stub):
  - PTA-shape (fc x pan[-1,1]): configs grouped by pan; exactly 2 block starts;
    each ear has all fc; within-ear order varies across seeds; ear order varies
    across seeds.
  - SRT-shape (pan[0.0]): 1 block, no reordering surprises, `_blocking_active`
    False.
  - Diotic-shape (fc x ref_level, no pan): identical membership to old product;
    flat shuffle still applied; `_blocking_active` False.
  - `_ear_block_start` length == n_configs in all cases.

## Open questions
- None blocking. (UX nicety: longer pause / explicit confirm at the ear switch
  vs same 5 s countdown -- left as-is; revisit only if operators ask.)
