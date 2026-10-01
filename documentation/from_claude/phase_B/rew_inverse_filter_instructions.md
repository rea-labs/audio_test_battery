# REW Headphone Inverse Filter Generation — Step-by-Step

*Verified against: REW official help docs, John Mulcahy (REW author) forum posts, and hands-on testing with Sennheiser HDA 300 + B&K 4153 on 2026-04-07. Last updated 2026-07-09 (rev 6).*
*Rev 5 (2026-06-23): added the multi-measurement averaging workflow (Step 1b); changed the inversion range from 100 Hz - 10 kHz to 20 Hz - 14 kHz throughout; replaced the multi-variant section with a single-filter rationale.*
*Rev 6 (2026-07-09): fixed RME UFX II -> UCX II throughout (typo; all work on this project uses the UCX II). Added Step 7 (SPL calibration + verification via `level_validator.py`), including the insert-earphone / low-ceiling case worked through with the Neurospec ER-2.*

---

## Overview

There are **two methods** in REW to generate an inverse correction filter for headphones:

- **Method A (Recommended): Direct Inversion via Trace Arithmetic** — inverts the raw measurement. Produces a continuous correction across all frequencies. Best for our use case.
- **Method B (Alternative): PEQ Auto-EQ → Export Filter IR** — generates parametric EQ filters to match a flat target, then exports the combined filter impulse response. Produces a stepped approximation (limited by number of PEQ bands).

**We use Method A.** It gives us a true continuous inverse that handles all frequencies, including the arbitrary masker frequencies in IFMC and broadband noise stimuli. Method B is documented as a backup.

---

## Prerequisites

- REW V5.20 or later (V5.30+ preferred — has improved trace arithmetic UI)
- RME UCX II configured as input and output in REW Preferences → Soundcard
- B&K mic calibration file loaded in REW Preferences → Cal files (if available)
- RME headphone gain locked in TotalMix (document the exact setting!)

---

## Method A: Direct Inversion (Recommended)

### Step 1 — Take the measurement

1. Open REW. Go to **Preferences → Soundcard** and configure your RME UCX II as both input and output. Set sample rate to **48000 Hz**.
2. If you have a calibration file for the B&K mic, load it in **Preferences → Cal files → Mic/Meter cal**.
3. Place headphone left ear on B&K 4153 coupler. Connect mic output to RME input.
4. In REW, click **Measure**. Settings:
   - Start Freq: **20 Hz**
   - End Freq: **20000 Hz**
   - Level: start conservatively (e.g. **-18 dBFS**), adjust if signal is too quiet/loud
   - Length: **256k** (gives good S/N ratio)
   - Sweeps: **1** (sufficient for headphones on a coupler — no room noise)
5. Click **Start**. Wait for measurement to complete.
6. **Name the measurement** (right-click on measurement tab): e.g., "DT250 Left - B&K 4153"
7. **Repeat for right ear.** Name: "DT250 Right - B&K 4153"
8. **Save both measurements:** File → Save all measurements (as .mdat backup)

### Step 1b — (Recommended) Average multiple measurements

A single headphone-on-coupler measurement is sensitive to how the cushion seats on the coupler: the seal — and therefore the response, especially at high frequencies — shifts each time you reseat. Averaging several repositioned measurements gives a more representative response to correct against.

1. **Take several measurements per ear** (e.g. 3-6), **lifting and reseating the headphone between each**. Re-running without repositioning only averages noise, not seating variability. Name them e.g. "DT250 L #1" ... "DT250 L #6".
2. *(Optional)* Select the same-ear measurements and **SPL-align** them over a stable mid-band (e.g. 200 Hz - 2 kHz) so seating-level differences don't skew the average.
3. **Average them:** go to the **All SPL** graph, in the trace-selector list **tick only the same-ear measurements** (untick everything else), then click **Average the responses** (lower-left of the All SPL display). REW adds a new averaged trace.
   - This is an RMS (magnitude) average. Do **not** use the Trace Arithmetic average instead — that is a vector (complex) average and will produce high-frequency cancellation dips wherever repositioned measurements disagree in phase.
