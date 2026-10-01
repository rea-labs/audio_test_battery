# PROLACTIN — Open Issues
_Generated 2026-06-05. Last revised 2026-07-17. Ordered by severity. Difficulty: 1 (trivial) to 10 (major effort). Session update log moved to the bottom of this doc (2026-07-17) — new entries are appended there, oldest first._

---

## CRITICAL — blocks data validity / causes wrong results

| # | Issue | Difficulty |
|---|-------|-----------|
| C1 | **dB HL unit contamination in PTA adaptive logic** — safety limits, threshold averaging, step logic may be operating on HL instead of SPL. Original symptom: threshold underflow to -167,061 dB (P0007, config 5, 2 kHz, 04.06.26). **Root cause re-attributed**: the underflow was a psychometric fit runaway (H1), not HL contamination — the HL conversion is downstream/innocent. Acute symptom now caught by the 2026-06-18 plausibility gate (-> NaN + warning). Narrower remaining concern: confirm step/limit/averaging logic runs on SPL, not HL (overlaps M12). Downgrade once that audit is clean. | 5 |
| ~~C2~~ | ~~**B6 hardware SPL re-measurement**~~ — **DONE** — SPL values measured and populated (DT250-A: 92.6 L / 91.4 R dB SPL). _RETSPL placeholder resolved 2026-06-19: TDH-39 -> ISO 389-8 HDA200 (Tier 0 circumaural approximation)._ | ~~3~~ |
| C3 | **TotalMix 1/2->7/8 routing gain mismatch** — IRs and SPL calibration were measured via outputs 7/8 (internally consistent). Toolbox playback goes out 1/2->7/8 via TotalMix routing; suspected -6 dB gain difference means paradigm output levels may be off by 6 dB. Verify by playing a known toolbox signal through 1/2->7/8 and measuring SPL vs. calibration-predicted value. Fix: set routing to unity gain in TotalMix (preferred), or bake a correction factor into `calibration_config.json`. **Confirmed +6 dB via 1/2->7/8 vs. direct 7/8; SPL anchors in `calibration_config.json` remeasured across all 4 profiles to account for it.** Downgrade candidate — verify remaining routing assumptions hold on next hardware session. | 3 |

---

## HIGH — affects measurement quality or data integrity

| # | Issue | Difficulty |
|---|-------|-----------|
| H1 | **Psychometric fit runaway on unbracketed staircases** — `scipy.curve_fit` unbounded; all-0/all-1 guard missed the varies-but-unbracketed case. Mulligan + `_has_stepped_down` gate (2026-06-18) prevent unbracketed tracks at source; post-fit plausibility gate maps residual runaway to NaN + operator re-run warning; `curve_fit` left unbounded by design. **Still HIGH PRIORITY, pending team discussion**: deeper fix (config-rerun/"mulligan" capability, auto-trigger vs. manual operator flag) not yet decided. Residual: near-zero positive `k` with in-range `theta` still passes (no `K_MIN` floor). | 6 |
| ~~H2~~ | ~~**CSV output audit**~~ — **RESOLVED 2026-06-19** (session 02): `pan` universal column, auto-logged outer vars, `amp_*` moved to console-only debug. | ~~3~~ |
| ~~H3~~ | ~~**dB HL column missing from data output**~~ — **RESOLVED 2026-06-19** (session 02): per-row `{inner}_HL` column, PTA only. | ~~2~~ |
| H4 | **IFMC/TMC probe level (Path B)** — `db_above_threshold` band-aided at 24 instead of correct 10; requires `trial_dur=0.016` as outer var in single PTA paradigm (not a separate `paradigm_pta_16`). `paradigm_pta.py` already supports `trial_dur` as a generic outer var (no change needed there) — remaining work is 4 small, already-scoped files (`test_pta.py`, `paradigm_setup_dialog.py`, `result_loader.py`, `test_ifmc.py`/`test_tmc.py`). Blocked on team product decision (T5/H4): both 0.5 s and 16 ms PTA per participant, or 16 ms only? | 3 |
| H5 | **IFMC: fully silent catch trials** — some catch trials play no sound while others work as intended (no click). Observed at freq_ratio 1.3 (durable ID, pre-reindex). Contributing cause (probe_level cross-pairing) likely removed 2026-07-01 session 02; diagnostic instrumentation added session 03 (console-only, verbose-gated) to distinguish gain-floor vs. degenerate-freq vs. not-a-bug. Root cause NOT yet confirmed — awaiting Tier-2 lab verbose run. | 4 |
| H6 | **Insufficient reversals handling** — if a run ends with too few reversals for a reliable threshold estimate, should prompt operator to redo. Options: always ask; ask only if below threshold; and/or increase `num_reversals` minimum to 2. Design decision needed. | 4 |
| ~~H7~~ | ~~**REW SPL weighting: dB(C) vs dB(Z)**~~ — **RESOLVED**: confirmed convention is Z-weighting (IEC 61672 flat/unweighted), not C-weighting; closed-loop SPL tuning method (self-consistent, immune to FIR/convention ambiguities) confirmed canonical going forward. | ~~4~~ |
| H8 | **IFMC high-config crash** — crashed at higher config counts before the probe_level cross-pairing fix (session 02). Likely already resolved as a side effect (config count corrected 28->14); not yet re-triggered in testing to confirm. Re-run the previously-crashing sweep; add try/except state-dump only if it still crashes. | 3 |
| H9 | **Windows lab PC thermal/crash campaign** — leading hypothesis: sustained CPU load from `update_display()` -> 4x `canvas.draw()`/trial on a large TkAgg figure. Resource-logging instrumentation (RSS/VMS/threads/handles + crash-traceback handler, all 11 paradigms) shipped 2026-07-03 session 02, awaiting a long IFMC/PTA run's data (flat vs. rising RSS decides memory-leak vs. thermal). Candidate fixes queued but not applied: `show_operator_display=False` in `test_ifmc.py`; `core.wait()`->`time.sleep()` for 3 non-critical waits in `adaptive_paradigm.py` (thermal hygiene, not primary suspect) — 4 open questions unresolved (play-gate switch in `trial_player.py`?, base-class `_wait()` vs. inline?, ship now vs. wait for replacement machine?, are local copies pushed?). Set `resource_logging: False` in `DEFAULTS.py` once the campaign ends. | 5 |

