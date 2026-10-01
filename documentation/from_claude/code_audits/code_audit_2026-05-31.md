# PROLACTIN Code Audit -- 2026-05-31

Focused audit of the four MultiThreshold-derived paradigms (PTA, IFMC, TMC, LDL),
covering adaptive STEPPING BEHAVIOR and DEFAULT VALUES. Includes a roadmap
snapshot and the resolution of the FM modulation-index item.

Scope was deliberately narrow: the PROLACTIN-specific extensions (AM, FM, GAP,
DLI, ILD, ITD, SRT) are NOT in the MultiThreshold spec and were not audited here.

---

## 0. IMPORTANT -- read before acting on the findings

**The parameter-value findings below carry real uncertainty and are NOT a
definitive bug list. Use this document to drive a verification pass WITH THE TEAM
on the correct default values -- not as a directive to change code.**

Sources of uncertainty:

1. The PROLACTIN plan CSV maps each paradigm to a UZH `paradigm_tEAS_*` variant
   (`tEAS_absThreshold`, `tEAS_IFMC`, `tEAS_forwardMasking`, `tEAS_LDL`). Those
   `.m` sources are NOT available (not on the public GitHub `multiThreshold 1.46`
   folder, not in the project). Every value below is therefore measured against
   the BASE MATLAB paradigm plus the PROLACTIN plan CSV. If a tEAS variant
   overrode a value, this audit cannot see it.
2. Original MATLAB start/limit values predate PROLACTIN's migration to true
   dB SPL. Absolute level comparisons are therefore weaker than relative ones.
3. Some PROLACTIN defaults are deliberate project choices that diverge from
   MATLAB by design; the plan CSV resolves some but not all of them.

Bottom line: treat each "mismatch" as a question for the team, with the MATLAB
reference, the plan CSV, and (where obtainable) the tEAS source as the three
inputs to reconcile.

## References used

- `multithreshold_matlab_reference.md` (MultiThreshold 1.46 source summary; NOT
  the UZH-modified version specifically).
