"""
level_validator.py
------------------
Standalone calibrated-level validation tool for PROLACTIN.

Produces calibrated stimuli (pure tone, white noise, WAV file, log sweep) at a
requested level and routes them through the SAME calibration pipeline the
paradigms use (CalibrationManager.prepare_samples / .spl_to_amplitude), so you
can confirm the toolbox emits the levels you think it does. Plays through the
configured RME device and/or writes a 32-bit-float WAV for offline measurement
(REW + B&K coupler).

Two layers, cleanly separable so the GUI can be swapped later (e.g. NiceGUI):

  LevelValidator     -- headless engine. Generation + calibration math + WAV
                        render need NO PsychoPy. Playback lazily imports the
                        PsychoPy sound backend.
  LevelValidatorGUI  -- thin tkinter front-end on the engine.

Stimulus level convention (matches SRT + the sine-peak SPL anchor):
  - tone / sweep  : generated at unit PEAK; per-channel gain from
                    spl_to_amplitude() (peak-referenced) sets the SPL.
  - noise / file  : RMS-normalised to 1/sqrt(2) before gain, so a given dB SPL
                    yields the same RMS as a sine at that dB SPL. (The
                    noise-vs-sine SPL bias is still pending hardware
                    verification on the coupler.)

Units:
  - dB SPL is wired for v1.
  - dB HL is HOOKED but provisional: _resolve_spl() will convert via the
    profile's RETSPL table the moment a transducer-appropriate table replaces
    the current ISO 389-1 placeholder. dB HL is only meaningful for a single
    frequency, so it is restricted to the 'tone' stimulus.

CLI examples:
    # Launch the GUI (default)
    python level_validator.py --config ../../calibration_data/calibration_config.json

    # Headless: build + report only
    python level_validator.py --config CFG --no-gui --type tone --freq 1000 --level 70

    # Headless: write a WAV for REW capture
    python level_validator.py --config CFG --no-gui --type sweep --f0 20 --f1 20000 \
        --dur 5 --level 80 --wav sweep_80dB.wav

    # Headless: play through the RME (requires hardware + PsychoPy)
    python level_validator.py --config CFG --no-gui --type noise --level 65 --dur 1 --play
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np


# --- import bootstrap -------------------------------------------------
# This file is intended to live in the toolbox `utils/` package, but it
# imports both a sibling package module (utils.calibration) and a
# top-level module (audio_devices). Put the toolbox root on sys.path so
# both resolve when launched as `python utils/level_validator.py` from
# the toolbox root. Mirrors tests/audible_smoke_test.py. Harmless if the
# file is instead placed at the toolbox root.
_TOOLBOX_ROOT = Path(__file__).resolve().parent.parent
if str(_TOOLBOX_ROOT) not in sys.path:
    sys.path.insert(0, str(_TOOLBOX_ROOT))


# ======================================================================
# Engine
# ======================================================================

class LevelValidator:
    """Headless calibrated-stimulus engine.

    Generation, the calibration math, and WAV render require only numpy/scipy.
    Playback lazily pulls in PsychoPy and the audio-device selection used by
    the paradigms, so the device routing matches a real run.
    """

    SUPPORTED_TYPES = ("tone", "noise", "file", "sweep")
    EAR_TO_PAN = {"both": None, "left": -1.0, "right": 1.0}

    def __init__(self, config_path, profile=None, fade_time=0.05):
        # Imported here (not at module top) so importing this module stays
        # lightweight; CalibrationManager itself is PsychoPy-free until a
        # Sound is built.
        from utils.calibration import CalibrationManager

        self.cm = CalibrationManager(config_path, profile=profile)
        self.fs = self.cm.sample_rate
        self.fade_time = float(fade_time)
        self._device_configured = False

    # ------------------------------------------------------------------
    # Level units (dB SPL now; dB HL hooked)
    # ------------------------------------------------------------------

    def _resolve_spl(self, level, units, freq_hz):
        """Resolve a requested level + units to a dB SPL value.

        dB SPL passes through. dB HL is converted via the profile RETSPL table
        (hook only for now -- the bundled table is an ISO 389-1 placeholder and
        is NOT valid for the circumaural transducers, so any HL result is
        provisional until that table is replaced).
        """
        u = (units or "dB SPL").strip().lower()
        if u in ("db spl", "spl"):
            return float(level)
        if u in ("db hl", "hl"):
            if not self.cm.hl_calibrated:
                raise ValueError(
                    "dB HL requested but this profile has no RETSPL table."
                )
            return float(self.cm.hl_converter.hl_to_spl(float(level),
                                                         float(freq_hz)))
        raise ValueError(f"Unknown units {units!r}; use 'dB SPL' or 'dB HL'.")

    # ------------------------------------------------------------------
    # Waveform generators (unit-referenced, PsychoPy-free)
    # ------------------------------------------------------------------

    def _apply_fades(self, wave):
        """Hann fade-in/out (mirrors event_gen.apply_fades)."""
        n = int(self.fade_time * self.fs)
        if n > 0 and 2 * n <= len(wave):
            win = np.hanning(2 * n)
            wave[:n] *= win[:n]
            wave[-n:] *= win[-n:]
        return wave

    def _gen_tone(self, freq, dur):
        t = np.arange(int(round(dur * self.fs))) / self.fs
        return self._apply_fades(np.sin(2.0 * np.pi * float(freq) * t))

    def _gen_noise(self, dur):
        n = int(round(dur * self.fs))
        w = np.random.normal(0.0, 1.0, n)
        w = self._apply_fades(w)
        rms = float(np.sqrt(np.mean(w ** 2)))
        if rms > 1e-12:
            w *= (1.0 / np.sqrt(2.0)) / rms  # RMS -> 1/sqrt(2) (sine-equivalent)
        return w

    def _gen_sweep(self, f0, f1, dur):
        """Exponential (log) sine sweep at unit peak, with Hann fades."""
        f0 = float(f0)
        f1 = float(f1)
        T = float(dur)
        if f0 <= 0 or f1 <= 0 or f1 == f0:
            raise ValueError("sweep requires f0 > 0, f1 > 0, f0 != f1.")
        n = int(round(T * self.fs))
        t = np.arange(n) / self.fs
        L = math.log(f1 / f0) / T
        K = (2.0 * np.pi * f0) / L
        phase = K * (np.exp(L * t) - 1.0)
        return self._apply_fades(np.sin(phase))

    def _load_wav(self, path):
        """Load a WAV to mono float, resample to fs, RMS-normalise to 1/sqrt(2)."""
        from scipy.io import wavfile

        file_fs, data = wavfile.read(str(path))
        data = np.asarray(data, dtype=np.float64)
        if data.ndim > 1:                      # downmix to mono
            data = data.mean(axis=1)
        if file_fs != self.fs:                 # resample to profile rate
            from math import gcd
            from scipy.signal import resample_poly
            g = gcd(int(file_fs), int(self.fs))
            data = resample_poly(data, self.fs // g, int(file_fs) // g)
        rms = float(np.sqrt(np.mean(data ** 2)))
        if rms > 1e-12:                        # RMS -> 1/sqrt(2) (matches SRT)
            data = data * ((1.0 / np.sqrt(2.0)) / rms)
        return data

    def build_mono(self, stim_type, *, freq=1000.0, dur=0.5,
                   f0=20.0, f1=20000.0, wav_path=None):
        if stim_type == "tone":
            return self._gen_tone(freq, dur)
        if stim_type == "noise":
            return self._gen_noise(dur)
        if stim_type == "sweep":
            return self._gen_sweep(f0, f1, dur)
        if stim_type == "file":
            if not wav_path:
                raise ValueError("stim_type 'file' requires wav_path.")
            return self._load_wav(wav_path)
        raise ValueError(
            f"Unknown stim_type {stim_type!r}; "
            f"use one of {self.SUPPORTED_TYPES}."
        )

    # ------------------------------------------------------------------
    # Calibrated render / play
    # ------------------------------------------------------------------

    def _prepare(self, stim_type, level, units, freq, dur, ear, f0, f1, wav_path):
        if ear not in self.EAR_TO_PAN:
            raise ValueError(f"ear must be one of {tuple(self.EAR_TO_PAN)}.")
        u = (units or "dB SPL").strip().lower()
        if u in ("db hl", "hl") and stim_type != "tone":
            raise ValueError(
                "dB HL is frequency-specific; only the 'tone' stimulus "
                "supports it."
            )
        spl = self._resolve_spl(level, units, freq)
        amp_L, amp_R = self.cm.spl_to_amplitude(spl)
        mono = self.build_mono(stim_type, freq=freq, dur=dur,
                               f0=f0, f1=f1, wav_path=wav_path)
        pan = self.EAR_TO_PAN[ear]
        return mono, pan, amp_L, amp_R, spl

    def build(self, stim_type, level, *, units="dB SPL", freq=1000.0, dur=0.5,
              ear="both", f0=20.0, f1=20000.0, wav_path=None):
        """Render the calibrated stereo buffer and a readout dict.

        Returns (stereo_ndarray, info_dict). No PsychoPy needed.
        """
        mono, pan, amp_L, amp_R, spl = self._prepare(
            stim_type, level, units, freq, dur, ear, f0, f1, wav_path)
        stereo = self.cm.prepare_samples(
            mono, self.fs, pan=pan, per_channel_gain=(amp_L, amp_R))
        info = self._describe(stim_type, level, units, spl, freq, ear,
                              amp_L, amp_R, stereo)
        return stereo, info

    def write_wav(self, out_path, stereo):
        """Write a 32-bit float stereo WAV (REW-friendly)."""
        from scipy.io import wavfile
        out_path = Path(out_path)
        wavfile.write(str(out_path), int(self.fs),
                      stereo.astype(np.float32))
        return out_path

    def play_samples(self, stereo, block=True):
        """Play an already-rendered stereo buffer through the RME device.

        Plays the EXACT buffer that build()/write_wav() produce, so what you
        measure offline equals what you hear.
        """
        self._ensure_device()
        from psychopy import sound as _ps  # first sound import reads device pref
        secs = stereo.shape[0] / self.fs
        snd = _ps.Sound(value=stereo.astype(np.float64), sampleRate=self.fs,
                        stereo=True, secs=secs, hamming=False)
        snd.play()
        if block:
            import time
            time.sleep(secs + 0.05)  # ringout is already inside `stereo`
        return snd

    def play(self, stim_type, level, *, block=True, **kw):
        """Convenience: build then play. Returns (sound, info)."""
        stereo, info = self.build(stim_type, level, **kw)
        snd = self.play_samples(stereo, block=block)
        return snd, info

    def _ensure_device(self):
        if self._device_configured:
            return
        try:
            import audio_devices
            audio_devices.find_and_configure()
        except Exception as ex:  # noqa: BLE001 -- device select is best-effort
            print(f"[level_validator] device auto-select skipped: {ex}",
                  file=sys.stderr)
        self._device_configured = True

    # ------------------------------------------------------------------
    # Readout
    # ------------------------------------------------------------------

    def _describe(self, stim_type, level, units, spl, freq, ear,
                  amp_L, amp_R, stereo):
        peak_L = float(np.max(np.abs(stereo[:, 0]))) if stereo.size else 0.0
        peak_R = float(np.max(np.abs(stereo[:, 1]))) if stereo.size else 0.0
        peak = max(peak_L, peak_R)
        headroom = (20.0 * math.log10(1.0 / peak)) if peak > 0 else float("inf")
        info = {
            "profile": self.cm.active_profile,
            "fir_calibrated": self.cm.fir_calibrated,
            "spl_calibrated": self.cm.spl_calibrated,
            "stim_type": stim_type,
            "requested_level": float(level),
            "units": units,
            "resolved_spl": float(spl),
            "freq_hz": float(freq),
            "ear": ear,
            "amp_target_L": amp_L,
            "amp_target_R": amp_R,
            "peak_post_fir_L": peak_L,
            "peak_post_fir_R": peak_R,
            "headroom_dB": headroom,
            "clipped": peak >= 1.0,
            "n_samples": int(stereo.shape[0]),
            "duration_s": stereo.shape[0] / self.fs,
            "sample_rate": self.fs,
        }
        # Full-scale ceiling (peak = 1.0) per ear, for sanity.
        if self.cm.spl_calibrated:
            info["full_scale_spl_L"] = self.cm.amplitude_to_spl(1.0, "left")
            info["full_scale_spl_R"] = self.cm.amplitude_to_spl(1.0, "right")
            info["max_spl_limit"] = self.cm.max_spl
        return info

    @staticmethod
    def format_info(info):
        """Human-readable readout block."""
        lines = [
            f"Profile         : {info['profile']}",
            f"  FIR calibrated: {info['fir_calibrated']}    "
            f"SPL calibrated: {info['spl_calibrated']}",
            f"Stimulus        : {info['stim_type']}  "
            f"({info['freq_hz']:.1f} Hz)  ear={info['ear']}",
            f"Level requested : {info['requested_level']:.1f} {info['units']}"
            f"  ->  {info['resolved_spl']:.1f} dB SPL",
            f"Target peak amp : L={info['amp_target_L']:.5f}  "
            f"R={info['amp_target_R']:.5f}",
            f"Peak after FIR  : L={info['peak_post_fir_L']:.5f}  "
            f"R={info['peak_post_fir_R']:.5f}",
            f"Headroom        : {info['headroom_dB']:.2f} dB"
            f"{'   *** CLIPPING ***' if info['clipped'] else ''}",
            f"Duration        : {info['duration_s']:.3f} s "
            f"({info['n_samples']} samples @ {info['sample_rate']} Hz)",
        ]
        if "full_scale_spl_L" in info:
            lines.append(
                f"Full-scale (1.0): L={info['full_scale_spl_L']:.1f}  "
                f"R={info['full_scale_spl_R']:.1f} dB SPL  "
                f"(limit {info['max_spl_limit']:.0f})"
            )
        return "\n".join(lines)


# ======================================================================
# CLI
# ======================================================================

def _build_arg_parser():
    p = argparse.ArgumentParser(
        description="PROLACTIN calibrated level-validation tool.")
    p.add_argument("--config", default="calibration_config.json",
                   help="Path to calibration_config.json.")
    p.add_argument("--profile", default=None,
                   help="Profile name (default: config/DEFAULTS.py 'default_headphone_calibration_profile').")
    p.add_argument("--no-gui", action="store_true",
                   help="Headless mode (build/report; no tkinter).")
    p.add_argument("--type", dest="stim_type", default="tone",
                   choices=LevelValidator.SUPPORTED_TYPES)
    p.add_argument("--level", type=float, default=70.0,
                   help="Level value (see --units).")
    p.add_argument("--units", default="dB SPL",
                   choices=["dB SPL", "dB HL"])
    p.add_argument("--freq", type=float, default=1000.0,
                   help="Frequency for tone (Hz).")
    p.add_argument("--f0", type=float, default=20.0, help="Sweep start (Hz).")
    p.add_argument("--f1", type=float, default=20000.0, help="Sweep end (Hz).")
    p.add_argument("--dur", type=float, default=10.0,
                   help="Duration (s) for tone/noise/sweep.")
    p.add_argument("--ear", default="left", choices=["both", "left", "right"])
    p.add_argument("--file", dest="wav_path", default=None,
                   help="WAV path for --type file.")
    p.add_argument("--fade", type=float, default=0.05, help="Fade time (s).")
    p.add_argument("--wav", dest="out_wav", default=None,
                   help="Write rendered stereo to this WAV.")
    p.add_argument("--play", action="store_true",
                   help="Play through the configured device.")
    return p


def run_cli(args):
    lv = LevelValidator(args.config, profile=args.profile, fade_time=args.fade)
    stereo, info = lv.build(
        args.stim_type, args.level, units=args.units, freq=args.freq,
        dur=args.dur, ear=args.ear, f0=args.f0, f1=args.f1,
        wav_path=args.wav_path)
    print(LevelValidator.format_info(info))
    if args.out_wav:
        out = lv.write_wav(args.out_wav, stereo)
        print(f"Wrote WAV: {out}")
    if args.play:
        print("Playing...")
        lv.play_samples(stereo, block=True)
        print("Done.")
    return 0


# ======================================================================
# GUI (tkinter) -- thin layer over the engine; drop-in replaceable
# ======================================================================

class LevelValidatorGUI:
    """Minimal tkinter front-end. Build/Play/Render with a live readout."""

    def __init__(self, config_path="calibration_config.json", profile=None):
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox

        self.config_path = config_path
        self._lv = None
        self._last_stereo = None
        self._current_sound = None
        self._play_after_id = None

        self.root = tk.Tk()
        self.root.title("PROLACTIN -- Level Validator")
        self._build_widgets()
        self._reload_engine(profile)

    # -- engine lifecycle --------------------------------------------------

    def _profiles_in_config(self):
        import json
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return list(cfg.get("profiles", {}).keys())
        except Exception:  # noqa: BLE001
            return []

    def _reload_engine(self, profile=None):
        fade = self._safe_float(self.fade_var.get(), 0.05)
        try:
            self._lv = LevelValidator(self.config_path, profile=profile,
                                      fade_time=fade)
        except Exception as ex:  # noqa: BLE001
            self.messagebox.showerror("Calibration error", str(ex))
            self._lv = None
            self._refresh_anchor_display()
            return
        # Populate / refresh profile dropdown.
        profs = self._profiles_in_config()
        if profs:
            self.profile_combo["values"] = profs
            self.profile_var.set(self._lv.cm.active_profile)
        self._refresh_anchor_display()
        self._set_readout(
            f"Loaded profile '{self._lv.cm.active_profile}' "
            f"(SPL calibrated={self._lv.cm.spl_calibrated}, "
            f"FIR calibrated={self._lv.cm.fir_calibrated}).")

    def _refresh_anchor_display(self):
        """Update the read-only measured_spl_left/right readout from the
        currently loaded profile. Purely informational."""
        if self._lv is None:
            self.anchor_var.set("(not loaded)")
            return
        try:
            spl_cfg = self._lv.cm._profile["spl_calibration"]
            left = spl_cfg.get("measured_spl_left")
            right = spl_cfg.get("measured_spl_right")
            ref = spl_cfg.get("reference_amplitude")
        except Exception:  # noqa: BLE001
            self.anchor_var.set("(no spl_calibration block)")
            return
        if left is None or right is None:
            self.anchor_var.set("measured_spl_left/right: null (uncalibrated)")
            return
        ref_txt = "null" if ref is None else f"{float(ref):.8f}"
        self.anchor_var.set(
            f"measured_spl_left: {float(left):.1f}    "
            f"measured_spl_right: {float(right):.1f}    "
            f"ref_amp: {ref_txt}")

    def _on_reload(self):
        """Re-read calibration_config.json from disk and rebuild the engine.

        Lets the operator edit measured_spl_left/right in the JSON, save, and
        pick up the new constants without restarting the script.
        """
        if self._current_sound is not None:
            self._stop_playback()
        self.config_path = self.config_var.get() or self.config_path
        # Keep the selected profile if it still exists in the reloaded config.
        wanted = self.profile_var.get() or None
        if wanted is not None and wanted not in self._profiles_in_config():
            wanted = None
        self._reload_engine(wanted)

    def _on_profile_change(self, *_):
        if self._lv is None:
            return
        self._reload_engine(self.profile_var.get())

    # -- widgets -----------------------------------------------------------

    def _build_widgets(self):
        tk, ttk = self.tk, self.ttk
        pad = {"padx": 6, "pady": 4}
        frm = ttk.Frame(self.root, padding=12)
        frm.grid(sticky="nsew")

        r = 0
        ttk.Label(frm, text="Config:").grid(row=r, column=0, sticky="e", **pad)
        self.config_var = tk.StringVar(value=str(self.config_path))
        ttk.Entry(frm, textvariable=self.config_var, width=42).grid(
            row=r, column=1, columnspan=2, sticky="we", **pad)
        ttk.Button(frm, text="Browse", command=self._pick_config).grid(
            row=r, column=3, **pad)

        r += 1
        ttk.Label(frm, text="Profile:").grid(row=r, column=0, sticky="e", **pad)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            frm, textvariable=self.profile_var, state="readonly", width=30)
        self.profile_combo.grid(row=r, column=1, columnspan=2, sticky="we", **pad)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)
        ttk.Button(frm, text="Reload", command=self._on_reload).grid(
            row=r, column=3, **pad)

        r += 1
        ttk.Label(frm, text="SPL anchor:").grid(row=r, column=0, sticky="e", **pad)
        self.anchor_var = tk.StringVar(value="(not loaded)")
        ttk.Label(frm, textvariable=self.anchor_var, foreground="#444444"
                  ).grid(row=r, column=1, columnspan=3, sticky="w", **pad)

        r += 1
        ttk.Label(frm, text="Stimulus:").grid(row=r, column=0, sticky="e", **pad)
        self.type_var = tk.StringVar(value="tone")
        ttk.Combobox(frm, textvariable=self.type_var, state="readonly",
                     width=12, values=list(LevelValidator.SUPPORTED_TYPES)
                     ).grid(row=r, column=1, sticky="w", **pad)

        r += 1
        ttk.Label(frm, text="Level:").grid(row=r, column=0, sticky="e", **pad)
        self.level_var = tk.StringVar(value="70")
        ttk.Entry(frm, textvariable=self.level_var, width=10).grid(
            row=r, column=1, sticky="w", **pad)
        self.units_var = tk.StringVar(value="dB SPL")
        ttk.Combobox(frm, textvariable=self.units_var, state="readonly",
                     width=8, values=["dB SPL", "dB HL"]).grid(
            row=r, column=2, sticky="w", **pad)

        r += 1
        ttk.Label(frm, text="Freq (Hz):").grid(row=r, column=0, sticky="e", **pad)
        self.freq_var = tk.StringVar(value="1000")
        ttk.Entry(frm, textvariable=self.freq_var, width=10).grid(
            row=r, column=1, sticky="w", **pad)

        r += 1
        ttk.Label(frm, text="Sweep f0/f1:").grid(
            row=r, column=0, sticky="e", **pad)
        self.f0_var = tk.StringVar(value="20")
        self.f1_var = tk.StringVar(value="20000")
        ttk.Entry(frm, textvariable=self.f0_var, width=10).grid(
            row=r, column=1, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.f1_var, width=10).grid(
            row=r, column=2, sticky="w", **pad)

        r += 1
        ttk.Label(frm, text="Duration (s):").grid(
            row=r, column=0, sticky="e", **pad)
        self.dur_var = tk.StringVar(value="10")
        ttk.Entry(frm, textvariable=self.dur_var, width=10).grid(
            row=r, column=1, sticky="w", **pad)
        ttk.Label(frm, text="Fade (s):").grid(row=r, column=2, sticky="e", **pad)
        self.fade_var = tk.StringVar(value="0.05")
        ttk.Entry(frm, textvariable=self.fade_var, width=8).grid(
            row=r, column=3, sticky="w", **pad)

        r += 1
        ttk.Label(frm, text="Ear:").grid(row=r, column=0, sticky="e", **pad)
        self.ear_var = tk.StringVar(value="left")
        ttk.Combobox(frm, textvariable=self.ear_var, state="readonly",
                     width=8, values=["both", "left", "right"]).grid(
            row=r, column=1, sticky="w", **pad)

        r += 1
        ttk.Label(frm, text="WAV file:").grid(row=r, column=0, sticky="e", **pad)
        self.wav_in_var = tk.StringVar(value="")
        ttk.Entry(frm, textvariable=self.wav_in_var, width=42).grid(
            row=r, column=1, columnspan=2, sticky="we", **pad)
        ttk.Button(frm, text="Browse", command=self._pick_input_wav).grid(
            row=r, column=3, **pad)

        r += 1
        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=4, sticky="w", pady=(10, 4))
        ttk.Button(btns, text="Preview (build)", command=self._on_build).pack(
            side="left", padx=4)
        self._play_btn = ttk.Button(btns, text="Play",
                                    command=self._on_play_stop)
        self._play_btn.pack(side="left", padx=4)
        ttk.Button(btns, text="Render WAV...", command=self._on_render).pack(
            side="left", padx=4)
        ttk.Button(btns, text="Exit", command=self._on_exit).pack(
            side="left", padx=4)

        r += 1
        self.readout = tk.Text(frm, width=64, height=12, wrap="none")
        self.readout.grid(row=r, column=0, columnspan=4, sticky="nsew", **pad)
        self.readout.configure(state="disabled")

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _safe_float(s, default):
        try:
            return float(s)
        except (TypeError, ValueError):
            return default

    def _set_readout(self, text):
        self.readout.configure(state="normal")
        self.readout.delete("1.0", "end")
        self.readout.insert("1.0", text)
        self.readout.configure(state="disabled")

    def _pick_config(self):
        path = self.filedialog.askopenfilename(
            title="Select calibration_config.json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if path:
            self.config_var.set(path)
            self.config_path = path
            self._reload_engine()

    def _pick_input_wav(self):
        path = self.filedialog.askopenfilename(
            title="Select WAV stimulus",
            filetypes=[("WAV", "*.wav"), ("All files", "*.*")])
        if path:
            self.wav_in_var.set(path)

    def _gather_params(self):
        return dict(
            stim_type=self.type_var.get(),
            level=self._safe_float(self.level_var.get(), 70.0),
            units=self.units_var.get(),
            freq=self._safe_float(self.freq_var.get(), 1000.0),
            dur=self._safe_float(self.dur_var.get(), 0.5),
            ear=self.ear_var.get(),
            f0=self._safe_float(self.f0_var.get(), 20.0),
            f1=self._safe_float(self.f1_var.get(), 20000.0),
            wav_path=(self.wav_in_var.get() or None),
        )

    def _build_current(self):
        if self.config_var.get() != self.config_path:
            self.config_path = self.config_var.get()
            self._reload_engine(self.profile_var.get() or None)
        if self._lv is None:
            raise RuntimeError("No calibration loaded.")
        self._lv.fade_time = self._safe_float(self.fade_var.get(), 0.05)
        p = self._gather_params()
        stereo, info = self._lv.build(
            p["stim_type"], p["level"], units=p["units"], freq=p["freq"],
            dur=p["dur"], ear=p["ear"], f0=p["f0"], f1=p["f1"],
            wav_path=p["wav_path"])
        self._last_stereo = stereo
        return stereo, info

    # -- button handlers ---------------------------------------------------

    def _on_build(self):
        try:
            _, info = self._build_current()
            self._set_readout(LevelValidator.format_info(info))
        except Exception as ex:  # noqa: BLE001
            self.messagebox.showerror("Build error", str(ex))

    def _on_play_stop(self):
        # Toggle: if something is playing, this click stops it.
        if self._current_sound is not None:
            self._stop_playback()
            return
        try:
            stereo, info = self._build_current()
            # Non-blocking play so the Stop button stays responsive.
            self._current_sound = self._lv.play_samples(stereo, block=False)
            self._play_btn.config(text="Stop")
            self._set_readout(LevelValidator.format_info(info) + "\n\nPlaying...")
            secs = stereo.shape[0] / self._lv.fs
            self._play_after_id = self.root.after(
                int(secs * 1000) + 100, self._playback_finished)
        except Exception as ex:  # noqa: BLE001
            self._current_sound = None
            self._play_btn.config(text="Play")
            self.messagebox.showerror("Playback error", str(ex))

    def _stop_playback(self):
        """Stop playback early (user pressed Stop)."""
        snd = self._current_sound
        if snd is not None:
            try:
                snd.stop()
            except Exception:  # noqa: BLE001
                pass
        self._playback_finished(stopped=True)

    def _playback_finished(self, stopped=False):
        """Reset UI when playback ends (naturally or via Stop)."""
        if self._play_after_id is not None:
            try:
                self.root.after_cancel(self._play_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._play_after_id = None
        self._current_sound = None
        self._play_btn.config(text="Play")
        cur = self.readout.get("1.0", "end").rstrip()
        tail = "\n\nStopped." if stopped else "\n\nDone."
        if cur.endswith("Playing..."):
            cur = cur[: -len("Playing...")].rstrip()
        self._set_readout(cur + tail)

    def _on_exit(self):
        self._stop_playback()
        self.root.destroy()

    def _on_render(self):
        try:
            stereo, info = self._build_current()
            path = self.filedialog.asksaveasfilename(
                title="Save rendered WAV", defaultextension=".wav",
                filetypes=[("WAV", "*.wav")])
            if not path:
                return
            out = self._lv.write_wav(path, stereo)
            self._set_readout(LevelValidator.format_info(info)
                              + f"\n\nWrote WAV: {out}")
        except Exception as ex:  # noqa: BLE001
            self.messagebox.showerror("Render error", str(ex))

    def run(self):
        self.root.mainloop()


# ======================================================================
# Entry point
# ======================================================================

def main(argv=None):
    args = _build_arg_parser().parse_args(argv)
    if args.no_gui:
        return run_cli(args)
    gui = LevelValidatorGUI(config_path=args.config, profile=args.profile)
    gui.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
