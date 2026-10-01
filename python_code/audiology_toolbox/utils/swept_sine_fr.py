"""
swept_sine_fr.py - Standalone headphone FR verification

Purpose
-------
Verify that CalibrationManager's inverse-IR + per-channel-gain pipeline
produces a flat acoustic FR on the B&K 4153 coupler. Exercises the same
prepare_samples() math used in PROLACTIN, so any regression in the
production code path will show up here as a non-flat measured FR.

See utils/swept_sine_fr_handoff.md for design rationale, architecture,
and common modification points.

Three modes
-----------
  online   - generate sweep, play via PsychoPy Sound (production path),
             record via sounddevice, deconvolve in Python, plot + summary.
             One-button verification.

  render   - generate sweep, apply prepare_samples(), write the
             before/after stereo WAVs to disk plus the mono reference
             sweep. Hand off to Reaper + REW for measurement, then run
             --mode analyze. Decouples Python from the play/record loop.

  analyze  - load recording WAV(s) plus the reference sweep saved by
             render mode, deconvolve, plot + summary.

Workflow (online, one-shot)
---------------------------
  python utils/swept_sine_fr.py --mode online --channel L \\
      --headphone beyerdynamic_dt250_a_ucx2 --compare

Workflow (offline, more trustworthy)
------------------------------------
  python utils/swept_sine_fr.py --mode render --channel L \\
      --headphone beyerdynamic_dt250_a_ucx2
  # Auto-creates swept_sine_fr_out/beyerdynamic_dt250_a_ucx2_L/
  # Play sweep_raw_*.wav and sweep_cal_*.wav in Reaper, record each
  # via B&K mic on RME input 1.
  python utils/swept_sine_fr.py --mode analyze \\
      --render-dir swept_sine_fr_out/beyerdynamic_dt250_a_ucx2_L \\
      --rec-raw <rec_raw_path>.wav --rec-cal <rec_cal_path>.wav \\
      --mic-cal <path-to-B&K-cal-file>.cal

Each plot is accompanied by a .txt summary file with the same base name.

Files written per run
---------------------
  swept_sine_fr_out/<profile>_<channel>/
    sweep_ref.wav                       (mono reference, deconv input)
    sweep_raw_<profile>_<channel>.wav   (stereo, bypass)
    sweep_cal_<profile>_<channel>.wav   (stereo, calibrated)
    render_meta.json                    (sweep params + paths)
    analyze_fr_<channel>_<ts>.png       (plot, created by analyze/online)
    analyze_fr_<channel>_<ts>.txt       (text summary)

Override the auto-subdir with --out-dir <path>.

TotalMix note
-------------
PsychoPy Sound plays into device channels 0/1 of the selected output
device. If your headphone amp is on RME physical outs 7+8, configure a
TotalMix workspace that routes software-out 1/2 to physical 7+8 and
save it. Lock the workspace before running so the gain doesn't drift
between bypass and cal measurements.

Acceptance criteria
-------------------
The cal'd curve should be within +/- tol_db (default 3) across the
analysis band (default 20 Hz - 16 kHz). The bypass curve is the raw
headphone response for visual comparison.

Plotted tolerance lines: +/-1 dB (always, dotted), +/-2 dB (always,
dashed), +/- user tolerance (default 3 dB, dash-dot).

Per-curve stats (printed, on plot, and in summary file):
  flatness (max - min)
  mean |deviation|
  rms deviation
  std deviation
  max and min deviation + their frequencies
  % of analysis band within +/-1, +/-2, +/-tolerance dB

Mic cal file
------------
B&K / RME .cal format: two-column CSV (freq_Hz, dB_deviation). Applied
by subtracting the interpolated cal value from the measured magnitude
(REW convention). Optional; bypass with --mic-cal "".

Scope (not under test by this script)
-------------------------------------
- SPL accuracy (use REW SPL logger + rms_analyzer + known amplitudes)
- PsychoPy Sound playback latency / sync (tested by paradigm runs)
- Per-channel gain math (this script passes per_channel_gain=None;
  test that path with PROLACTIN itself + the SPL verification workflow)

Cross-platform (Mac + Windows). Requires numpy, scipy, matplotlib,
sounddevice (online mode), psychopy (online mode).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve


# ---------------------------------------------------------------------------
# Import CalibrationManager from sibling utils/ regardless of CWD
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from calibration import CalibrationManager, CalibrationError  # noqa: E402


# ===========================================================================
# Defaults / constants
# ===========================================================================

DEFAULT_FS                = 48000
DEFAULT_SWEEP_DUR_S       = 5.0
DEFAULT_SWEEP_F_LOW_HZ    = 20.0
DEFAULT_SWEEP_F_HIGH_HZ   = 20000.0
DEFAULT_SILENCE_PRE_S     = 0.5
DEFAULT_SILENCE_POST_S    = 1.0
DEFAULT_SWEEP_LEVEL_DBFS  = -20.0
DEFAULT_TOLERANCE_DB      = 3.0
DEFAULT_NORMALIZE_BAND_HZ = (200.0, 8000.0)
DEFAULT_ANALYSIS_BAND_HZ  = (20.0, 16000.0)
DEFAULT_PLOT_FREQ_RANGE   = (20.0, 20000.0)
DEFAULT_PLOT_DB_RANGE     = (-30.0, 10.0)
DEFAULT_SMOOTH_OCT_FRAC   = 1.0 / 6.0

# Tolerance bands always drawn on the plot, in addition to the
# user-configurable --tolerance-db (default 3.0).
ALWAYS_DRAWN_TOLERANCES_DB = (1.0, 2.0)

DEFAULT_CONFIG_PATH       = "../../calibration_data/calibration_config.json"
DEFAULT_OUT_DIR           = "swept_sine_fr_out"
DEFAULT_IN_DEVICE         = "Fireface UCX"
DEFAULT_OUT_DEVICE        = "Fireface UCX"
DEFAULT_IN_CHANNEL_1BASED = 1


# ===========================================================================
# Math primitives (no I/O)
# ===========================================================================

def gen_log_sweep(fs: int,
                  f1: float,
                  f2: float,
                  duration_s: float,
                  pre_silence_s: float = 0.0,
                  post_silence_s: float = 0.0) -> np.ndarray:
    """
    Generate a Farina log sweep with optional silence padding.

    Sweep formula (Farina 2000):
        s(t) = sin(2*pi*f1*T/R * (exp(R*t/T) - 1)), R = ln(f2/f1)

    The sweep is NOT level-scaled here -- caller is responsible for
    setting the playback level.

    Returns the 1D mono sweep including pre/post silence.
    """
    if f1 <= 0 or f2 <= 0 or f2 <= f1:
        raise ValueError(f"Invalid sweep range: {f1} Hz to {f2} Hz")

    N = int(round(fs * duration_s))
    t = np.arange(N, dtype=np.float64) / fs
    R = np.log(f2 / f1)
    phase = 2.0 * np.pi * f1 * duration_s / R * (np.exp(R * t / duration_s) - 1.0)
    sweep = np.sin(phase)

    # Short fade-in/out (5 ms) to kill click artifacts at sweep edges.
    fade_samps = int(0.005 * fs)
    if fade_samps > 0 and fade_samps * 2 < N:
        win = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade_samps) / fade_samps))
        sweep[:fade_samps] *= win
        sweep[-fade_samps:] *= win[::-1]

    pre = np.zeros(int(round(fs * pre_silence_s)), dtype=np.float64)
    post = np.zeros(int(round(fs * post_silence_s)), dtype=np.float64)
    return np.concatenate([pre, sweep, post])


def deconvolve_fr(recording: np.ndarray,
                  reference_sweep: np.ndarray,
                  fs: int,
                  analysis_band_hz: Tuple[float, float]
                  ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Frequency-domain deconvolution: recover the system FR from a sweep
    recording.

    Math:
        recording  = reference_sweep (*) h_system   (* = convolution)
        H_system(f) = FFT(recording) / FFT(reference_sweep)

    This is mathematically equivalent to Farina inverse-sweep convolution
    within the sweep band; the Farina formulation is just a regularization
    trick to handle band edges. For a 20 Hz - 20 kHz sweep analyzed over
    100 Hz - 10 kHz, direct division has no numerical issue inside the
    analysis band.

    Outside the analysis band, the result is dominated by noise floor
    and small denominators -- caller should restrict plotting/analysis
    to the analysis_band_hz.

    Returns
    -------
    freqs : 1D ndarray, Hz, rfft frequency grid
    mag_db : 1D ndarray, dB magnitude (unnormalized)
    """
    n_fft = int(2 ** np.ceil(np.log2(max(len(recording), len(reference_sweep)) * 2)))
    S = np.fft.rfft(reference_sweep, n_fft)
    R = np.fft.rfft(recording, n_fft)

    # Regularize denominator at frequencies where the sweep has near-zero
    # energy (= outside the sweep band).
    s_mag = np.abs(S)
    eps = 1e-6 * float(np.max(s_mag))
    S_safe = np.where(s_mag < eps, eps, S)
    H = R / S_safe

    freqs = np.fft.rfftfreq(n_fft, 1.0 / fs)
    mag_db = 20.0 * np.log10(np.abs(H) + 1e-30)
    return freqs, mag_db


