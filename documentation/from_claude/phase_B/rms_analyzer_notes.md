# rms_analyzer - handoff notes

Last updated: 2026-05-18. Companion to `utils/rms_analyzer.py`.

## What it is
Standalone utility. Computes RMS / peak statistics over a time range from
either a WAV file (dB FS) or a REW V5 SPL meter log (dB SPL). Not part of
the PROLACTIN runtime. Auto-detects input type by extension (.wav vs .txt).

## Run
```
conda activate /Users/spin3d/Documents/Projects/SpiN3D_DIZH/software/python/test_battery/.venv
python utils/rms_analyzer.py            # file picker + interactive GUI
python utils/rms_analyzer.py file.wav   # interactive GUI (full-file range pre-selected)
python utils/rms_analyzer.py file.wav --start 1.0 --end 4.0 --no-gui   # headless
```

## Design decisions (rationale not obvious from code)
- **Default window: rectangular.** Hann available but uncompensated -- biased
  by ~4.26 dB. Kept only as a hook for future spectral-analysis work, not
  for level measurement. Compensation logic was added then removed by user
  request (extra complexity for nothing).
- **Overall RMS AND mean-of-windowed RMS both reported.** Match for
  stationary signals; gap = non-stationarity indicator.
- **REW "peak" = max(LZpeak)**, the meter's Z-weighted peak hold. NOT a sample
  peak (log doesn't store raw samples).
- **REW overall RMS = Leq-style** energy mean (`10*log10(mean(10^(L/10)))`),
  not arithmetic mean of dB. Per-window REW stats use the same energy
  averaging within each rolling block.
- **Single tkinter root** used for BOTH the file picker (as dialog parent)
  and the embedded matplotlib canvas. No phantom small window.
- **Bottom subplot shows full-file windowed RMS** (static, computed once at
  startup, plain line no markers). Selection is overlaid as orange spans on
  both subplots. SpanSelector active on both.
- **GUI is shown by default.** Pass `--no-gui` to suppress (headless). The
  old `--plot` flag is still accepted (no-op; for backward compat).
- **Output gated on "Use this selection" button.** Drags update stats panel
  in real time but do not write anything. Closing via X exits without writing.
- **"Write to file" checkbox in GUI.** Pre-checked when `--output` was given
  on the CLI. If checked and no path known, a save dialog is triggered on
  accept. In headless mode `--output` is still honoured directly.
- **x-axis locked to [0, duration_s].** `ax_top.autoscale(enable=False, axis='x')`
  called after `tight_layout` prevents matplotlib margins and SpanSelector
  from adding blank space on first draw or after the first drag.
- **Playback row (WAV only).** Play/Stop button + Volume slider (-60..0 dB,
  default -15 dB). Uses `_os_play()` / `_os_stop()` -- OS-native commands,
  no extra Python dependencies (macOS: `afplay`; Windows: `winsound`;
  Linux: `paplay`/`aplay`). Non-blocking; button polled every 200 ms via
  `tk_root.after`. New drag stops playback automatically.
- **"Select All" button** resets selection to [0, duration_s], updates
  SpanSelector extents visually, re-runs analysis.
- **Channel is 1-based in the CLI**, 0-based internally.
- **ASCII-only source** (verified byte-by-byte at each save).
- Cross-platform (pathlib, tkinter, no shell-outs).

## Numerical regression tests (passing as of handoff)
- 1 kHz sine @ amp=0.0272, float32 WAV: Overall RMS = -34.319 dB FS,
  peak = -31.309 dB FS. Stationary -> std = 0.
- REW log 12-18 s selection (calibration tone steady region): Leq =
  100.569 dB SPL, mean-of-windowed = 100.587, std = 0.116 dB,
  max LZpeak = 114.4 dB SPL.
- Hann (uncompensated) on stationary sine: mean-of-windowed = -38.580 dB FS
  = -34.319 - 4.261, matches textbook 20*log10(sqrt(3/8)) bias.

## UNTESTED at handoff
The GUI itself was never run end-to-end -- sandbox had no display. On first
interactive use, verify:
- Only ONE window appears at any time (file picker -> plot, no overlap)
- Stats panel visible below plot and updates live on drag
- Span drags work from BOTH subplots
- x-axis shows exactly [0, duration] with no blank margins, stable after drags
- Play/Stop button visible for WAV files (requires `sounddevice`)
- Volume slider defaults to -15 dB
- "Select All" restores full-file selection and updates the span widget handles
- "Write to file" checkbox: unchecked by default (checked if --output given)
- Checking "Write to file" + accept with no path -> save dialog appears
- "Use this selection" -> mainloop exits, report printed
- Closing window via X prints "Selection not confirmed" and exits 0
- Headless mode (--no-gui) skips GUI; --output still writes the file

## Deferred / future work
- **Ambisonic B-format input.** Multi-channel WAV loading already works;
  needs a `--channel-mode` flag (single / bformat-w / bformat-energy /
  binaural-decode). Perceptual weighting between channels must be
  calibrated against in-room measurements. Design notes preserved in the
  comment block at the bottom of `rms_analyzer.py`.
- **A/C weighting IIR filters for WAV** so WAV-derived dB FS can be
  correlated against the weighted REW columns. Straightforward.
- **Display floor at -120 dB FS?** Silent windows currently show as
  -400 dB FS (epsilon floor for log10(0)). Mathematically honest, visually
  alarming. Could cap at -120 dB FS for display only.
- **Playback backend upgrade.** Current `_os_play()` uses `afplay`/`winsound`/
  `aplay` -- simple but no device routing, no calibration gain, no sample-
  accurate timing. Future: replace with the toolbox `TrialPlayer` / PsychoPy
  backend so playback is consistent with PROLACTIN's calibrated output chain.
  The `_os_play` / `_os_stop` function pair is the only thing that needs to
  change; the rest of the GUI wiring stays identical.

## Integrity signatures (grep-able next session)
- `def _os_play`                               -- OS-native playback launch
- `def _os_stop`                               -- OS-native playback stop + cleanup
- `def show_plot_and_pick_range`              -- tkinter-embedded plot
- `def format_stats_block`                    -- in-GUI stats text
- `def _pick_input_file_via_dialog(tk_root)`  -- shared-root signature
- `def _make_tk_root_withdrawn`               -- lazy root factory
- `should_plot = not args.no_gui`
- `_SD_AVAILABLE = True`                      -- sounddevice optional import
- `ax_top.set_xlim(0.0, src.duration_s)`      -- xlim lock
- `vol_scale.set(-15)`                        -- default playback volume
- `write_var = tk.BooleanVar`                 -- write-to-file checkbox
- `'--no-gui', action='store_true'`
- `'--window-shape', choices=['rect', 'hann'], default='rect'`
- File length: ~1194 lines, pure ASCII
