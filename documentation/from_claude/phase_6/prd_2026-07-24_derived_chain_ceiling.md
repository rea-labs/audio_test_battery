# PRD 2026-07-24 — Derived chain ceiling (M15 + M18 + M19)

_Scope: `calibration.py`, `config/DEFAULTS.py`, `calibration_config.json`,
`utils/level_validator.py`, `utils/ir_analyzer.py` (**new file**),
`rew_inverse_filter_instructions.md`. No paradigm file, no GUI, no
adaptive-logic edit. Optional Step 5 touches `adaptive_paradigm.py` — see Open
Questions._

---

## Goal

Stop hand-maintaining `max_spl`. Split the single field into a **team policy
ceiling** (config/DEFAULTS, human decision) and a **chain ceiling** (physics,
derived at load from the anchor + FIR). Closes M15 structurally rather than by
guard; retires M18 and M19.

---

## Root cause / current state (verified in code, 2026-07-24)

- `calibration.py` L524 `max_spl` = `self._profile.get("max_spl", 105.0)`.
  Pure config read, no relation to what the chain can actually produce.
- All four over-ear profiles carry `max_spl: 105` while anchors span
  97.4-101.3 dB. 105 is the team safety policy value, **not** the output of
  the Step 5 formula (~117-120). ER-2's 87 **is** the formula output, computed
  by hand. Two incompatible semantics in one field.
- `spl_to_amplitude()` L444 clamps requested SPL to `max_spl`, but nothing
  checks the resulting post-FIR peak stays < 1.0 (= M15).
- Backstop exists but is late: `prepare_samples()` L374 warns + clips at
  runtime on `peak > 1.0`. Catches the symptom mid-trial, not the config error
  at load.
- `level_validator.py` L305-306 computes the full-scale line via
  `amplitude_to_spl(1.0, ear)` = **pre-FIR** basis. Reports unit X R = 123.5
  where the post-FIR truth is 120.5. Over-reports by exactly the FIR peak gain
  (+3.02 dB at 1 kHz). The `Headroom` line on L325 is already post-FIR-correct,
  so the two printed lines are mutually inconsistent today.
- `varspec`-side paradigm soft caps (`test_ldl.py` `max: 105.0`,
  `test_pta.py`, `test_srt.py`) are hardcoded against the over-ear value and
  never consult the profile (= M16).

### Measured, unit X (Eric, 2026-07-24, `--ear right --freq 1000`)

```
target peak amp R    = 0.07159   (= reference_amplitude)
peak after FIR R     = 0.10131   -> |H(1k)| = +3.02 dB
headroom             = 19.89 dB  (post-FIR, correct as printed)
chain ceiling R      = 100.6 + 19.89 = 120.49 dB SPL
max_spl (3 dB hdrm)  = 117.5
level_validator says = 123.5     (pre-FIR basis; wrong)
```

### IR analysis, unit X (2026-07-24, WAVs `..._2026-06-23_48k.wav`, 4096 taps, 48 kHz)

Method: 8x zero-padded rfft, magnitude peak over 20 Hz - 14 kHz. IRs are float
and used as-is (`_load_ir` applies no amplitude normalisation), so this matches
runtime exactly.

| | left | right |
|---|---|---|
| `\|H(1 kHz)\|` | +3.22 dB | +3.01 dB |
| `max\|H(f)\|` | **+14.40 dB @ 3497 Hz** | **+12.84 dB @ 3519 Hz** |
| `min\|H(f)\|` | -5.23 dB @ 53 Hz | -2.82 dB @ 51 Hz |
| RMS (power) gain | +5.89 dB | +5.12 dB |
| `sum\|h\|` (L1) | +22.77 dB | +21.35 dB |

**Method validated:** computed `|H_R(1k)|` = +3.01 dB against the bench-measured
+3.02 dB from `level_validator`. Independent confirmation the derivation is
correct.

Resulting ceilings (`measured_spl + 20*log10(1/ref_amp) - gain`, quieter of the
two, minus 3 dB headroom):

| norm | L | R | `max_spl` | binds on |
|---|---|---|---|---|
| `\|H(1k)\|` | 120.98 | 120.49 | 117.5 | right |
| **`max\|H(f)\|` (D2)** | 109.80 | 110.67 | **106.8** | **left** |
| `sum\|h\|` (L1) | 101.43 | 102.16 | 98.4 | left |