4. **CRITICAL — give the average an impulse response:** select the averaged trace, then **Actions → Generate Minimum Phase → Generate**.
   - The RMS average is **magnitude-only**: REW discards phase, so the result has no impulse response. Trace Arithmetic's 1/A inversion needs a complex response to operate on. Without this step the 1/A inversion options (target level, exclude notches) disappear and the resulting inverse is wrong. Generate Minimum Phase constructs the unique minimum-phase IR matching the averaged magnitude, turning it into a proper invertible measurement.
5. **Continue with Steps 2-6 using the averaged min-phase trace** wherever those steps refer to "your measurement" / "the left ear measurement." Run Step 4 as written — because the averaged trace is already minimum phase, its 1/A inverse is already causal, so Step 4 simply confirms this (harmless either way).
6. **Repeat for the right ear.**

**Troubleshooting:** if the 1/A target-level / exclude-notches options vanish, or the inverse looks flipped relative to a single-measurement inverse, you skipped step 4 above — the raw RMS average has no impulse response.

### Step 2 — Inspect and smooth the measurement

1. Click on the left ear measurement tab.
2. Click **SPL & Phase** button to view frequency response.
3. Apply **1/6 octave smoothing** (using the smoothing dropdown at the bottom of the measurement tab).
   - This removes mic noise and narrow measurement artifacts while preserving the headphone's actual response shape
   - Prevents the inverse from trying to correct features that vary with headphone repositioning
   - 1/6 octave is a good starting point; 1/3 is more conservative (less correction detail), 1/12 is more aggressive

4. Look for: bass roll-off (below ~80 Hz), any presence peaks (3-5 kHz), treble irregularities. This is normal for headphones on a flat-plate coupler.

**IMPORTANT:** The smoothing must be applied to the measurement BEFORE running the inversion in Step 3. REW's trace arithmetic uses the currently applied smoothing settings. Inverting a smoothed measurement means you only correct the broad headphone response shape (which is what you want). Inverting first and smoothing after is mathematically different and less correct.

### Step 3 — Generate the inverse via Trace Arithmetic

1. Go to the **All SPL** graph (button at top of REW window).
2. Click the **Trace arithmetic** button (in the Actions panel on the right side).
3. In the Trace Arithmetic controls:
   - Set **A** to your left ear measurement (dropdown).
   - Select the operation **1/A** (this inverts both magnitude and phase).

4. **Set the frequency limits** (CRITICAL):
   - Check the boxes for frequency limits
   - **Lower limit: 20 Hz**
   - **Upper limit: 14000 Hz**
   - Outside these limits, the inversion blends to unity gain over a 1-octave span (REW handles this automatically — no abrupt discontinuity)

5. **Set the maximum gain** (CRITICAL for safety):
   - Set to **20 dB**
   - This prevents the inverse from applying huge boosts where the headphone has deep notches

6. **Leave "Exclude notches from inversion" UNCHECKED.** This feature tells REW to skip inverting narrow notches, but on headphone-on-coupler measurements it tends to treat real driver behavior as notches and produces hard discontinuities in the inverse filter (the result drops abruptly to 0 dB at each detected notch). With the 20 dB max gain already limiting extreme boosts, full inversion produces a smoother, more useful filter. The feature is more appropriate for room measurements where deep comb-filter notches from reflections would otherwise cause problems.

7. Set the **target level**: check **"Auto"** to let REW set it based on the average level of the measurement. (The inverse only reshapes — no overall gain change.)

8. Click **Go** (or **Apply**).

9. A **new measurement tab** appears containing the inverse (named something like "1/ DT250 Left - B&K 4153"). Inspect it:
   - The SPL plot should be an approximate mirror image of the original measurement
   - Outside 20 Hz - 14 kHz, the response should flatten to ~0 dB (unity)
   - No extreme peaks (should be within the 20 dB max gain limit)

10. **Repeat steps 3-9 for the right ear measurement.**

### Step 4 — Generate the minimum-phase version

The 1/A inversion produces an **acausal** impulse response (energy before t=0). This is explicitly documented in REW's help: *"for division and inversion... the result is typically not causal."* We must convert it to a minimum-phase IR before it can be used for convolution.

REW offers two paths for this. Both produce equivalent results; pick whichever is more convenient.

**Path A — Adds a min phase trace to the existing measurement tab:**