---

## MEDIUM — affects usability or correctness of secondary features

| # | Issue | Difficulty |
|---|-------|-----------|
| M1 | **PTA GUI unit inconsistency** — previous-threshold display shows HL, but `trial_amp` subplot and psychometric subplot still show SPL. Needs rationalization. | 4 |
| M2 | **Psychometric function line not drawn** — fit line missing from operator GUI plot. | 3 |
| M3 | **Previous-thresholds subplot cleanup (PTA)** — multiple outer vars need separate lines/colors; real x-axis values (not ordinal); optional connect-points. Now unblocked (every outer var logged consistently as of H2) — before starting, consult past chat "gui not exposing all outer variables". | 5 |
| M4 | **Previous-thresholds subplot for IFMC** — how to present results given multiple masker frequencies? Config count now confirmed correct (14, session 02 cross-pairing fix) — no longer an open question. Same unblock/prereq as M3. | 5 |
| M5 | **Active calibration profile in paradigm setup dialog** — expose as read-only label (mirrors audio device display); eventually a picker menu. | 3 |
| M6 | **TotalMix config in paradigm setup dialog** — show active snapshot as read-only label; can't auto-verify without OSC. | 4 |
| M7 | **`active_profile` moved to `DEFAULTS.py`** — currently buried in `calibration_config.json`. | 2 |
| M8 | **Manual config-rerun (operator/participant redo)** — discard and restart a config mid-run; distinct from the automatic first-trial mulligan, now implemented (see 2026-06-18 update). Still deferred pending team input. Open questions: rollback depth, stimulus caching, catch-trial handling, void-with-flag logging, per-trial cap, gameability, whether discarded data is saved. PRD scoped but deferred. | 5 |
| ~~M9~~ | ~~**LDL "too loud" as reversal**~~ — **RESOLVED 2026-07-17**: team decision — 5 dB step while "Comfortable", 3 dB from the first "Loud" onwards; reduction latches (a later "Comfortable" does not restore the coarse step). `RATING_LABELS` + `response_label` now report the actual rating (was collapsed to `Comfortable/Loud`). | ~~2~~ |
| M10 | **Verify dB SPL -> dB HL conversion** numerically against ISO 389 RETSPL values. _Partially addressed 2026-06-19: table now ISO 389-8 HDA200 (valid circumaural ref) and the HL output is gated by an explicit `hl_reportable` flag. Remaining: numeric spot-check of HLConverter output against the table, ideally on calibrated hardware._ | 2 |
| M11 | **Noise vs. tone SPL calibration closure** — ~1.3 dB bias between noise and sine; ref "Noise vs tone spl note 2026-06-04". Related to H7 (now resolved — weighting convention settled; bias itself unresolved). | 4 |
| M12 | **Safety limits audit** — lower/upper limit checks suspected broken during HL conversion; needs unit audit across all paradigms. Overlaps C1. | 4 |
| ~~M13~~ | ~~**TMC gap sizes: verify against MultiThreshold MATLAB**~~ — **RESOLVED 2026-07-01 (session 03)**: confirmed 4 gaps [5, 10, 20, 40 ms] per `paradigm_tinnoice_TMC.m` (`betweenRuns.variableList1`); `TMC_PROLACTIN_GAPS` corrected (was 3 gaps [30, 50, 70 ms]). | ~~3~~ |
| M14 | **AM/FM implementation double-check** — follow up on discussion with Nick; verify both implementations are correct and consistent with agreed spec. FM math itself verified correct (2026-05-31) — this item is about the broader spec-consistency discussion with Nick, not the FM bug. | 3 |
| M15 | **`spl_to_amplitude()` has no full-scale guard** — `max_spl` clamps the *requested* SPL, but nothing checks the resulting digital amplitude stays below 1.0. Never fires on the over-ear profiles (~123 dB ceiling); one bad `max_spl` edit from silently clipping on a low-ceiling profile (e.g. ER-2, 87 dB) and presenting distortion as a calibrated level. Suggested: load-time warning in `CalibrationManager` when `max_spl > measured_spl + 20*log10(1/reference_amplitude)`. Documented as a "Known gap" in `rew_inverse_filter_instructions.md` Step 7 but not fixed. | 3 |
| M16 | **LDL `max: 105.0` soft-cap on low-ceiling profiles** — matches the over-ear profiles' `max_spl`; not adjusted per-profile. LDL's new coarse +5 dB step (M9) reaches the ceiling faster. On a low-ceiling profile (ER-2, 87 dB) a run would silently clamp at `max` rather than reach true discomfort. Interacts with M15 — resolve together. Not urgent: LDL is explicitly out of ER-2 scope (see L23). | 3 |

