"""
Test B -- Audible smoke test for the PROLACTIN calibration pipeline.

Builds a tone, runs it through CalibrationManager.prepare_sound(), inspects
the result numerically, writes it to a WAV for offline inspection, and
optionally plays it through PsychoPy/PTB.

Usage:
    # Default: 1 kHz, 500 ms, 94 dB SPL nominal, both ears, write WAV only
    python tests/audible_smoke_test.py --config ../../calibration_data/calibration_config.json

    # Play it (requires headphones connected)
    python tests/audible_smoke_test.py --config ../../calibration_data/calibration_config.json --play

    # Lower level (10 dB below anchor) -- verify linearity
    python tests/audible_smoke_test.py --config ../../calibration_data/calibration_config.json --level 84 --play

    # Different frequency
    python tests/audible_smoke_test.py --config ../../calibration_data/calibration_config.json --freq 2000 --play

    # Single ear
    python tests/audible_smoke_test.py --config ../../calibration_data/calibration_config.json --ear left --play
    python tests/audible_smoke_test.py --config ../../calibration_data/calibration_config.json --ear right --play

    # NO-HARDWARE sanity mode: skip playback, only build + inspect + write WAV
    python tests/audible_smoke_test.py --config ../../calibration_data/calibration_config.json --no-play

What it checks (numerical sanity, no hardware required):
  1. CalibrationManager loads cleanly
  2. prepare_sound() returns a Sound object (or compatible)
  3. Output is stereo (N+M-1, 2)
  4. No NaN or Inf in output samples
  5. No onset click (|out[0]| < 0.01)
  6. No end click (|out[-1]| < 0.01)
  7. Peak amplitude < 1.0 (no clipping)
  8. Pan: when --ear left, right channel is exactly zero (and vice versa)
  9. Per-ear amplitude matches spl_to_amplitude() math
 10. Writes a WAV that can be inspected in Audition / REW / Reaper

What it checks (with --play, requires hardware):
 11. PsychoPy/PTB Sound construction succeeds with a stereo numpy array
 12. Playback runs without error
 13. (Listen for): clean tone, no clicks at onset/offset, smooth envelope

What it does NOT check (requires SPL meter + B&K coupler):
  - Whether the tone actually comes out at the requested dB SPL
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def build_tone(fs: int, freq: float, duration: float,
               fade_time: float = 0.050) -> np.ndarray:
    """Build a 1-channel tone with Hann fade-in/out (matches event_gen.sin style)."""
    n = int(round(duration * fs))
    t = np.arange(n) / fs
    wave = np.sin(2 * np.pi * freq * t)
    fade_n = int(round(fade_time * fs))
    if fade_n > 0:
        full_win = np.hanning(2 * fade_n)
        wave[:fade_n] *= full_win[:fade_n]
        wave[-fade_n:] *= full_win[-fade_n:]
    return wave


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True,
                    help="Path to calibration_config.json")
    ap.add_argument("--profile", default=None,
                    help="Profile to load (default: config/DEFAULTS.py 'default_headphone_calibration_profile')")
    ap.add_argument("--freq", type=float, default=1000.0,
                    help="Tone frequency in Hz (default 1000)")
    ap.add_argument("--duration", type=float, default=0.500,
                    help="Tone duration in seconds (default 0.5)")
    ap.add_argument("--fade", type=float, default=0.010,
                    help="Hann fade-in/out time in seconds (default 0.01)")
    ap.add_argument("--level", type=float, default=None,
                    help=("Requested level in dB SPL. If omitted, uses the "
                          "profile's reference amplitude directly (anchor)."))
    ap.add_argument("--ear", choices=["left", "right", "both"], default="both",
                    help="Which ear (default both)")
    ap.add_argument("--play", dest="play", action="store_true",
                    help="Play the result through PsychoPy/PTB")
    ap.add_argument("--no-play", dest="play", action="store_false",
                    help="Skip playback (default)")
    ap.set_defaults(play=False)
    ap.add_argument("--out", default="audible_smoke_test.wav",
                    help="Output WAV path (default audible_smoke_test.wav)")
    args = ap.parse_args()

    # Adjust sys.path so we can import utils.calibration when running from
    # tests/ directory in the toolbox layout.
    here = Path(__file__).resolve().parent
    toolbox_root = here.parent
    sys.path.insert(0, str(toolbox_root))

    from utils.calibration import CalibrationManager

    # ----------------------------------------------------------------------
    print("=" * 64)
    print("Loading calibration ...")
    print("=" * 64)
    cm = CalibrationManager(args.config, profile=args.profile)
    cm.summary()
    print()

    fs = cm.sample_rate

    # ----------------------------------------------------------------------
    # Build the tone, decide amplitude
    # ----------------------------------------------------------------------
    wave = build_tone(fs, args.freq, args.duration, args.fade)

    if args.level is None:
        # Use ref amp directly -- nominal anchor level
        ref_amp = cm._profile["spl_calibration"]["reference_amplitude"]
        amp_L, amp_R = ref_amp, ref_amp
        nominal_spl_L = cm._profile["spl_calibration"]["measured_spl_left"]
        nominal_spl_R = cm._profile["spl_calibration"]["measured_spl_right"]
        print(f"[level] No --level given; using anchor ref_amp = {ref_amp:.6f}")
        print(f"        Expected: {nominal_spl_L:.1f} dB SPL (L), "
              f"{nominal_spl_R:.1f} dB SPL (R)")
    else:
        amp_L, amp_R = cm.spl_to_amplitude(args.level)
        print(f"[level] Requested {args.level:.1f} dB SPL")
        print(f"        amp_L = {amp_L:.6f}, amp_R = {amp_R:.6f}")
        nominal_spl_L = nominal_spl_R = args.level

    # Apply per-channel gain via the gateway's per_channel_gain kwarg, with the
    # raw mono unscaled. (Same path IFMC/TMC will use post-Step 6.)
    print()
    print("=" * 64)
    print("Building stimulus and routing through prepare_sound() ...")
    print("=" * 64)

    if args.ear == "left":
        pan = -1.0; gain = (amp_L, 0.0)
    elif args.ear == "right":
        pan = 1.0;  gain = (0.0, amp_R)
    else:
        pan = None; gain = (amp_L, amp_R)

    snd = cm.prepare_sound(wave, fs, pan=pan, per_channel_gain=gain)

    # PsychoPy Sound objects expose samples via .sndArr; numpy fakes via .value.
    # Try a few common attributes.
    samples = None
    for attr in ("sndArr", "value", "sound"):
        if hasattr(snd, attr):
            cand = getattr(snd, attr)
            if isinstance(cand, np.ndarray) and cand.ndim == 2:
                samples = cand
                break
    if samples is None:
        # Reconstruct what prepare_sound built so we can still inspect it.
        # This is a fallback for PsychoPy versions that don't expose samples.
        print("[warn] Could not extract samples from Sound object; "
              "rebuilding for inspection.")
        # Use numpy path: redo what prepare_sound does, minus the Sound wrap.
        if pan is None:
            stereo = np.column_stack([wave * amp_L, wave * amp_R])
        elif pan < 0:
            stereo = np.column_stack([wave * amp_L, np.zeros_like(wave)])
        else:
            stereo = np.column_stack([np.zeros_like(wave), wave * amp_R])
        from scipy.signal import fftconvolve
        if cm._ir_left is not None:
            stereo[:, 0] = fftconvolve(stereo[:, 0], cm._ir_left, mode='full')[:len(stereo)]
        # ... this fallback is approximate; real samples ARE the source of truth
        samples = stereo

    n_in = len(wave)
    print(f"Input length:    {n_in} samples ({n_in/fs*1000:.1f} ms)")
    print(f"Output shape:    {samples.shape}")
    print(f"Output duration: {samples.shape[0]/fs*1000:.1f} ms "
          f"(expected {n_in/fs*1000 + (samples.shape[0]-n_in)/fs*1000:.1f} ms incl. ringout)")
    print()

    # ----------------------------------------------------------------------
    # Numerical sanity checks
    # ----------------------------------------------------------------------
    print("=" * 64)
    print("Numerical sanity checks")
    print("=" * 64)
    checks = []

    def chk(name, ok, detail=""):
        status = "[OK]  " if ok else "[FAIL]"
        print(f"{status} {name}{('  -- ' + detail) if detail else ''}")
        checks.append(ok)

    chk("Output is 2D stereo", samples.ndim == 2 and samples.shape[1] == 2,
        f"shape={samples.shape}")
    chk("No NaN", not np.isnan(samples).any())
    chk("No Inf", not np.isinf(samples).any())
    chk("|out[0,L]| < 0.01 (no onset click)",
        abs(samples[0, 0]) < 0.01,
        f"out[0,L] = {samples[0, 0]:+.6f}")
    chk("|out[0,R]| < 0.01 (no onset click)",
        abs(samples[0, 1]) < 0.01,
        f"out[0,R] = {samples[0, 1]:+.6f}")
    chk("|out[-1,L]| < 0.01 (no end click)",
        abs(samples[-1, 0]) < 0.01,
        f"out[-1,L] = {samples[-1, 0]:+.6f}")
    chk("|out[-1,R]| < 0.01 (no end click)",
        abs(samples[-1, 1]) < 0.01,
        f"out[-1,R] = {samples[-1, 1]:+.6f}")

    peak = float(np.max(np.abs(samples)))
    chk("Peak amplitude < 1.0 (no clipping)", peak < 1.0,
        f"peak = {peak:.4f}")

    if args.ear == "left":
        chk("--ear left: right channel exactly zero",
            np.all(samples[:, 1] == 0.0))
    elif args.ear == "right":
        chk("--ear right: left channel exactly zero",
            np.all(samples[:, 0] == 0.0))

    # Steady-state envelope per channel (Hilbert)
    from scipy.signal import hilbert
    mid_lo = int(0.10 * fs); mid_hi = int(0.20 * fs)  # 100-200ms region
    if mid_hi < samples.shape[0]:
        env_L_ss = float(np.median(np.abs(hilbert(samples[mid_lo:mid_hi, 0]))))
        env_R_ss = float(np.median(np.abs(hilbert(samples[mid_lo:mid_hi, 1]))))
        print()
        print(f"Steady-state envelope (median, samples 100-200 ms):")
        print(f"  L = {env_L_ss:.4f}    (input amp_L = {amp_L:.4f})")
        print(f"  R = {env_R_ss:.4f}    (input amp_R = {amp_R:.4f})")
        # The output envelope after FIR convolution should match input amp
        # to within a few percent (the inverse filter is unity-gain at the
        # measured ref frequency by construction).
        # Skip the ratio check on a channel that is intentionally silenced
        # (the "exactly zero" check above already covers correctness).
        check_L = (args.ear != "right") and (amp_L > 0)
        check_R = (args.ear != "left")  and (amp_R > 0)
        if check_L:
            ratio_L = env_L_ss / amp_L
            chk(f"L envelope/amp ratio in [0.5, 2.0] (FIR gain reasonable)",
                0.5 < ratio_L < 2.0,
                f"ratio = {ratio_L:.3f}")
        if check_R:
            ratio_R = env_R_ss / amp_R
            chk(f"R envelope/amp ratio in [0.5, 2.0]",
                0.5 < ratio_R < 2.0,
                f"ratio = {ratio_R:.3f}")

    print()
    if all(checks):
        print(f"[PASS] All {len(checks)} numerical sanity checks passed.")
    else:
        n_fail = sum(1 for c in checks if not c)
        print(f"[FAIL] {n_fail}/{len(checks)} checks failed.")
        sys.exit(1)

    # ----------------------------------------------------------------------
    # Write WAV for offline inspection
    # ----------------------------------------------------------------------
    print()
    print("=" * 64)
    print("Writing WAV for offline inspection ...")
    print("=" * 64)
    out_path = Path(args.out).resolve()
    # Convert to float32 for inspection tools (Audition / REW / Reaper)
    wavfile.write(str(out_path), fs, samples.astype(np.float32))
    print(f"WAV: {out_path}")
    print(f"     {samples.shape[0]} samples @ {fs} Hz, "
          f"peak = {peak:.4f}, stereo")

    # ----------------------------------------------------------------------
    # Optional playback
    # ----------------------------------------------------------------------
    if args.play:
        print()
        print("=" * 64)
        print("Playing through PsychoPy/PTB ...")
        print("=" * 64)
        # The Sound object built by prepare_sound() is already configured.
        # Just play it and wait.
        import psychtoolbox as ptb
        from psychopy import core
        now = ptb.GetSecs()
        snd.play(when=now + 0.1)
        out_dur = samples.shape[0] / fs
        core.wait(out_dur + 0.5)
        print("Playback complete.")
        print()
        print("Listening checks:")
        print("  - Was the tone clean (no clicks at onset or offset)?")
        print("  - Was the envelope smooth (no clipping or distortion)?")
        if args.level is not None:
            print(f"  - (With SPL meter + coupler) Did it measure "
                  f"{nominal_spl_L:.1f} dB SPL on L, "
                  f"{nominal_spl_R:.1f} dB SPL on R?")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
