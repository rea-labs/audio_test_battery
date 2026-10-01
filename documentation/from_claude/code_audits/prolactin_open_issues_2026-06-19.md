# PROLACTIN — Open Issues
_Generated 2026-06-05. Last revised 2026-06-19. Ordered by severity. Difficulty: 1 (trivial) to 10 (major effort)._

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

## Update 2026-06-18 — Mulligan + psychometric fit-runaway fix (threshold underflow)

Colleague commit `7ed6058` (mulligan), reviewed this session; the post-fit
plausibility guard was added on top. Addresses the -167,061 dB underflow (H1 / C1
symptom). Confirmed present and pushed in the project; `is_mulligan` verified in
PTA/FM/LDL logs.

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
  Warning is console-only (non-blocking, Mac/Windows-safe); could surface on
  `operator_display` later.
- **Deliberately NOT done**: `curve_fit` left unbounded (fix is behavioral/upstream,
  not numerical); no `fit_status` column (log bloat); no `K_MIN` floor (residual:
  near-zero positive `k` with in-range `theta` still passes).

The manual operator/participant redo work (trial-redo and config-rerun) is
SEPARATE and still deferred — see M8.

Outstanding from this session: the agreed one-line LDL `is_mulligan` docstring
note (see L18) is not yet added; `paradigm_ldl.py` was not edited.

---

## CRITICAL — blocks data validity / causes wrong results

| # | Issue | Difficulty |
|---|-------|-----------|
| C1 | **dB HL unit contamination in PTA adaptive logic** — safety limits, threshold averaging, step logic may be operating on HL instead of SPL. Original symptom: threshold underflow to -167,061 dB (P0007, config 5, 2 kHz, 04.06.26). **Root cause re-attributed**: the underflow was a psychometric fit runaway (H1), not HL contamination — the HL conversion is downstream/innocent. Acute symptom now caught by the 2026-06-18 plausibility gate (-> NaN + warning). Narrower remaining concern: confirm step/limit/averaging logic runs on SPL, not HL (overlaps M12). Downgrade once that audit is clean. | 5 |
| ~~C2~~ | ~~**B6 hardware SPL re-measurement**~~ — ~~all SPL values in `calibration_config.json` are null.~~ **DONE** — SPL values measured and populated (DT250-A: 92.6 L / 91.4 R dB SPL). _RETSPL placeholder resolved 2026-06-19: TDH-39 -> ISO 389-8 HDA200 (Tier 0 circumaural approximation). See M10 and the 2026-06-19 update._ | ~~3~~ |
| C3 | **TotalMix 1/2->7/8 routing gain mismatch** — IRs and SPL calibration were measured via outputs 7/8 (internally consistent). Toolbox playback goes out 1/2->7/8 via TotalMix routing; suspected -6 dB gain difference (possible stereo->mono summing artifact) means paradigm output levels may be off by 6 dB. Verify by playing a known toolbox signal through 1/2->7/8 and measuring SPL vs. calibration-predicted value. Fix: set routing to unity gain in TotalMix (preferred), or bake a correction factor into `calibration_config.json`. | 3 |

---

## HIGH — affects measurement quality or data integrity

| # | Issue | Difficulty |
|---|-------|-----------|
| H1 | **Psychometric fit runaway on unbracketed staircases** — `scipy.curve_fit` unbounded; all-0/all-1 guard missed the varies-but-unbracketed case. **Largely addressed 2026-06-18**: first-trial mulligan + `_has_stepped_down` gate prevent unbracketed tracks; post-fit plausibility gate maps residual runaway to NaN + operator re-run warning; `curve_fit` left unbounded by design. Residual: an in-range `theta` with near-zero but positive `k` would still pass (`k>0` only catches inverted slopes; no `K_MIN` floor) — but not observed in isolation, since the observed runaway had out-of-range `theta` already caught by the range test. Revisit only if a flat-in-range fit appears. See the 2026-06-18 update. | 6 |
| H2 | **CSV output audit** — `amp_L`/`amp_R` columns possibly unnecessary, `pan` missing, other columns TBD. Need actual output file to audit against spec. | 3 |
| H3 | **dB HL column missing from data output** — should always be present, not just for the final threshold. | 2 |
| H4 | **IFMC/TMC probe level (Path B)** — `db_above_threshold` band-aided at 24 instead of correct 10; requires `trial_dur=0.016` as outer var in single PTA paradigm. Team discussion needed. | 6 |
| H5 | **IFMC: fully silent catch trials** — some catch trials play no sound at all while others work as intended (no click). Observed only in config 4 (freq_ratio 1.3) so far. Root cause unknown; needs investigation. | 4 |
| H6 | **Insufficient reversals handling** — if a run ends with too few reversals for a reliable threshold estimate, should prompt operator to redo. Options: always ask; ask only if below threshold; and/or increase `num_reversals` minimum to 2. Design decision needed. | 4 |
| H7 | **REW SPL weighting: dB(C) vs dB(Z)** — REW meter was set to dB(C) rather than dB(Z) during calibration measurements; dB(C) weighting causes a discrepancy of several dB for white noise (less so for tones). All unweighted (dB(Z)) measurements should be used for consistency. Needs confirmation with Pat re: team convention, and re-measurement if calibration was done with dB(C). | 4 |