def smooth_oct(freqs: np.ndarray,
               mag_db: np.ndarray,
               oct_frac: float,
               n_points: int = 512,
               f_min: Optional[float] = None,
               f_max: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fractional-octave smoothing by log-spaced bin averaging.

    For each output frequency f, average mag_db over [f / 2^(oct_frac/2),
    f * 2^(oct_frac/2)]. If no input bins fall in that range (e.g. very
    low f), nearest-neighbor is used.
    """
    if f_min is None:
        f_min = max(freqs[1], 10.0)  # skip DC
    if f_max is None:
        f_max = freqs[-1]

    out_freqs = np.logspace(np.log10(f_min), np.log10(f_max), n_points)
    out_db = np.zeros_like(out_freqs)
    factor = 2.0 ** (oct_frac / 2.0)
    for i, f in enumerate(out_freqs):
        lo, hi = f / factor, f * factor
        mask = (freqs >= lo) & (freqs <= hi)
        if mask.sum() > 0:
            out_db[i] = float(np.mean(mag_db[mask]))
        else:
            idx = int(np.argmin(np.abs(freqs - f)))
            out_db[i] = float(mag_db[idx])
    return out_freqs, out_db


def normalize_to_band(freqs: np.ndarray,
                      mag_db: np.ndarray,
                      band_hz: Tuple[float, float]) -> np.ndarray:
    """Subtract mean(mag_db within band) so curves overlay cleanly."""
    mask = (freqs >= band_hz[0]) & (freqs <= band_hz[1])
    if mask.sum() == 0:
        return mag_db
    return mag_db - float(np.mean(mag_db[mask]))


def flatness_db(freqs: np.ndarray,
                mag_db: np.ndarray,
                band_hz: Tuple[float, float]) -> float:
    """Max - min over band, in dB. Lower is flatter. Kept for back-compat;
    compute_stats() returns this plus more."""
    mask = (freqs >= band_hz[0]) & (freqs <= band_hz[1])
    if mask.sum() == 0:
        return float("nan")
    return float(np.max(mag_db[mask]) - np.min(mag_db[mask]))


def compute_stats(freqs: np.ndarray,
                  mag_db: np.ndarray,
                  band_hz: Tuple[float, float],
                  tol_levels_db: Tuple[float, ...] = (1.0, 2.0, 3.0)
                  ) -> Dict:
    """
    Deviation statistics over a frequency band.

    `mag_db` is assumed to already be normalized (e.g. to mean of 0
    over the normalize band). Stats are computed against that 0-reference
    so positive numbers = peaks, negative = dips.

    Returns a dict:
      flatness_db     max - min in band (dB)
      mean_abs_db     mean(|mag|) in band - average absolute deviation
      rms_db          sqrt(mean(mag**2)) in band
      std_db          std(mag) in band - how much the curve "wiggles"
      max_db, max_freq    largest positive deviation + its freq
      min_db, min_freq    largest negative deviation + its freq
      pct_within      dict mapping tolerance (dB) -> percent of bins
                      where |mag| <= tolerance
    """
    mask = (freqs >= band_hz[0]) & (freqs <= band_hz[1])
    if mask.sum() == 0:
        return {"flatness_db": float("nan"), "mean_abs_db": float("nan"),
                "rms_db": float("nan"), "std_db": float("nan"),
                "max_db": float("nan"), "max_freq": float("nan"),
                "min_db": float("nan"), "min_freq": float("nan"),
                "pct_within": {tol: float("nan") for tol in tol_levels_db}}

    band_db = mag_db[mask]
    band_freqs = freqs[mask]
    max_idx = int(np.argmax(band_db))
    min_idx = int(np.argmin(band_db))

    return {
        "flatness_db": float(band_db.max() - band_db.min()),
        "mean_abs_db": float(np.mean(np.abs(band_db))),
        "rms_db":      float(np.sqrt(np.mean(band_db ** 2))),
        "std_db":      float(np.std(band_db)),
        "max_db":      float(band_db[max_idx]),
        "max_freq":    float(band_freqs[max_idx]),
        "min_db":      float(band_db[min_idx]),
        "min_freq":    float(band_freqs[min_idx]),
        "pct_within":  {float(tol): float(np.mean(np.abs(band_db) <= tol) * 100.0)
                        for tol in tol_levels_db},
    }


# ===========================================================================
# Mic calibration file (B&K / RME .cal format)
# ===========================================================================

def load_mic_cal(path: Optional[Path]) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """
    Parse a two-column .cal file: freq_Hz, dB_deviation.

    Returns (freqs, dB) or None if path is None / empty. Skips blank
    lines and lines that don't parse as numbers (treats them as headers).
    """
    if path is None or str(path) == "":
        return None
    path = Path(path)
    if not path.is_file():
        warnings.warn(f"Mic cal file not found: {path}. Skipping mic correction.",
                      stacklevel=2)
        return None

    freqs = []
    dbs = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.replace(",", " ").split()
            if len(parts) < 2:
                continue
            try:
                fr = float(parts[0])
                db = float(parts[1])
            except ValueError:
                continue
            freqs.append(fr)
            dbs.append(db)

    if not freqs:
        warnings.warn(f"Mic cal file {path} parsed empty. Skipping.",
                      stacklevel=2)
        return None
    return np.asarray(freqs), np.asarray(dbs)


def apply_mic_cal(freqs: np.ndarray,
                  mag_db: np.ndarray,
                  cal_data: Optional[Tuple[np.ndarray, np.ndarray]]
                  ) -> np.ndarray:
    """
    Subtract the interpolated mic correction from measured magnitude
    (REW convention: cal file represents mic's deviation from flat).

    Out-of-range frequencies (below/above the cal file's coverage) use
    the nearest end value (clamp, not extrapolate).
    """
    if cal_data is None:
        return mag_db
    cal_freqs, cal_db = cal_data
    correction = np.interp(freqs, cal_freqs, cal_db,
                           left=cal_db[0], right=cal_db[-1])
    return mag_db - correction


# ===========================================================================
# I/O helpers
# ===========================================================================

def write_wav(path: Path, fs: int, samples: np.ndarray) -> None:
    """Write a float32 WAV. Clips to +/- 1 before writing (defensive)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.clip(samples, -1.0, 1.0).astype(np.float32)
    wavfile.write(str(path), int(fs), data)


def read_wav(path: Path,
             expected_fs: Optional[int] = None,
             channel: Optional[int] = None) -> Tuple[int, np.ndarray]:
    """
    Read a WAV file as float64 in [-1, 1].

    If `channel` is given and the file is multi-channel, that channel
    (0-indexed) is selected. Otherwise channel 0 is used for stereo.
    Raises if expected_fs is set and doesn't match the file.
    """
    fs, data = wavfile.read(str(path))
    if expected_fs is not None and fs != expected_fs:
        raise ValueError(f"{path}: fs={fs}, expected {expected_fs}")

    if np.issubdtype(data.dtype, np.integer):
        max_val = float(np.iinfo(data.dtype).max)
        data = data.astype(np.float64) / max_val
    else:
        data = data.astype(np.float64)

    if data.ndim == 2:
        ch = 0 if channel is None else int(channel)
        if ch >= data.shape[1]:
            raise ValueError(f"{path}: requested channel {ch} but file has "
                             f"{data.shape[1]} channels")
        data = data[:, ch]
    return fs, data


def channel_to_pan(channel: str) -> float:
    """L -> -1.0, R -> +1.0."""
    c = channel.strip().upper()
    if c == "L":
        return -1.0
    if c == "R":
        return +1.0
    raise ValueError(f"channel must be 'L' or 'R', got {channel!r}")


# ===========================================================================
# Device discovery (sounddevice)
# ===========================================================================

def list_devices() -> None:
    """Print a numbered list of audio devices. Used by --list-devices."""
    import sounddevice as sd
    print(sd.query_devices())


def find_device(name_substr: str, kind: str) -> Optional[int]:
    """
    Return the index of the first device whose name contains `name_substr`
    (case-insensitive) and that has channels of the requested kind.

    kind: 'input' or 'output'.
    Returns None if no match.
    """
    if not name_substr:
        return None
    import sounddevice as sd
    name_substr_lo = name_substr.lower()
    for idx, dev in enumerate(sd.query_devices()):
        if name_substr_lo not in dev["name"].lower():
            continue
        if kind == "input" and dev["max_input_channels"] > 0:
            return idx
        if kind == "output" and dev["max_output_channels"] > 0:
            return idx
    return None


def select_devices_interactively() -> Tuple[str, str]:
    """
    Print the device list and prompt the user for input and output device
    indices. Validates that the chosen device has channels of the right
    kind. Returns (in_name, out_name) so callers can pass names downstream
    (sounddevice and PsychoPy both accept name substring).
    """
    import sounddevice as sd
    print("\nAvailable audio devices:")
    print(sd.query_devices())
    print()

    def _prompt(prompt: str, kind: str) -> Tuple[int, str]:
        chan_key = "max_input_channels" if kind == "input" \
                   else "max_output_channels"
        while True:
            raw = input(prompt).strip()
            try:
                idx = int(raw)
                dev = sd.query_devices(idx)
            except (ValueError, IndexError):
                print(f"  '{raw}' is not a valid device index. Try again.")
                continue
            if dev[chan_key] == 0:
                print(f"  Device {idx} ({dev['name']}) has no {kind} "
                      f"channels. Try again.")
                continue
            return idx, dev["name"]

    in_idx, in_name = _prompt("Input device index:  ", "input")
    out_idx, out_name = _prompt("Output device index: ", "output")
    print()
    print(f"Selected input:  [{in_idx}] {in_name}")
    print(f"Selected output: [{out_idx}] {out_name}")
    return in_name, out_name


def resolve_devices(args) -> Tuple[str, str]:
    """
    Resolve the input and output device names based on CLI flags.

    Precedence:
      1. --set-interface  -> prompt interactively
      2. otherwise        -> use --in-device / --out-device (default
                             "Fireface UCX" substring match)

    Raises RuntimeError if a default / explicit device string does not
    match any device of the appropriate kind (so the user doesn't
    silently fall back to the system default mic/speakers).
    """
    if args.set_interface:
        return select_devices_interactively()

    import sounddevice as sd
    in_idx = find_device(args.in_device, "input")
    out_idx = find_device(args.out_device, "output")
    if in_idx is None:
        raise RuntimeError(
            f"No input device matches '{args.in_device}'. "
            f"Run with --list-devices to see options, then re-run with "
            f"--in-device <substring> or --set-interface."
        )
    if out_idx is None:
        raise RuntimeError(
            f"No output device matches '{args.out_device}'. "
            f"Run with --list-devices to see options, then re-run with "
            f"--out-device <substring> or --set-interface."
        )
    in_name = sd.query_devices(in_idx)["name"]
    out_name = sd.query_devices(out_idx)["name"]
    print(f"  resolved input:  [{in_idx}] {in_name}")
    print(f"  resolved output: [{out_idx}] {out_name}")
    return in_name, out_name


def resolve_out_dir(args, profile_name: str) -> Path:
    """
    Resolve the output directory for render / online modes.

    - If --out-dir is given explicitly, use it as-is.
    - Otherwise, return DEFAULT_OUT_DIR / "<profile>_<channel>/" so
      different headphone runs don't clobber each other.
    """
    if args.out_dir is not None:
        return Path(args.out_dir)
    return Path(DEFAULT_OUT_DIR) / f"{profile_name}_{args.channel.upper()}"


# ===========================================================================
# Audio capture (online mode): record via sounddevice, play via PsychoPy
# ===========================================================================

def play_and_record(stereo: np.ndarray,
                    fs: int,
                    in_device_name: str,
                    out_device_name: str,
                    in_channel_1based: int,
                    rec_extra_s: float = 0.5) -> np.ndarray:
    """
    Play a stereo buffer via PsychoPy Sound and record simultaneously
    via sounddevice. Returns the 1D mono recording.

    Recording duration = playback duration + rec_extra_s (captures any
    acoustic tail).

    Sounddevice's record is started first (non-blocking); PsychoPy Sound
    is then triggered. The pre-silence in the sweep absorbs the small
    jitter between record-start and play-trigger (typically << 50 ms).

    Caller should have already validated that in_device_name and
    out_device_name match real devices (e.g. via resolve_devices()).
    """
    import sounddevice as sd

    n_samples = stereo.shape[0]
    play_dur_s = n_samples / fs
    rec_dur_s = play_dur_s + rec_extra_s
    rec_n = int(round(rec_dur_s * fs))

    in_dev_idx = find_device(in_device_name, "input")
    print(f"  record device: idx={in_dev_idx} "
          f"({sd.query_devices(in_dev_idx)['name']}) "
          f"ch={in_channel_1based}")

    # Configure PsychoPy device by name BEFORE importing sound.
    # Already-imported case: setting prefs.hardware.audioDevice is best-effort.
    from psychopy import prefs as _prefs
    _prefs.hardware["audioLib"] = ["PTB"]
    if out_device_name:
        _prefs.hardware["audioDevice"] = out_device_name
        print(f"  play device: '{out_device_name}' (substring match)")
    from psychopy import sound as _ps_sound
    import psychtoolbox as ptb
    import psychopy.core as core

    # Start recording (non-blocking).
    rec = sd.rec(rec_n,
                 samplerate=fs,
                 channels=1,
                 mapping=[in_channel_1based],
                 device=in_dev_idx,
                 dtype="float64")

    # Build Sound and play.
    snd = _ps_sound.Sound(value=stereo.astype(np.float32),
                          sampleRate=fs,
                          stereo=True,
                          secs=play_dur_s,
                          hamming=False)
    # Small lead-in so PsychoPy is fully ready when recording is rolling.
    time.sleep(0.05)
    now = ptb.GetSecs()
    snd.play(when=now)
    # Wait for playback (PTB scheduling margin + a hair).
    core.wait(play_dur_s + 0.1)

    # Wait for recording to finish.
    sd.wait()
    return rec[:, 0].astype(np.float64)


# ===========================================================================
# Render mode: write WAVs for offline DAW playback
# ===========================================================================

def render_sweeps(calibration: CalibrationManager,
                  fs: int,
                  f1: float,
                  f2: float,
                  duration_s: float,
                  pre_silence_s: float,
                  post_silence_s: float,
                  sweep_level_dbfs: float,
                  channel: str,
                  out_dir: Path) -> Dict[str, Path]:
    """
    Generate the sweep, build the raw + cal stereo buffers, write all
    files plus render_meta.json. Returns a dict of paths.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Mono reference sweep (no calibration, no pan).
    sweep_level = 10.0 ** (sweep_level_dbfs / 20.0)
    sweep_mono = sweep_level * gen_log_sweep(fs, f1, f2, duration_s,
                                             pre_silence_s, post_silence_s)

    pan = channel_to_pan(channel)

    # Raw stereo (bypass): manual pan, no calibration math.
    raw_stereo = np.zeros((len(sweep_mono), 2), dtype=np.float64)
    if pan < 0:
        raw_stereo[:, 0] = sweep_mono
    else:
        raw_stereo[:, 1] = sweep_mono

    # Calibrated stereo: production pipeline.
    cal_stereo = calibration.prepare_samples(sweep_mono, fs,
                                             pan=pan,
                                             per_channel_gain=None)

    # Peak diagnostics.
    raw_peak = float(np.max(np.abs(raw_stereo)))
    cal_peak = float(np.max(np.abs(cal_stereo)))
    print(f"  raw peak: {raw_peak:.4f}  ({20*np.log10(raw_peak + 1e-30):+.2f} dB FS)")
    print(f"  cal peak: {cal_peak:.4f}  ({20*np.log10(cal_peak + 1e-30):+.2f} dB FS)")
    if cal_peak >= 0.999:
        print("  *** WARNING: cal peak hit clip guard. Lower --sweep-level-dbfs ***")

    # File paths. Stereo sweep WAVs include the profile + channel so the
    # filenames are self-describing if they get moved out of the run dir
    # (e.g. dragged into Reaper). Reference sweep + meta keep fixed names
    # since they only ever live inside this run dir.
    profile = calibration.active_profile
    chan = channel.upper()
    p_ref = out_dir / "sweep_ref.wav"
    p_raw = out_dir / f"sweep_raw_{profile}_{chan}.wav"
    p_cal = out_dir / f"sweep_cal_{profile}_{chan}.wav"
    p_meta = out_dir / "render_meta.json"

    write_wav(p_ref, fs, sweep_mono)
    write_wav(p_raw, fs, raw_stereo)
    write_wav(p_cal, fs, cal_stereo)

    meta = {
        "fs": fs,
        "channel": channel.upper(),
        "f1_hz": f1,
        "f2_hz": f2,
        "duration_s": duration_s,
        "pre_silence_s": pre_silence_s,
        "post_silence_s": post_silence_s,
        "sweep_level_dbfs": sweep_level_dbfs,
        "calibration_config_path": str(calibration._config_path),
        "calibration_profile": calibration.active_profile,
        "fir_calibrated": calibration.fir_calibrated,
        "raw_peak": raw_peak,
        "cal_peak": cal_peak,
        "sweep_ref_wav": p_ref.name,
        "sweep_raw_wav": p_raw.name,
        "sweep_cal_wav": p_cal.name,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    with open(p_meta, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"  wrote: {p_ref.name}, {p_raw.name}, {p_cal.name}, {p_meta.name}")
    return {"ref": p_ref, "raw": p_raw, "cal": p_cal, "meta": p_meta}


# ===========================================================================
# Plotting
# ===========================================================================

def plot_overlay(curves: List[Dict],
                 out_path: Path,
                 tolerance_db: float,
                 normalize_band_hz: Tuple[float, float],
                 analysis_band_hz: Tuple[float, float],
                 plot_freq_range: Tuple[float, float],
                 plot_db_range: Tuple[float, float],
                 title_extra: str = "") -> None:
    """
    Overlay one or more FR curves on a single log-frequency plot.

    Each `curves` entry: {'label', 'freqs', 'mag_db', 'stats'}.
    Stats are rendered as a small text box per curve in the upper-right.

    Tolerance bands drawn (from tightest to loosest):
      +/-1 dB   (always)
      +/-2 dB   (always)
      +/-tolerance_db (user-configurable; default 3.0)
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # --------------------------------------------------------------
    # Plot curves
    # --------------------------------------------------------------

    curve_handles = []
    curve_labels = []
    curve_colors = []

    for c in curves:
        line, = ax.semilogx(
            c["freqs"],
            c["mag_db"],
            label=c["label"],
            linewidth=1.6,
        )

        curve_handles.append(line)
        curve_labels.append(c["label"])
        curve_colors.append(line.get_color())

    # --------------------------------------------------------------
    # Tolerance bands
    # --------------------------------------------------------------

    tol_handles = []
    tol_labels = []

    all_tols = sorted(
        set(list(ALWAYS_DRAWN_TOLERANCES_DB) + [tolerance_db])
    )

    styles = {
        1.0: ("0.78", ":",  0.9),
        2.0: ("0.62", "--", 1.0),
        3.0: ("0.45", "-.", 1.0),
    }

    for tol in all_tols:

        color, ls, lw = styles.get(
            tol,
            ("0.35", "-.", 1.2)
        )

        label = f"+/-{tol:.1f} dB tolerance"

        # Positive line gets legend label
        line = ax.axhline(
            +tol,
            color=color,
            linestyle=ls,
            linewidth=lw,
            label=label,
        )

        # Negative line does NOT get legend label
        ax.axhline(
            -tol,
            color=color,
            linestyle=ls,
            linewidth=lw,
        )

        tol_handles.append(line)
        tol_labels.append(label)

    ax.axhline(
        0,
        color="0.88",
        linestyle="-",
        linewidth=0.6,
    )

    # --------------------------------------------------------------
    # Analysis-band shading
    # --------------------------------------------------------------

    ax.axvspan(
        analysis_band_hz[0],
        analysis_band_hz[1],
        alpha=0.05,
        color="green",
    )

    # --------------------------------------------------------------
    # Axes formatting
    # --------------------------------------------------------------

    ax.set_xlim(plot_freq_range)
    ax.set_ylim(plot_db_range)

    ax.set_xlabel("Frequency (Hz)")

    ax.set_ylabel(
        f"Magnitude (dB re mean over "
        f"{normalize_band_hz[0]:.0f}-"
        f"{normalize_band_hz[1]:.0f} Hz)"
    )

    title = (
        f"swept_sine_fr  "
        f"{datetime.now().isoformat(timespec='seconds')}"
    )

    if title_extra:
        title += f"\n{title_extra}"

    ax.set_title(title, fontsize=10)

    ax.grid(True, which="both", alpha=0.3)

    # --------------------------------------------------------------
    # Legends
    # --------------------------------------------------------------

    # # Curve legend (bottom-left)
    # leg_curves = ax.legend(
    #     curve_handles,
    #     curve_labels,
    #     loc="lower left",
    #     fontsize=9,
    #     framealpha=0.9,
    # )

    # Tolerance legend (bottom-center, single row)
    leg_tols = ax.legend(
        tol_handles,
        tol_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.005),
        ncol=len(tol_labels),
        fontsize=9,
        framealpha=0.9,
        columnspacing=1.5,
        handlelength=2.8,
    )

    # Keep both legends
    # ax.add_artist(leg_curves)

    # --------------------------------------------------------------
    # Per-curve stats boxes
    #
    # Place first curve bottom-left, second curve bottom-right
    # so they stay out of the main data region.
    # --------------------------------------------------------------

    stats_positions = [
        (0.015, 0.09, "left"),   # bottom-left
        (0.985, 0.09, "right"),  # bottom-right
    ]

    for i, (c, color) in enumerate(zip(curves, curve_colors)):

        s = c["stats"]

        pct_text = "  ".join(
            f"+/-{tol:.1f}:{s['pct_within'][tol]:5.1f}%"
            for tol in sorted(s["pct_within"].keys())
        )

        text = (
            f"{c['label']}\n"
            f"  flatness:   {s['flatness_db']:6.2f} dB\n"
            f"  mean |dev|: {s['mean_abs_db']:6.2f} dB\n"
            f"  std:        {s['std_db']:6.2f} dB\n"
            f"  max: {s['max_db']:+6.2f} dB @ {s['max_freq']:6.0f} Hz\n"
            f"  min: {s['min_db']:+6.2f} dB @ {s['min_freq']:6.0f} Hz\n"
            f"  {pct_text}"
        )

        # Fallback if more than 2 curves
        if i < len(stats_positions):
            x, y, ha = stats_positions[i]
        else:
            x, y, ha = (0.985, 0.98 - i * 0.23, "right")

        ax.text(
            x, y, text,
            transform=ax.transAxes,
            fontsize=7.5,
            family="monospace",
            ha=ha,
            va="bottom",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor="white",
                alpha=0.85,
                edgecolor=color,
                linewidth=1.2,
            ),
        )

    fig.tight_layout(rect=[0, 0.08, 1, 1])
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"  plot: {out_path}")