---

## LOW — quality of life, polish, future features

| # | Issue | Difficulty |
|---|-------|-----------|
| L1 | **Quasi-random start-value jitter** — investigate low-discrepancy sequences (Halton/Sobol/stratified) to reduce threshold estimate variance. Needs justification vs. MultiThreshold spec intent. | 5 |
| L2 | **Sensation level paradigm** — PTA with in-ear headphones, SPL display mode, different frequency set. Essentially a PTA config variant. | 3 |
| L3 | **ExperimentController class** — paradigm registry as source of truth; deprecate test scripts as primary entry points. Largest planned architectural change; midpoint-reset lift (L5) a candidate at that time. | 9 |
| L4 | **MockParticipant / headless testing infrastructure** — good timing now that migration churn has ended. | 6 |
| L5 | **Lift midpoint-reset machinery into base class** — currently duplicated across ~10 paradigms; candidate for ExperimentController refactor. | 5 |
| L6 | **`utils/__init__.py` eager-import cleanup** — circular import landmine; flagged during `audio_devices` fix. | 3 |
| L7 | **`paradigm_ifmc.py` UTF-8 arrows** — decision: leave as-is vs. ASCII-normalisation pass (TMC already clean). | 1 |
| L8 | **Load field defaults to `P` for digit-only manual entry** — decision pending. | 1 |
| L9 | **Default letter field to last-used letter** | 2 |
| L10 | **PEQ-based calibration** — 9-band biquad chain alternative to FIR convolution. REW workflow now documented (Configurable PEQ, RBJ Q, flatness/match/boost targets specified); `rew_to_tmreq.py` scoped for non-TotalMix use. | 7 |
| L11 | **Separate RME UCX II FR from headphone IR** — loopback measurement, divide out. Marginal benefit given flat UCX II response, but cleaner. | 4 |
| L12 | **Delete deprecated SRT files** — once SRT verified on calibrated hardware. | 1 |
| L13 | **ITD noise: independent per-ear signals** — currently same noise signal both ears; invalid at zero ITD. | 3 |
| L14 | **Operator GUI FP warning text not paradigm-aware** — generic detection text shown even for lateralisation paradigms. | 3 |
| ~~L15~~ | ~~**Mojibake cleanup in `trial_player.py`** lines 451-453.~~ — **RESOLVED 2026-07-01**: `->` arrows in the trailing datetime-conversion comment block restored to real UTF-8. | ~~1~~ |
| L16 | **LUFS/loudness normalization for complex signals** | 6 |
| L17 | **TotalMix OSC programmatic snapshot switching** — `/3/snapshots/N/1 f 1.0` via `python-osc`. Two planned templates: (a) no-PEQ default, (b) single multi-headphone workspace via snapshots. More pressing since 2026-07-09 — the ER-2 profile sits on a different physical output (Analog 1/2) than the over-ear profiles (front HP jack). | 5 |
| L18 | **`self.post_stim_pause` migration to `DEFAULTS.py`** — added 2026-07-01 as a plain attribute with a TODO marker; centralize when DEFAULTS.py work (M7-adjacent) happens. | 2 |
| L19 | **`reaction_time_s` calibration offset** — carries ~85 ms FIR-ringout inflation (4096 taps/48 kHz); accepted as a known, documented offset. Revisit only if cross-calibration RT comparison becomes necessary. | 2 |
| L20 | **`response_label` vocabulary change (LDL)** — CSVs collected before 2026-07-17 read `Comfortable/Loud`; new runs read `Comfortable` or `Loud` separately (see M9). No consumer currently parses this column exactly (checked), but flag for `result_loader.py` / future plotting work to handle both. | 1 |
| L21 | **Calibration profiles don't record their physical output** — ER-2 is on Analog 1/2; the other four profiles assume the front HP jack. Selecting a profile doesn't prompt the operator to repatch. Suggested: `output_channels` field per profile (`"analog_1_2"` / `"headphone"`), ideally enforced/warned by `audio_devices.py`. | 2 |
| L22 | **4157 mic calibration file unverified** — the mic cal file for the B&K 4157 coupler's internal mic could not be located; the 4153 round's cal file was reused (defensible for the same physical mic, but unverified). Re-measure with the correct cal file before clinical use. | 2 |
| L23 | **ER-2 anchor placement** — currently top-of-range (83.5/84.0 dB SPL); error in `spl_to_amplitude()` is zero at the anchor by construction and grows with distance. Consider re-anchoring mid-range if L24's slope check shows a real residual error. Confirmed paradigm scope: 87 dB ceiling fine for IFMC/TMC/GAP at moderate probe levels, marginal for PTA on an impaired ear, unusable for LDL (see M16). | 3 |
| L24 | **ER-2 linearity re-measure (deferred)** — current linearity rests on 3 broadband points with ~0.5 dB scatter at the bottom. Cleaner test: REW RTA on the 1 kHz bin (not broadband SPL), 5 points near the anchor (84/79/74/69/64 dB), fit the slope. Slope 1.00 +/- 0.01 -> profile final; ~1.03 -> real error worth correcting. | 2 |
| L25 | **`retspl` for insert earphones (ER-2)** — currently `null` (SPL-only). If dB HL is ever wanted, correct family is ISO 389-2 (IEC 60318-4 occluded-ear simulator), tabulated for the ER-3A — the ER-2 is not itself a listed standard transducer, so this remains a research-grade approximation. Source values from the published standard, not memory. | 3 |
| L26 | **`calibration_config_local.json`** (git-ignored, takes precedence over `calibration_config.json`) — mirrors the existing `DEFAULTS.py` / `DEFAULTS_local.py` pattern. Not yet implemented. | 2 |
| L27 | **ER-2 -> HP output migration will invalidate the current ER-2 calibration** — a splitter is planned so the ER-2 can use the front headphone outputs (confirmed louder). Different output stage = different gain: the anchor must be re-measured (Step 7) and `max_spl` recomputed when this happens. Do not carry 83.5/84.0 across. | 1 |
| L28 | **2026-07-03 demo-regression follow-ups** — deferred to next lab visit: (a) live-verify PTA demo shows Duration and plays, IFMC/TMC demo-with-no-data shows 60 dB and plays, loading thresholds auto-fills real Probe dB, editing demo `probe_freq` resyncs the level field; (b) typing a demo `probe_freq` not in the table silently falls back to the 60 dB easy default — safe, but flag if the team wants stricter "must pick a listed freq" behaviour; (c) `_spl_to_amp`'s demo field is labelled "dB SPL" always, but falls back to legacy `db2amp` if an uncalibrated profile slips through (label becomes a minor misnomer in that case — expected calibrated in clinical use). | 2 |