Quieter ear is now R (100.6) — flipped from L at the 2026-07-23 re-anchor. Note
the **binding ear flips to left** under D2, because L's FIR boosts 1.6 dB harder
at 3.5 kHz. The quieter-ear shortcut in the Step 5 doc formula is therefore
wrong in general — the ceiling must be computed per ear and minimised after
the gain term, not before.
**Conclusion for M18: the arithmetic result is ~117.5, far above the 105 policy
cap, so no config value changes.** M18 closes as "verified, no edit", not as a
recompute-and-write.

---

## Decisions (from grilling, 2026-07-24)

| # | Decision |
|---|---|
| D1 | 105 is a **team safety policy** value, may move to 110. Lives in `DEFAULTS.py`, one place. |
| D2 | Chain ceiling uses **`max\|H(f)\|`** over the inversion band, per ear. Not `\|H(1k)\|` (only valid for 1 kHz tones; PTA spans 250-8k, IFMC/TMC probes arbitrary). Not `sum\|h\|` / L1 (true worst case over all inputs, but 10+ dB more conservative and binds on signals no paradigm generates). `max\|H(f)\|` is the exact worst case for **any sinusoid**, and every PROLACTIN stimulus is a tone, modulated tone, or narrowband. |
| D3 | Band = the **REW inversion range**, 20 Hz - 14 kHz. Outside it the inverse filter is unity by construction, so this is the real peak; the restriction only excludes min-phase numerical artifacts at DC/Nyquist. Stored per-profile as `inversion_range_hz`, default `[20, 14000]` — it is a measurement property, not a toolbox constant. |
| D4 | Headroom = 3 dB, in `DEFAULTS.py`. |
| D5 | Per-profile `max_spl` **removed** from all five profiles. Redundant once derived; keeping it is a confusion source and the only way M15 can recur. |
| D6 | `CalibrationManager.max_spl` becomes `min(policy_ceiling, chain_ceiling_quieter_ear)`. All five existing call sites consume it as a property and are unaffected. |
| D7 | **No block in `CalibrationManager`.** With D5 there is no misconfigurable state left — `min()` is unconditionally safe, and `chain < policy` is a legitimate hardware fact (ER-2), not an error. Blocking there would demand an acknowledgment every ER-2 run. M15 closes structurally. |
| D8 | The genuine block case is a **paradigm soft cap exceeding the calibrated ceiling** (`test_ldl.py` `max: 105.0` on an 87 dB chain) = M16. Belongs at paradigm startup, not calibration load. Scoped as optional Step 5. |
| D9 | `amplitude_to_spl()` semantics **unchanged** (pre-FIR, by definition — it converts a digital amplitude). Docstring gains an explicit note. New method added rather than existing one redefined. |
| D10 | Doc-hygiene rule applies: docstrings, comments, `_description` strings and `rew_inverse_filter_instructions.md` Step 5 updated in the same edits. |

---

## Implementation, per file

### 1. `config/DEFAULTS.py` — additive, 2 keys

```python
# Toolbox-wide SPL safety ceiling (team decision). The effective ceiling on
# any profile is min(this, the profile's derived chain ceiling).
"spl_safety_ceiling_db": 105.0,

# Headroom subtracted from the computed full-scale SPL when deriving a
# profile's chain ceiling.
"calibration_headroom_db": 3.0,
```

### 2. `calibration.py` — one new private method, one rewritten property

New `_chain_ceiling_spl()`:

- rfft each IR to `n_fft >= 8 * len(ir)` (zero-padded, so the magnitude
  response is finely sampled and the true peak is not missed between bins).
- mask to `inversion_range_hz` from the profile, default `[20, 14000]`.
- `gain_db = 20*log10(max(|H(f)|))` per ear.
- `ceiling_ear = measured_spl_ear + 20*log10(1/reference_amplitude) - gain_db`
- return `min(ceiling_L, ceiling_R) - calibration_headroom_db`.
- **Fallbacks:** no FIR loaded -> `gain_db = 0.0` (passthrough, correct);
  not `spl_calibrated` -> return `None`; ear present but its IR missing ->
  that ear contributes at `gain_db = 0`.
- Computed **once** in `__init__` after `load_inverse_filters()`, cached in
  `self._chain_ceiling`. Not per-call — an rfft per `spl_to_amplitude()` would
  be a per-trial cost.

Rewritten `max_spl` property:

```python
policy = DEFAULTS["spl_safety_ceiling_db"]     # lazy import, same guarded
                                               # pattern as load_config()
if self._chain_ceiling is None:
    return float(policy)
return float(min(policy, self._chain_ceiling))
```

`summary()` gains a line printing policy / chain / effective so the operator can
see which one binds.

