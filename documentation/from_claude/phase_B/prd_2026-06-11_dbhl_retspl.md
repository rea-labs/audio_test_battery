# PRD — dB HL conversion: RETSPL correction + HL-reportable hardening

Date: 2026-06-11
Constraints: (a) existing hardware only — no new headphones; (b) research use, "good enough" + disclosed assumptions.

## Goal

Replace the invalid TDH-39 (supra-aural) RETSPL with a circumaural reference matched to DT250/K271 in the IEC 60318-1 (B&K 4153) ear. Ship a disclosed "good-enough" conversion now (Tier 0); define the existing-hardware path to an accurate house conversion (Tier 1). Per team decision, dB HL is implemented for PTA ONLY; every other threshold suppresses HL. Make this explicit per-paradigm (also fixes a wrong SRT HL value and drops LDL's out-of-scope HL).

## Strategy (why)

- `HL = SPL - RETSPL` is valid only when the SAME transducer is on both sides. SPL side = DT250 (your cal). Reference side must be circumaural. TDH-39 is supra-aural -> wrong; error ~ +14.5 dB @ 125 Hz, ~+7.5 @ 250/3000.
- No transducer-neutral, coupler-referenced curve exists. Free-field threshold (ISO 389-7) and equal-loudness/Fletcher-Munson are free-field/binaural — wrong reference frame (HRTF baked in), ISO 389-7 itself says do not compare to coupler data. Closest valid coupler+circumaural reference = ISO 389-8 HDA200.
- KEY LEVER: a Sennheiser HDA200 is on hand (uncalibrated). That IS the reference transducer. It enables a within-subject DT250-vs-HDA200 behavioral measurement that yields a DT250-specific RETSPL directly (Tier 1) — removing the ΔRECD assumption for real, with no new hardware. ΔRECD is a real-ear quantity, so coupler-only measurement cannot recover it; behavioral (real-ear) measurement can.

## Tiers

- Tier 0 — ship now, no new measurement. Adopt ISO 389-8 HDA200 RETSPL. Residual = ΔRECD(DT250,HDA200), unquantified but bounded small (circumaural↔circumaural). Disclose.
- Tier 1 — accuracy target, existing hardware + listeners. Calibrate HDA200 profile; run normal-hearing panel on DT250 + HDA200 same session; derive house RETSPL_DT250; swap table. Within-subject differential cancels most between-subject variance, so small N (~5-10 ears) is usable (unlike absolute biological cal). Same code path; better numbers.
- Tier 2 — deferred. Full ISO 389-9 absolute biological cal, or DD450 purchase. OUT.

## Tier 0 implementation (per file)

### calibration_config.json  (data only — no code change; loader already builds HLConverter from `table`)
Replace `retspl.table` in all four profiles (DT250 A/B/X, K271 — all circumaural) with ISO 389-8 / ANSI S3.6-2018 HDA200:

    125: 30.5   250: 18.0   500: 11.0   750: 6.0   1000: 5.5   1500: 5.5
    2000: 4.5   3000: 2.5   4000: 9.5   6000: 17.0  8000: 17.5

Update each `retspl.source`:
"ISO 389-8:2004 / ANSI S3.6-2018 HDA200 RETSPL (IEC 60318-1). Applied to circumaural DT250/K271 as approximation; residual ΔRECD(DT250 vs HDA200) unquantified. Research display only — not clinical."
Update `_retspl_note` to match.

### adaptive_paradigm.py
`_threshold_to_hl` (~L1508): change the gate from implicit `level_units == "dB SPL"` to explicit opt-in.
- New rule: write HL only if `_get_paradigm_metadata().get("hl_reportable") is True` AND `hl_calibrated` AND `fc` set.
- Reason: HL is meaningful only for an absolute single-ear dB SPL level at one pure-tone fc, and per team scope only PTA reports it. Inferring eligibility from `level_units` is fragile and currently over-fires for LDL (out of scope) and SRT (speech — invalid).

### paradigm_pta.py
Add `"hl_reportable": True` to `_get_paradigm_metadata()` (trial_amp = dB SPL level at fc). The ONLY paradigm that reports HL (team decision). Preserves current behavior.

### paradigm_ldl.py
Add `"hl_reportable": False`. BEHAVIOR CHANGE: LDL currently emits `threshold_dB_HL` (via the old `level_units` gate). Per team decision (HL = PTA only), drop it. LDL HL is technically valid (level at fc) but out of agreed scope. Explicit `False` + comment so the removal is documented, not an emergent side effect.

### paradigm_srt.py
Add `"hl_reportable": False`. BEHAVIOR CHANGE: SRT currently emits `threshold_dB_HL` computed with the pure-tone RETSPL(fc). Doubly wrong to drop — (i) out of agreed scope (HL = PTA only); (ii) invalid anyway for a broadband speech threshold (needs a speech RETSPL per IEC 60645, not pure-tone RETSPL(fc)).

### IFMC / TMC / AM / FM / GAP / DLI / ILD / ITD
No change. No flag -> no HL column. Suppression now intentional (inner var is a non-level or difference quantity).

### operator_gui.py
No change this pass. (The SPL-mode y-label tweak "Threshold (dB)" -> "Threshold (dB SPL)" is a plot label -> deferred to the plotting pass, decision 6.)

## Tier 1 protocol (measurement; only code = the later config table swap)

1. Build HDA200 calibration profile (inverse IR + SPL ref) — same REW/TotalMix workflow as DT250.
2. Validate chain: normal ears on HDA200, behavioral PTA thresholds; (threshold - ISO 389-8 RETSPL) should average ~0 dB HL.
3. Same ears, same session, on DT250. Per-frequency house RETSPL_DT250 = DT250 coupler-SPL-at-threshold (or = HDA200 table + mean[DT250-HDA200] difference).
4. N ~ 5-10 otologically-normal ears (within-subject difference -> low variance). Use the PTA paradigm itself (dogfood).
5. Swap config table HDA200 -> house RETSPL_DT250. Update `source` to "house biological RETSPL, DT250, N=__, <date>".

## Disclosure / justification (constraint b)

- Lives in: `retspl.source` (already surfaced to CSV header via `retspl_source`) + `_retspl_note` + methods text.
- Assumption stated: RETSPL_DT250 ≈ RETSPL_HDA200 (ΔRECD ≈ 0).
- Impact bound: a purpose-built HDA200 successor (DD450) needed only small RETSPL corrections vs HDA200 — within ~5 dB, concentrated at 8 kHz. DT250 is not an HDA200 replica, so expect somewhat more, mostly at band edges (125 Hz, >=6 kHz). Mid-band (0.5-4 kHz) likely within a few dB. Tier 1 removes the assumption entirely.

## Key signatures (for session-cleanup changelog)

- calibration_config.json: `"125": 30.5` ; `"source": "ISO 389-8`
- adaptive_paradigm.py: `get("hl_reportable")` in `_threshold_to_hl`
- paradigm_pta.py: `"hl_reportable": True`
- paradigm_ldl.py / paradigm_srt.py: `"hl_reportable": False`

## Out of scope

- All plotting changes -> separate pass (audiogram inverted-y / log-freq-x; SPL-mode y-label "dB" -> "dB SPL").
- Shared RETSPL CSV refactor (keep per-profile inline for now).
- Speech-HL (speech RETSPL) path for SRT.
- HL for IFMC/TMC and difference paradigms.
- Any change to staircase / fit / `spl_to_amplitude` / calibration math.
- Extra table frequencies (1250/1600/3150).

## Suggested implementation order

| # | Step | File(s) |
|---|------|---------|
| 1 | RETSPL table + source/note | calibration_config.json |
| 2 | Gate -> hl_reportable | adaptive_paradigm.py |
| 3 | Flags: PTA true; LDL, SRT false | paradigm_pta/ldl/srt.py |
| 4 | Verify | run PTA in HL mode (column + header source present); run LDL, SRT, IFMC (NO HL column) |

## Decisions (resolved 2026-06-11)

1. Scope = Tier 0 only this pass. Tier 1 (HDA200 house cal) and Tier 2 deferred to later passes.
2. Remove the `threshold_dB_HL` column from LDL and SRT. PTA is the only HL paradigm.
3. K271: apply the HDA200 table for now (K271 not in planned use); revisit in Tier 1.
4. Per-profile inline RETSPL table. Shared-CSV refactor deferred to a future larger refactor.
5. Disclosure caveat: fold into `retspl.source` (already surfaced to the CSV header). No dedicated field; no header-writer change.
6. Plotting (audiogram + SPL-mode y-label) deferred to a separate pass.