def write_summary(curves: List[Dict],
                  out_path: Path,
                  run_info: Dict) -> None:
    """
    Write a human-readable text companion to the PNG plot. Same base
    name, .txt extension.

    `run_info` keys (all optional):
      mode, profile, channel, config_path, mic_cal_path,
      sweep_f1_hz, sweep_f2_hz, sweep_duration_s, sweep_level_dbfs,
      analysis_band_hz, normalize_band_hz, tolerance_db, smooth_oct_frac,
      timestamp
    """
    lines = []
    lines.append("swept_sine_fr - measurement summary")
    lines.append("=" * 52)
    for key in ("timestamp", "mode", "profile", "channel",
                "config_path", "mic_cal_path"):
        if key in run_info:
            lines.append(f"{key:20s}  {run_info[key]}")
    lines.append("")
    lines.append("Sweep / analysis params")
    lines.append("-" * 52)
    for key in ("sweep_f1_hz", "sweep_f2_hz", "sweep_duration_s",
                "sweep_level_dbfs", "analysis_band_hz",
                "normalize_band_hz", "tolerance_db", "smooth_oct_frac"):
        if key in run_info:
            lines.append(f"{key:20s}  {run_info[key]}")
    lines.append("")
    lines.append("Results")
    lines.append("=" * 52)

    band_str = ""
    if "analysis_band_hz" in run_info:
        b = run_info["analysis_band_hz"]
        band_str = f" (analysis band {b[0]:.0f}-{b[1]:.0f} Hz)"

    for c in curves:
        s = c["stats"]
        lines.append(f"\n{c['label']}{band_str}")
        lines.append("-" * 52)
        lines.append(f"  flatness (max-min): {s['flatness_db']:7.2f} dB")
        lines.append(f"  mean |deviation|:   {s['mean_abs_db']:7.2f} dB")
        lines.append(f"  rms deviation:      {s['rms_db']:7.2f} dB")
        lines.append(f"  std deviation:      {s['std_db']:7.2f} dB")
        lines.append(f"  max: {s['max_db']:+7.2f} dB @ {s['max_freq']:7.1f} Hz")
        lines.append(f"  min: {s['min_db']:+7.2f} dB @ {s['min_freq']:7.1f} Hz")
        lines.append(f"  % of analysis band within tolerance:")
        for tol in sorted(s["pct_within"].keys()):
            lines.append(f"     +/- {tol:.1f} dB:  "
                         f"{s['pct_within'][tol]:5.1f} %")

    # If both bypass and cal curves are present, show the improvement.
    by_label = {c["label"]: c for c in curves}
    cal_keys = [k for k in by_label if "calibrated" in k.lower()]
    bypass_keys = [k for k in by_label if "bypass" in k.lower()]
    if cal_keys and bypass_keys:
        cal = by_label[cal_keys[0]]["stats"]
        byp = by_label[bypass_keys[0]]["stats"]
        delta_flat = byp["flatness_db"] - cal["flatness_db"]
        delta_mean = byp["mean_abs_db"] - cal["mean_abs_db"]
        lines.append("")
        lines.append("Calibration improvement (bypass - calibrated)")
        lines.append("-" * 52)
        lines.append(f"  delta flatness:    {delta_flat:+7.2f} dB "
                     f"(positive = cal is flatter)")
        lines.append(f"  delta mean |dev|:  {delta_mean:+7.2f} dB")

    text = "\n".join(lines) + "\n"
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(text)
    print(f"  summary: {out_path}")