### 3. `calibration_config.json` — 5 profiles

- Remove `"max_spl"` from all five (D5).
- Add `"inversion_range_hz": [20, 14000]` to all five.
- `beyerdynamic_dt250_x_ucx2._description` rewritten for the 2026-07-23
  re-anchor (= M19; draft text in `session_changelog_2026-07-23_session_02.md`).
- Nothing else touched — no anchor value, no IR path, no RETSPL table.

### 2b. `utils/ir_analyzer.py` — NEW, standalone, off the runtime path

Purpose: check a candidate inverse filter *before* it is committed to a profile,
i.e. immediately after a REW export. Answers "what ceiling does this filter cost
me, and where?"

**Not called by any runtime path.** No paradigm, no `TrialPlayer`, no
`CalibrationManager` code path imports it. Operator-invoked only. Dependency
direction is strictly one-way: `utils/ir_analyzer.py` -> `calibration.py`, never
the reverse. (Importing the shared function is *not* pipeline integration — the
runtime never reaches this module.)

Shares math with Step 2 rather than duplicating it. `calibration.py` gains a
module-level pure function:

```python
def fir_peak_gain_db(ir, fs, lo_hz=20.0, hi_hz=14000.0) -> float
```

Module-level, not a method, so the CLI can import it without constructing a
`CalibrationManager`. `_chain_ceiling_spl()` calls it; so does the analyzer.
One implementation, no drift.

Two modes:

| mode | invocation | source of anchor |
|---|---|---|
| candidate | `--wav LEFT.wav RIGHT.wav --ref-amp A --spl-l X --spl-r Y` | CLI args | 
| profile | `--profile NAME [--config PATH]` | `calibration_config.json` |

Candidate mode is the one that matters — `CalibrationManager` structurally
cannot serve it, because the profile entry does not exist yet.

Reports per ear: taps, `|H(1k)|`, `max|H(f)|` + the frequency it occurs at,
`min|H(f)|`, RMS gain, `sum|h|`; then the resulting chain ceiling per norm and
which ear binds. Optional `--compare OLD_L.wav OLD_R.wav` prints the per-channel
1 kHz gain delta between two filter generations (this is the F8 test, see Side
Finding).

**Rework required from the throwaway script used in this session.** That script
hardcodes `/mnt/user-data/uploads/` paths, `REF_AMP`, and unit X's `measured_spl`
values as module constants — pointing it at another profile yields confident
wrong numbers. All of it moves to argparse. Treat the script as a spec of the
math, not as a starting file.

Follows `rms_analyzer.py` / `level_validator.py` convention: thin CLI over
library code, `argparse`, no GUI dependency, importable without side effects.



L303-306: replace `amplitude_to_spl(1.0, ear)` with the post-FIR figure,
i.e. `requested_level + headroom_dB` per ear (the `Headroom` line at L325 is
already computed correctly, so this makes the two consistent). Label changes to
`Full-scale (post-FIR)`. Print the effective ceiling and which term binds.

### 5. `rew_inverse_filter_instructions.md` — rev 7

Step 5 becomes "verify, don't set": the value is derived at load. Retain the
formula as the explanation of what the code does. Update the "Known gap"
callout — it is now closed. Note the `inversion_range_hz` field.

### 6. *(optional, D8)* `adaptive_paradigm.py` — M16 block

At paradigm startup, if `inner_var.data['max'] > self.calibration.max_spl`:
raise / operator-acknowledge prompt naming both values. ~10 lines. Closes M16.

---

## Key signatures

`config/DEFAULTS.py`
- `"spl_safety_ceiling_db": 105.0,`
- `"calibration_headroom_db": 3.0,`

`calibration.py`
- `def fir_peak_gain_db(`  (module-level, not a method)
- `def _chain_ceiling_spl(self)`
- `self._chain_ceiling`
- `inversion_range_hz`

`utils/ir_analyzer.py` (new file)
- `def main(` + `argparse`
- `--wav` / `--profile` / `--compare`
- zero hits for `/mnt/` and for any hardcoded `measured_spl` literal

`calibration_config.json`
- `"inversion_range_hz": [20, 14000]`
- absence of `"max_spl"` (grep should return zero hits)

`utils/level_validator.py`
- `Full-scale (post-FIR)`

---

## Out of scope

- Any `paradigm_*.py` or `test_*.py` file (except optional Step 5, which is
  `adaptive_paradigm.py` only — still no paradigm subclass).