1. Select the **1/A inverse measurement tab**.
2. Click the **SPL & Phase** tab.
3. Open the **Actions** panel (right side).
4. Click **"Generate Minimum Phase"** → **Generate**.
5. REW adds a **min phase trace** (gray line) to the existing 1/A measurement. No new tab is created.

**Path B — Creates a separate min phase measurement tab:**

1. Select the **1/A inverse measurement tab**.
2. Go to the **All SPL** graph.
3. Open **Actions** → **Measurement actions** (right side).
4. In the **Min. phase version** section, click **"Make min phase copy"**.
5. A dialog appears ("Generate min phase") with options:
   - **Include cal file effects:** checked (default)
   - **Other options:** leave at defaults
   - Click **Generate and close**
6. REW creates a **new measurement tab** containing the minimum-phase version.

**Verify:** Whichever path you used, the min phase data should closely match the 1/A magnitude response. If the original measurement was smoothed before inversion (Step 2), the min phase version should already be clean.

The export procedure in Step 6 handles both paths.

### Step 5 — Verify the correction (in REW)

1. Go to the **All SPL** graph.
2. Use **Trace Arithmetic**:
   - Set A = **original measurement** (e.g., "DT250 Left - B&K 4153")
   - Set B = **1/A inverse** (e.g., "1/ DT250 Left - B&K 4153")
   - Operation = **A * B**
3. Click Go.
4. The result should be **approximately flat** across 20 Hz - 14 kHz (within +/- 2 dB). Outside that range, it follows the original measurement (because the inverse is unity there).
5. If not flat enough: adjust smoothing, frequency limits, or max gain and redo steps 3-4.

### Step 6 — Export as WAV

**If you used Path A in Step 4** (min phase trace added to existing 1/A tab):

1. Select the **1/A inverse measurement tab**.
2. Go to **File → Export impulse response as WAV**.
3. In the export dialog, select **"Export min phase version of IR"** (this exports the MP trace from the measurement).

**If you used Path B in Step 4** (new min phase measurement tab created):

1. Select the **new min phase measurement tab** (the one created by "Make min phase copy").
2. Go to **File → Export impulse response as WAV**.
3. In the export dialog, select **"Export measured IR"** (the measurement itself is already minimum-phase, so exporting its "measured" IR is correct).

**Common export settings (both paths):**