# ===========================================================================
# Recording -> smoothed normalized FR (shared by online and analyze)
# ===========================================================================

def recording_to_curve(recording: np.ndarray,
                       reference_sweep: np.ndarray,
                       fs: int,
                       mic_cal: Optional[Tuple[np.ndarray, np.ndarray]],
                       analysis_band_hz: Tuple[float, float],
                       normalize_band_hz: Tuple[float, float],
                       smooth_oct_frac: float,
                       label: str,
                       tolerance_db: float) -> Dict:
    """
    Full pipeline: deconvolve -> mic-cal-correct -> smooth -> normalize ->
    compute stats. Prints a concise per-curve summary.

    Returns a dict ready to feed into plot_overlay and write_summary:
      {'label', 'freqs', 'mag_db', 'stats'}
    where 'stats' is the output of compute_stats().
    """
    freqs_raw, mag_raw = deconvolve_fr(recording, reference_sweep, fs,
                                       analysis_band_hz)
    mag_raw = apply_mic_cal(freqs_raw, mag_raw, mic_cal)

    # Smooth onto a log-spaced grid.
    freqs_smooth, mag_smooth = smooth_oct(
        freqs_raw, mag_raw, smooth_oct_frac,
        f_min=max(analysis_band_hz[0] / 2.0, 10.0),
        f_max=min(analysis_band_hz[1] * 2.0, fs / 2.0),
    )

    # Normalize on the smoothed curve (mean over normalize band -> 0 dB).
    mag_norm = normalize_to_band(freqs_smooth, mag_smooth, normalize_band_hz)

    stats = compute_stats(freqs_smooth, mag_norm, analysis_band_hz,
                          tol_levels_db=tuple(list(ALWAYS_DRAWN_TOLERANCES_DB) +
                                              [tolerance_db]))

    band = analysis_band_hz
    print(f"  {label:18s} over {band[0]:.0f}-{band[1]:.0f} Hz:")
    print(f"     flatness:    {stats['flatness_db']:6.2f} dB (max-min)")
    print(f"     mean |dev|:  {stats['mean_abs_db']:6.2f} dB")
    print(f"     std:         {stats['std_db']:6.2f} dB")
    print(f"     max:        {stats['max_db']:+6.2f} dB @ "
          f"{stats['max_freq']:5.0f} Hz")
    print(f"     min:        {stats['min_db']:+6.2f} dB @ "
          f"{stats['min_freq']:5.0f} Hz")
    tols_sorted = sorted(stats["pct_within"].keys())
    for tol in tols_sorted:
        print(f"     within +/-{tol:.1f} dB: "
              f"{stats['pct_within'][tol]:5.1f}% of band")

    return {"label": label, "freqs": freqs_smooth, "mag_db": mag_norm,
            "stats": stats}