---

## MEDIUM — affects usability or correctness of secondary features

| # | Issue | Difficulty |
|---|-------|-----------|
| M1 | **PTA GUI unit inconsistency** — previous-threshold display shows HL, but `trial_amp` subplot and psychometric subplot still show SPL. Needs rationalization. | 4 |
| M2 | **Psychometric function line not drawn** — fit line missing from operator GUI plot. | 3 |
| M3 | **Previous-thresholds subplot cleanup (PTA)** — multiple outer vars need separate lines/colors; real x-axis values (not ordinal); optional connect-points. | 5 |
| M4 | **Previous-thresholds subplot for IFMC** — how to present results given multiple masker frequencies? Number of configs also needs checking. | 5 |
| M5 | **Active calibration profile in paradigm setup dialog** — expose as read-only label (mirrors audio device display); eventually a picker menu. | 3 |
| M6 | **TotalMix config in paradigm setup dialog** — show active snapshot as read-only label; can't auto-verify without OSC. | 4 |
| M7 | **`active_profile` moved to `DEFAULTS.py`** — currently buried in `calibration_config.json`. | 2 |
| M8 | **Manual redo features (two distinct, both deferred pending team)** — *(1) Trial-redo (misclick):* build on the existing repeat path with per-trial state-snapshot rollback. Decisions to settle: depth (default 1 = previous trial only), identical-stimulus replay (cache/replay the prepared spec), catch-trial handling, void-with-flag vs delete-row, redo cap (default 2/trial), participant vs operator trigger + gameability. Default plan unless changed: depth 1, identical replay, void-with-flag, both triggers, cap 2/trial. *(2) Config-rerun:* re-run a whole config; treat as separate/sub-issue. Concrete hook now exists — an implausible-reject (NaN threshold) config is the natural 'offer operator a re-run' trigger. Both distinct from the automatic first-trial mulligan (implemented 2026-06-18). | 5 |
| M9 | **LDL "too loud" as reversal** — team decision needed: should a loud response trigger step-size reduction (e.g. +3 dB -> +1 dB)? | 2 |
| M10 | **Verify dB SPL -> dB HL conversion** numerically against ISO 389 RETSPL values. _Partially addressed 2026-06-19: table now ISO 389-8 HDA200 (valid circumaural ref) and the HL output is gated by an explicit `hl_reportable` flag. Remaining: numeric spot-check of HLConverter output against the table, ideally on calibrated hardware._ | 2 |
| M11 | **Noise vs. tone SPL calibration closure** — ~1.3 dB bias between noise and sine; ref "Noise vs tone spl note 2026-06-04". Related to H7. | 4 |
| M12 | **Safety limits audit** — lower/upper limit checks suspected broken during HL conversion; needs unit audit across all paradigms. | 4 |
| M13 | **TMC gap sizes: verify against MultiThreshold MATLAB** — "wasn't it four different gap sizes in MATLAB?" Check GitHub (multithreshold 1.46) for correct TMC config, then cross-reference with UZH version. | 3 |
| M14 | **AM/FM implementation double-check** — follow up on discussion with Nick; verify both implementations are correct and consistent with agreed spec. | 3 |

---

## LOW — quality of life, polish, future features