- `PROLACTIN_paradigm_plan_overview.csv` (project's own test plan).
- Reference doc's summary of `Documentation_multiThreshold_UZH_UPDATE.docx`
  (UZH mods: catch-trial log-and-continue, per-channel calibration, GUI/language
  -- none of which alter paradigm step sizes or start values).

Not consulted directly: `Lecluyse2013IJAprofiles.pdf` (see open question 5).

---

## 1. FINDINGS (severity-ranked; FLAG, do not auto-fix)

### MEDIUM

#### 1.1 TMC fine step is +/-2 dB; base MATLAB paradigm_TMC.m specifies -4 dB
- Location: `test_tmc.py:61-62` (`step_up_final=2`, `step_down_final=-2`).
- Reference is explicit: "TMC fine step is -4 dB vs IFMC's -2 dB." The coarser
  fine step exists because masker-level TMC tracks are noisier than IFMC's.
- Impact: a 2 dB fine step converges differently from the protocol intent.
- Caveat: cannot confirm whether `tEAS_forwardMasking` overrode -4 to -2.
- Suggested resolution: set `step_*_final = +/-4`, OR record a deliberate
  decision to keep +/-2.

#### 1.2 IFMC default masker-ratio set = 7 values (MATLAB); plan CSV specifies 5
- Location: `paradigm_ifmc.py:359` / `test_ifmc.py` ->
  `[0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6]`.
- Plan CSV: `0.7, 0.9, 1, 1.1, 1.3` (drops 0.5 and 1.6).
- The code follows the original MATLAB set, not the PROLACTIN plan.
- Suggested resolution: decide which set is canonical for deployment.

#### 1.3 PTA default frequencies = [500, 1000, 2000, 4000]; plan CSV lists 9
- Location: `paradigm_pta.py:327`.
- Plan CSV: `125, 250, 500, 1000, 2000, 4000, 6000, 8000, 12000`.
- The hardcoded set is missing 125 / 250 / 6000 / 8000 / 12000.
- Likely benign IF the runtime setup dialog supplies the real frequency set and
  this is only a demo default. Needs confirmation.
- Suggested resolution: confirm the dialog overrides this at runtime, or widen
  the default to the plan set.

### LOW

#### 1.4 IFMC start-value jitter is multiplicative; PTA/TMC are additive
- Location: `paradigm_ifmc.py:88-90`
  (`base_start * uniform(1/1.2, 1.2)`).
- `masker_level` is a linear-dB variable (per the project's own convention), so
  the spec form -- "randomize within +/- half of the large step" -- is ADDITIVE,
  which PTA (`paradigm_pta.py:91-95`) and TMC (`paradigm_tmc.py:114-119`) already
  use. Multiplicative jitter scales with the start value and is asymmetric
  (start=20 -> -3.3/+4 dB; start=50 would be -8.3/+10 dB).
- Impact: affects only the startup value, not the converged threshold.
- Suggested resolution: switch IFMC to additive `base + uniform(-half_step,
  +half_step)` to match the other two paradigms.

#### 1.5 Start values diverge from MATLAB; TMC starts BELOW IFMC
- PTA 60 (MATLAB 30), IFMC 20 (10), TMC 10 (50), LDL 50 (75).
- Absolute differences are weak evidence post-dB-SPL migration. The notable item
  is RELATIVE: MATLAB starts TMC well above IFMC (50 vs 10) because on-frequency
  masking needs more masker; PROLACTIN inverts that (TMC 10 < IFMC 20). Starting
  TMC at 10 dB SPL spends extra startup trials climbing to threshold.
- Impact: startup efficiency, not correctness.
- Suggested resolution: reconsider the TMC start value with the team.

#### 1.6 PTA tone durations = [0.5, 1.0] s; MATLAB absThreshold = 0.25 s
- Location: `paradigm_pta.py:331`.
- 0.5 s is defensible for clinical PTA; the 1.0 s second duration is unusual.
- Suggested resolution: confirm both durations are intended (not a leftover).

---

## 2. VERIFIED CORRECT (no action)

- Step DIRECTION, all four paradigms:
  - PTA: heard -> quieter (psyFunSlope +1).
  - IFMC / TMC: heard -> masker level UP (inverted psyFunSlope -1 convention),
    implemented via "harder" -> masker += step_up.
  - LDL: ascending; ends on first "uncomfortable" (`trials_after_reversal=1`).
- Coarse/fine phase boundary at the first reversal; on the reversal trial the
  masker/level is reset to the midpoint and make_harder/make_easier are cleared,
  so no double-step is applied (the TMC/IFMC fix from 2026-05-30 -- confirmed
  sound).
- Catch-trial schedule: trial 0 never, trial 1 always, otherwise probabilistic;
  per-run rate adaptation. Matches the reference.
- Catch-trial handling is LOG-AND-CONTINUE (no streak change, warning shown),
  matching the UZH modification rather than the original stop-and-restart.
- TMC gaps {30, 50, 70} ms and LDL frequencies {500, 1000, 2000, 4000, 8000}
  both match the plan CSV exactly.

---

## 3. ROADMAP SNAPSHOT (as of 2026-05-31)

Gates data collection:
1. [DONE] FM modulation-index item -- resolved (see section 4).
2. B6 SPL re-measurement -- hardware-gated; blocks every SPL-dependent paradigm
   (`spl_to_amplitude()` raises until null SPL values are populated).

Infrastructure (no hardware needed):
3. MockParticipant / headless testing (`headless=True` flag, MockParticipant +
   per-paradigm subclasses for DLI/LDL/GAP).
4. ExperimentController (paradigm registry as source of truth; deprecate test
   scripts as entry points). Fold the duplicated midpoint-reset machinery into
   the base class here.

Recommended ordering note: do #3 before #4. ExperimentController is the largest
structural change to date; regression coverage (MockParticipant running all
paradigms headless to a known threshold) should exist before config ownership is
moved around.

Decisions / small code:
- IFMC/TMC Path B (`trial_dur` as outer var; revert `db_above_threshold` 24 -> 10).
- IFMC arrow ASCII normalization (leave vs. sweep).
- Load-field digit-only default; default participant letter.
- Stale audit-doc cleanup (see section 4).
- This audit's section 1 items (verify default values with the team).

Deferred (tracked, not scheduled):
- PEQ-based calibration alternative to FIR convolution.
- Separate RME UCX II FR from headphone IR (loopback DAC->ADC, divide out).
- NiceGUI migration for the participant GUI (tablet).
- Centralized per-paradigm defaults config.
- Per-channel SPL probe handling in IFMC/TMC.
- 105 dB SPL safety ceiling -- awaiting team confirmation.
- TotalMix workspace templates (no-PEQ baseline + multi-headphone snapshot).

---

## 4. FM modulation-index resolution + stale-audit flag

RESOLVED (2026-05-31). `event_gen.fm()` math was verified correct: standard
sinusoidal FM, `beta = delta_f / fm`, `delta_f = fc * mod_ind / 100`. The
percent-to-deviation convention (`mod_ind` as percent) was accepted via listening
checks by Prague-experienced testers.

Caveat: this rests on listening verification, NOT a primary-source citation.
There is no spec document confirming the percent convention. Fine to proceed for
data collection; flagged here so the "verified by ear, no primary source" basis
is on record.

STALE PRIOR AUDIT -- action item:
- `code_audit_2026-02-19.md` sections 1.3 and 5.4 describe the OLD raw-beta FM
  behavior as a live bug. That description is now stale. Correct or annotate
  those sections next time that file is touched so the resolved item does not
  resurface as a phantom bug.

---

## 5. Open questions for the team

1. TMC fine step: intentional +/-2, or restore MATLAB's -4? Does
   `tEAS_forwardMasking` settle it?
2. IFMC ratios: 7 (MATLAB) or 5 (plan CSV)?
3. PTA frequencies/durations: are the hardcoded values demo defaults overridden
   by the setup dialog at runtime, or the actual deployment config?
4. Make IFMC start-jitter additive to match PTA/TMC?
5. `trials_after_reversal = 10`: not verified against Lecluyse 2013 (not loaded).
   MATLAB's 10 / 20 are TOTAL-trial counts, not post-reversal counts, so they are
   not directly comparable. Confirm the intended post-reversal count against the
   Lecluyse procedure.