# ===========================================================================
# Mode: online
# ===========================================================================

def run_online(args, calibration: CalibrationManager) -> None:
    """Generate + play + record + analyze, all in Python."""
    fs = DEFAULT_FS
    if calibration.sample_rate != fs:
        raise RuntimeError(f"Calibration profile fs={calibration.sample_rate} "
                           f"!= script fs={fs}. Aborting.")

    # Resolve audio devices up front (interactive or substring).
    print("[online] resolving audio devices ...")
    in_device, out_device = resolve_devices(args)

    print("[online] generating sweep ...")
    sweep_level = 10.0 ** (args.sweep_level_dbfs / 20.0)
    sweep_mono = sweep_level * gen_log_sweep(fs, args.f_low, args.f_high,
                                             args.sweep_dur,
                                             args.silence_pre,
                                             args.silence_post)
    pan = channel_to_pan(args.channel)

    # Build stereo buffers.
    raw_stereo = np.zeros((len(sweep_mono), 2), dtype=np.float64)
    if pan < 0:
        raw_stereo[:, 0] = sweep_mono
    else:
        raw_stereo[:, 1] = sweep_mono
    cal_stereo = calibration.prepare_samples(sweep_mono, fs,
                                             pan=pan,
                                             per_channel_gain=None)

    raw_peak = float(np.max(np.abs(raw_stereo)))
    cal_peak = float(np.max(np.abs(cal_stereo)))
    print(f"  raw peak {raw_peak:.3f} | cal peak {cal_peak:.3f}")
    if cal_peak >= 0.999:
        print("  *** WARNING: cal peak at clip. Lower --sweep-level-dbfs. ***")

    out_dir = resolve_out_dir(args, calibration.active_profile)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[online] output -> {out_dir}")

    # Which to play?
    if args.bypass_only and args.cal_only:
        raise ValueError("--bypass-only and --cal-only are mutually exclusive")
    if args.bypass_only:
        plays = [("raw", raw_stereo)]
    elif args.cal_only:
        plays = [("cal", cal_stereo)]
    else:
        # Default (and explicit --compare): both, in bypass -> cal order.
        plays = [("raw", raw_stereo), ("cal", cal_stereo)]

    mic_cal = load_mic_cal(args.mic_cal if args.mic_cal else None)

    curves = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for label, stereo in plays:
        print(f"[online] playing+recording '{label}' ...")
        rec = play_and_record(stereo, fs,
                              in_device_name=in_device,
                              out_device_name=out_device,
                              in_channel_1based=args.in_channel)
        rec_path = out_dir / f"online_{label}_{args.channel.upper()}_{timestamp}.wav"
        write_wav(rec_path, fs, rec)
        print(f"  recording -> {rec_path.name}")
        curves.append(recording_to_curve(
            rec, sweep_mono, fs, mic_cal,
            (args.analysis_low, args.analysis_high),
            (args.norm_low, args.norm_high),
            args.smooth_oct,
            label=("bypass (no cal)" if label == "raw" else "calibrated"),
            tolerance_db=args.tolerance_db,
        ))

    plot_path = out_dir / f"online_fr_{args.channel.upper()}_{timestamp}.png"
    title_extra = (f"profile: {calibration.active_profile} | "
                   f"channel: {args.channel.upper()} | "
                   f"sweep {args.f_low:.0f}-{args.f_high:.0f} Hz")
    plot_overlay(curves, plot_path,
                 tolerance_db=args.tolerance_db,
                 normalize_band_hz=(args.norm_low, args.norm_high),
                 analysis_band_hz=(args.analysis_low, args.analysis_high),
                 plot_freq_range=DEFAULT_PLOT_FREQ_RANGE,
                 plot_db_range=DEFAULT_PLOT_DB_RANGE,
                 title_extra=title_extra)
    write_summary(curves, plot_path.with_suffix(".txt"), {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": "online",
        "profile": calibration.active_profile,
        "channel": args.channel.upper(),
        "config_path": str(args.config),
        "mic_cal_path": args.mic_cal or "(none)",
        "sweep_f1_hz": args.f_low,
        "sweep_f2_hz": args.f_high,
        "sweep_duration_s": args.sweep_dur,
        "sweep_level_dbfs": args.sweep_level_dbfs,
        "analysis_band_hz": (args.analysis_low, args.analysis_high),
        "normalize_band_hz": (args.norm_low, args.norm_high),
        "tolerance_db": args.tolerance_db,
        "smooth_oct_frac": args.smooth_oct,
    })