- **Format:** **32-bit Float**
- **Channels:** **Mono**
- **Normalise samples to peak value:** **ON**
- **Apply IR Window before Export:** **OFF**
- **Place t=0 at sample index:** checked, set to **256** (provides headroom for the filter's pre-ring — ~15 samples of low-amplitude oscillation before the main peak is normal for a bandlimited filter)
- **Export this sample count:** checked, set to **4k** (4096 samples = ~85ms at 48kHz — more than sufficient, the IR decays within ~100 samples of the peak)
- **Sample rate:** **48 kHz** only

4. Save as: `dt250_ucx2_inverse_L.wav`
5. **Repeat the entire process (Steps 3-6) for the right ear.** Save as: `dt250_ucx2_inverse_R.wav`

> **Why minimum phase and not the raw 1/A "measured" IR?**
>
> The raw 1/A "measured" IR is acausal — it has a symmetric peak with
> energy on both sides (pre-ringing and post-ringing). This cannot be
> used for real-time convolution. The min phase version has the same
> magnitude response but reconstructs a causal IR where all energy
> follows the peak.
>
> **Why not "Place t=0 at sample index: 0"?**
>
> The minimum-phase IR has ~15 samples of low-amplitude pre-ring before
> the main peak (normal for a bandlimited correction filter). Setting
> t=0 at 256 provides headroom so this pre-ring isn't clipped. At 48kHz,
> 256 samples = ~5ms of leading silence — negligible for convolution.
>
> **Why 4096 samples?**
>
> The IR decays to near-zero within ~100 samples of the peak. 4096
> samples provides generous margin. The remaining samples are silence,
> which adds no computational cost to FFT-based convolution (which
> operates on power-of-2 block sizes anyway).

---

## Step 7 — SPL Calibration and Verification (`level_validator.py`)

*Applies regardless of which method produced the IRs.*

The IRs flatten the **frequency response**. They say nothing about **absolute
level** — the toolbox still has no idea what dB SPL a given digital amplitude
produces. Step 7 measures that, and it is the final verification that the whole
chain works end to end.

**Order matters.** The SPL anchor is measured with the tone routed *through*
`CalibrationManager` with the inverse IR applied. The anchor is therefore only
valid for the IRs it was measured with. **If you regenerate the IRs, redo Step 7.**

### What is being stored

`calibration_config.json` stores a *pair* per profile:

```
reference_amplitude   -- a fixed digital peak amplitude
measured_spl_left     -- the dB SPL that amplitude produces at the left ear
measured_spl_right    -- ... and the right
```

and `spl_to_amplitude()` interpolates from that pair:

```
amp = reference_amplitude * 10 ** ((target_spl - measured_spl) / 20)
```

Only the *pair* is meaningful. There are two equivalent ways to obtain it:

- **Method A (use this).** Fix the amplitude, measure whatever SPL comes out,
  store that SPL.
- **Method B.** Fix a target SPL (e.g. 94 dB), tune the amplitude until the
  meter reads it, store that amplitude.

These are algebraically identical. Method B is only usable when the chain can
actually *reach* the target — on a low-output chain it has no solution, and
turning the amplitude past 1.0 produces clipping, not more level. **Method A
always works.** Historic note: `reference_amplitude = 0.07158961057522077`,
shared by the over-ear profiles, was originally bootstrapped via Method B on the
DT250. Later profiles reuse that fixed amplitude unchanged and simply record
whatever SPL results, which is why their `measured_spl` values range from ~92 to
~101 dB rather than all reading 94.

### The placeholder trick

`spl_to_amplitude()` needs `measured_spl_*` to be non-null before it will run at
all (`spl_calibrated` gates it), but you can't know those values until you've
measured. Chicken-and-egg. Resolve it by setting the placeholder **equal to the
level you will request**:

```
measured_spl_left  = 77.0
measured_spl_right = 77.0     ... then request exactly 77 dB SPL
```

Because `target_spl == measured_spl`, the exponent is zero and
`spl_to_amplitude()` returns exactly `reference_amplitude`. The coupler sees the
raw anchor tone.

- Do **not** use `0.0` as the placeholder. `spl_calibrated` would still be True,
  and any normal request would compute an amplitude far above 1.0 and clip.
- Do **not** use `null`. That flips `spl_calibrated` to False and
  `spl_to_amplitude()` raises, so nothing can play.
- Pick a placeholder near the expected anchor level, so an accidental request
  errs quiet rather than loud.

### Procedure

**Prerequisites**

- [ ] Inverse filter WAVs from Step 6 in `headphone_IR_data/`, paths written into
      the profile's `inverse_filter` block
- [ ] Headphone on the coupler (**not** on a head)
- [ ] RME output gain at the calibration setting, **locked**
      (TotalMix -> Store to device -> Lock Keys -> ALL). Document the setting.
- [ ] REW SPL meter **pistonphone-anchored this session** (94 dB SPL @ 1 kHz).
      Without this, every number below is relative and meaningless.
- [ ] TotalMix visible, so you can watch the output meter for clipping

**1. Dry run (no sound).** Confirms the profile loads, both IRs resolve, and
shows the amplitude before anything reaches the transducer.

```bash
python utils/level_validator.py \
    --config /path/to/calibration_data/calibration_config.json \
    --profile <profile_name> \
    --no-gui --type tone --freq 1000 --level <placeholder> --ear left --dur 3
```

Check the readout:

- `FIR calibrated: True` and `SPL calibrated: True`
- `Target peak amp` equals `reference_amplitude` exactly
  (if not, the placeholder and the request have drifted apart — fix before playing)
- `Peak after FIR` is the value TotalMix will show, as dBFS: `20*log10(peak)`
- `clipped: False`

Repeat with `--ear right`. Expect the opposite channel to read exactly `0.00000`.

**2. Measure the anchor, one ear at a time.** Add `--play`, lengthen the tone.

```bash
python utils/level_validator.py --config CFG --profile PROF \
    --no-gui --type tone --freq 1000 --level <placeholder> --ear left --dur 10 --play
```

The REW SPL meter takes **>10 s to stabilise** — wait for it to settle, don't
read the first number. Record the value. Repeat for `--ear right`.

Cross-check `Peak after FIR` against the TotalMix output meter. They should agree
(e.g. post-FIR peak 0.44 -> `20*log10(0.44) = -7.1 dBFS`). Disagreement means
there is unexpected gain or attenuation somewhere in TotalMix.

**3. Write the two readings** into `measured_spl_left` / `measured_spl_right`,
save the JSON, and press **Reload** in the `level_validator` GUI (or restart if
running headless). The `SPL anchor:` line confirms the new values loaded.

**4. Linearity check.** This validates the `20*log10` assumption that the entire
calibration rests on. With the real anchor `<L>` now in the file:

```
--level <L>       -> meter should read <L>
--level <L-10>    -> should read 10 dB lower
--level <L-20>    -> should read 20 dB lower
--level <L-30>    -> should read 30 dB lower
```

Judge the **deltas between steps**, not the absolute values. Within ~1 dB is
fine. Points close to the noise floor scatter more; if the lowest point is
unstable, either ignore it or re-measure that point with REW's **RTA on the
1 kHz bin** rather than broadband SPL (narrowband rejects out-of-band noise and
settles faster).

If the deltas do **not** track — the steps compress as level rises — the output
stage is limiting. Stop. No value in the profile is trustworthy. See the
low-ceiling notes below.

**5. Compute and set `max_spl`.** The chain's ceiling is the SPL at digital full
scale:

```
full_scale_spl = measured_spl + 20*log10(1 / peak_after_FIR)
max_spl        = full_scale_spl - 3        (3 dB headroom)
```

Use the **quieter ear** so the ceiling is conservative. Set `max_spl` in the
profile to this value, not to a copied-in default.

> **Known gap.** `max_spl` clamps the *requested* SPL. It does **not** check that
> the resulting amplitude stays below 1.0. On a high-ceiling profile this never
> matters. On a low-ceiling profile, an over-large `max_spl` will silently clip
> and present distortion as a calibrated level. Watch TotalMix.

**6. Round-trip sanity check.** Request a round number and confirm the meter
agrees within ~1 dB:

```bash
--level 70 --ear right --dur 15 --play
```

If it reads high by exactly the placeholder offset, the Reload didn't take.

**7. Multi-frequency check (optional but recommended).** Play the same dB SPL at
250 / 500 / 1k / 2k / 4k / 8k Hz. All should measure within ~2 dB of each other
— this is the inverse filter and the SPL math composing correctly, and is the
real end-to-end proof that Steps 1-6 worked.

### Anchor placement

Error in `spl_to_amplitude()` is **zero at the anchor by construction** and grows
with distance from it. Two competing pulls:

- Anchoring **near the top** of the usable range gives the best meter SNR during
  the measurement itself.
- Anchoring **mid-range** minimises error at the levels you will actually present.

If the linearity check comes back clean (slope 1.00), it doesn't matter. If there
is a residual slope error, put the anchor in the middle of your working range.

### Insert earphones and low-ceiling chains

Worked through with the **Neurospec / Etymotic ER-2** on 2026-07-09. Relevant if
a transducer will not play loud enough:

- The ER-2 is a **10 ohm** load. That is very low. RME **line outputs**
  (Analog 1/2) are designed to drive high-impedance inputs and are
  **current-limited** into 10 ohm; the output voltage collapses and the result is
  very quiet. The **front headphone output** has a real output stage and drives
  it far louder. Confirmed empirically.
- If a split 2x mono-jack connector forces you onto the line outputs, expect a
  much lower ceiling. Measured full scale on that chain: **~90.6 dB SPL**, versus
  **~123 dB** for the over-ear profiles on the HP jack.
- **`reference_amplitude` is per-profile.** The over-ear profiles share one value
  only because they share one locked HP gain on one output. A transducer on a
  different physical output needs its own anchor amplitude. For the ER-2 it was
  raised to `0.5` (post-FIR peak 0.44, `-7.1 dBFS`) to sit near the top of the
  usable range while staying below clipping.
- **Do not treat a low ceiling as a reason to inflate `reference_amplitude`.**
  Changing it cannot make the chain louder: `measured_spl` moves with it and the
  two cancel exactly. Only analog gain, or a different output, changes the
  physics.
- **Changing the physical output invalidates the calibration.** Moving the ER-2
  from the line outs to the HP jack (e.g. via a splitter) means a different
  output stage and gain. Re-measure the anchor and recompute `max_spl`.
- The `_description` field on the profile should record **which output** the
  calibration belongs to. Selecting a profile does not currently tell the
  operator to repatch.

### The `retspl` block

`retspl` maps frequency -> RETSPL offset for `dB_HL = dB_SPL - RETSPL(freq)`. It
is **transducer- and coupler-specific**:

- Circumaural (DT250, K271) on the 4153: the ISO 389-8 / ANSI S3.6 **HDA200**
  table is used as a research-grade approximation.
- **Insert earphones (ER-2) on the 4157: the HDA200 table is invalid.** The
  correct family is **ISO 389-2** (insert phones, IEC 60318-4 occluded-ear
  simulator), whose tabulated values are for the **ER-3A** — the ER-2 is not a
  listed standard transducer, so it remains an approximation either way.

Set `"retspl": null` to disable dB HL conversion for a profile and report dB SPL
only. This is the safe default until a defensible table exists.

---

## Method B: PEQ Auto-EQ (Alternative / Backup)

This method uses REW's parametric EQ engine to generate correction filters, then exports their combined impulse response. The filter IR is inherently minimum phase (confirmed by REW author John Mulcahy: "The filters impulse response is inherently minimum phase").

### Steps

1. Select your measurement. Click **EQ** button.
2. **Equaliser:** select **"Generic"** (maximum flexibility).
3. **Target Settings:**
   - Target Type: **"Full range speaker"**
   - LF Cutoff: **0 Hz** (flat to DC)
   - Set target level: adjust so the flat target line sits near the average of your measurement
4. **Match Range:** set to **20 Hz - 14,000 Hz**
5. In **Filter Tasks**, click **"Match response to target"**.
6. REW generates PEQ filters. Check the predicted response — it should be reasonably flat within the match range.
7. Fine-tune: manually adjust or add filters as needed.
8. Go to **File → Export filters impulse response as WAV**.
   - This exports a **128k sample** mono WAV containing the combined impulse response of all PEQ filters.
   - **Sample rate:** 48000 Hz
   - **Format:** 32-bit Float
   - **Normalize:** ON
9. Save as your inverse filter WAV file.

**Limitation:** PEQ correction is limited by the number of filter bands (typically 10-20). It won't perfectly match a headphone's detailed frequency response. For our use case, Method A is better.

---

## Important Notes

### On the "1/A" vs "1/|A|" operations

- **1/A** inverts both magnitude and phase. **Use this one.** The result is acausal, which is why we generate a minimum-phase version before export.
- **1/|A|** inverts magnitude only and produces a **linear-phase** (symmetric, acausal) result by design. Not recommended — 1/A + min phase export gives a shorter, more efficient filter.

### On the frequency range (20 Hz - 14 kHz)

We generate a **single** inverse filter spanning **20 Hz - 14 kHz**:
- **Upper limit 14 kHz:** the practical ceiling for valid calibration on the B&K 4153. Above ~10 kHz the coupler's behaviour becomes unreliable, and 14 kHz is taken as the absolute maximum for trustworthy correction — beyond it the inverse would be correcting coupler artifacts rather than the headphone.
- **Lower limit 20 Hz:** taken as low as the measurement supports. The 20 dB max-gain cap (Step 3, item 5) limits how hard the inverse boosts the bass roll-off, so extending down to 20 Hz does not produce runaway low-frequency gain.

(Earlier revisions kept several variants at different ranges, e.g. 50-12k and 200-8k. Those are superseded by the single 20 Hz - 14 kHz filter.)

---

## Quick Reference Checklist

```
MEASUREMENT
[ ] REW configured: RME UCX II, 48 kHz, mic cal file loaded
[ ] RME HP gain locked in TotalMix (document the setting!)
[ ] Left ear measured (log sweep, 256k length)
[ ] Right ear measured
[ ] Measurements saved as .mdat

AVERAGING (recommended; repeat for L and R)
[ ] 3-6 measurements taken, repositioning between each
[ ] All SPL → tick same-ear measurements → Average the responses (RMS, NOT vector)
[ ] Averaged trace → Actions → Generate Minimum Phase (REQUIRED before 1/A)
[ ] Continue below using the averaged min-phase trace

SMOOTH + INVERT (repeat for L and R)
[ ] Apply 1/6 octave smoothing to the MEASUREMENT (before inversion)
[ ] All SPL → Trace Arithmetic → 1/A
[ ] Frequency limits: 20 Hz - 14,000 Hz
[ ] Max gain: 20 dB
[ ] Exclude notches: OFF (discontinuities in result if ON)
[ ] Auto target level
[ ] Result inspected: mirror of original, no extreme peaks

MINIMUM-PHASE CONVERSION (repeat for L and R — pick one path)
[ ] Path A: SPL & Phase → Actions → Generate Minimum Phase
    → adds gray MP trace to existing 1/A tab
[ ] Path B: All SPL → Actions → Measurement actions → Min. phase version
    → "Make min phase copy" → creates a new measurement tab

VERIFICATION (repeat for L and R)
[ ] All SPL → Trace Arithmetic: original * 1/A inverse
[ ] Result ≈ flat (+/- 2 dB, 20 Hz - 14 kHz)

EXPORT (repeat for L and R)
[ ] If Path A was used: select the 1/A tab, export "Export min phase version of IR"
[ ] If Path B was used: select the new MP tab, export "Export measured IR"
[ ] File → Export impulse response as WAV
[ ] Format: 32-bit Float
[ ] Mono
[ ] Normalise: ON
[ ] Apply IR Window: OFF
[ ] Place t=0 at sample index: 256
[ ] Export this sample count: 4k
[ ] Sample rate: 48 kHz
[ ] Saved as dt250_ucx2_inverse_L.wav / _R.wav

EXPECTED RESULT IN AUDIO EDITOR
[ ] 4096 samples, 48 kHz, 32-bit float, mono
[ ] ~256 samples of near-silence
[ ] Sharp peak at ~sample 256
[ ] ~15 samples of low-amplitude pre-ring before peak (normal)
[ ] Rapid decay to near-zero within ~100 samples after peak
[ ] Remaining samples are silence

SPL CALIBRATION -- Step 7 (level_validator.py; redo if IRs change)
[ ] IR paths written into the profile's inverse_filter block
[ ] Headphone on the coupler, NOT on a head
[ ] RME output gain locked (TotalMix -> Store -> Lock Keys -> ALL); setting noted
[ ] REW SPL meter pistonphone-anchored this session (94 dB @ 1 kHz)
[ ] Placeholder measured_spl_left/right set EQUAL to the level you will request
[ ] Dry run (--no-gui, no --play): Target peak amp == reference_amplitude,
    clipped: False, opposite ear reads 0.00000
[ ] Anchor measured, left ear (--play, --dur 10, let meter settle >10 s)
[ ] Anchor measured, right ear
[ ] Peak after FIR cross-checked against the TotalMix output meter (dBFS)
[ ] Real values written to measured_spl_left/right; Reload pressed; anchor
    line in GUI confirms new values
[ ] Linearity: -10 / -20 / -30 dB requests track within ~1 dB (judge DELTAS)
[ ] max_spl = measured_spl + 20*log10(1/peak_after_FIR) - 3 dB, quieter ear
[ ] Round-trip: request 70 dB SPL, meter reads ~70
[ ] Multi-frequency: 250/500/1k/2k/4k/8k Hz at one level, all within ~2 dB
[ ] retspl set (or explicitly null -- null for insert earphones)
[ ] Profile _description records which physical output was used

OPTIONAL
[ ] Different smoothing levels (1/3, 1/6, 1/12) applied to measurement
```

---

## Python Fallback

If REW's workflow doesn't produce satisfactory results, we have a Python fallback planned (`generate_inverse_ir.py`) that:
1. Loads the raw measurement IR from REW (exported as WAV)
2. Computes the inverse in the frequency domain
3. Applies frequency-range windowing (bandpass)
4. Computes minimum-phase via `scipy.signal.minimum_phase()`
5. Exports as WAV

This is ~50 lines of scipy code and can be built as needed.
