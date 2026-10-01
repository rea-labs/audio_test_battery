# PRD - AM/FM per-frequency target (carrier) level

_2026-07-18, rev 2. GitLab: "FM/AM: 1) add individual threshold config for target level."_
_Scope confirmed: AM + FM only._

## Decisions locked (this round)

1. **Handoff = (a)**: per-freq levels live in `params`; dialog mutates in place;
   run reconstructs from the same dict. `set_target_levels()` retained as the
   optional runtime hook, not the primary path.
2. Levels stored as **absolute dB SPL** (not threshold + dB-SL offset).
3. GUI **rebuilds target rows live** when the fc set/values change (new freqs at
   60, surviving freqs keep their entry, removed freqs dropped). This rebuild IS
   the fc<->array lockstep mechanism - they cannot drift out of length, so no
   separate divergence guard is needed.
4. Target levels supplied as a **length-n list co-indexed with `fc`** (zipped by
   index, NOT crossed), stored in a **dedicated params key, NOT an `outer_*`
   slot**. Default auto-built from the fc outer var when no list is supplied.
5. **All-or-nothing**: a supplied array must match `len(fc)` exactly (fail-fast);
   if none supplied, the whole map defaults to 60. In the GUI every field must be
   filled on OK.

## Goal

Give each carrier frequency `fc` its own target (carrier) level instead of one
flat 60 dB SPL. Plumbing + GUI exposure now; defaults to 60 when no array given.

## Design

`tone_level_db` becomes a **co-indexed parallel array to `fc`**, not an outer var:

- **Representation.** A length-n list aligned to `fc` (`level[i]` pairs with
  `fc[i]`). Zipped into `_target_level_by_freq: {fc -> dB SPL}` at construction.
- **Why not a literal `outer_N`.** The base config builder crosses all `outer_*`
  via `itertools.product`; a length-n `tone_level_db` outer var would give n x n
  mismatched configs (the documented `probe_level` cross-pairing bug). Zip, not
  cross - so it is kept out of the product. (A generic base-class "co-index" var
  is deliberately NOT built; too much blast radius for AM/FM-only.)
- **Derivation.** `_derive_dependent_params()` sets
  `self.tone_level_db = _target_level_by_freq[self.fc]` after the base sets outer
  vars (normal run + demo). No map / missing freq -> 60 fallback.
- **Default.** No array supplied -> auto-build `{fc: 60.0}` from the fc list.
- **Validation.** Supplied array length != `len(fc)` -> raise at construction.

No calibration-path change (`spl_to_amplitude(tone_level_db)` untouched).
No CSV-schema change: `get_log_data()` logs `tone_level_db` from the attribute
(`if hasattr(self,'tone_level_db')`), so demotion keeps the column provided the
attribute is set.

## Implementation, per file

### `paradigm_am.py`, `paradigm_fm.py` (identical edits)

- `self._target_level_by_freq = {}` **before** `super().__init__()` (base runs
  `set_current_config(0)` -> `_derive_dependent_params()` during construction).
- Build the map from config: read the supplied `target_level` list, zip with the
  `fc` outer var, validate `len` match; if absent, `{fc: 60.0}`.
- `set_target_levels(freq_to_db)` - fail-fast against configured `fc` (mirrors
  IFMC `set_probe_levels`). Optional runtime hook (file/other-paradigm loader).
- Override `_derive_dependent_params()`: derive `self.tone_level_db` from
  `self.fc`; 60 fallback.
- Docstrings / inline comments / `__main__` demo comments updated: "carrier level
  (outer variable)" -> "carrier level (per-freq array co-indexed with fc)".
  (doc-hygiene rule)
- `__main__` demo block: drop the `tone_level_db` outer_3 VarSpec.

### `test_am.py`, `test_fm.py`

- Remove `"outer_3"` (`tone_level_db`).
- Add the co-indexed target array (length = `len(AUDIOMETRIC_FREQS)`), all 60.0.
  Stored in a dedicated params key (see Open Q1), NOT an `outer_*` slot.
- Post-demotion configs = `fc x fm` only - unchanged from today.

### `paradigm_setup_dialog.py` - base `ParadigmSetupDialog`

- New `_build_target_level_editor()`, rendered **only when `params` carries the
  target-level key**. Conditional => zero blast radius on DLI/ILD/ITD/GAP/PTA/
  LDL/SRT.
- One dB `Entry` per `fc`, pre-filled from the map (60 when defaulting).
- **Live rebuild** on fc-set / values change (reuse `_on_set_change`): new freqs
  get 60, entries for surviving freqs preserved, dropped freqs removed.
- On OK: **every field required** (non-empty numeric, else error); build the
  length-n array in fc order and write back per Open Q1.

## Key signatures (for session-cleanup changelog)

- `paradigm_am.py` / `paradigm_fm.py`:
  - `self._target_level_by_freq = {}`
  - `def set_target_levels(self, freq_to_db):`
  - `def _derive_dependent_params(self):`
- `paradigm_setup_dialog.py`: `def _build_target_level_editor(self`
- `test_am.py` / `test_fm.py`: target-level key present AND **zero hits** for
  `outer_3` + `tone_level_db` together.

## Out of scope (hard fence)

- **DLI / ILD / ITD** `ref_level_db` - same flat-60 pattern, NOT touched.
- **IFMC / TMC** and `ThresholdSetupDialog`.
- Any actual **file loader** or cross-paradigm threshold read: only the
  `set_target_levels()` hook ships; no file parsing, no dB-SL offset math.
- Generic base-class co-indexed-outer-var support.
- `fc` values / frequency sets / `fm`; CSV schema; calibration path.

## Suggested order

| # | Step | Verify |
|---|------|--------|
| 1 | Paradigm plumbing (am, fm): map, zip, validate, derive, 60 fallback | demo runs at 60 |
| 2 | Demote in test_am/test_fm; add co-indexed array | config count = fc x fm; `tone_level_db` still in CSV |
| 3 | GUI editor: per-fc fields, live rebuild, all-required | edit a freq, confirm it reaches the run |
| 4 | Sweep | `ast.parse`; `ord(c)>127` garbage check; additive-diff on test_*.py |

## Open questions

None outstanding. Both prior questions resolved:

- **Params key** - confirmed dedicated key `"target_level"` ->
  `VarSpec(name="tone_level_db", data=[...])`, kept out of the `outer_*` product.
- **Length-mismatch UX** - live rebuild (decision 3) keeps fc and the array in
  lockstep; no separate live length guard. Construction-time raise remains as the
  backstop for programmatic (`set_target_levels`) misuse.
