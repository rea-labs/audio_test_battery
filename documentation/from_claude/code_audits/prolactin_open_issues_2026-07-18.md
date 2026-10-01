# PROLACTIN — Open Issues
_Generated 2026-06-05. Last revised 2026-07-18 (session 02). Ordered by severity. Difficulty: 1 (trivial) to 10 (major effort). Session update log moved to the bottom of this doc (2026-07-17) — new entries are appended there, oldest first._

---

## CRITICAL — blocks data validity / causes wrong results

| # | Issue | Difficulty |
|---|-------|-----------|
| C1 | **dB HL unit contamination in PTA adaptive logic** — safety limits, threshold averaging, step logic may be operating on HL instead of SPL. Original symptom: threshold underflow to -167,061 dB (P0007, config 5, 2 kHz, 04.06.26). **Root cause re-attributed**: the underflow was a psychometric fit runaway (H1), not HL contamination — the HL conversion is downstream/innocent. Acute symptom now caught by the 2026-06-18 plausibility gate (-> NaN + warning). Narrower remaining concern: confirm step/limit/averaging logic runs on SPL, not HL (overlaps M12). Downgrade once that audit is clean. | 5 |
| ~~C2~~ | ~~**B6 hardware SPL re-measurement**~~ — **DONE** — SPL values measured and populated (DT250-A: 92.6 L / 91.4 R dB SPL). _RETSPL placeholder resolved 2026-06-19: TDH-39 -> ISO 389-8 HDA200 (Tier 0 circumaural approximation)._ | ~~3~~ |
| C3 | **TotalMix 1/2->7/8 routing gain mismatch** — IRs and SPL calibration were measured via outputs 7/8 (internally consistent). Toolbox playback goes out 1/2->7/8 via TotalMix routing; suspected -6 dB gain difference means paradigm output levels may be off by 6 dB. Verify by playing a known toolbox signal through 1/2->7/8 and measuring SPL vs. calibration-predicted value. Fix: set routing to unity gain in TotalMix (preferred), or bake a correction factor into `calibration_config.json`. **Confirmed +6 dB via 1/2->7/8 vs. direct 7/8; SPL anchors in `calibration_config.json` remeasured across all 4 profiles to account for it.** Downgrade candidate — verify remaining routing assumptions hold on next hardware session. _2026-07-18 (session 02): residual hardware re-verification now DONE for headphones X and C; remaining profiles still to confirm on the next hardware session._ | 3 |

---

## HIGH — affects measurement quality or data integrity