---

## Questions for the Team

These are open theoretical/methodological questions that affect protocol design or parameter choices. Not bugs — need team input before any implementation decision.

| # | Question |
|---|----------|
| T1 | **Frequency set: reduce to 1 standard + tinnitus frequency?** — Would reduce session time and is theoretically motivated. Question: what do we do with control participants (no tinnitus frequency)? |
| T2 | **GAP: why only in noise and not at specific frequencies?** — There is potential complexity with clicks due to short gap durations + short fade times at specific frequencies. Is noise-only the right choice? |
| T3 | **ILD: is this test meaningful?** — Concern that ILD results may reflect hearing asymmetry rather than true ILD sensitivity ("I often heard as if the sound came more from the right, but that's just because I have better hearing there"). Is DLI sufficient, making ILD redundant? |
| ~~T4~~ | ~~**LDL: should "too loud" response count as a reversal for step-size purposes?**~~ — **RESOLVED 2026-07-17**, see M9. |
| T5 | **IFMC/TMC probe level: 10 dB SL above probe's own 16 ms threshold** — requires Path B implementation. Currently band-aided at 24 dB above long-tone PTA threshold. Team sign-off needed before reverting to 10. (See also H4.) |
| ~~T6~~ | ~~**SPL weighting convention: dB(Z) for everything?**~~ — **RESOLVED**: Z-weighting (IEC 61672 flat/unweighted) confirmed as convention; closed-loop SPL tuning confirmed canonical. |
| T7 | **Ear-order fixed L->R vs. randomized (PTA/LDL ear-blocking)** — currently randomized per run per team decision (2026-06-30); confirm holds after first live runs, or flip to fixed L->R if clinical/data-entry convention expects it. |
| T8 | **Catch-trial exponential-decay tau=2** — confirm intended steady-state relaxation speed (currently ~5-run half-life) once team reviews live data; tau is buried in `catch_trial_rate[3]`, not yet operator-editable in GUI. |
| T9 | **LDL start level 60 dB SPL** — revisit if a participant's true LDL is below 60 (severe hyperacusis/recruitment), which would ceiling-clip trial 1. |
| T10 | **Mulligan/config-rerun auto-trigger** — should a runaway/unbracketed fit auto-trigger a mid-session config rerun (with infinite-rerun guard), or stay a manual operator flag? (See H1.) |
| T11 | **Keep the H5 catch-audibility diagnostic print permanently, or strip it once H5 is diagnosed?** — lightweight (console-only, verbose-gated); leaning keep. |
| T12 | **TMC frequency list: reconcile with MATLAB single-freq (1000 Hz) vs. PROLACTIN plan's [500, 1000]?** — left untouched (out of scope) in session 03; team call needed if MATLAB parity is wanted. |
| T13 | **ER-2 (insert earphone) paradigm scope** — colleague states "85 dB should be mostly fine" for their tests; the 87 dB ceiling clears that. Confirm which paradigms are actually in scope before data collection: fine for IFMC/TMC/GAP at moderate probe levels, marginal for PTA on an impaired ear, unusable for LDL. |

