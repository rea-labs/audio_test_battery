# PRD 2026-07-01 (pass 2) — IFMC/TMC catch trials, high-config crash, TMC gaps

_Scope: IFMC + TMC. **Depends on PRD #1 landing + re-upload first** (config indexing
changes when the crossed product is removed; the two symptoms below are both
config-indexed, so they must be re-observed against the corrected set)._

---

## Goal

1. **H5 — IFMC silent catch trials.** Catch trials should play masker-only (this is
   ALREADY coded, `paradigm_ifmc.py` L148-156). Bug is intermittent SILENCE, not a
   design gap. Observed "only in config 4 (freq_ratio 1.3)" — but that index is from
   the CROSSED 28-config set; after PRD #1 the config set is 14 and that index moves.
   Instrument, re-observe post-PRD-#1, then fix once cause is known.
2. **IFMC crash at high config values.** No repro, no traceback yet. Suspect: a
   crossed (probe_freq, probe_level) pair (pre-PRD-#1) fed a mismatched/out-of-range
   probe amp or bad `fc` into playback at extreme configs. PRD #1 may fix it outright.
   Add instrumentation so the NEXT occurrence yields a full state dump.
3. **TMC gap set alignment.** `TMC_PROLACTIN_GAPS = [0.030, 0.050, 0.070]` vs MT 1.46
   `paradigm_TMC.m` = `[0.01,0.03,0.05,0.07,0.09]`. Team flagged 0.03-vs-0.04; M13
   recalls "four gaps." Target set NOT settled in project docs -> **needs Eric's
   confirmed target list before editing** (see open Q1).

---

## Why this is an investigation PRD (H5 + crash)

Root causes unknown; no repro for either. Do NOT pre-write speculative fixes.
Phase 1 = instrument + reproduce against the CORRECT (post-PRD-#1) config set.
Phase 2 = targeted fix once the dump identifies the cause. Real risk otherwise:
"fixing" a symptom that was only an artifact of the crossed product and vanishes
after PRD #1.

---

## Implementation

### Phase 1 — instrumentation (paradigm_ifmc.py; mirror to paradigm_tmc.py if wanted)

**H5 catch-trial audibility probe** (catch branch, IFMC L140-156):
- Before `tp.new_trial(...)`, when `verbose`, print the resolved catch-trial audio
  state: `config_num`, `masker_freq` (= `probe_freq*masker_freq_ratio`),
  `masker_level`, `amp_L`, `amp_R`. A silent masker will show as amp ~0 or a
  degenerate `masker_freq` -> pinpoints whether silence is (a) zero gain,
  (b) bad freq, or (c) new_trial not actually scheduling audio.
- No new CSV column (log bloat); console-only, gated on `verbose`.

**Crash state-dump** (config setup / prepare_trial):
- Wrap `prepare_trial` body in try/except that, on exception, prints full config
  state (`config_num`, `probe_freq`, `probe_level`, `masker_freq_ratio`,
  `masker_level`, resolved `masker_freq`) then re-raises. Turns the next crash into
  a diagnosable traceback + state instead of a bare stack. Remove or gate once cause
  is found.

### Phase 2 — fix (deferred until Phase-1 dump identifies cause)
- H5: fix per dump (e.g. gain-floor guard, or a genuine `new_trial` scheduling bug).
- Crash: fix per dump, OR confirm PRD #1 already resolved it (re-run the config that
  crashed; if clean across all 14, close as A-fixed).

### TMC gap set (paradigm-independent, once target confirmed)
- `standard_frequencies.py` L34: replace `TMC_PROLACTIN_GAPS` list with the
  team-confirmed set. Single-line data change; no logic edit.
- Re-check `paradigm_tmc.py` docstring examples (L17, L63) reference the same set.

---

## Key signatures (new versions)
- paradigm_ifmc.py: catch-trial audibility print (e.g. `catch audio: masker_freq=`);
  `prepare_trial` state-dump except block (e.g. `IFMC prepare_trial failed; config=`)
- standard_frequencies.py: `TMC_PROLACTIN_GAPS = [<confirmed set>]` (pending Q1)

## Verification
- H5: run IFMC (post-PRD-#1) through all 14 configs; confirm every catch trial's
  console line shows non-zero `amp_L/amp_R` + sane `masker_freq`; confirm audibly
  no silent catch (lab, by ear).
- Crash: re-run the previously-crashing config sweep; either no crash (A-fixed) or a
  clean state dump for Phase 2.
- Gaps: `len(TMC_PROLACTIN_GAPS)` == confirmed count; TMC config count ==
  `gaps x freq`; print line matches.
- ast.parse + garbage-char sweep on touched files.

---

## Out of scope (explicit)
- Problem A / B (PRD #1) — must already be merged + re-uploaded.
- Mulligan step-up symmetry — deferred (Eric, 2026-07-01).
- H4 / T5 probe-level Path B (24 -> 10 dB) — separate.
- Catch-trial exponential-decay rate logic (2026-06-30 base-class change) — Eric
  confirmed these bugs predate it; not implicated, not touched.
- Any base-class edit.

---

## Suggested order
| # | Step |
|---|------|
| 0 | Confirm PRD #1 merged + files re-uploaded (session-start signature check) |
| 1 | Add H5 catch-audibility print + crash state-dump (IFMC) |
| 2 | Re-run IFMC all configs; capture catch-trial lines + any crash dump |
| 3 | Phase-2 fix per findings (or close crash as A-fixed) |
| 4 | TMC gap set -> confirmed list (after Q1) |
| 5 | ast.parse + garbage sweep; changelog |

---

## Open questions
1. **TMC target gap set — BLOCKER for the gap edit.** Project docs don't agree:
   shipped `[30,50,70]` ms; MT 1.46 `[10,30,50,70,90]` ms; team said "0.04"; M13
   said "four gaps." What is the confirmed target list (ms)? I will not guess a
   clinical parameter.
2. **H5 scope if PRD #1 fixes it.** If, after PRD #1, no catch trial is silent across
   all 14 configs, do we still add the instrumentation (as a permanent verbose
   diagnostic) or drop it? I lean: keep the lightweight verbose print, drop the
   try/except wrapper.
3. **Instrument TMC too, or IFMC-only?** Crash reported for IFMC; H5 is IFMC. TMC
   shares the structure. Add the same prints to TMC now (cheap, symmetric) or only
   if TMC also misbehaves?