# ===========================================================================
# Mode: render
# ===========================================================================

def run_render(args, calibration: CalibrationManager) -> None:
    """Write the WAVs for offline DAW playback. No playback or recording."""
    fs = DEFAULT_FS
    if calibration.sample_rate != fs:
        raise RuntimeError(f"Calibration profile fs={calibration.sample_rate} "
                           f"!= script fs={fs}. Aborting.")

    out_dir = resolve_out_dir(args, calibration.active_profile)
    print(f"[render] writing sweeps to {out_dir} ...")
    paths = render_sweeps(calibration, fs,
                          f1=args.f_low,
                          f2=args.f_high,
                          duration_s=args.sweep_dur,
                          pre_silence_s=args.silence_pre,
                          post_silence_s=args.silence_post,
                          sweep_level_dbfs=args.sweep_level_dbfs,
                          channel=args.channel,
                          out_dir=out_dir)
    profile = calibration.active_profile
    chan = args.channel.upper()
    rec_raw_name = f"rec_raw_{profile}_{chan}.wav"
    rec_cal_name = f"rec_cal_{profile}_{chan}.wav"
    print()
    print("Next steps:")
    print(f"  1. In Reaper (or any DAW): play {paths['raw'].name} through")
    print(f"     your calibrated playback chain (RME UCX II out -> headphones")
    print(f"     -> B&K 4153 coupler). Record the B&K mic on RME input ch 1.")
    print(f"     Save the recording as e.g. {rec_raw_name}.")
    print(f"  2. Repeat for {paths['cal'].name}. Save as {rec_cal_name}.")
    print(f"  3. Run:")
    print(f"     python utils/swept_sine_fr.py --mode analyze \\")
    print(f"         --render-dir {out_dir} \\")
    print(f"         --rec-raw <path-to>/{rec_raw_name} \\")
    print(f"         --rec-cal <path-to>/{rec_cal_name} \\")
    print(f"         --mic-cal <path-to-mic-cal-file>.cal")
    print(f"     (omit --mic-cal if you don't want mic FR correction applied)")