---

## Notes

- **C1, M12, M1** are likely manifestations of the same root problem (HL conversion not fully integrated into adaptive logic). Fixing C1 properly should resolve or clarify both.
- **H1 (fit runaway) and M8 (manual config-rerun)** are related — the automatic first-trial mulligan (2026-06-18) is the implemented mitigation; M8's operator-facing manual redo remains deferred and is PROLACTIN's current #1 open priority pending team discussion.
- **H7 and M11** — H7 (weighting convention) is now resolved; the residual noise-vs-tone bias itself (M11) is not.
- **C3** — routing gain confirmed and corrected in calibration config; residual verification is a hardware task, not a code task.
- **L18, L19** are new pending items from the 2026-07-01 reaction-time session; both low-severity/deferred by design.
- **H5, H8, M13** — session 02 (IFMC/TMC outer-var fix) and session 03 (TMC gap correction + H5 instrumentation) are related: the probe_level cross-pairing bug fixed in session 02 is a suspected contributing cause for both H5 and H8; confirmation of both awaits lab/live testing. M13 is independently resolved (data-value fix, not related to the cross-pairing bug).
- **T4 = M9** (both now resolved 2026-07-17), **T5 = H4** — historical cross-reference retained above even though T4/M9 are closed.
- **M15, M16, L21-L27** are new 2026-07-09 items, all from the ER-2 (insert earphone) calibration session. Several (L23, L24, L27) require the calibration rig / lab hardware and cannot be progressed remotely.
- **H9** (Windows thermal/crash campaign) ties together several previously-scattered threads: the resource-logging instrumentation (2026-07-03 session 02), the `show_operator_display` candidate fix, and the `core.wait()`->`time.sleep()` thermal-hygiene fix. All still pending a long lab run.
- Since 2026-06-19: eleven sessions of code work (06-19_02, 06-26 recovery, 06-30 x3, 07-01, 07-01_02, 07-01_03, 07-03, 07-03_02, 07-09, 07-17), all with clean signature verification at every subsequent session start. The 06-26 session's root cause (stale-base edit) is the reason paradigm-file signatures, not just `adaptive_paradigm.py`, are now checked every session.


## Update Log

_Ordered oldest to newest. New entries are appended at the end._

---

## Update 2026-06-18 — Mulligan + psychometric fit-runaway fix (threshold underflow)

Colleague-authored edits to `adaptive_paradigm.py`, reviewed and extended that
session. Addresses the -167,061 dB underflow (H1 / C1 symptom). Confirmed present
and pushed in the project; `is_mulligan` verified in PTA/FM/LDL logs.

- **First-trial mulligan** in `update_counters()`: the first non-catch trial is
  forgiven (streak reset to 0, `make_easier=True`, row tagged `is_mulligan`).
  Inherited by all paradigms (none override `update_counters`); `is_mulligan`
  column confirmed in PTA/FM/LDL output. Reduces unbracketed staircases at source.
- **`_has_stepped_down` reversal gate**: prevents a track terminating while still
  monotonically all-yes (the config-14 non-bracketing case).
- **Post-fit plausibility gate**: rejects a fit when `theta` is outside
  `inner_var.data['min'/'max']` or `k <= 0` -> NaN for `threshold_dB` / `slope_k`
  (and auto-NaN for `threshold_dB_HL`), plus an unconditional `!`-banner operator
  warning naming the config as a re-run candidate (not gated on `verbose`).
- **Deliberately NOT done**: `curve_fit` left unbounded (fix is behavioral/upstream,
  not numerical); no `fit_status` column (log bloat); no `K_MIN` floor (residual:
  near-zero positive `k` with in-range `theta` still passes).

The manual operator/participant config-rerun (discard-and-restart mid-run) is a
SEPARATE, still-deferred feature — see M8.

---

## Update 2026-06-19 — dB HL: RETSPL correction + HL-reportable gate (Tier 0)

Implemented `prd_2026-06-11_dbhl_retspl.md` (Tier 0). Files edited:
`calibration_config.json`, `adaptive_paradigm.py`, `paradigm_pta.py`,
`paradigm_ldl.py`, `paradigm_srt.py`.

- **RETSPL table swapped** TDH-39 (supra-aural placeholder) -> ISO 389-8:2004 /
  ANSI S3.6-2018 HDA200 (IEC 60318-1, circumaural) in all four profiles, as the
  full ISO 389-8:2004 Table 1 HDA200 third-octave series (23 frequencies,
  125 Hz-8 kHz, including the standard-interpolated fillers; verified against
  the published table, not memory) beyond the PRD's original 11. Applied to DT250/K271 as a disclosed
  approximation; residual RECD difference vs HDA200 unquantified, expected small.
  `retspl.source` + `_retspl_note` updated to state the assumption.