- `spl_to_amplitude()` math — unchanged.
- `prepare_samples()` runtime clip/warn — unchanged, retained as backstop.
- `amplitude_to_spl()` semantics — unchanged (D9).
- Anchor values, IR paths, RETSPL tables.
- M21 (noise level convention) and the crest-factor axis. `max|H(f)|` bounds
  sinusoids; broadband maskers are a separate problem and stay with the runtime
  backstop for now.
- M22 / M23 (anchor robustness) — blocked on the artificial ear. (Note the
  Side Finding may retire M22 without one.)
- The 105 -> 110 policy change. This PRD only makes it a one-line edit.
- **Any runtime use of `utils/ir_analyzer.py`.** It is operator-invoked only.
  Nothing in `calibration.py`, `adaptive_paradigm.py`, `trial_player.py` or any
  paradigm may import it. Enforced by grep at review: `ir_analyzer` must appear
  in no file outside `utils/`.
- Auto-validation of filters at load. Explicitly rejected — checking a candidate
  filter is a deliberate operator action after a REW export, not a startup cost.

---

## Suggested implementation order

| # | Step | Files | Commit |
|---|---|---|---|
| 1 | DEFAULTS constants | `DEFAULTS.py` | 1 |
| 2 | `fir_peak_gain_db()` + `_chain_ceiling_spl()` + `max_spl` property + `summary()` | `calibration.py` | 2 |
| 2b | Standalone analyzer CLI (candidate + profile modes, `--compare`) | `utils/ir_analyzer.py` *(new)* | 2 |
| 3 | Config: strip `max_spl`, add `inversion_range_hz`, unit X `_description` | `calibration_config.json` | 3 |
| 4 | Full-scale line fix | `level_validator.py` | 4 |
| 5 | Doc rev 7 | `rew_inverse_filter_instructions.md` | 4 |
| 6 | *(optional)* M16 startup block | `adaptive_paradigm.py` | 5 |

Steps 1-2 are independently verifiable headless (instantiate a
`CalibrationManager`, print `max_spl`, compare against the hand-computed
106.8 for unit X). Step 3 must not land before Step 2 or every profile silently
falls back to the 105.0 literal default. Step 2b depends on 2 (imports
`fir_peak_gain_db`) but nothing depends on 2b — it can slip without blocking
anything.

---

## Adversarial review — high-severity risks

1. **Ordering hazard on Step 3.** Removing `"max_spl"` from the config before
   the derived property exists leaves `.get("max_spl", 105.0)` returning the
   hardcoded default — ER-2 would silently jump from 87 to 105 on an 87 dB
   chain. That is a *louder-than-safe* regression on the one profile where it
   matters. **Mitigation:** Steps 2 and 3 in that order, non-negotiable;
   verify ER-2 `max_spl` reads ~87 before and after.

2. **`max|H(f)|` is much larger than `|H(1k)|` — CONFIRMED, and it bites.**
   Measured +14.40 dB (L) / +12.84 dB (R) at ~3.5 kHz, vs +3.2 / +3.0 at 1 kHz.
   Unit X chain ceiling is therefore **106.8 dB**, not the ~117.5 the 1 kHz
   figure implied. Consequences:
   - Today's 105 policy cap survives, but with only **1.8 dB of margin**. It was
     never verified, only assumed safe.
   - **The proposed bump to 110 is not achievable on unit X.** A 3.5 kHz tone at
     110 dB SPL would clip post-FIR. The team decision on 105 -> 110 is
     therefore constrained by hardware, not just policy — it needs this number
     before it is taken.
   - A +14 dB inverse boost concentrated at 3.5 kHz is itself worth a look. It
     is consistent with the profile's "exclude notches from inversion = OFF"
     setting inverting a coupler notch. Possibly related to the recorded unit X
     right-IR defect (L39). Flagged, not in scope here.
   **Mitigation:** run the same analysis on the other four profiles before
   Step 3, as read-only desk work. If any lands below 105 the `min()` will
   silently lower that profile's ceiling on first run, and the team should hear
   about it first.

3. **Silently lowering a ceiling an operator set deliberately.** D6's `min()`
   means a profile can lose headroom with no visible cause. **Mitigation:**
   `summary()` prints policy / chain / effective and names the binding term;
   `level_validator` does the same.

4. **DEFAULTS import in `calibration.py`.** The module is deliberately usable
   standalone (`load_config()` guards its DEFAULTS import in try/except so
   utility scripts work outside the toolbox package). The new property must use
   the identical guarded pattern with a 105.0 literal fallback, or
   `level_validator` and `calibration_check` break when run bare.