# ===========================================================================
# Mode: analyze
# ===========================================================================

def run_analyze(args) -> None:
    """Load recordings + render metadata, deconvolve, plot."""
    if args.render_dir is None:
        raise ValueError(
            "--mode analyze requires --render-dir <path>. "
            "Use the path printed by render mode's 'Next steps' output."
        )
    render_dir = Path(args.render_dir)
    meta_path = render_dir / "render_meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Missing render_meta.json in {render_dir}. "
                                f"Did you run --mode render first?")
    with open(meta_path) as f:
        meta = json.load(f)
    fs = int(meta["fs"])
    print(f"[analyze] render meta: fs={fs} Hz, channel={meta['channel']}, "
          f"profile={meta['calibration_profile']}, "
          f"sweep {meta['f1_hz']}-{meta['f2_hz']} Hz x {meta['duration_s']}s")

    # Load reference sweep (mono).
    sweep_ref_path = render_dir / meta["sweep_ref_wav"]
    fs_ref, sweep_mono = read_wav(sweep_ref_path, expected_fs=fs)
    print(f"  loaded sweep ref: {sweep_ref_path.name} ({len(sweep_mono)} samples)")

    mic_cal = load_mic_cal(args.mic_cal if args.mic_cal else None)

    curves = []
    if args.rec_raw:
        rec_fs, rec = read_wav(Path(args.rec_raw), expected_fs=fs,
                               channel=args.rec_channel)
        print(f"  loaded rec_raw: {args.rec_raw} ({len(rec)} samples)")
        curves.append(recording_to_curve(
            rec, sweep_mono, fs, mic_cal,
            (args.analysis_low, args.analysis_high),
            (args.norm_low, args.norm_high),
            args.smooth_oct,
            label="bypass (no cal)",
            tolerance_db=args.tolerance_db,
        ))
    if args.rec_cal:
        rec_fs, rec = read_wav(Path(args.rec_cal), expected_fs=fs,
                               channel=args.rec_channel)
        print(f"  loaded rec_cal: {args.rec_cal} ({len(rec)} samples)")
        curves.append(recording_to_curve(
            rec, sweep_mono, fs, mic_cal,
            (args.analysis_low, args.analysis_high),
            (args.norm_low, args.norm_high),
            args.smooth_oct,
            label="calibrated",
            tolerance_db=args.tolerance_db,
        ))
    if not curves:
        raise ValueError("analyze mode requires --rec-raw and/or --rec-cal")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_path = render_dir / f"analyze_fr_{meta['channel']}_{timestamp}.png"
    title_extra = (f"profile: {meta['calibration_profile']} | "
                   f"channel: {meta['channel']} | "
                   f"sweep {meta['f1_hz']:.0f}-{meta['f2_hz']:.0f} Hz | "
                   f"offline DAW measurement")
    plot_overlay(curves, plot_path,
                 tolerance_db=args.tolerance_db,
                 normalize_band_hz=(args.norm_low, args.norm_high),
                 analysis_band_hz=(args.analysis_low, args.analysis_high),
                 plot_freq_range=DEFAULT_PLOT_FREQ_RANGE,
                 plot_db_range=DEFAULT_PLOT_DB_RANGE,
                 title_extra=title_extra)
    write_summary(curves, plot_path.with_suffix(".txt"), {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": "analyze",
        "profile": meta["calibration_profile"],
        "channel": meta["channel"],
        "config_path": meta.get("calibration_config_path", "(unknown)"),
        "mic_cal_path": args.mic_cal or "(none)",
        "sweep_f1_hz": meta["f1_hz"],
        "sweep_f2_hz": meta["f2_hz"],
        "sweep_duration_s": meta["duration_s"],
        "sweep_level_dbfs": meta["sweep_level_dbfs"],
        "analysis_band_hz": (args.analysis_low, args.analysis_high),
        "normalize_band_hz": (args.norm_low, args.norm_high),
        "tolerance_db": args.tolerance_db,
        "smooth_oct_frac": args.smooth_oct,
    })