- **HL output gate hardened**: `_threshold_to_hl` writes `threshold_dB_HL` only
  when `_get_paradigm_metadata().get("hl_reportable") is True` (was the fragile
  implicit `level_units == "dB SPL"`). Per team decision HL = PTA only. PTA True;
  LDL and SRT False (drops LDL's out-of-scope HL and SRT's invalid pure-tone-
  RETSPL speech HL); all other paradigms unflagged -> no HL column.
- **Not touched** (deferred per PRD): plotting/audiogram, shared-RETSPL CSV
  refactor, speech-RETSPL for SRT, and the `operator_units="dB HL"` *input* path
  (`_resolve_level_to_spl`) -- confirmed inert for SRT/LDL under normal dB-SPL
  operation and fails loud (no `self.fc`) if mis-set to dB HL.

Tier 1 (HDA200 house cal to remove the RECD assumption) remains future work.

---

## Update 2026-06-19 (session 02) — H2/H3 CSV output audit: RESOLVED

- **H3**: per-row `{inner}_HL` column added via existing gated `_threshold_to_hl()`
  (PTA only; omitted elsewhere).
- **H2**: `pan` now a universal always-logged column (fixed a real bug — PTA
  selects ear via `pan` but it was never logged); base auto-logs every outer
  var by name (structurally prevents missing-outer-var bugs); `amp_*` columns
  removed from data file, moved to console-only behind `debug_amps` flag.

---

## Update 2026-06-26 — H2 stale-base recovery

