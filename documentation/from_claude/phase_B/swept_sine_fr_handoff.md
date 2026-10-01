# swept_sine_fr.py - design notes & handoff

Last updated: 2026-05-19. Companion document to `utils/swept_sine_fr.py`. If
you're picking this up to make changes, read this first.

---

## What this script is for

Standalone verification utility. Plays a known log sweep through PROLACTIN's
production calibration pipeline (`CalibrationManager.prepare_samples()`),
records the result on the B&K 4153 coupler, deconvolves to recover the
acoustic FR, and reports how flat it is.

If the script reports a flat (< +/- a few dB) response, the production
inverse-IR convolution + per-channel-gain math is working correctly on the
hardware. If it doesn't, something is wrong with `prepare_samples()`, the IR
files, or the playback chain (TotalMix routing, gain, etc.).

This script is NOT part of the paradigm runtime. It is run manually to
validate calibration before / after IR re-measurement.

## What this script tests, and what it doesn't

**Tested:**
- The combined FIR inverse filter + stereo channel routing math in
  `CalibrationManager.prepare_samples()`.
- Correctness of the convolution length (uses `mode='full'`, length N+M-1).
- That the calibrated sweep, when played and recorded on the coupler,
  produces an acoustically flat FR.

**Not tested by this script:**
- Absolute SPL accuracy. The script intentionally passes
  `per_channel_gain=None` so it isolates the FR-shaping math from the
  level math. SPL is verified separately (REW SPL logger + rms_analyzer
  + known amplitudes).
- PsychoPy Sound playback latency or timing precision (covered by paradigm
  runs).
- The `per_channel_gain` code path (covered by paradigms that compute
  `spl_to_amplitude()` and pass the result through).

## Three modes

| Mode      | What it does                                          | When to use                                |
|-----------|-------------------------------------------------------|--------------------------------------------|
| `render`  | Writes raw + calibrated stereo sweep WAVs to disk.    | The trustworthy path. Lets you use REW /   |
|           | No playback or recording.                             | Reaper for the measurement loop.           |
| `analyze` | Loads recordings + reference sweep from `render`,     | Always pair with `render`.                 |
|           | deconvolves, plots, writes text summary.              |                                            |
| `online`  | Python end-to-end: gens + plays via PsychoPy Sound,   | Convenience. Less trustworthy because it   |
|           | records via sounddevice, plots, writes summary.       | depends on Python play/record sync.        |

The render + analyze split exists because the Python play+record sync is
the weakest part of the chain. By writing WAVs and using Reaper / REW (which
have well-tuned audio sync), the result depends only on the math we want to
verify.

## File output structure

Default location: `swept_sine_fr_out/<profile>_<channel>/`. Auto-created
to keep different headphones / channels separate. Override with
`--out-dir <path>` to write directly.

```
swept_sine_fr_out/beyerdynamic_dt250_a_ucx2_L/
  sweep_ref.wav                                      <- mono ref, deconv input
  sweep_raw_beyerdynamic_dt250_a_ucx2_L.wav          <- stereo, bypass
  sweep_cal_beyerdynamic_dt250_a_ucx2_L.wav          <- stereo, calibrated
  render_meta.json                                   <- sweep params + paths
  analyze_fr_L_<timestamp>.png                       <- plot (analyze + online)
  analyze_fr_L_<timestamp>.txt                       <- text summary
  online_fr_L_<timestamp>.png                        <- (online only)
  online_<raw|cal>_L_<timestamp>.wav                 <- (online: recordings)
```

`render_meta.json` records the actual filenames it wrote. `analyze` mode
reads it to find the reference sweep, so renaming output files in the
future just requires updating one place (`render_sweeps()`).

## Key design decisions

### Why `prepare_samples()` was split out of `prepare_sound()`

`render` mode needs the post-calibration stereo ndarray (to write to WAV).
Getting samples back out of a `psychopy.sound.Sound` object is fragile
(depends on internal attributes that vary by backend). Solution: the math
lives in `prepare_samples()` (returns ndarray); `prepare_sound()` is a
thin wrapper that calls it and wraps in Sound. Both production and the
test execute exactly the same math.

### Why sounddevice for recording in online mode

The variable under test is the playback path. Recording is just
measurement infrastructure. Sounddevice is simpler than PsychoPy's
microphone class, exposes input-channel mapping explicitly, and decouples
record-driver bugs from the playback-path verification.

Clock drift between PTB (play) and sounddevice (record) over a 5 s sweep
at 48 kHz is <1 sample. Not relevant.

### Why direct frequency-domain deconvolution, not Farina inverse sweep

```
H(f) = FFT(recording) / FFT(reference_sweep)
```

This is mathematically equivalent to Farina convolution within the sweep
band. Farina's inverse-sweep trick is a band-edge regularization. Since
our sweep (20 Hz - 20 kHz) covers the analysis band (20 Hz - 16 kHz) with
margin, simpler is better. The denominator is regularized with a small
epsilon at frequencies outside the sweep band; those frequencies are
outside the analysis band anyway.

### Why auto-subdir per profile + channel

