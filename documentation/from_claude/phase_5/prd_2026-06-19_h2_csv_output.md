# PRD — H2: CSV output audit (outer-var logging + pan + amp removal)

Date: 2026-06-19  (rev 2 — explicit amp deletion, was suffix-filter)
Constraints: smallest viable diff; Mac/Windows-safe; no calibration/GUI edits.

## Goal

Make every data file self-describing: log ALL outer vars (fixes PTA `pan`/ear
never logged), `pan` always present, and remove the `amp_*` audit columns from
the CSV (console-debug only, on request).

## Root problem (why)

- `get_log_data()` hand-lists columns per paradigm -> drift. PTA default config
  (`test_pta.py`) sets `outer_2 = VarSpec(name="pan", data=[-1.0, 1.0])` (ear
  select), but PTA logs `fc, trial_dur, amp_L/R`, NOT `pan` -> CSV has no per-row
  ear, and logs `trial_dur` (fixed here) instead of the real IV. Latent across
  all 11 paradigms.
- Base already knows outer vars generically: `self.outer_vars` (names) + values
  set per-config via `set_current_config` setattr -> `getattr(self, name)`.
  Auto-logging them makes missing-outer-var structurally impossible.
- `amp_L/amp_R` (+ `tone{1,2}_amp_L/R`, `masker_amp_L/R`) = per-ear COMMANDED
  digital gains, audit only. Decision: out of files; debug-console only.

## Consumer safety (verified)

No code reads `amp_*` columns back from the CSV. All `amp_L/amp_R` references
outside paradigms are local vars from `spl_to_amplitude`, or `result_loader.py`
RE-computing amps from calibration (L336/400) -- it never trusts the logged
column. Deletion breaks nothing downstream. The `_last_*amp*` instance attrs are
set in `prepare_trial` and passed to the player as `per_channel_gain`; only the
`get_log_data` entries are the logging surface, so removing them has no playback
effect and leaves the attrs available for debug.

## No pan duplication (why)

Paths writing pan: (a) always-present literal, (b) a paradigm's own get_log_data
(LDL/SRT), (c) outer-var loop when pan is outer (PTA). All write the SAME key
`"pan"` from `self.pan`. Dict = one entry/key; pandas = one column/key. Result:
exactly one `pan` column, consistent value, no matter how many paths fire.

## Implementation

### A. `adaptive_paradigm.py` (base)

1. `__init__` (~L180, near `self.pan`): add
   `self.debug_amps = False   # console-print per-ear amp audit when True`
2. `log_data()`:
   - a) add `"pan": getattr(self, "pan", 0.0),` to base `row_data` literal
     (after `is_mulligan`). Always-present laterality column.
   - b) after the literal (before H3 HL block), auto-log every outer var:
     ```
     for _outer in self.outer_vars:
         row_data[_outer.name] = getattr(self, _outer.name, None)
     ```
     Assigning an existing key updates in place (no reorder); only genuinely
     missing outer vars (e.g. PTA `pan`) get appended.
   - c) end of method (after H3 block, before append), debug-only amp print:
     ```
     if getattr(self, "debug_amps", False):
         _amps = {k: v for k, v in self.__dict__.items()
                  if k.startswith("_last") and "amp" in k}
         if _amps:
             print(f"  [amp debug] cfg {self.config_num} tr {self.trial_num}: "
                   + ", ".join(f"{k}={v}" for k, v in _amps.items()))
     ```
     Reads existing `_last_*amp*` attrs only. Never touches the logged row.

### B. Paradigm files (delete amp log lines + docstring bullets)

| file | remove from get_log_data |
|------|--------------------------|
| paradigm_pta.py  | `amp_L`, `amp_R` |
| paradigm_am.py   | `amp_L`, `amp_R` |
| paradigm_fm.py   | `amp_L`, `amp_R` |
| paradigm_gap.py  | `amp_L`, `amp_R` |
| paradigm_dli.py  | `tone1_amp_L/R`, `tone2_amp_L/R` (4) |
| paradigm_ild.py  | `amp_L`, `amp_R` |
| paradigm_itd.py  | `amp_L`, `amp_R` |
| paradigm_ldl.py  | `amp_L`, `amp_R` (keep `pan`, `response_label`) |
| paradigm_srt.py  | `amp_L`, `amp_R` (keep `pan`, `word`, `trial_dur`) |
| paradigm_ifmc.py | `masker_amp_L/R` (+ multi-line audit comment) |
| paradigm_tmc.py  | `masker_amp_L/R` (+ multi-line audit comment) |

Inner var stays paradigm-logged (paradigms transform units: GAP -> ms,
ITD -> us). No base inner backstop (avoids raw/transformed dup).

## Key signatures (for cleanup changelog)

- `"pan": getattr(self, "pan", 0.0),`
- `for _outer in self.outer_vars:`
- `self.debug_amps = False`
- amp deletion: post-change `grep -rn '"amp_L"\|"amp_R"\|tone._amp\|masker_amp'
  paradigm_*.py` returns ZERO get_log_data hits (only `_last_*` attr refs remain)

## Out of scope (explicit fence)

- Outer-var **re-designation** review per paradigm (which vars should be outer)
  + how they're plotted. Deeper M3/M4 audit; team. H2 logs whatever's designated
  and is the prerequisite that makes that audit tractable.
- IFMC/TMC `itertools.product` cross-pairing fix (Problem A) + GUI gap (Problem
  B). NB auto-logging now surfaces Problem A's invalid pairings in the data.
- Plotting (M3/M4). H2 delivers the stable column contract only.
- amp semantics (pre/post-pipeline, RMS-of-buffer): moot -- amps leave the CSV.

## Order

| # | Step |
|---|------|
| 1 | base: `debug_amps` flag, `pan` literal, outer-var loop, debug print |
| 2 | delete amp lines from the 11 paradigms (+ docstrings) |
| 3 | verify each: `sed` range, `ast.parse`, non-ASCII grep |
| 4 | grep sweep: zero amp get_log_data hits remain |
| 5 | mock-DataFrame smoke test: PTA-like w/ `pan` outer -> `pan` present every row, `amp_*` absent; `debug_amps=True` prints |

## Open questions

None outstanding. (Q1 resolved: explicit deletion. Q2: dedicated `debug_amps`,
debug print kept minimal -- say the word to drop it entirely. Q3: deeper
outer-var/plot audit is separate, fenced above.)