The 2026-06-19 H2 commit was made against **stale local `/mnt/project` paradigm
copies**, silently clobbering 8 local-only lines (PTA's `hl_reportable: True`,
LDL/SRT's `False` + comment, and `demo_duration_attr` in AM/FM/DLI/ILD/ITD).
Symptom: PTA lost both dB HL columns. Forward-fixed (no git restore); all 8
lines re-added, amp-column deletions kept intact. **Process fix**: session-start
check now greps a paradigm-file signature every session, not just
`adaptive_paradigm.py` (see memory / session-start protocol).

---

## Update 2026-06-30 (x3) — Catch-trial decay, ear-blocking, LDL start level

Three sessions, all base-class or single-file:

- **Catch-trial rate**: clean-run branch now relaxes exponentially toward
  baseRate (`rate_new = base + (rate_old-base)*(1-exp(-tau))`) instead of a
  fixed subtract, matching UZH MT. `catch_trial_rate` reshaped to
  `[start, baseRate, max, tau, increment] = [0.2, 0.1, 0.5, 2.0, 0.1]`.
  `paradigm_ldl.py` extended to matching 5-element `[0,0,0,0,0]` (required —
  LDL runs the same update code, would IndexError otherwise).
- **Ear-blocking (single-ear paradigms, PTA/LDL only)**: `pan` pulled out of
  the global shuffle and treated as a blocking outer var — all configs for one
  ear run before the other, ear order randomized per run for counterbalancing.
  "Beginning LEFT/RIGHT ear" label added to the pause screen. Base-class-only
  (`adaptive_paradigm.py`); diotic paradigms unaffected (verified headless).
- **LDL start level**: 50 -> 60 dB SPL (`test_ldl.py` operative value +
  `paradigm_ldl.py` fallback sync). Ceiling-clip risk flagged for severe
  hyperacusis cases below 60 dB LDL — revisit if seen in target population.

---

## Update 2026-07-01 — Reaction time logging + post-stim pause reduction

Universal `reaction_time_s` column (all 11 paradigms, zero paradigm-file edits),
referenced to end of last audible interval (`stim_end_time`, PTB clock,
background/masker-inclusive, repeat-safe). Anti-click pause reduced 0.5 -> 0.1 s
(now `self.post_stim_pause`, TODO: move to DEFAULTS.py). Files: `trial_player.py`,
`adaptive_paradigm.py`.

- Not runtime-tested (no psychopy/ptb in this env) — **live smoke-test needed
  next lab visit**: confirm column populates, values sane.
- `post_stim_pause=0.1` needs a click-test on UCX II; nudge to 0.15-0.2 if audible.
- RT carries a known calibration-dependent ~85 ms inflation (4096-tap FIR
  ringout) — accepted, single-column decision (confound-free R3 variant
  designed then dropped).

---

## Update 2026-07-01 (session 02) — IFMC/TMC outer-var fix (probe_level cross-pairing + dialog editor)

Implemented PRD `prd_2026-07-01_ifmc_tmc_outer_vars.md` (Approach 1). No
base-class edits; only `paradigm_ifmc.py`, `paradigm_tmc.py`, `test_ifmc.py`,
`test_tmc.py`, `paradigm_setup_dialog.py` touched.

- **Problem A (cross-product bug)**: `probe_level` demoted from an
  independent outer var to a `probe_freq -> amplitude` lookup
  (`set_probe_levels()`), removing the `itertools.product` cross-pairing that
  inflated config counts to `ratios x freq^2` (IFMC) and fed mismatched probe
  amplitudes into playback. Config count corrected to `ratios x freq` (IFMC:
  14, was 28) / `gaps x freq` (TMC, before session 03's gap fix). Likely a
  contributing cause of both H5 (silent catch trials) and the IFMC
  high-config crash — neither confirmed closed yet; both need re-verification
  against the corrected config count (see H8, new).
- **Problem B**: remaining outer var (`masker_freq_ratio` / `gap_duration`)
  exposed as an editable field in `ThresholdSetupDialog` (previously only
  rendered in `test_*.py`).
- Two live-testing ordering bugs fixed same session (init-before-super for
  `_probe_level_by_freq`; config-0 derivation on construction) — see session
  changelog for detail.
- Live-smoke-tested (Eric, macOS): IFMC construction OK,
  `Total runs: 14 (2 freq x 7 ratios)`, first trial plays. Full IFMC
  run-to-completion and TMC live run still outstanding.

---

## Update 2026-07-01 (session 03) — TMC gap correction + H5 diagnostic instrumentation

Implemented PRD `prd_2026-07-01_ifmc_tmc_catch_gaps.md` Phase 1 (investigation /
instrumentation) + the TMC gap-set data fix. No base-class edits; only
`standard_frequencies.py`, `paradigm_ifmc.py`, `paradigm_tmc.py` touched.

- **TMC gap set corrected** (`standard_frequencies.py`): `TMC_PROLACTIN_GAPS` ->
  `[0.005, 0.010, 0.020, 0.040]` s (5/10/20/40 ms, 4 gaps; source
  `paradigm_tinnoice_TMC.m`), replacing the shipped `[0.030, 0.050, 0.070]`
  (3 gaps). Config count now `4 gaps x freq`. **Resolves M13.**
- **H5 catch-audibility diagnostic** added to IFMC + TMC catch branches
  (`prepare_trial`): replaces the old one-line verbose catch print with a
  richer dump (`config_num`, masker freq +ratio/gap, `masker_level` + config
  `min`, `amp_L`/`amp_R`). Verbose-gated, console-only, no CSV/audio-path
  change. Instrumentation only — no fix applied. Watch the ratio=1.3 catch
  lines specifically (durable ID, pre-reindex).
- **Crash try/except**: deliberately NOT added — the IFMC high-config crash is
  probably already fixed as a side effect of session 02's cross-pairing
  removal; add only if the config sweep still crashes.
- **New minor finding**: TMC frequency list mismatch — MATLAB source uses a
  single `targetFrequency=[1000]`; PROLACTIN plan / `TMC_PROLACTIN_FREQS` use
  `[500, 1000]`. Left untouched (out of PRD scope); reconcile if the team
  wants MATLAB parity.

---

## Update 2026-07-03 (session 01) — Demo-trial regressions: PTA duration field + IFMC/TMC probe-level

Two demo-trial regressions fixed (both introduced by earlier PRDs, not new
features). No base-class behaviour change for the 9 paradigms that don't
override the new hook.

- **PTA (and all `demo_duration_attr` paradigms) had lost the demo
  "Duration (s)" field.** The consumer block in `_build_demo_section` was
  gone though the attr was still set. Restored, driven by
  `demo_duration_attr`, default = paradigm's live attr value, deduped
  against an outer-var of the same name. Renders nothing for GAP/IFMC/TMC
  (`demo_duration_attr = None`).
- **IFMC/TMC demo crashed** with `'ParadigmIFMC' object has no attribute
  'probe_level'`: session 02's `probe_level` demotion to a derived lookup
  only ran in `set_current_config`, which the demo path never calls, and the
  dialog's paradigm instance never gets `set_probe_levels()` (that runs
  post-dialog on a *separate* instance) — so the probe map was empty at demo
  time. Fixed via a new `_derive_dependent_params()` base-class hook (no-op
  default) called at the end of `set_current_config` *and* after applying
  `demo_vals` in `play_demo_trial`, plus a dedicated dB-SPL demo
  "Probe level (dB SPL)" field in `ThresholdSetupDialog` that injects
  `probe_level` directly via a new `_augment_demo_vals()` hook — so the demo
  no longer depends on `set_probe_levels`.

Files touched: `adaptive_paradigm.py` (new hook + 2 call sites),
`paradigm_ifmc.py` / `paradigm_tmc.py` (`set_current_config` override
replaced by `_derive_dependent_params` override), `paradigm_setup_dialog.py`
(demo Duration field restored; demo probe-level field + injection added). No
`test_*.py`, no other `paradigm_*.py`, no calibration/result_loader files.

---

## Update 2026-07-03 (session 02) — Resource logging + crash-handler instrumentation for the Windows lab-PC investigation

Debug instrumentation for the lab-PC lag/crash investigation (thermal vs.
memory), all in the base class so all 11 paradigms inherit it. No paradigm
files touched.

- **Always-on crash handler** (`adaptive_paradigm.py`): on an uncaught
  exception mid-run, saves partial temp data + a timestamped traceback to
  `debug_logs/`, then re-raises. Traceback file present = software bug; temp
  CSV present but no traceback file = external kill (SIGKILL bypasses the
  handler — OOM/thermal).
- **Opt-in per-trial resource logger** (`utils/resource_logger.py`, NEW):
  RSS/VMS/thread/handle counts every trial (O(1), psutil), optional gc
  object-count scan (Sound/Figure/ndarray) gated by `resource_scan_every`.
  Line-buffered CSV (crash-safe), never raises into the trial loop, degrades
  gracefully if psutil is absent. Toggle centralized in `DEFAULTS.py`
  (`resource_logging: True`, `resource_scan_every: 0`).
- A prior source review found no Python-side leak (DataFrame rebuilt not
  appended and freed each trial; GUI axes cleared every redraw; Sound
  objects are per-trial locals) — the only risk not provable from source is
  native PTB audio-track release, which the logger will surface as rising
  RSS.
- Verified end-to-end on Mac via a forced-crash smoke test (crash file +
  temp both written, re-raise clean).
- `PROLACTIN_resource_logging_handoff.md` (NEW) — team setup/run guide.
  `environment.yml` — added `psutil`.
- Awaiting from a long IFMC/PTA run: the resource CSV (flat vs. rising
  `rss_mb`), any crash file, and handle-count trend. See H9.

---

## Update 2026-07-09 — ER-2 insert-earphone calibration profile + level_validator Reload + REW instructions rev 6

Added a full calibration profile for the Neurospec/Etymotic ER-2 insert
earphone (unit C) and completed its SPL calibration. Added a Reload button +
read-only SPL anchor display to `level_validator.py`. Rewrote
`rew_inverse_filter_instructions.md` to rev 6 (fixed a longstanding UFX II ->
UCX II typo across 5 instances; added Step 7 documenting the SPL calibration
/ verification procedure, previously undocumented).

- **New `calibration_config.json` profile** `neurospec_er2_c_ucx2`. The four
  existing profiles untouched. `reference_amplitude: 0.5` (deliberately not
  the shared over-ear value — the ER-2 is on a different physical output).
  `measured_spl_left: 83.5` / `measured_spl_right: 84.0` (1 kHz, B&K 4157).
  `retspl: null` (ISO 389-8 HDA200 invalid for an insert earphone; correct
  family is ISO 389-2/ER-3A, team decision: report SPL only for now).
- **Hardware constraint discovered:** ER-2 is a 10 ohm load driven from the
  Analog 1/2 line outputs (its connector precludes the front HP jack). Line
  outs are current-limited into 10 ohm, so full-scale SPL on this chain is
  only ~90.6 dB vs. ~123 dB on the over-ear profiles. `max_spl` set to 87
  (90.6 - 3 dB headroom). Linearity verified over a 30 dB range, holds
  within ~0.6 dB.
- **`level_validator.py`:** Reload button (re-reads config path, rebuilds
  `CalibrationManager`, preserves selected profile if still present) + a
  read-only "SPL anchor:" label so the operator can confirm a reload took
  effect. No other changes to this file.
- **`rew_inverse_filter_instructions.md` rev 6:** new Step 7 documents what
  the `reference_amplitude`/`measured_spl_*` pair actually represents,
  Method A vs. Method B anchoring, the placeholder trick, anchor placement
  trade-offs, the insert-earphone/low-ceiling case, and the `retspl` block —
  none of this was previously written down.
- Several new gaps surfaced by this work (no full-scale clipping guard,
  profiles don't record their physical output, unverified 4157 mic cal
  file, etc.) — see M15, L21-L27, T13.

---

## Update 2026-07-17 — LDL step-size team decision (M9/T4): RESOLVED

Closed open issue M9/T4 (LDL "too loud" as reversal). Team decision: the LDL
ascent uses a 5 dB step while the participant rates "Comfortable" and 3 dB
from the first "Loud" onwards. The reduction latches — a later "Comfortable"
does not restore the coarse step. Two files, both LDL-only; no base-class or
calibration-path change.

- **`paradigm_ldl.py`:** `initialize_adaptive_param()` resets a
  `_loud_reported` latch + `_last_rating` per config; `check_answer()` sets
  the latch on the first Loud rating and stashes the rating for logging;
  `adapt_difficulty()` selects `step_up_initial` (5.0) while unlatched,
  `step_up_final` (3.0) after — reusing the project's usual
  initial/final-step keys, but switching on the Loud rating instead of
  `total_num_reversals` (LDL's single real reversal ends the config, so
  `step_up_final` was previously dead code). New `RATING_LABELS` class dict
  shared by console output and `get_log_data()`; `response_label` now
  reports `Comfortable`/`Loud`/`Uncomfortable` as actually given, instead of
  the old collapsed `Comfortable/Loud` label (old label kept only as a
  fallback if no rating was recorded). Docstrings updated throughout.
- **`test_ldl.py`:** `step_up_initial: 3.0 -> 5.0`; `step_up_final` value
  unchanged (3.0) but now actually live; comments/docstring/banner updated.
- **Discussed, no change made:** LDL deliberately has no start-level jitter
  (matches the MultiThreshold reference — `jitterStartdB = 0` is explicit
  for the discomfort paradigm). Reviewed the anticipation-error and
  lattice-quantization counter-arguments; neither justified a change. M9's
  5 dB grid (vs. MT's uniform 3 dB) makes the quantization argument
  marginally stronger than before — accepted as the price of the coarse
  step. See L1 if start-jitter is ever revisited; LDL should likely stay
  out of scope for it.
- Existing LDL CSVs collected before this session use the old
  `response_label` vocabulary — see L20.