# ===========================================================================
# main / argparse
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Headphone FR verification via swept sine + "
                    "CalibrationManager.prepare_samples()",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--mode", choices=("online", "render", "analyze"),
                   default="render",
                   help="online = Python-only loop; render = write WAVs for "
                        "offline DAW; analyze = process offline recordings")

    p.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                   help="Path to calibration_config.json")
    p.add_argument("--headphone", default=None,
                   help="Profile name (case-insensitive). If not given, "
                        "uses the config's active_profile. Examples: "
                        "akg_k271_mkii_k_ucx2, beyerdynamic_dt250_a_ucx2.")
    p.add_argument("--channel", default="L", choices=("L", "R"),
                   help="Channel under test")
    p.add_argument("--out-dir", default=None,
                   help="Output directory. If omitted, auto-creates "
                        f"{DEFAULT_OUT_DIR}/<profile>_<channel>/ to keep "
                        "different headphone runs separate.")

    # Sweep params
    p.add_argument("--sweep-dur", type=float, default=DEFAULT_SWEEP_DUR_S)
    p.add_argument("--f-low", type=float, default=DEFAULT_SWEEP_F_LOW_HZ)
    p.add_argument("--f-high", type=float, default=DEFAULT_SWEEP_F_HIGH_HZ)
    p.add_argument("--silence-pre", type=float, default=DEFAULT_SILENCE_PRE_S)
    p.add_argument("--silence-post", type=float, default=DEFAULT_SILENCE_POST_S)
    p.add_argument("--sweep-level-dbfs", type=float,
                   default=DEFAULT_SWEEP_LEVEL_DBFS,
                   help="Peak level of raw sweep in dB FS. Cal-mode sweep may "
                        "exceed this after IR convolution; lower if clip "
                        "guard fires.")

    # Analysis params
    p.add_argument("--norm-low", type=float, default=DEFAULT_NORMALIZE_BAND_HZ[0])
    p.add_argument("--norm-high", type=float, default=DEFAULT_NORMALIZE_BAND_HZ[1])
    p.add_argument("--analysis-low", type=float, default=DEFAULT_ANALYSIS_BAND_HZ[0])
    p.add_argument("--analysis-high", type=float, default=DEFAULT_ANALYSIS_BAND_HZ[1])
    p.add_argument("--tolerance-db", type=float, default=DEFAULT_TOLERANCE_DB)
    p.add_argument("--smooth-oct", type=float, default=DEFAULT_SMOOTH_OCT_FRAC,
                   help="Fractional-octave smoothing (e.g. 0.166 = 1/6 oct)")

    # Mic cal
    p.add_argument("--mic-cal", default="",
                   help="Path to two-column .cal file (freq_Hz, dB). "
                        "Empty = no mic correction.")

    # Online mode device options
    p.add_argument("--in-device", default=DEFAULT_IN_DEVICE,
                   help="Substring match for sounddevice input device")
    p.add_argument("--out-device", default=DEFAULT_OUT_DEVICE,
                   help="Substring match for PsychoPy audio output device")
    p.add_argument("--in-channel", type=int, default=DEFAULT_IN_CHANNEL_1BASED,
                   help="1-based input channel for recording")
    p.add_argument("--set-interface", action="store_true",
                   help="Online mode: print the device list and prompt "
                        "interactively for the input and output device "
                        "indices. Overrides --in-device / --out-device.")
    p.add_argument("--list-devices", action="store_true",
                   help="Print audio device list and exit")

    # Online-mode play selection
    p.add_argument("--compare", action="store_true",
                   help="Explicit alias for default behavior (play both "
                        "bypass and cal). Mutually exclusive with the "
                        "--*-only flags below.")
    p.add_argument("--bypass-only", action="store_true",
                   help="Online mode: play only the raw (bypass) sweep")
    p.add_argument("--cal-only", action="store_true",
                   help="Online mode: play only the calibrated sweep")

    # Analyze-mode inputs
    p.add_argument("--render-dir", default=None,
                   help="Analyze mode: path to the directory containing "
                        "render_meta.json + sweep_ref.wav (printed by render "
                        "mode's 'Next steps' output)")
    p.add_argument("--rec-raw", default="",
                   help="Analyze mode: WAV of the bypass recording")
    p.add_argument("--rec-cal", default="",
                   help="Analyze mode: WAV of the calibrated recording")
    p.add_argument("--rec-channel", type=int, default=0,
                   help="0-indexed channel to use from multi-channel "
                        "recording WAV (default: 0)")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_devices:
        list_devices()
        return 0

    print("=" * 70)
    print(" swept_sine_fr  --  mode:", args.mode)
    print("=" * 70)
    print(f"  TotalMix reminder: ensure RME software out 1/2 is routed to")
    print(f"  your headphone amp's physical outputs and the workspace is")
    print(f"  locked. Mismatched routing between runs will invalidate the")
    print(f"  comparison.")
    print()

    if args.mode in ("online", "render"):
        try:
            calibration = CalibrationManager(args.config,
                                             profile=args.headphone)
        except (FileNotFoundError, CalibrationError) as e:
            print(f"!!! Failed to load calibration: {e}")
            return 2
        calibration.summary()
        if not calibration.fir_calibrated:
            print("\n!!! Calibration has no FIR inverse filters loaded. This")
            print("!!! script's purpose is to verify those filters. Aborting.")
            return 3

    if args.mode == "online":
        run_online(args, calibration)
    elif args.mode == "render":
        run_render(args, calibration)
    elif args.mode == "analyze":
        run_analyze(args)
    else:
        raise ValueError(f"unknown mode {args.mode}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