Without this, every render to the default `--out-dir` would clobber the
previous one. Explicit `--out-dir <path>` bypasses the auto-subdir for
users who want consolidated output.

### Why all output files go in the same directory

Plot + summary + sweeps + recordings + meta all live together so one
directory holds the complete state of one measurement. Easy to ZIP and
share, or move around, without losing context.

## Common modification points

### Change the analysis band
Edit `DEFAULT_ANALYSIS_BAND_HZ` near the top of `swept_sine_fr.py`, or
pass `--analysis-low <Hz> --analysis-high <Hz>`. Currently `(20, 16000)`.

### Change the always-drawn tolerance lines
Edit `ALWAYS_DRAWN_TOLERANCES_DB` (currently `(1.0, 2.0)`). The
user-configurable tolerance is `--tolerance-db` (default 3.0). All three
lines (1, 2, 3 dB) are drawn by default; the user-configurable one gets
the legend entry.

### Change the smoothing
Edit `DEFAULT_SMOOTH_OCT_FRAC` (currently 1/6 octave) or pass
`--smooth-oct 0.0833` for 1/12 octave, etc. Smaller value = less
smoothing = finer detail visible.

### Change the normalize band
The normalize band is the range over which we compute the "0 dB"
reference (curves are shifted so this band averages to 0). Default
200-8000 Hz. Edit `DEFAULT_NORMALIZE_BAND_HZ` or pass
`--norm-low --norm-high`.

Note: changing the normalize band shifts the curves vertically; it does
NOT affect the flatness, std, or peak-deviation numbers (those are
shape metrics, invariant under uniform vertical shift).

### Add a new calibration profile
Edit `calibration_data/calibration_config.json`. Profile naming
convention: `<model>_<unit_id>_<interface>`, all lowercase. Set
`active_profile` to make it the default. Profile lookup is
case-insensitive (handled by CalibrationManager).

### Add a new stat to the per-curve output
Three places to update:
1. `compute_stats()` - add the computation, return in the dict
2. `recording_to_curve()` - add a print line for stdout
3. `write_summary()` - add a line to the text file
4. `plot_overlay()` - add to the per-curve text annotation

## Validation done

The math has been validated against synthesized data (no live audio in
the dev environment):

1. **Synthetic FIR LPF deconvolution.** Generated a sweep, convolved with
   a known 5 kHz lowpass FIR, deconvolved with this script's pipeline,
   compared the recovered FR to the true FR. Mean abs error 0.012 dB,
   max abs error 0.20 dB across 200 Hz - 10 kHz.

2. **Identity check.** Used the cal'd sweep itself as the "recording".
   Yielded 0.00 dB flatness as expected.

3. **Simulated headphone response.** Built a synthetic "headphone" with
   a 3 kHz resonant peak (iirpeak). Bypass curve shows the peak;
   calibrated curve (synthetic FIR LPF * resonance) shows expected
   combined response. Plot annotations and summary file format verified.

4. **Cross-platform smoke test.** Module parses on Python 3.12, all
   functions exercised via unit-style tests in the dev sandbox.

Live hardware testing is done by Eric on the project Mac with the RME
UCX II. No CI / automated test suite for this script.

## Known limitations / future work

1. **Interface FR not separated from headphone IR.** Current IRs were
   measured with the RME UCX II as both the playback DAC and recording
   ADC, so the IR captures the combined RME+headphone response. This is
   correct for same-RME playback in PROLACTIN. Future improvement:
   measure the RME's own FR via loopback and divide it out of the IR.
   Marginal benefit (RME UCX II is very flat across audio band) but
   cleaner conceptual separation.

2. **Multiple identical `sweep_ref.wav` on disk.** One per output dir.
   Could be deduplicated via hash+symlink. Not a real problem right now.

3. **No automatic pass/fail.** The plot + summary file show all the
   numbers; user inspects. Could add a hard exit code based on whether
   the cal curve is within `--tolerance-db` across the analysis band.
   Held off because measurement noise can cause spurious failures.

4. **Online mode device routing.** PsychoPy Sound writes to channels
   0+1 of the selected output device. The user's TotalMix workspace
   must route those to the physical headphone-amp outputs. There's no
   programmatic way to specify physical outs 7+8 from PsychoPy.

5. **SPL math not exercised.** This script passes `per_channel_gain=None`
   so it isolates the FR math. SPL verification is a separate workflow
   (not yet built; see PROLACTIN deferred work).

## Dependencies

- `numpy`, `scipy`, `matplotlib` (always required)
- `sounddevice` (online mode only - imported lazily)
- `psychopy` (online mode only - imported lazily)

ASCII-only source. Tested on Mac (Core Audio); should work on Windows
(WASAPI / ASIO via sounddevice / PsychoPy).

## Files maintained together

- `utils/swept_sine_fr.py` - the script
- `utils/calibration.py` - `prepare_samples()` is the function under test
- `calibration_data/calibration_config.json` - profile definitions
- `utils/swept_sine_fr_handoff.md` - this doc

If you change the public API of `prepare_samples()` in `calibration.py`,
make sure to update `swept_sine_fr.py`'s call sites (`render_sweeps()`,
`run_online()`).
