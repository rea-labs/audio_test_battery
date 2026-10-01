"""
rms_analyzer.py
---------------
Time-range RMS analysis for WAV files and REW V5 SPL meter log exports.

Two input modes (auto-detected by file extension):

  WAV (.wav)
    - Computes windowed RMS in dB FS over a selected time range.
    - Reports overall RMS, mean / min / max / std of windowed RMS,
      and sample peak (dB FS).

  REW SPL log (.txt)
    - Parses the columnar log REW writes from its SPL meter logger.
    - Uses the LCS (C-weighted slow) column as the level time series.
    - Reports stats in dB SPL. "Peak" here is the max of the LZpeak
      column (Z-weighted peak hold from the meter), NOT a sample peak.

Validation: out-of-range start/end/channel inputs are clamped to defaults
with a warning printed to stderr (per user spec).

Output: report printed to terminal; optionally written to a text file.
Optional interactive plot with a draggable time-range selector that
re-runs the analysis and reprints the report on each selection.

Designed to grow toward multi-channel / Ambisonic-B-format inputs later
without architectural rework -- see SourceInfo and the channel-mode notes
at the bottom of the file.

Usage examples:
    python utils/rms_analyzer.py                                # file picker + interactive GUI
    python utils/rms_analyzer.py recording.wav                  # interactive GUI
    python utils/rms_analyzer.py recording.wav --start 1.0 --end 4.0 --no-gui   # headless
    python utils/rms_analyzer.py recording.wav --channel 2 --window 0.5
    python utils/rms_analyzer.py recording.wav --start 1.0 --end 4.0 --output rms.txt
    python utils/rms_analyzer.py SPL_log.txt

The interactive GUI is shown by default. Pass --no-gui to suppress it (requires
both --start and --end to be specified for a meaningful headless run). File
output can also be triggered via the "Write to file" checkbox in the GUI.

Default window shape is rectangular. Hann is available via --window-shape
hann as a hook for future spectral-analysis work; it is NOT compensated
for window gain, so Hann RMS values will read ~4.26 dB low.

Cross-platform (Mac / Windows). Requires numpy, scipy, matplotlib (matplotlib
only needed if --plot is used). tkinter (stdlib) is used for the file picker.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from scipy.io import wavfile

import os as _os
import platform as _platform
import subprocess as _subprocess
import tempfile as _tempfile

# Playback uses OS-native commands -- no extra Python dependencies needed.
# Future improvement: swap _os_play() for the toolbox TrialPlayer / PsychoPy
# backend so that device routing, calibration gain, and sample-accurate timing
# stay consistent with the rest of PROLACTIN. The subprocess approach is
# sufficient for standalone calibration sanity-checks in the meantime.


# ---------------------------------------------------------------------------
# OS-native WAV playback (no extra deps)
# ---------------------------------------------------------------------------

def _os_play(samples_1d: np.ndarray, fs: float, gain_db: float):
    """
    Write `samples_1d` (float64, mono) to a temp WAV and launch OS playback.
    Returns (proc, tmp_path).
      - proc  : subprocess.Popen on Mac/Linux; None on Windows (winsound)
      - tmp_path : caller must delete when done

    Stop:
      Mac/Linux  -- proc.terminate()
      Windows    -- winsound.PlaySound(None, winsound.SND_PURGE)
    """
    gain = 10.0 ** (gain_db / 20.0)
    data = np.clip(samples_1d.astype(np.float64) * gain, -1.0, 1.0)
    data_i16 = (data * 32767.0).astype(np.int16)

    fd, tmp = _tempfile.mkstemp(suffix='.wav')
    _os.close(fd)
    wavfile.write(tmp, int(fs), data_i16)

    proc = None
    system = _platform.system()
    try:
        if system == 'Darwin':
            proc = _subprocess.Popen(['afplay', tmp])
        elif system == 'Windows':
            import winsound
            winsound.PlaySound(tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            # Linux: try paplay (PulseAudio) then aplay (ALSA)
            for cmd in (['paplay', tmp], ['aplay', '-q', tmp]):
                try:
                    proc = _subprocess.Popen(cmd)
                    break
                except FileNotFoundError:
                    continue
    except Exception as exc:
        print("WARNING: playback launch failed: " + str(exc), file=sys.stderr)
        try:
            _os.unlink(tmp)
        except OSError:
            pass
        return None, None

    return proc, tmp


def _os_stop(proc, tmp_path):
    """Stop a playback launched by _os_play and clean up the temp file."""
    if proc is not None:
        try:
            proc.terminate()
        except Exception:
            pass
    elif _platform.system() == 'Windows':
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
    if tmp_path is not None:
        try:
            _os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Window utilities
# ---------------------------------------------------------------------------

def _window_samples(shape: str, n: int) -> Optional[np.ndarray]:
    """
    Return the window taper as a 1-D array, or None for rectangular
    (which is equivalent to no weighting -- callers can skip the
    multiply for speed).

    NOTE: Hann here is the RAW window, NOT RMS-gain compensated. A
    Hann-windowed RMS underestimates the true signal RMS by ~4.26 dB
    for stationary signals. The Hann option is intended as a hook for
    future spectral-analysis features, not for level measurement.
    """
    if shape == 'rect':
        return None
    elif shape == 'hann':
        return np.hanning(n).astype(np.float64)
    else:
        raise ValueError("Unknown window shape: " + repr(shape))


def _to_db(x: float, eps: float = 1e-20) -> float:
    return 20.0 * np.log10(max(float(x), eps))


def _to_db_array(x: np.ndarray, eps: float = 1e-20) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(x.astype(np.float64), eps))


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------

@dataclass
class SourceInfo:
    """
    Unified description of a loaded source.

    Holds enough information that the analysis routine doesn't need to
    branch on file type for time/level operations. For multi-channel
    future work (e.g. Ambisonic B-format), the data layout below already
    supports multi-channel WAVs; only the channel-aggregation policy
    needs to grow.
    """
    kind: str                            # 'wav' or 'rew_log'
    path: Path
    duration_s: float
    num_channels: int                    # WAV: actual; REW: always 1
    unit_label: str                      # 'dB FS' or 'dB SPL'
    metadata: dict = field(default_factory=dict)

    # WAV-only
    samples: Optional[np.ndarray] = None  # shape (N,) mono or (N, C) multi
    sample_rate: Optional[float] = None

    # REW-only
    log_times: Optional[np.ndarray] = None
    log_levels: Optional[np.ndarray] = None       # LCS column (dB SPL)
    log_peak_hold: Optional[np.ndarray] = None    # LZpeak column (dB SPL)
    log_interval_s: Optional[float] = None


def load_wav(path: Path) -> SourceInfo:
    fs, raw = wavfile.read(str(path))

    if np.issubdtype(raw.dtype, np.integer):
        max_val = float(np.iinfo(raw.dtype).max)
        samples = raw.astype(np.float64) / max_val
    elif np.issubdtype(raw.dtype, np.floating):
        samples = raw.astype(np.float64)
    else:
        raise ValueError("Unsupported WAV dtype: " + str(raw.dtype))

    num_channels = 1 if samples.ndim == 1 else samples.shape[1]
    n_samples = samples.shape[0]
    duration_s = n_samples / float(fs)

    return SourceInfo(
        kind='wav',
        path=path,
        duration_s=duration_s,
        num_channels=num_channels,
        unit_label='dB FS',
        metadata={
            'sample_rate_hz': int(fs),
            'dtype': str(raw.dtype),
            'num_samples': int(n_samples),
        },
        samples=samples,
        sample_rate=float(fs),
    )


def load_rew_log(path: Path) -> SourceInfo:
    """
    Parse a REW V5 SPL meter log export.

    The file is plain text: a metadata header (one 'key: value' per line),
    followed by a column header line starting with 'Time[s]', followed by
    rows of whitespace-separated values. The trailing 'Time of day' field
    is a single timestamp token (despite being three words in the header).
    """
    metadata: dict = {}
    data_start_idx: Optional[int] = None
    header_cols: Optional[list] = None

    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()

    for i, line in enumerate(lines):
        if line.startswith('Time[s]'):
            header_cols = line.split()
            data_start_idx = i + 1
            break
        # Capture metadata keys of interest
        for key in ('Soundcard cal', 'Mic/meter cal', 'SPL cal offset',
                    'High Pass Filter', 'Date', 'Start', 'Log length',
                    'Log interval'):
            if line.startswith(key) and ':' in line:
                metadata[key] = line.split(':', 1)[1].strip()
                break

    if data_start_idx is None or header_cols is None:
        raise ValueError("Could not find 'Time[s]' header in " + str(path))

    # We need columns 0..5: Time[s] LCS LCSMin LCSMax LZpeak LCeq
    expected = ['Time[s]', 'LCS', 'LCSMin', 'LCSMax', 'LZpeak', 'LCeq']
    for idx, name in enumerate(expected):
        if idx >= len(header_cols) or header_cols[idx] != name:
            raise ValueError(
                "REW log header mismatch at column " + str(idx) +
                ": expected " + repr(name) +
                ", got " + repr(header_cols[idx] if idx < len(header_cols) else None) +
                ". Full header: " + str(header_cols)
            )

    rows = []
    for line in lines[data_start_idx:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            rows.append([float(p) for p in parts[:6]])
        except ValueError:
            # Trailing junk line, skip
            continue

    if not rows:
        raise ValueError("No numeric rows parsed from " + str(path))

    data = np.array(rows, dtype=np.float64)
    times = data[:, 0]
    lcs = data[:, 1]
    lzpeak = data[:, 4]

    # Resolve log interval: prefer metadata, fall back to median of diffs
    log_interval_s: Optional[float] = None
    if 'Log interval' in metadata:
        try:
            log_interval_s = float(metadata['Log interval'].split()[0])
        except (ValueError, IndexError):
            log_interval_s = None
    if log_interval_s is None and len(times) > 1:
        log_interval_s = float(np.median(np.diff(times)))
    if log_interval_s is None or log_interval_s <= 0:
        raise ValueError("Could not determine log interval for " + str(path))

    duration_s = float(times[-1])

    return SourceInfo(
        kind='rew_log',
        path=path,
        duration_s=duration_s,
        num_channels=1,
        unit_label='dB SPL',
        metadata=metadata,
        log_times=times,
        log_levels=lcs,
        log_peak_hold=lzpeak,
        log_interval_s=log_interval_s,
    )


# ---------------------------------------------------------------------------
# Input validation (clamp with warnings -- per user spec)
# ---------------------------------------------------------------------------

def validate_inputs(src: SourceInfo,
                    t_start: Optional[float],
                    t_end: Optional[float],
                    channel_1based: Optional[int]) -> Tuple[float, float, int]:
    """
    Clamp t_start, t_end, channel into valid ranges. Print warnings to
    stderr when a fallback is applied. Channel is 1-based in; returned
    channel index is 0-based for internal use.

    Constraints enforced:
      0 <= t_start <= t_end <= duration_s
      1 <= channel_1based <= num_channels
    """
    warnings_list = []

    # t_start
    if t_start is None:
        t_start_v = 0.0
    else:
        t_start_v = float(t_start)
        if t_start_v < 0:
            warnings_list.append(
                "start_time " + str(t_start_v) + " < 0; using 0"
            )
            t_start_v = 0.0
        elif t_start_v > src.duration_s:
            warnings_list.append(
                "start_time " + str(t_start_v) + " > file duration " +
                "{:.6f}".format(src.duration_s) + "; using 0"
            )
            t_start_v = 0.0

    # t_end
    if t_end is None:
        t_end_v = src.duration_s
    else:
        t_end_v = float(t_end)
        if t_end_v > src.duration_s:
            warnings_list.append(
                "end_time " + str(t_end_v) + " > file duration " +
                "{:.6f}".format(src.duration_s) + "; using file end"
            )
            t_end_v = src.duration_s
        if t_end_v < t_start_v:
            warnings_list.append(
                "end_time " + str(t_end_v) + " < start_time " +
                "{:.6f}".format(t_start_v) + "; using file end"
            )
            t_end_v = src.duration_s

    # channel
    if channel_1based is None:
        channel_0based = 0
    else:
        c = int(channel_1based)
        if c < 1 or c > src.num_channels:
            warnings_list.append(
                "channel " + str(c) + " out of range [1, " +
                str(src.num_channels) + "]; using 1"
            )
            channel_0based = 0
        else:
            channel_0based = c - 1

    for w in warnings_list:
        print("WARNING: " + w, file=sys.stderr)

    return t_start_v, t_end_v, channel_0based


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    src_path: str
    src_kind: str
    unit_label: str

    t_start: float
    t_end: float
    duration_selected: float
    channel_1based: int

    window_s: float
    hop_s: float
    window_shape: str
    n_windows: int

    overall_rms_db: float
    mean_windowed_rms_db: float
    min_windowed_rms_db: float
    max_windowed_rms_db: float
    std_windowed_rms_db: float

    peak_db: Optional[float]
    peak_label: str

    metadata: dict = field(default_factory=dict)

    # Plot support (not part of report text)
    plot_times: Optional[np.ndarray] = None
    plot_signal: Optional[np.ndarray] = None
    window_centers: Optional[np.ndarray] = None
    window_rms_db: Optional[np.ndarray] = None


def _windowed_rms_from_samples(samples_1d: np.ndarray,
                               fs: float,
                               window_s: float,
                               hop_s: float,
                               shape: str) -> Tuple[np.ndarray, np.ndarray]:
    """Sliding-window RMS over a 1-D float sample buffer. Returns
    (window_center_times_s, rms_db_per_window)."""
    n_win = max(1, int(round(window_s * fs)))
    n_hop = max(1, int(round(hop_s * fs)))

    w = _window_samples(shape, n_win)  # None for rect
    n = len(samples_1d)

    # Short-selection fallback: just one window over what's there
    if n < n_win:
        rms = float(np.sqrt(np.mean(samples_1d.astype(np.float64) ** 2)))
        return np.array([n / (2.0 * fs)]), np.array([_to_db(rms)])

    starts = np.arange(0, n - n_win + 1, n_hop, dtype=np.int64)
    rms_values = np.empty(len(starts), dtype=np.float64)

    for i, s in enumerate(starts):
        seg = samples_1d[s:s + n_win].astype(np.float64)
        if w is not None:
            seg = seg * w
        rms_values[i] = np.sqrt(np.mean(seg * seg))

    centers = (starts + n_win / 2.0) / fs
    return centers, _to_db_array(rms_values)


def _windowed_levels_from_db_series(times: np.ndarray,
                                    levels_db: np.ndarray,
                                    window_s: float,
                                    hop_s: float,
                                    log_interval_s: float
                                    ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Energy-averaged windowed Leq from a pre-computed dB time series
    (used for REW-log inputs). Each window's value is:
        10 * log10( mean( 10^(level/10) ) )
    which is the physically correct way to average dB power levels.
    """
    n_win = max(1, int(round(window_s / log_interval_s)))
    n_hop = max(1, int(round(hop_s / log_interval_s)))
    n = len(levels_db)

    if n < n_win:
        power = 10.0 ** (levels_db / 10.0)
        mean_db = 10.0 * np.log10(max(float(np.mean(power)), 1e-20))
        center = (times[0] + times[-1]) / 2.0
        return np.array([center]), np.array([mean_db])

    starts = np.arange(0, n - n_win + 1, n_hop, dtype=np.int64)
    out = np.empty(len(starts), dtype=np.float64)
    for i, s in enumerate(starts):
        block_power = 10.0 ** (levels_db[s:s + n_win] / 10.0)
        out[i] = 10.0 * np.log10(max(float(np.mean(block_power)), 1e-20))

    centers = times[starts + n_win // 2]
    return centers, out


def analyze(src: SourceInfo,
            t_start: float,
            t_end: float,
            channel_0based: int,
            window_s: float,
            hop_s: float,
            window_shape: str) -> AnalysisResult:
    """Run the full analysis on a validated source/range/channel."""

    if window_s <= 0 or hop_s <= 0:
        raise ValueError("window and hop must be > 0 seconds")

    if t_end <= t_start:
        raise ValueError("After validation, t_end must be > t_start "
                         "(got " + str(t_start) + ", " + str(t_end) + ")")

    if src.kind == 'wav':
        fs = src.sample_rate
        i_start = max(0, int(round(t_start * fs)))
        i_end = min(src.samples.shape[0], int(round(t_end * fs)))
        if i_end <= i_start:
            raise ValueError("Selected range collapsed to zero samples")

        if src.samples.ndim == 1:
            seg = src.samples[i_start:i_end].astype(np.float64)
        else:
            seg = src.samples[i_start:i_end, channel_0based].astype(np.float64)

        # Overall RMS: single value across the whole selection
        overall_rms = float(np.sqrt(np.mean(seg * seg)))
        overall_rms_db = _to_db(overall_rms)

        # Peak: sample peak in dB FS
        peak = float(np.max(np.abs(seg)))
        peak_db = _to_db(peak)
        peak_label = 'sample peak (dB FS)'

        # Windowed RMS series
        centers_rel, rms_db_arr = _windowed_rms_from_samples(
            seg, fs, window_s, hop_s, window_shape
        )
        centers_abs = centers_rel + t_start

        plot_times = np.arange(seg.shape[0]) / fs + t_start
        plot_signal = seg

    elif src.kind == 'rew_log':
        mask = (src.log_times >= t_start) & (src.log_times <= t_end)
        idx = np.where(mask)[0]
        if len(idx) == 0:
            raise ValueError("Selected time range contains no REW log rows")

        times_sel = src.log_times[idx]
        lcs_sel = src.log_levels[idx]
        lzpeak_sel = src.log_peak_hold[idx]

        # Overall: energetic mean (Leq) of LCS values across the selection
        power = 10.0 ** (lcs_sel / 10.0)
        overall_rms_db = 10.0 * np.log10(max(float(np.mean(power)), 1e-20))

        # Peak from log: max LZpeak (Z-weighted peak hold)
        peak_db = float(np.max(lzpeak_sel))
        peak_label = 'max LZpeak (dB SPL, Z-weighted peak hold)'

        centers_abs, rms_db_arr = _windowed_levels_from_db_series(
            times_sel, lcs_sel, window_s, hop_s, src.log_interval_s
        )

        plot_times = times_sel
        plot_signal = lcs_sel

    else:
        raise ValueError("Unknown source kind: " + repr(src.kind))

    return AnalysisResult(
        src_path=str(src.path),
        src_kind=src.kind,
        unit_label=src.unit_label,
        t_start=t_start,
        t_end=t_end,
        duration_selected=t_end - t_start,
        channel_1based=channel_0based + 1,
        window_s=window_s,
        hop_s=hop_s,
        window_shape=window_shape,
        n_windows=int(len(rms_db_arr)),
        overall_rms_db=float(overall_rms_db),
        mean_windowed_rms_db=float(np.mean(rms_db_arr)),
        min_windowed_rms_db=float(np.min(rms_db_arr)),
        max_windowed_rms_db=float(np.max(rms_db_arr)),
        std_windowed_rms_db=float(np.std(rms_db_arr)),
        peak_db=float(peak_db),
        peak_label=peak_label,
        metadata=src.metadata,
        plot_times=plot_times,
        plot_signal=plot_signal,
        window_centers=centers_abs,
        window_rms_db=rms_db_arr,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_report(res: AnalysisResult) -> str:
    bar = "=" * 70
    lines = [bar, "RMS Analysis Report", bar]
    lines.append("Input file       : " + res.src_path)
    lines.append("Input type       : " + res.src_kind)
    lines.append("Level units      : " + res.unit_label)

    if res.src_kind == 'wav':
        lines.append("Sample rate (Hz) : " + str(res.metadata.get('sample_rate_hz')))
        lines.append("WAV dtype        : " + str(res.metadata.get('dtype')))
        lines.append("Channel analyzed : " + str(res.channel_1based) + " (1-based)")
    elif res.src_kind == 'rew_log':
        for k in ('Date', 'Mic/meter cal', 'SPL cal offset', 'Log interval'):
            if k in res.metadata:
                lines.append("{:<17s}: {}".format(k, res.metadata[k]))

    lines.append("")
    lines.append("Time range       : {:.6f} s -> {:.6f} s (duration {:.6f} s)".format(
        res.t_start, res.t_end, res.duration_selected))
    lines.append("Window           : {:g} s ({}), hop {:g} s, {} window(s)".format(
        res.window_s, res.window_shape, res.hop_s, res.n_windows))
    lines.append("")
    lines.append("Overall RMS              : {:+9.3f} {}".format(
        res.overall_rms_db, res.unit_label))
    lines.append("Mean of windowed RMS     : {:+9.3f} {}".format(
        res.mean_windowed_rms_db, res.unit_label))
    lines.append("Min  of windowed RMS     : {:+9.3f} {}".format(
        res.min_windowed_rms_db, res.unit_label))
    lines.append("Max  of windowed RMS     : {:+9.3f} {}".format(
        res.max_windowed_rms_db, res.unit_label))
    lines.append("Std  of windowed RMS     : {:+9.3f} dB".format(
        res.std_windowed_rms_db))
    lines.append("Peak                     : {:+9.3f}  ({})".format(
        res.peak_db, res.peak_label))
    lines.append(bar)
    return "\n".join(lines)


def format_stats_block(res: AnalysisResult) -> str:
    """Compact multi-line stats string for the in-GUI panel.
    Same numbers as format_report, but no header/metadata."""
    u = res.unit_label
    return "\n".join([
        "Time range:   {:.3f} -> {:.3f} s   (duration {:.3f} s)".format(
            res.t_start, res.t_end, res.duration_selected),
        "Window:       {:g} s ({}), hop {:g} s, {} window(s)".format(
            res.window_s, res.window_shape, res.hop_s, res.n_windows),
        "",
        "  Overall RMS          : {:+9.3f} {}".format(res.overall_rms_db, u),
        "  Mean of windowed RMS : {:+9.3f} {}".format(res.mean_windowed_rms_db, u),
        "  Min  of windowed RMS : {:+9.3f} {}".format(res.min_windowed_rms_db, u),
        "  Max  of windowed RMS : {:+9.3f} {}".format(res.max_windowed_rms_db, u),
        "  Std  of windowed RMS : {:+9.3f} dB".format(res.std_windowed_rms_db),
        "  Peak                 : {:+9.3f}  ({})".format(res.peak_db, res.peak_label),
    ])


# ---------------------------------------------------------------------------
# Interactive window (matplotlib embedded in tkinter)
# ---------------------------------------------------------------------------

def show_plot_and_pick_range(src: SourceInfo,
                             initial_result: AnalysisResult,
                             window_s: float,
                             hop_s: float,
                             window_shape: str,
                             channel_0based: int,
                             tk_root,
                             output_path: Optional[Path] = None,
                             ) -> Tuple[AnalysisResult, bool]:
    """
    Open the interactive window. Matplotlib canvas is embedded directly in
    `tk_root` so there's only one window. Returns (final_result, accepted).
    `accepted` is True iff the user clicked 'Use this selection'. The root
    is destroyed before this function returns.

    If output_path is given, the 'Write to file' checkbox is pre-checked.
    Writing is handled inside this function; callers do not need to write.
    """
    import tkinter as tk
    from tkinter import filedialog
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import (
        FigureCanvasTkAgg, NavigationToolbar2Tk,
    )
    from matplotlib.widgets import SpanSelector

    # Bring the (previously withdrawn) root into view
    try:
        tk_root.attributes('-topmost', False)
    except Exception:
        pass
    tk_root.title("RMS Analyzer - " + Path(src.path).name)
    tk_root.deiconify()

    # ------------------------------------------------------------------
    # Figure (built independently of pyplot since we're embedding)
    # ------------------------------------------------------------------
    fig = Figure(figsize=(11, 5))
    ax_top = fig.add_subplot(2, 1, 1)
    ax_bot = fig.add_subplot(2, 1, 2, sharex=ax_top)

    # Top panel: full source overview
    if src.kind == 'wav':
        if src.samples.ndim == 1:
            full_signal = src.samples
        else:
            full_signal = src.samples[:, channel_0based]
        full_times = np.arange(len(full_signal)) / src.sample_rate
        if len(full_signal) > 200_000:
            stride = max(1, len(full_signal) // 100_000)
            ax_top.plot(full_times[::stride], full_signal[::stride], lw=0.5)
        else:
            ax_top.plot(full_times, full_signal, lw=0.5)
        ax_top.set_ylabel('amplitude')
        ax_top.set_title("Waveform - {} (ch {})".format(
            Path(src.path).name, channel_0based + 1))
    else:
        ax_top.plot(src.log_times, src.log_levels, lw=0.8, label='LCS')
        ax_top.plot(src.log_times, src.log_peak_hold, lw=0.5,
                    alpha=0.5, label='LZpeak')
        ax_top.set_ylabel('level ({})'.format(src.unit_label))
        ax_top.set_title("REW SPL log - " + Path(src.path).name)
        ax_top.legend(loc='lower right', fontsize=8)

    # Bottom panel: full-file windowed RMS (static, computed once),
    # plain line, no markers
    full_file_result = analyze(src, 0.0, src.duration_s, channel_0based,
                               window_s, hop_s, window_shape)
    ax_bot.plot(full_file_result.window_centers,
                full_file_result.window_rms_db, lw=0.8)
    ax_bot.set_xlabel('time (s)')
    ax_bot.set_ylabel('windowed RMS ({})'.format(src.unit_label))
    ax_bot.set_title("Windowed RMS (full file)  -  "
                     "window={:g}s, hop={:g}s, shape={}".format(
        window_s, hop_s, window_shape))

    # Selection spans on BOTH panels, kept in sync
    span_top = [ax_top.axvspan(initial_result.t_start, initial_result.t_end,
                               color='orange', alpha=0.18)]
    span_bot = [ax_bot.axvspan(initial_result.t_start, initial_result.t_end,
                               color='orange', alpha=0.18)]

    # Fix x-axis to exactly [0, duration] -- prevent matplotlib margins and
    # SpanSelector from expanding the view on first draw or drag.
    fig.tight_layout()
    ax_top.set_xlim(0.0, src.duration_s)
    ax_top.autoscale(enable=False, axis='x')  # ax_bot inherits via sharex

    # ------------------------------------------------------------------
    # Tkinter layout
    # Packing order: toolbar top, canvas middle, bottom_frame bottom.
    # Within bottom_frame rows are packed top-to-bottom.
    # ------------------------------------------------------------------
    canvas = FigureCanvasTkAgg(fig, master=tk_root)
    toolbar = NavigationToolbar2Tk(canvas, tk_root, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side='top', fill='x')
    canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    bottom_frame = tk.Frame(tk_root)
    bottom_frame.pack(side='bottom', fill='x')

    # Row 1: stats (monospaced, left-aligned)
    stats_var = tk.StringVar()
    stats_label = tk.Label(bottom_frame, textvariable=stats_var,
                           justify='left', anchor='w', font=('Courier', 11),
                           padx=10, pady=4)
    stats_label.pack(side='top', fill='x')

    # Row 2: playback controls (WAV only)
    play_btn = None
    vol_scale = None
    _is_playing = [False]

    if src.kind == 'wav':
        play_row = tk.Frame(bottom_frame)
        play_row.pack(side='top', fill='x', padx=6, pady=2)

        play_btn = tk.Button(play_row, text='Play', width=6)
        play_btn.pack(side='left', padx=(6, 4))

        tk.Label(play_row, text='Volume (dB):').pack(side='left')
        vol_scale = tk.Scale(play_row, from_=-60, to=0, resolution=1,
                             orient='horizontal', length=140,
                             showvalue=True)
        vol_scale.set(-15)
        vol_scale.pack(side='left', padx=(2, 12))

        tk.Label(play_row, text='Drag on either subplot to select a range.',
                 fg='gray40').pack(side='left', padx=6)

    # Row 3: accept row (Select All, Write checkbox, Use this selection)
    accept_row = tk.Frame(bottom_frame)
    accept_row.pack(side='top', fill='x', pady=4)

    select_all_btn = tk.Button(accept_row, text='Select All')
    select_all_btn.pack(side='left', padx=(10, 6))

    write_var = tk.BooleanVar(value=(output_path is not None))
    write_chk = tk.Checkbutton(accept_row, text='Write to file',
                                variable=write_var)
    write_chk.pack(side='left', padx=6)

    accept_btn = tk.Button(accept_row, text='Use this selection')
    accept_btn.pack(side='right', padx=10, pady=2)

    if src.kind != 'wav':
        # Hint text lives in accept_row when there is no play row
        tk.Label(accept_row,
                 text='Drag on either subplot to select a range.',
                 fg='gray40').pack(side='left', padx=10)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    current_holder = [initial_result]
    accepted_holder = [False]
    output_holder = [output_path]   # may be set by save dialog on accept

    def _refresh_stats(res: AnalysisResult):
        stats_var.set(format_stats_block(res))

    _refresh_stats(initial_result)

    # ------------------------------------------------------------------
    # Playback helpers (OS-native via _os_play / _os_stop)
    # ------------------------------------------------------------------
    _play_proc = [None]    # subprocess.Popen or None (Windows)
    _play_tmp  = [None]    # temp WAV path

    def _stop_playback():
        if _is_playing[0]:
            _os_stop(_play_proc[0], _play_tmp[0])
            _play_proc[0] = None
            _play_tmp[0] = None
            _is_playing[0] = False
            if play_btn is not None:
                play_btn.configure(text='Play')

    def _poll_playback_done():
        """Poll proc every 200 ms; reset button when it exits naturally."""
        if not _is_playing[0]:
            return
        proc = _play_proc[0]
        if proc is not None:
            if proc.poll() is not None:   # process finished
                _os_stop(None, _play_tmp[0])
                _play_proc[0] = None
                _play_tmp[0] = None
                _is_playing[0] = False
                if play_btn is not None:
                    play_btn.configure(text='Play')
                return
        # Windows: no proc, estimate done by duration; keep polling
        # (winsound stops on its own; Stop button calls _os_stop to purge)
        tk_root.after(200, _poll_playback_done)

    def _on_play_stop():
        if _is_playing[0]:
            _stop_playback()
            return
        res = current_holder[0]
        fs = src.sample_rate
        i_start = max(0, int(round(res.t_start * fs)))
        i_end = min(src.samples.shape[0], int(round(res.t_end * fs)))
        if src.samples.ndim == 1:
            seg = src.samples[i_start:i_end].copy().astype(np.float64)
        else:
            seg = src.samples[i_start:i_end, channel_0based].copy().astype(np.float64)
        proc, tmp = _os_play(seg, fs, vol_scale.get())
        if tmp is None:   # launch failed; _os_play already printed warning
            return
        _play_proc[0] = proc
        _play_tmp[0] = tmp
        _is_playing[0] = True
        play_btn.configure(text='Stop')
        tk_root.after(200, _poll_playback_done)

    if play_btn is not None:
        play_btn.configure(command=_on_play_stop)

    # ------------------------------------------------------------------
    # Selection callback
    # ------------------------------------------------------------------
    def _on_select(t_start_new, t_end_new):
        if (t_end_new - t_start_new) < 1e-6:
            return
        _stop_playback()
        ts, te, _ = validate_inputs(src, t_start_new, t_end_new,
                                    channel_0based + 1)
        try:
            res = analyze(src, ts, te, channel_0based,
                          window_s, hop_s, window_shape)
        except ValueError:
            return
        current_holder[0] = res
        _refresh_stats(res)
        span_top[0].remove()
        span_top[0] = ax_top.axvspan(ts, te, color='orange', alpha=0.18)
        span_bot[0].remove()
        span_bot[0] = ax_bot.axvspan(ts, te, color='orange', alpha=0.18)
        canvas.draw_idle()

    def _on_select_all():
        _on_select(0.0, src.duration_s)
        # Update the visual span-selector handles too
        try:
            sel_top.extents = (0.0, src.duration_s)
            sel_bot.extents = (0.0, src.duration_s)
        except Exception:
            pass
        canvas.draw_idle()

    select_all_btn.configure(command=_on_select_all)

    # Span selectors on both axes so the user can drag from either subplot
    sel_top = SpanSelector(
        ax_top, _on_select, 'horizontal',
        useblit=True, props=dict(alpha=0.3, facecolor='tab:orange'),
        interactive=True, drag_from_anywhere=True,
    )
    sel_bot = SpanSelector(
        ax_bot, _on_select, 'horizontal',
        useblit=True, props=dict(alpha=0.3, facecolor='tab:orange'),
        interactive=True, drag_from_anywhere=True,
    )
    # Keep references alive so they are not garbage-collected
    tk_root._rms_span_selectors = (sel_top, sel_bot)

    # ------------------------------------------------------------------
    # Accept / close
    # ------------------------------------------------------------------
    def _on_accept():
        _stop_playback()
        if write_var.get():
            # Resolve output path (prompt if not yet known)
            if output_holder[0] is None:
                try:
                    tk_root.attributes('-topmost', True)
                except Exception:
                    pass
                chosen = filedialog.asksaveasfilename(
                    parent=tk_root,
                    title="Save RMS analysis report",
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt"), ("All files", "*")],
                )
                try:
                    tk_root.attributes('-topmost', False)
                except Exception:
                    pass
                if chosen:
                    output_holder[0] = Path(chosen)
            if output_holder[0] is not None:
                report = format_report(current_holder[0])
                output_holder[0].write_text(report + "\n", encoding='utf-8')
                print("Report written to " + str(output_holder[0]))
        accepted_holder[0] = True
        tk_root.quit()

    def _on_close():
        _stop_playback()
        tk_root.quit()

    accept_btn.configure(command=_on_accept)
    tk_root.protocol('WM_DELETE_WINDOW', _on_close)

    tk_root.mainloop()
    try:
        tk_root.destroy()
    except Exception:
        pass

    return current_holder[0], accepted_holder[0]


# ---------------------------------------------------------------------------
# File-picker fallback (when no input file is passed on the CLI)
# ---------------------------------------------------------------------------

def _pick_input_file_via_dialog(tk_root) -> Optional[Path]:
    """
    Open the tkinter Open dialog parented on the existing `tk_root`. Returns
    the chosen Path, or None if the user cancels. The root is left in
    place (still withdrawn) so it can be reused for the plot window.
    """
    from tkinter import filedialog

    # Briefly raise topmost so the dialog appears in front on macOS
    try:
        tk_root.attributes('-topmost', True)
    except Exception:
        pass

    try:
        chosen = filedialog.askopenfilename(
            parent=tk_root,
            title="Select a WAV file or REW SPL log",
            filetypes=[
                ("WAV or log files", "*.wav *.txt *.log"),
                ("WAV files", "*.wav"),
                ("Log / text files", "*.txt *.log"),
                ("All files", "*"),
            ],
        )
    finally:
        try:
            tk_root.attributes('-topmost', False)
        except Exception:
            pass

    if not chosen:
        return None
    return Path(chosen)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="RMS analysis for WAV files and REW SPL meter logs.",
    )
    ap.add_argument('input', type=Path, nargs='?', default=None,
                    help="Input file (.wav, or .txt for a REW SPL log). "
                         "If omitted, a file-picker dialog is shown.")
    ap.add_argument('--start', type=float, default=None,
                    help="Start time in seconds (default: 0)")
    ap.add_argument('--end', type=float, default=None,
                    help="End time in seconds (default: end of file)")
    ap.add_argument('--channel', type=int, default=None,
                    help="Channel to analyze, 1-based (default: 1; WAV only)")
    ap.add_argument('--window', type=float, default=0.1,
                    help="Window length in seconds (default: 0.1)")
    ap.add_argument('--hop', type=float, default=None,
                    help="Hop length in seconds (default: window / 2)")
    ap.add_argument('--window-shape', choices=['rect', 'hann'], default='rect',
                    help="Window shape (default: rect). Hann is a raw "
                         "(uncompensated) window for future spectral-analysis "
                         "use; it gives biased RMS values.")
    ap.add_argument('--no-gui', action='store_true',
                    help="Suppress the interactive GUI. Requires --start and "
                         "--end to be set for a meaningful result.")
    ap.add_argument('--plot', action='store_true',
                    help="Deprecated alias: the GUI is now shown by default. "
                         "This flag is accepted but has no additional effect.")
    ap.add_argument('--output', type=Path, default=None,
                    help="Write the report to this file as well (also "
                         "available via the 'Write to file' checkbox in the GUI)")
    return ap


def _make_tk_root_withdrawn() -> Optional[object]:
    """Create a single tkinter root for the whole session (file dialog
    and/or interactive plot), already withdrawn. Returns None if tkinter
    isn't available."""
    try:
        import tkinter as tk
    except ImportError:
        print("ERROR: tkinter not available; pass --start and --end on the "
              "command line to run headless.", file=sys.stderr)
        return None
    r = tk.Tk()
    r.withdraw()
    return r


def main(argv=None) -> int:
    args = _build_argparser().parse_args(argv)

    # One tkinter root, lazily created and reused for both the file picker
    # and the interactive plot, so the user never sees two windows.
    tk_root = None

    def _cleanup_root():
        nonlocal tk_root
        if tk_root is not None:
            try:
                tk_root.destroy()
            except Exception:
                pass
            tk_root = None

    # ----- Resolve input path (file dialog if not provided) -----
    input_path = args.input
    if input_path is None:
        tk_root = _make_tk_root_withdrawn()
        if tk_root is None:
            return 2
        input_path = _pick_input_file_via_dialog(tk_root)
        if input_path is None:
            print("No input file selected.", file=sys.stderr)
            _cleanup_root()
            return 0

    if not input_path.exists():
        print("ERROR: input file not found: " + str(input_path), file=sys.stderr)
        _cleanup_root()
        return 2

    suffix = input_path.suffix.lower()
    if suffix == '.wav':
        src = load_wav(input_path)
    elif suffix in ('.txt', '.log'):
        src = load_rew_log(input_path)
    else:
        print("ERROR: unknown input extension " + repr(suffix) +
              " (expected .wav, .txt, or .log)", file=sys.stderr)
        _cleanup_root()
        return 2

    hop_s = args.hop if args.hop is not None else (args.window / 2.0)

    t_start, t_end, channel_0based = validate_inputs(
        src, args.start, args.end, args.channel
    )

    initial_result = analyze(src, t_start, t_end, channel_0based,
                             args.window, hop_s, args.window_shape)

    # GUI is shown by default; --no-gui suppresses it.
    should_plot = not args.no_gui

    if should_plot:
        if tk_root is None:
            tk_root = _make_tk_root_withdrawn()
            if tk_root is None:
                return 2
        # File writing is handled inside the GUI via the 'Write to file'
        # checkbox; we pass output_path so the checkbox is pre-checked
        # when --output was given on the CLI.
        final_result, accepted = show_plot_and_pick_range(
            src, initial_result, args.window, hop_s,
            args.window_shape, channel_0based,
            tk_root=tk_root,
            output_path=args.output,
        )
        # show_plot_and_pick_range destroyed the root itself
        tk_root = None
        if not accepted:
            print("Selection not confirmed; no output written.",
                  file=sys.stderr)
            return 0
        result = final_result
    else:
        # Headless: clean up any file-dialog root that may have been created
        _cleanup_root()
        result = initial_result

    report = format_report(result)
    print(report)

    # In headless mode, honour --output directly.
    # In GUI mode the checkbox already handled writing.
    if not should_plot and args.output is not None:
        args.output.write_text(report + "\n", encoding='utf-8')
        print("Report written to " + str(args.output))

    return 0


# ---------------------------------------------------------------------------
# Future-work notes (kept here so they don't get lost):
#
# 1. Ambisonic B-format inputs.
#    The WAV path already handles multi-channel files. To support B-format,
#    add a --channel-mode flag with options like:
#       single             -- current behavior, one channel via --channel
#       bformat-w          -- analyze only the W (omni) channel
#       bformat-energy     -- sqrt(W^2 + X^2 + Y^2 + Z^2), proxy for total
#                             sound-field energy
#       binaural-decode    -- convolve with HRTFs (or a measured BRIR set)
#                             then compute RMS on the binaural mixdown
#    The right perceptual weighting between channels is an empirical
#    question -- best calibrated by comparing computed values against
#    in-room measurements at the listening position.
#
# 2. A/C weighting filters for WAV inputs (so WAV-derived dB FS can be
#    correlated against weighted REW columns) -- straightforward IIR.
# ---------------------------------------------------------------------------


if __name__ == '__main__':
    sys.exit(main())