| # | Issue | Difficulty |
|---|-------|-----------|
| H1 | **Psychometric fit runaway on unbracketed staircases** — `scipy.curve_fit` unbounded; all-0/all-1 guard missed the varies-but-unbracketed case. Mulligan + `_has_stepped_down` gate (2026-06-18) prevent unbracketed tracks at source; post-fit plausibility gate maps residual runaway to NaN + operator re-run warning; `curve_fit` left unbounded by design. **Still HIGH PRIORITY, pending team discussion**: deeper fix (config-rerun/"mulligan" capability, auto-trigger vs. manual operator flag) not yet decided. _Residual near-zero-`k` gap CLOSED 2026-07-18: `PSYCHOMETRIC_K_MIN = 0.01` floor added, and the guard's slope test is now signed (see H10). The fit-validation half of H1 is therefore complete; what remains is purely the rerun-policy decision (T10)._ | 6 |
| ~~H2~~ | ~~**CSV output audit**~~ — **RESOLVED 2026-06-19** (session 02): `pan` universal column, auto-logged outer vars, `amp_*` moved to console-only debug. | ~~3~~ |
| ~~H3~~ | ~~**dB HL column missing from data output**~~ — **RESOLVED 2026-06-19** (session 02): per-row `{inner}_HL` column, PTA only. | ~~2~~ |
| H4 | **IFMC/TMC probe level (Path B)** — `db_above_threshold` band-aided at 24 instead of correct 10; requires `trial_dur=0.016` as outer var in single PTA paradigm (not a separate `paradigm_pta_16`). `paradigm_pta.py` already supports `trial_dur` as a generic outer var (no change needed there) — remaining work is 4 small, already-scoped files (`test_pta.py`, `paradigm_setup_dialog.py`, `result_loader.py`, `test_ifmc.py`/`test_tmc.py`). Blocked on team product decision (T5/H4): both 0.5 s and 16 ms PTA per participant, or 16 ms only? | 3 |
| H5 | **IFMC: fully silent catch trials** — some catch trials play no sound while others work as intended (no click). Observed at freq_ratio 1.3 (durable ID, pre-reindex). Contributing cause (probe_level cross-pairing) likely removed 2026-07-01 session 02; diagnostic instrumentation added session 03 (console-only, verbose-gated) to distinguish gain-floor vs. degenerate-freq vs. not-a-bug. Root cause NOT yet confirmed — awaiting Tier-2 lab verbose run. _2026-07-18 (session 02): considered LIKELY FIXED (via the probe_level cross-pairing removal) but needs clear confirmation — a loopback capture of an IFMC run, inspecting catch-trial epochs for true silence, is the ear-free way to confirm._ | 4 |
| H6 | **Insufficient reversals handling** — if a run ends with too few reversals for a reliable threshold estimate, should prompt operator to redo. Options: always ask; ask only if below threshold; and/or increase `num_reversals` minimum to 2. Design decision needed. | 4 |
| ~~H7~~ | ~~**REW SPL weighting: dB(C) vs dB(Z)**~~ — **RESOLVED**: confirmed convention is Z-weighting (IEC 61672 flat/unweighted), not C-weighting; closed-loop SPL tuning method (self-consistent, immune to FIR/convention ambiguities) confirmed canonical going forward. | ~~4~~ |
| H8 | **IFMC high-config crash** — crashed at higher config counts before the probe_level cross-pairing fix (session 02). Likely already resolved as a side effect (config count corrected 28->14); not yet re-triggered in testing to confirm. Re-run the previously-crashing sweep; add try/except state-dump only if it still crashes. _2026-07-18 (session 02): now suspected to be the dying lab PC (see H9), not a software bug — confirm once the replacement PC is set up and tested._ | 3 |
| H9 | **Windows lab PC thermal/crash campaign** — leading hypothesis: sustained CPU load from `update_display()` -> 4x `canvas.draw()`/trial on a large TkAgg figure. Resource-logging instrumentation (RSS/VMS/threads/handles + crash-traceback handler, all 11 paradigms) shipped 2026-07-03 session 02, awaiting a long IFMC/PTA run's data (flat vs. rising RSS decides memory-leak vs. thermal). Candidate fixes queued but not applied: `show_operator_display=False` in `test_ifmc.py`; `core.wait()`->`time.sleep()` for 3 non-critical waits in `adaptive_paradigm.py` (thermal hygiene, not primary suspect) — 4 open questions unresolved (play-gate switch in `trial_player.py`?, base-class `_wait()` vs. inline?, ship now vs. wait for replacement machine?, are local copies pushed?). Set `resource_logging: False` in `DEFAULTS.py` once the campaign ends. _2026-07-18 (session 02): now suspected to be the dying lab PC itself (failing hardware), not the software load — confirm once the replacement PC is set up and tested. The `canvas.draw()` / `core.wait()` thermal-hygiene fixes remain worth doing regardless, but may not be the crash cause._ | 5 |
| ~~H10~~ | ~~**IFMC/TMC logged NaN for every threshold**~~ — **RESOLVED 2026-07-18**: the implausible-fit guard (2026-06-18) required `k > 0`. IFMC/TMC adapt the MASKER level, so p(yes) FALLS with level and `k` is necessarily NEGATIVE — every physically correct IFMC/TMC fit was rejected and logged as NaN. Surfaced while implementing M3/M4 (empty panel 39 + no psychometric curve were the same NaN). Fix: `psychometric_slope_sign` class attr (+1 detection / -1 masking), guard now `k*sign >= PSYCHOMETRIC_K_MIN`. Verified on live IFMC data — configs fit theta = 93.0 / 75.8 / 77.0 dB SPL, all previously discarded. Detection paradigms unaffected; an inverted PTA fit is still rejected. **Data already collected is affected — see M17.** | ~~4~~ |

---

## MEDIUM — affects usability or correctness of secondary features