| # | Issue | Difficulty |
|---|-------|-----------|
| L1 | **Quasi-random start-value jitter** — investigate low-discrepancy sequences (Halton/Sobol/stratified) to reduce threshold estimate variance. Needs justification vs. MultiThreshold spec intent. | 5 |
| L2 | **Sensation level paradigm** — PTA with in-ear headphones, SPL display mode, different frequency set. Essentially a PTA config variant. | 3 |
| L3 | **ExperimentController class** — paradigm registry as source of truth; deprecate test scripts as primary entry points. | 9 |
| L4 | **MockParticipant / headless testing infrastructure** | 6 |
| L5 | **Lift midpoint-reset machinery into base class** — currently duplicated across ~10 paradigms; candidate for ExperimentController refactor. | 5 |
| L6 | **`utils/__init__.py` eager-import cleanup** — circular import landmine; flagged during `audio_devices` fix. | 3 |
| L7 | **`paradigm_ifmc.py` UTF-8 arrows** — decision: leave as-is vs. ASCII-normalisation pass (TMC already clean). | 1 |
| L8 | **Load field defaults to `P` for digit-only manual entry** — decision pending. | 1 |
| L9 | **Default letter field to last-used letter** | 2 |
| L10 | **PEQ-based calibration** — 9-band biquad chain alternative to FIR convolution. | 7 |
| L11 | **Separate RME UCX II FR from headphone IR** — loopback measurement, divide out. | 4 |
| L12 | **Delete deprecated SRT files** — once SRT verified on calibrated hardware. | 1 |
| L13 | **ITD noise: independent per-ear signals** — currently same noise signal both ears; invalid at zero ITD. | 3 |
| L14 | **Operator GUI FP warning text not paradigm-aware** — generic detection text shown even for lateralisation paradigms. | 3 |
| L15 | **Mojibake cleanup in `trial_player.py`** lines 451-453. | 1 |
| L16 | **LUFS/loudness normalization for complex signals** | 6 |
| L17 | **TotalMix OSC programmatic snapshot switching** — `/3/snapshots/N/1 f 1.0` via `python-osc`. | 5 |
| L18 | **LDL `is_mulligan` docstring note** — add one line to `paradigm_ldl.py` clarifying that `is_mulligan=True` in LDL means 'first presented level already uncomfortable', NOT 'a miss was forgiven'. LDL intentionally left ungated; phantom `make_easier` step verified inert (logged level captured pre-step). Outstanding from the 2026-06-18 session. | 1 |

---

## Questions for the Team

These are open theoretical/methodological questions that affect protocol design or parameter choices. Not bugs — need team input before any implementation decision.

| # | Question |
|---|----------|
| T1 | **Frequency set: reduce to 1 standard + tinnitus frequency?** — Would reduce session time and is theoretically motivated. Question: what do we do with control participants (no tinnitus frequency)? |
| T2 | **GAP: why only in noise and not at specific frequencies?** — There is potential complexity with clicks due to short gap durations + short fade times at specific frequencies. Is noise-only the right choice? |
| T3 | **ILD: is this test meaningful?** — Concern that ILD results may reflect hearing asymmetry rather than true ILD sensitivity ("I often heard as if the sound came more from the right, but that's just because I have better hearing there"). Is DLI sufficient, making ILD redundant? |
| T4 | **LDL: should "too loud" response count as a reversal for step-size purposes?** — i.e. trigger step reduction from +3 dB to +1 dB, even if it doesn't affect subsequent trial logic. (See also M9.) |
| T5 | **IFMC/TMC probe level: 10 dB SL above probe's own 16 ms threshold** — requires Path B implementation. Currently band-aided at 24 dB above long-tone PTA threshold. Team sign-off needed before reverting to 10. (See also H4.) |
| T6 | **SPL weighting convention: dB(Z) for everything?** — Pat to confirm: should all REW measurements (tones and noise) use unweighted dB(Z)? Current calibration may have used dB(C), causing a bias for noise. (See also H7.) |

---

## Notes

- **C1, M12, M1** are likely manifestations of the same root problem (HL conversion not fully integrated into adaptive logic). Fixing C1 properly should resolve or clarify both.
- **H1 (fit runaway) and M8 (manual redo features)** are related — the automatic first-trial mulligan (2026-06-18) is the implemented mitigation; M8's manual trial-redo and config-rerun remain deferred (the config-rerun now has a natural trigger: an implausible-reject NaN config).
- **H7 and M11** are related — both touch the noise vs. tone SPL discrepancy.
- **T4 = M9**, **T5 = H4** — listed in both places for visibility.
- **C3** is a hardware verification task, not a code task.