5. **Zero-padding factor.** An 8x-padded rfft on a 4096-tap filter is 32k bins
   — negligible cost, once, at load. Under-padding risks missing a narrow peak
   between bins and over-reporting the ceiling. Do not "optimise" this to
   `n_fft = len(ir)`.

6. **Windows/Mac.** Pure numpy, no path or device dependency. No portability
   concern.

---

## Side finding — IR changes silently invalidate the SPL anchor (new issue)

Eric's hypothesis, 2026-07-24: the unit X anchor drift (F8/M22) may be caused by
the inverse filters having been regenerated on **2026-06-23** without the anchor
being re-measured against them. Assessed as **strong and testable**.

Mechanism: `measured_spl` is defined as the SPL produced by `reference_amplitude`
*played through the FIR*. Change the FIR and the anchor is stale by exactly the
change in that filter's gain at the anchor frequency — **per channel**. That
reproduces the one signature that ruled out the coupler as the cause: the drift
was channel-**asymmetric** (+2.1 L / +0.8 R, 1.3 dB apart), which a shared
coupler or a shared interface change cannot produce, but two independently
regenerated IRs trivially can.

Falsifiable prediction. Current filters measure `|H_L(1k)|` = +3.22 dB,
`|H_R(1k)|` = +3.01 dB. If the hypothesis holds, the superseded pre-2026-06-23
filters must measure:

```
|H_old_L(1k)| = 3.22 - 2.1 = ~1.1 dB
|H_old_R(1k)| = 3.01 - 0.8 = ~2.2 dB
```

Test = load the old WAVs, one rfft each, compare. **Pure desk work, no
artificial ear, ~10 minutes.** If it confirms, F8/M22 closes with a known cause
and the pending re-measurement is unnecessary.

Note the current L/R gap at 1 kHz is only 0.21 dB, so the *present* filters are
near-symmetric — consistent with the asymmetry having lived in the old pair.

**Process gap this exposes (recommend logging as a new issue):** regenerating an
inverse filter invalidates that profile's `measured_spl`, exactly as changing the
physical output path does (already documented at L27 for the output case). There
is no guard, no reminder, and no recorded linkage between the IR files and the
anchor date. Candidate fix, pairing with the `interface_serial` proposal in H11:
store `ir_generated` and `anchor_measured` dates per profile and warn at load
when the IR is newer than the anchor. Cheap, and it makes this class of drift
self-reporting.

## Side note — broadband maskers have less margin than tones

Measured RMS (power) gain over the band is +5.89 dB (L) / +5.12 dB (R), against
+3.2 / +3.0 at 1 kHz. So noise sits ~2.7 dB closer to the ceiling than a 1 kHz
tone at equal nominal SPL, before crest factor is even considered. `max|H(f)|`
still bounds it correctly for the guard's purposes, and the runtime backstop in
`prepare_samples()` remains. Recorded for M21; not actioned here.



---

## Resolved since first draft

- **Old unit X IRs exist** (Eric, 2026-07-24). The F8 anchor-drift test in the
  Side Finding is unblocked and is the recommended first action next session.
- **`utils/ir_analyzer.py` is in scope** as Step 2b: standalone, operator-invoked,
  never on the runtime path. Name follows `rms_analyzer.py`.

## Deferred to the implementation session (Eric, 2026-07-24)

- **D7** — block-vs-`min`. PRD currently assumes D7 as written (no block in
  `CalibrationManager`; M15 closes structurally). Revisit before Step 2 lands.
- **Step 6 / M16** — paradigm soft cap vs calibrated ceiling. In or out.

---

## Open questions

1. **`inversion_range_hz` per-profile, or a single DEFAULTS constant?**
   Per-profile is more correct (it describes how that filter was made) and
   matches the H11/L21 "config describes the physical setup" direction, but it
   is a fifth thing to keep in sync per profile. Per-profile is the recommendation.
2. **Bump policy to 110 in the same commit, or separately?** Recommend
   separately: this PRD should be a no-behaviour-change refactor on the over-ear
   profiles, so a regression is unambiguous. Note the measured 106.8 dB unit X
   ceiling means 110 is **not reachable** there regardless — the team needs that
   number before deciding.
3. **Run the `max|H(f)|` analysis on the other four profiles before Step 3?**
   Recommended. If any lands below 105 the `min()` silently lowers that profile
   on first run. Attach the IRs and it is one command.
4. **New issue for the IR-invalidates-anchor process gap?** (`ir_generated` /
   `anchor_measured` dates per profile + load-time warning.) Out of scope here;
   needs an issue number if it is to survive this session.