| # | Issue | Difficulty |
|---|-------|-----------|
| ~~M1~~ | ~~**PTA GUI unit inconsistency**~~ — **RESOLVED 2026-07-17 (session 02)**: `_level_series()` converts a level array to display units in one place; panels 38/40 now follow `operator_units`, gated by `_operator_in_hl()` (requires `hl_calibrated` + `hl_reportable` + a resolvable `fc`) so LDL/SRT and uncalibrated runs stay in SPL and _say_ SPL. | ~~4~~ |
| ~~M2~~ | ~~**Psychometric function line not drawn**~~ — **RESOLVED 2026-07-17 (session 02)**: root cause was state/ordering, not the fit. _Note: a second, unrelated cause of a missing curve was found 2026-07-18 for IFMC/TMC only — the threshold really was NaN (see H10)._ | ~~3~~ |
| ~~M3~~ | ~~**Previous-thresholds subplot cleanup (PTA)**~~ — **RESOLVED 2026-07-18**: panel 39 now plots threshold vs the real values of `outer_1` (PTA `fc` -> a true audiogram: log x-axis, ticks at 250/500/1000/2000/4000/8000), with `outer_2..N` as visually distinct series and a real `ax.legend()` replacing the free-text box. Points connected. Per-marker value labels removed. See the 2026-07-18 update. | ~~5~~ |
| ~~M4~~ | ~~**Previous-thresholds subplot for IFMC**~~ — **RESOLVED 2026-07-18** (same commit as M3): `outer_1` = `masker_freq_ratio` gives the conventional IFMC contour on the x-axis; `probe_freq` becomes one series per frequency instead of collapsing onto a single indistinguishable line. Constants (`fm`, `tone_level_db`, `ref_level_db`) are filtered out of the series and shown as an annotation. **Note: M3/M4 only became testable once H10 was fixed — panel 39 was empty because every IFMC threshold was NaN, not because of a plotting bug.** | ~~5~~ |
| M5 | **Active calibration profile in paradigm setup dialog** — expose as read-only label (mirrors audio device display); eventually a picker menu. | 3 |
| M6 | **TotalMix config in paradigm setup dialog** — show active snapshot as read-only label; can't auto-verify without OSC. | 4 |
| M7 | **`active_profile` moved to `DEFAULTS.py`** — currently buried in `calibration_config.json`. | 2 |
| M8 | **Manual config-rerun (operator/participant redo)** — discard and restart a config mid-run; distinct from the automatic first-trial mulligan, now implemented (see 2026-06-18 update). Still deferred pending team input. Open questions: rollback depth, stimulus caching, catch-trial handling, void-with-flag logging, per-trial cap, gameability, whether discarded data is saved. PRD scoped but deferred. | 5 |
| ~~M9~~ | ~~**LDL "too loud" as reversal**~~ — **RESOLVED 2026-07-17**: team decision — 5 dB step while "Comfortable", 3 dB from the first "Loud" onwards; reduction latches (a later "Comfortable" does not restore the coarse step). `RATING_LABELS` + `response_label` now report the actual rating (was collapsed to `Comfortable/Loud`). | ~~2~~ |
| M10 | **Verify dB SPL -> dB HL conversion** numerically against ISO 389 RETSPL values. _Partially addressed 2026-06-19: table now ISO 389-8 HDA200 (valid circumaural ref) and the HL output is gated by an explicit `hl_reportable` flag. Remaining: numeric spot-check of HLConverter output against the table, ideally on calibrated hardware._ | 2 |
| M11 | **Noise vs. tone SPL calibration closure** — ~1.3 dB bias between noise and sine; ref "Noise vs tone spl note 2026-06-04". Related to H7 (now resolved — weighting convention settled; bias itself unresolved). | 4 |
| M12 | **Safety limits audit** — lower/upper limit checks suspected broken during HL conversion; needs unit audit across all paradigms. Overlaps C1. | 4 |
| ~~M13~~ | ~~**TMC gap sizes: verify against MultiThreshold MATLAB**~~ — **RESOLVED 2026-07-01 (session 03)**: confirmed 4 gaps [5, 10, 20, 40 ms] per `paradigm_tinnoice_TMC.m` (`betweenRuns.variableList1`); `TMC_PROLACTIN_GAPS` corrected (was 3 gaps [30, 50, 70 ms]). | ~~3~~ |
| M14 | **AM/FM implementation double-check** — follow up on discussion with Nick; verify both implementations are correct and consistent with agreed spec. FM math itself verified correct (2026-05-31) — this item is about the broader spec-consistency discussion with Nick, not the FM bug. _2026-07-18 (session 02): per-fc `tone_level_db` target-level feature added (was flat 60 dB); the new per-carrier level behaviour is now part of what the Nick review covers. Loopback recording is the ear-free way to confirm the per-fc levels track the table (relative dB) — see L37 / Notes._ _2026-07-18 (session 02): implementation seems OK on inspection, but still worth digging into further before sign-off — not yet closed._ | 3 |
| M15 | **`spl_to_amplitude()` has no full-scale guard** — `max_spl` clamps the *requested* SPL, but nothing checks the resulting digital amplitude stays below 1.0. Never fires on the over-ear profiles (~123 dB ceiling); one bad `max_spl` edit from silently clipping on a low-ceiling profile (e.g. ER-2, 87 dB) and presenting distortion as a calibrated level. Suggested: load-time warning in `CalibrationManager` when `max_spl > measured_spl + 20*log10(1/reference_amplitude)`. Documented as a "Known gap" in `rew_inverse_filter_instructions.md` Step 7 but not fixed. | 3 |
| M16 | **LDL `max: 105.0` soft-cap on low-ceiling profiles** — matches the over-ear profiles' `max_spl`; not adjusted per-profile. LDL's new coarse +5 dB step (M9) reaches the ceiling faster. On a low-ceiling profile (ER-2, 87 dB) a run would silently clamp at `max` rather than reach true discomfort. Interacts with M15 — resolve together. Not urgent: LDL is explicitly out of ER-2 scope (see L23). | 3 |
| M17 | **Historical IFMC/TMC results carry NaN thresholds** — every IFMC/TMC config run between the 2026-06-18 plausibility guard landing and the 2026-07-18 fix logged `threshold_dB` = NaN (see H10). Raw per-trial data is intact, so thresholds are recomputable offline from the CSVs. **Action: establish how far back this goes and whether any of it feeds an analysis** — promote to HIGH if it does. _Tracked as L33 in `session_changelog_2026-07-18.md`; re-tiered here, since the LOW tier is "quality of life / polish" and this is data integrity._ _2026-07-18 (session 02): not a concern right now — raw per-trial data is intact and recomputable, and nothing currently consumes these thresholds. Backwards compatibility of historical results will matter eventually, but not yet; revisit before any analysis actually depends on pre-fix IFMC/TMC runs._ | 2 |

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
| ~~L7~~ | ~~**`paradigm_ifmc.py` UTF-8 arrows**~~ — **RESOLVED 2026-07-18 (session 02)**: the plain-Unicode arrows are fine and pass the sweep. The original garbage-char problem was emojis / icon characters that weren't being re-encoded or displayed properly — not the `→` text arrows. Nothing to normalise here; the ban stays on emoji/icon glyphs only, per the agreed policy. | ~~1~~ |
| L8 | **Load field defaults to `P` for digit-only manual entry** — decision pending. | 1 |
| L9 | **Default letter field to last-used letter** | 2 |
| L10 | **PEQ-based calibration** — 9-band biquad chain alternative to FIR convolution. REW workflow now documented (Configurable PEQ, RBJ Q, flatness/match/boost targets specified); `rew_to_tmreq.py` scoped for non-TotalMix use. | 7 |
| L11 | **Separate RME UCX II FR from headphone IR** — loopback measurement, divide out. Marginal benefit given flat UCX II response, but cleaner. | 4 |
| ~~L12~~ | ~~**Delete deprecated SRT files**~~ — **DONE 2026-07-18 (session 02)**: moved to the `/deprecated` folder. | ~~1~~ |
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
| ~~L29~~ | ~~**Placeholder axis labels masquerade as rendered output**~~ — **RESOLVED 2026-07-18** (M3/M4 D9): `'Threshold (dB)'` was byte-identical to the non-HL dynamic label, so "not yet rendered" was indistinguishable from "rendered in SPL mode". Placeholders are now unitless (`'Threshold'`, `'Stimulus Level'`) at BOTH sites (startup + `clear_display()`). Panel 39's placeholder x label is `'Outer Variable'` (was `'Configuration Number'`, which named a variable the panel no longer plots). | ~~1~~ |
| ~~L30~~ | ~~**Panel 40 x-label hardcoded `'Stimulus Level'`**~~ — **RESOLVED 2026-07-18** (M3/M4 D8): wrong for GAP (`gap_duration`, s), AM/FM (`mod_ind`, %), ITD (`itd_ms`). `VarSpec` now carries optional `label`/`units` display metadata and the axis names itself via `axis_label()`. The same defect in the fit legend (`Fit: θ=0.0 dB SPL` on GAP) and in panel 39's y-label (`Threshold (dB)` on a seconds-valued GAP threshold) was fixed in the same commit. | ~~2~~ |
| L31 | **`_update_*_plot()` early-return-before-`clear()`** — panels retain stale content when they have no data for the current config. Harmless today (arguably desirable at rollover — it is why the psychometric curve lingers into config N+1 trial 0), but it is why L29 was confusing. Deliberate; documented. | 2 |
| L32 | **`PSYCHOMETRIC_K_MIN = 0.01` needs team ratification** — the near-zero-`k` floor added 2026-07-18 (closing H1's residual gap) is a threshold applied to real participant fits, chosen by the assistant, not by the team. Rationale: ~50x below Lecluyse & Meddis's shallowest reported slope (0.5 normal / 1.0 impaired), so it should only ever catch numerical garbage, not shallow-but-real fits. Single module constant in `adaptive_paradigm.py`; trivial to move or change. See T14. | 1 |
| L34 | **Panel 39 constants annotation placement is provisional** — outer vars that don't vary (`fm`, `tone_level_db`, `ref_level_db`) are filtered out of the series and rendered as small italic text above the axes, right-aligned (M3/M4 D3). PRD flagged "revisit after live use"; now live on AM/FM/DLI/ILD/ITD. | 1 |
| L35 | **`paradigm_*.py` `__main__` demo blocks build metadata-free VarSpecs** — `paradigm_pta`, `_am`, `_fm`, `_dli`, `_gap`, `_ifmc`, `_itd`, `_ild` construct their own `VarSpec`s without `label`/`units`, so their axes fall back to bare identifiers. D8 fallback working as designed; cosmetic, demo-only. Trivial to fill if anyone uses those demos. | 2 |
| ~~L37~~ | ~~**AM/FM per-fc target level + scrollable setup dialog — pending live validation**~~ (2026-07-18 session 02) — **DONE 2026-07-18 (session 02)**: verified working (Start reachable, scroll + hint behave, per-fc dB editor persists, demo carrier-level field plays). Base-dialog scroll-layout change confirmed OK. | ~~2~~ |

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
| T14 | **`PSYCHOMETRIC_K_MIN` floor value** — is 0.01 the right minimum acceptable psychometric slope for a fit to be logged rather than discarded as NaN? Chosen as ~50x below the shallowest slope Lecluyse & Meddis report, i.e. sized to catch numerical garbage only. Needs Nick/Pat sign-off before it touches participant data. (See L32, H1.) |
| T13 | **ER-2 (insert earphone) paradigm scope** — colleague states "85 dB should be mostly fine" for their tests; the 87 dB ceiling clears that. Confirm which paradigms are actually in scope before data collection: fine for IFMC/TMC/GAP at moderate probe levels, marginal for PTA on an impaired ear, unusable for LDL. |
| T15 | **AM/FM per-fc target level — design ratification** (2026-07-18 session 02, GitLab request "FM/AM: add individual threshold config for target level"). Two open sub-decisions: (a) **demo carrier-level field** is currently an independent override (type any dB for the demo, decoupled from the per-fc map); alternative is WYSIWYG (demo mirrors the per-fc map value for the chosen demo fc, no separate field). (b) **Extend per-fc treatment to DLI/ILD/ITD `ref_level_db`?** — those still use one flat 60 dB across frequencies; the AM/FM plumbing (`_build_target_level_map` / `set_target_levels` / per-fc dialog editor) is the ready template, and a base-class lift is warranted if extending to >2 paradigms. Whether a per-fc reference is even wanted for level-difference / lateralisation paradigms is a methodology call, not just an implementation one. |

---

## Notes

- **C1, M12, M1** are likely manifestations of the same root problem (HL conversion not fully integrated into adaptive logic). Fixing C1 properly should resolve or clarify both. _M1 is now resolved (2026-07-17 session 02) at the DISPLAY layer only — the GUI reads `operator_units` and converts in one gated place. That does not touch C1/M12, which are about the adaptive logic's own units. If anything M1's `hl_reportable`/`hl_calibrated` gate makes C1 easier to audit, since HL now has exactly one entry point._
- **H1 (fit runaway) and M8 (manual config-rerun)** are related — the automatic first-trial mulligan (2026-06-18) is the implemented mitigation; M8's operator-facing manual redo remains deferred and is PROLACTIN's current #1 open priority pending team discussion. _As of 2026-07-18 the fit-validation side of H1 is complete (theta range + signed slope + `K_MIN`); the outstanding work is entirely the rerun-policy decision (T10)._
- **H10 (IFMC/TMC NaN thresholds) and M17 (historical data)** — H10 is the fixed bug, M17 is its fallout in data already collected. H10 also explains why M3/M4 could not be verified on IFMC until it was fixed: the panel was empty because the data was NaN, not because the plot was wrong.
- **H10 is a cautionary case for guards written against one paradigm family.** `k > 0` was correct for the eight detection paradigms and silently wrong for the two masking ones. The fix (`psychometric_slope_sign`) makes the assumption explicit and greppable rather than implicit in a comparison operator. Worth checking other guards for the same shape — a condition that is true for PTA and assumed universal.
- **H7 and M11** — H7 (weighting convention) is now resolved; the residual noise-vs-tone bias itself (M11) is not.
- **C3** — routing gain confirmed and corrected in calibration config; residual verification is a hardware task, not a code task.
- **L18, L19** are new pending items from the 2026-07-01 reaction-time session; both low-severity/deferred by design.
- **H5, H8, M13** — session 02 (IFMC/TMC outer-var fix) and session 03 (TMC gap correction + H5 instrumentation) are related: the probe_level cross-pairing bug fixed in session 02 is a suspected contributing cause for both H5 and H8; confirmation of both awaits lab/live testing. M13 is independently resolved (data-value fix, not related to the cross-pairing bug).
- **T4 = M9** (both now resolved 2026-07-17), **T5 = H4** — historical cross-reference retained above even though T4/M9 are closed.
- **M15, M16, L21-L27** are new 2026-07-09 items, all from the ER-2 (insert earphone) calibration session. Several (L23, L24, L27) require the calibration rig / lab hardware and cannot be progressed remotely.
- **H9** (Windows thermal/crash campaign) ties together several previously-scattered threads: the resource-logging instrumentation (2026-07-03 session 02), the `show_operator_display` candidate fix, and the `core.wait()`->`time.sleep()` thermal-hygiene fix. All still pending a long lab run.
- Since 2026-06-19: thirteen sessions of code work (06-19_02, 06-26 recovery, 06-30 x3, 07-01, 07-01_02, 07-01_03, 07-03, 07-03_02, 07-09, 07-17, 07-17_02, 07-18), all with clean signature verification at every subsequent session start. The 06-26 session's root cause (stale-base edit) is the reason paradigm-file signatures, not just `adaptive_paradigm.py`, are now checked every session.
- **Process lesson, 2026-07-18: verify what is DELIVERED, not what was edited.** A stale `varspec.py` was shipped mid-session (amended in the working copy, never re-copied to the output directory) and crashed PTA on trial 1 with `axis_label() got an unexpected keyword argument 'units_override'`. The harnesses passed throughout — because they imported the working copy, which the user never receives. Adopted: diff every delivered file against its tested source before presenting, and run harnesses against the delivered artifacts. This is the same class of failure as 06-26 (stale base), one step further down the pipeline. _Tracked as L36 in `session_changelog_2026-07-18.md`; recorded here as a process note rather than a numbered issue, alongside the 06-26 lesson._
- **Stale-base check earned its keep again, 2026-07-18.** The project copy of `paradigm_tmc.py` was provably stale (zero hits for `threshold_plot_x_log`, which Eric had applied locally). Shipping a whole file would have silently reverted it; class-attr changes were delivered as paste fragments instead, merged against Eric's own pasted headers.
- **Loopback recording is the ear-free validation lane (2026-07-18 session 02).** With the B&K artificial ear unavailable, a loopback capture (system output recorded back into an input) still gives waveform + envelope + *relative* levels — everything except absolute SPL. Loopback-progressable now: **L37** (AM/FM per-fc levels track the table in relative dB; AM depth / FM deviation correct on the recording — feeds M14), **H5** (record an IFMC run; identify which catch trials are truly silent — the console diagnostic (H5) gives the correlate), **M15** (dB-SPL sweep -> confirm recorded level tracks requested 1:1 and no full-scale clipping at a low-ceiling profile's top), **C3** (relative +6 dB routing re-confirm), **L11/L13** (interface-vs-headphone FR split; ITD per-ear independence). Blocked until the ear returns: absolute-SPL items — RETSPL/**M10**, noise-vs-tone bias **M11**, ER-2 linearity **L24**, absolute **C3**, 4157 mic **L22**.


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

---

## Update 2026-07-17 (session 02) — Operator GUI: units (M1), psychometric curve (M2), redraw audit

_Backfilled 2026-07-18: this session's outcomes were not recorded in the
2026-07-17 revision of this doc, which is why L29-L31 were referenced by the
changelogs but absent here._

- **M1 — RESOLVED.** `_level_series()` (NEW) converts a level array to display
  units in one place; panels 38/40 follow `operator_units`. Gated by
  `_operator_in_hl()`, which requires `hl_calibrated` AND the paradigm's
  `hl_reportable` AND a resolvable `fc` — so LDL/SRT and uncalibrated runs stay
  in dB SPL and say so, rather than silently mislabelling.
- **M2 — RESOLVED.** Psychometric fit line now drawn. Root cause was
  state/ordering, not the fit itself.
- **Redraw audit:** `update_display()` drops panel 37 and issues a single
  `draw_idle()`; five per-trial `canvas.draw()` calls removed; `update_stimulus()`
  (NEW) separates the stimulus readout from the plot refresh. Relevant to H9.
- **New issues raised:** L29 (placeholder labels masquerading as rendered
  output), L30 (panel 40 x-label hardcoded), L31 (early-return-before-`clear()`).
  L29/L30 were rolled into the M3/M4 PRD as D9/D8 and are now resolved; L31
  stands as deliberate/documented.
- **M3/M4 deliberately NOT started** — PRD written and approved instead
  (`prd_2026-07-17_m3_m4_threshold_plot.md`, decisions D1-D15).

---

## Update 2026-07-18 — M3/M4 threshold plot + IFMC/TMC NaN-threshold root cause (H10)

Implemented M3/M4 per the approved PRD (all four commits), which surfaced H10 —
a pre-existing bug that had been discarding every IFMC and TMC threshold.

### M3/M4 — panel 39 and axis metadata

- **`varspec.py`:** `VarSpec` gains optional `label`/`units`, plus a module-level
  `axis_label(vs, units_override=None)`. Purely additive — both fields default to
  `""` and every consumer tolerates their absence (AST-verified: zero positional
  `VarSpec()` calls in the codebase, so inserting fields after `data` is safe).
  **`units` labels the unit the values are STORED in; it is never a conversion
  instruction** (D11). `gap_duration` declares `units="s"` because that is what
  it holds.
- **All 11 `test_*.py`:** metadata only, +2 lines each. Machine-verified per file
  that stripping exactly the inserted metadata restores the original
  byte-for-byte — proving zero changes to `name=`/`data=`.
- **`operator_gui.py`:** panel 39 x = real `outer_1` values; `outer_2..N` become
  series but only where they actually vary (five paradigms declare constants as
  outer vars; crossing those in would tag every line with noise — they are
  annotated instead). Real `ax.legend()` replaces the wheat text box. Log x-axis
  inferred at >= 1.0 decades, overridable via `threshold_plot_x_log`. Ticks
  forced to the actual values (a log PTA axis reads 250/500/.../8000, not
  decades). String `outer_1` (ITD `signal_type`) takes a categorical path.
  Panels 38/40 name their axes from the VarSpec.
- **`adaptive_paradigm.py`:** `threshold_plot_x_log` class attr; `params`
  docstring now documents that `outer_1` is the primary/x-axis variable by
  convention (position already encodes primacy — not schema-enforced).
- **TMC pinned linear** (`threshold_plot_x_log = False`): its `gap_duration`
  spans 0.90 decades, just under the 1.0 threshold. Widening the gap set to
  50 ms would hit exactly 1.0 and silently flip the axis — verified live in a
  harness, then pinned rather than left to inference.

### H10 — the guard that rejected every IFMC/TMC fit

Implementing M3/M4 exposed that IFMC's panel 39 was empty and its psychometric
curve missing. Both were the same NaN: `threshold_dB` was empty on every row of
every completed config. The fit was fine — the guard was throwing it away.

- The 2026-06-18 plausibility guard required `k > 0`. IFMC/TMC adapt the MASKER
  level, so raising it masks the probe: p(yes) falls with level and `k` is
  **necessarily negative**. Both paradigms document this as "REVERSED LOGIC" in
  their own `adapt_difficulty()` docstrings.
- Fix: `psychometric_slope_sign` class attr (base `+1`; IFMC/TMC override `-1`);
  guard is now `k * sign >= PSYCHOMETRIC_K_MIN`. The sign is a property of the
  paradigm and is never inferred from the data being validated — the guard's job
  is to catch a slope running the wrong way.
- `PSYCHOMETRIC_K_MIN = 0.01` closes H1's residual near-zero-`k` gap in the same
  guard. **Assistant-chosen value — see L32/T14.**
- Verified against live IFMC data: configs fit theta = 93.04 / 75.82 / 76.96 dB
  SPL, all previously discarded. Config 3 reproduced the console's rejected
  `theta=77.0, k=-1.14e+01` exactly. Ten regression cases still reject: runaway
  theta, flat `k`, **inverted PTA fit**, theta out of range, IFMC positive `k`,
  `k` just below the floor.
- **Data already collected is affected — see M17.**

### Verification

Three headless harnesses (tk/matplotlib/psychopy stubbed, driving the real
methods): panel 38/40 labels 10/10; panel 39 across all 11 paradigm shapes; the
guard against real IFMC data + 10 regression cases. Garbage-char sweep clean
across all 14 shipped files. All 11 `test_*.py` additive-diff proven. Live-confirmed
by Eric: PTA panel 39 renders as a real audiogram; IFMC thresholds populate and
the curve draws (descending, negative `k`).

### Deviations from the PRD (all ratified)

- `mod_ind` gets `units="%"` — the PRD said dimensionless; `event_gen.py` divides
  by 100 and both paradigm docstrings say percent.
- `trial_amp` keeps `units="dB SPL"`; the GUI supplies `dB HL` at draw time via
  `units_override`. A static `"dB HL"` would let the label lie about an
  unconverted number (D11).
- `pan` -> `label="Pan"`, not `"Ear"` (D13 defers the value mapping; `Ear=-1` is
  worse than `Pan=-1`). Renders as `Pan=-1`, not `-1.0` — the `%g` formatter that
  makes `fc=8000` and `gap=0.005` both read correctly drops trailing zeros.
- Panel 39's y-label follows the INNER var's unit (PRD said leave y alone).
  `Threshold (dB)` was wrong for GAP (s) / AM/FM (%) / ITD (ms) — the same defect
  as L30 one panel up. Now `Threshold (s)` / `Threshold (%)` / `Threshold (dB SPL)`.
- Sign-aware guard + `K_MIN` — outside M3/M4 entirely; shipped because M3/M4
  surfaced it.

### ID mapping vs. `session_changelog_2026-07-18.md`

The changelog assigned LOW-tier IDs to everything new. Two were re-tiered here,
since in this doc the letter prefix IS the severity tier:

| changelog | this doc | why |
|---|---|---|
| L32 | **L32** (+ T14) | unchanged; team question cross-referenced like T5=H4 |
| L33 | **M17** | data integrity, not "quality of life / polish" |
| L34 | **L34** | unchanged |
| L35 | **L35** | unchanged |
| L36 | **Notes bullet** | a process lesson, not a code issue — sits with the 06-26 lesson |

**L33 and L36 are RETIRED in this doc — do not reuse.** They exist in
`session_changelog_2026-07-18.md` and are remapped above; assigning them to new
issues would silently collide with that changelog. Next free LOW id is **L38**
(L37 used by the 2026-07-18 session 02 update below).

---

## Update 2026-07-18 (session 02) — AM/FM per-fc target level + scrollable setup dialog

Implemented GitLab request "FM/AM: add individual threshold config for target
level". Scope: AM + FM only. Files: `paradigm_am.py`, `paradigm_fm.py`,
`paradigm_setup_dialog.py` (base `ParadigmSetupDialog` only), `test_am.py`,
`test_fm.py`. `adaptive_paradigm.py` untouched (only reuses existing
`_derive_dependent_params` hook + `set_current_config` ordering). No new
severity-table bug closed — this is a feature add, not a fix.

### What changed

- **`tone_level_db` demoted from outer var to a per-fc target-level array**,
  co-indexed with `fc` and zipped **by index** (NOT crossed) — deliberately
  avoids the documented `probe_level` cross-pairing bug (see IFMC probe-level
  history). Config count invariant: still `fc x fm`, no product inflation.
- `_build_target_level_map(params)` (zip-by-index, fail-fast on length mismatch,
  all-60 when absent), `set_target_levels(freq_to_db)` runtime override hook
  (mirrors IFMC `set_probe_levels`; future cross-paradigm "load from another
  paradigm" path), `_derive_dependent_params()` sets `tone_level_db` from the map
  after outer vars are set with a 60 dB fallback for unconfigured fc.
- **Setup dialog**: new per-fc dB editor (`_build_target_level_editor` /
  `_rebuild_target_rows`), rendered only when a `target_level` VarSpec is present,
  live-rebuilt on fc-set change with edits preserved by frequency; writes the
  fc-ordered array back to `params["target_level"].data`.
- **Scrollable layout**: `_build_ui` restructured to pin header + Start/Cancel and
  put variable sections in a height-capped, vertically-resizable scroll canvas
  (`_fit_to_screen`), fixing the off-screen Start button. A "Scroll down for more
  options" hint (`_update_scroll_hint`) shows only while content overflows. This
  touches the **base dialog**, so it affects every base-dialog paradigm — see L37.
- **Demo carrier-level field restored** (AM/FM only), gated on `target_level`,
  writing a `_demo_tone_level` override key independent of the per-fc map.

### New / affected issues

- **L37** — live validation of the above (Mac then Windows) + scroll-layout
  regression pass across the other base-dialog setup dialogs. Ear-free.
- **T15** — design ratification: (a) demo field independent-override vs WYSIWYG;
  (b) whether to extend per-fc treatment to DLI/ILD/ITD `ref_level_db` (still flat
  60). AM/FM plumbing is the template; base-class lift if it goes past 2 paradigms.
- **M14** annotated — the new per-carrier level behaviour is now inside the Nick
  spec-consistency review.

### No-ear next step (loopback)

The per-fc levels are verifiable **without the artificial ear**: a loopback
recording of two+ carrier frequencies with distinct target-level entries should
show recorded-RMS deltas matching the table's dB deltas (relative, not absolute
SPL), and confirm AM depth / FM deviation on the captured waveform. Feeds M14.
See the Notes "loopback lane" bullet for the full ear-free / ear-blocked split.

### Verification done this session

ast.parse clean on all 5 delivered files; garbage sweep clean (0 mojibake; the
dialog's 13 non-ASCII are pre-existing em-dash/arrow, new code uses `\u` escapes).
Map builder, derive/override, and the dialog editor exercised with real methods
(tk stubbed): zip-by-index, default-60, length-mismatch raise, load-path,
missing-freq fail-fast, demo override precedence, live add/remove preservation,
accept-array fc order, empty-field rejection, scroll height-cap + hint toggle,
demo field present for AM/FM and absent for PTA. Config count invariant confirmed.
