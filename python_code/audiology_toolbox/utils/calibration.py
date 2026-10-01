"""
CalibrationManager - headphone calibration for PROLACTIN.

Two calibration layers:
  1. Frequency response correction via FIR inverse filter convolution
  2. Absolute SPL mapping via measured amplitude-to-SPL reference

The prepare_sound() method is the single gateway through which all audio
is routed before playback. It is a thin wrapper around prepare_samples(),
which does the actual math:
  - Mono -> stereo conversion (with optional pan)
  - Per-channel gain scaling (for paradigms that use dB SPL)
  - FIR inverse filter convolution
  - Safety clipping check

prepare_sound() then wraps the result in a PsychoPy Sound object.
Test / utility code that needs the post-calibration ndarray directly
(e.g. to write a WAV for offline acoustic verification) should call
prepare_samples() instead.

Design: optional dependency. TrialPlayer and paradigms accept an instance
or None. If None, current uncalibrated behavior is preserved.

State is tracked with two independent flags:
  - fir_calibrated: left AND right IR WAVs loaded successfully
  - spl_calibrated: reference_amplitude + measured_spl_left + measured_spl_right
                    are all non-null

Either flag may be False independently (e.g. SPL measured but FIR pending).
Calibration-dependent methods raise or warn based on which flag is required.

See phase_b_calibration_plan.md for the full design rationale.
"""

import json
import warnings
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, resample_poly


# psychopy.sound is imported lazily inside prepare_sound() so that this
# module can be used offline (unit tests, IR-generation utilities) without
# pulling in the PsychoPy runtime.


class CalibrationError(RuntimeError):
    """Raised when a calibrated operation is attempted without valid data."""


class CalibrationManager:
    """
    Manages headphone calibration: FIR inverse filters + dB SPL mapping.

    Parameters
    ----------
    config_path : str or Path
        Path to calibration_config.json. Inverse filter WAV paths inside
        the config are resolved relative to the config file's parent
        directory (not the current working directory).
    profile : str, optional
        Which profile to load. Defaults to
        config/DEFAULTS.py["default_headphone_calibration_profile"].
    """

    # ------------------------------------------------------------------
    # Construction / loading
    # ------------------------------------------------------------------

    def __init__(self,
                 config_path: Union[str, Path],
                 profile: Optional[str] = None):
        self._config_path = Path(config_path).resolve()
        if not self._config_path.is_file():
            raise FileNotFoundError(
                f"Calibration config not found: {self._config_path}"
            )
        self._config_dir = self._config_path.parent
        self._raw_config = None       # full JSON document
        self._profile_name = profile  # None -> default from config/DEFAULTS.py
        self._profile = None          # the active profile dict
        self._ir_left = None          # 1D numpy float array or None
        self._ir_right = None         # 1D numpy float array or None
        self._sample_rate = None      # system sample rate from profile
        self._sound_cls = None        # cached psychopy.sound.Sound class
        self._hl_converter = None     # HLConverter or None (optional dB HL layer)

        self.load_config()
        self.load_inverse_filters()
        self.load_hl_converter()

        # Emit one-shot warnings about partial-calibration state.
        if not self.spl_calibrated:
            warnings.warn(
                f"CalibrationManager: profile '{self.active_profile}' has "
                f"null SPL calibration values. spl_to_amplitude() will raise.",
                stacklevel=2,
            )
        if not self.fir_calibrated:
            warnings.warn(
                f"CalibrationManager: profile '{self.active_profile}' is "
                f"missing one or both inverse filter WAVs. prepare_sound() "
                f"will pass audio through without frequency correction.",
                stacklevel=2,
            )

    def load_config(self) -> None:
        """Parse the JSON config and select the active profile."""
        with open(self._config_path, "r", encoding="utf-8") as f:
            self._raw_config = json.load(f)

        if self._profile_name is None:
            # The default profile lives in config/DEFAULTS.py (not in this
            # JSON) so there is a single home for it. Imported lazily and
            # guarded so calibration.py stays usable standalone (e.g. from
            # utility scripts run outside the toolbox package).
            try:
                from config.DEFAULTS import DEFAULTS
                self._profile_name = DEFAULTS.get(
                    "default_headphone_calibration_profile"
                )
            except Exception:
                self._profile_name = None
        if self._profile_name is None:
            raise CalibrationError(
                "No profile specified and no "
                "'default_headphone_calibration_profile' in config/DEFAULTS.py."
            )

        profiles = self._raw_config.get("profiles", {})
        # Case-insensitive profile lookup. Build a lower -> canonical map
        # and resolve the user-supplied name back to the original key, so
        # downstream code and logs use the spelling from the JSON.
        ci_map = {k.lower(): k for k in profiles.keys()}
        requested_lo = self._profile_name.lower()
        if requested_lo not in ci_map:
            raise CalibrationError(
                f"Profile '{self._profile_name}' not found in config. "
                f"Available: {list(profiles)}"
            )
        self._profile_name = ci_map[requested_lo]
        self._profile = profiles[self._profile_name]
        self._sample_rate = int(self._profile.get("sample_rate", 48000))

    def load_inverse_filters(self) -> None:
        """Load left/right FIR inverse filters, resampling if needed."""
        ir_cfg = self._profile.get("inverse_filter", {})
        self._ir_left = self._load_ir(ir_cfg.get("left"), "left")
        self._ir_right = self._load_ir(ir_cfg.get("right"), "right")

    def _load_ir(self,
                 rel_path: Optional[str],
                 channel_label: str) -> Optional[np.ndarray]:
        """Helper: load one IR WAV and normalize/resample as needed."""
        if rel_path is None:
            return None

        ir_path = (self._config_dir / rel_path).resolve()
        if not ir_path.is_file():
            warnings.warn(
                f"CalibrationManager: {channel_label} IR WAV not found: "
                f"{ir_path}. Skipping frequency correction for this channel.",
                stacklevel=2,
            )
            return None

        fs, data = wavfile.read(str(ir_path))

        # Collapse to mono if file is accidentally stereo.
        if data.ndim > 1:
            warnings.warn(
                f"IR WAV {ir_path.name} is multi-channel; using channel 0.",
                stacklevel=2,
            )
            data = data[:, 0]

        # Normalize integer WAVs to float in [-1, 1]; float WAVs pass through.
        if np.issubdtype(data.dtype, np.integer):
            max_val = float(np.iinfo(data.dtype).max)
            data = data.astype(np.float64) / max_val
        else:
            data = data.astype(np.float64)

        # Resample if IR file sample rate differs from profile sample rate.
        if fs != self._sample_rate:
            warnings.warn(
                f"IR WAV {ir_path.name} sample rate ({fs} Hz) differs from "
                f"profile sample rate ({self._sample_rate} Hz). Resampling.",
                stacklevel=2,
            )
            data = resample_poly(data, self._sample_rate, fs)

        return data

    def load_hl_converter(self) -> None:
        """
        Build the optional dB SPL <-> dB HL converter from the profile's
        'retspl' block. Absent/null -> HL conversion unavailable (None).

        The 'retspl' block may carry either an inline 'table' ({freq: offset})
        or a 'csv' path (resolved relative to the config file). 'source' is
        an optional provenance label. Any problem (missing hl_converter
        module, bad table, missing CSV) disables HL gracefully with a warning
        rather than failing construction.
        """
        retspl_cfg = self._profile.get("retspl")
        if not retspl_cfg:
            self._hl_converter = None
            return

        try:
            from hl_converter import HLConverter
        except ImportError:
            warnings.warn(
                "CalibrationManager: hl_converter module not found; "
                "dB HL conversion disabled.",
                stacklevel=2,
            )
            self._hl_converter = None
            return

        source = retspl_cfg.get("source")
        table = retspl_cfg.get("table")
        csv_rel = retspl_cfg.get("csv")
        try:
            if table:
                if csv_rel:
                    warnings.warn(
                        "CalibrationManager: profile has both retspl 'table' "
                        "and 'csv'; using 'table'.",
                        stacklevel=2,
                    )
                self._hl_converter = HLConverter(table, source=source)
            elif csv_rel:
                csv_path = (self._config_dir / csv_rel).resolve()
                self._hl_converter = HLConverter.from_csv(csv_path,
                                                          source=source)
            else:
                warnings.warn(
                    "CalibrationManager: 'retspl' present but has no 'table' "
                    "or 'csv'; dB HL conversion disabled.",
                    stacklevel=2,
                )
                self._hl_converter = None
        except (ValueError, FileNotFoundError) as exc:
            warnings.warn(
                f"CalibrationManager: failed to build HLConverter ({exc}); "
                f"dB HL conversion disabled.",
                stacklevel=2,
            )
            self._hl_converter = None

    # ------------------------------------------------------------------
    # Gateway: prepare_samples / prepare_sound
    # ------------------------------------------------------------------

    def prepare_samples(self,
                        samples: np.ndarray,
                        fs: int,
                        pan: Optional[float] = None,
                        per_channel_gain: Optional[Tuple[float, float]] = None
                        ) -> np.ndarray:
        """
        Apply the calibration pipeline and return the stereo sample buffer.

        This is the math half of the playback gateway. `prepare_sound()`
        calls this and then wraps the result in a psychopy.sound.Sound.
        Test / utility code that needs the post-calibration samples
        directly (e.g. to write a WAV for offline analysis) should call
        this method.

        Pipeline:
          1. Mono -> stereo (respecting pan)
          2. Per-channel gain (if provided)
          3. FIR inverse filter convolution (per channel; skipped if IR None)
          4. Peak safety check (warn + clamp if > 1.0)

        Parameters
        ----------
        samples : numpy.ndarray
            1D mono of shape (N,) or 2D stereo (N, 2).
        fs : int
            Sample rate. Must match profile sample rate.
        pan : float or None
            None or 0: diotic. <0: left only. >0: right only.
            Ignored if `samples` is already stereo.
        per_channel_gain : (gain_L, gain_R) or None
            Scalar multiplier per channel, applied after stereo conversion
            and before FIR convolution. Used for SPL asymmetry compensation
            in mono-generating paradigms (IFMC/TMC).

        Returns
        -------
        numpy.ndarray of shape (N + M - 1, 2) where M is the FIR length,
        or (N, 2) if no FIR is loaded.
        """
        if fs != self._sample_rate:
            raise CalibrationError(
                f"prepare_samples: fs={fs} does not match profile sample rate "
                f"{self._sample_rate}. Runtime resampling is not supported."
            )

        samples = np.asarray(samples, dtype=np.float64)

        # 1. Mono -> stereo.
        if samples.ndim == 1:
            if pan is not None and pan < 0:
                stereo = np.column_stack([samples, np.zeros_like(samples)])
            elif pan is not None and pan > 0:
                stereo = np.column_stack([np.zeros_like(samples), samples])
            else:
                stereo = np.column_stack([samples, samples])
        elif samples.ndim == 2 and samples.shape[1] == 2:
            stereo = samples.astype(np.float64, copy=True)
        else:
            raise ValueError(
                f"prepare_sound: samples must be 1D or (N, 2); got shape "
                f"{samples.shape}"
            )

        # 2. Per-channel gain.
        if per_channel_gain is not None:
            g_L, g_R = per_channel_gain
            stereo[:, 0] *= g_L
            stereo[:, 1] *= g_R

        # 3. FIR inverse filter convolution (per channel).
        # Use mode='full' and keep the FULL output (length N + M - 1).
        # The extra M-1 samples past the input's nominal end are the filter's
        # natural ringout, which is designed to cancel the headphone's own
        # post-stimulus ringing. Truncating would leave the headphone's
        # natural decay uncorrected at the ear.
        #
        # For scheduled events (masker->gap->probe etc.), the ringout of
        # event N overlaps event N+1 in time; PsychoPy/PTB mixes overlapping
        # Sound objects in hardware, which is the correct behavior
        # (acoustically, the ringout and the next event DO coexist at the
        # ear).
        #
        # Wrong alternatives tried:
        #   mode='same'     -- skips (M-1)/2 samples from the full
        #                      convolution start, obliterating the input
        #                      fade-in (onset click) AND chopping the
        #                      fade-out region (tail goes to zero early).
        #   mode='full'[:N] -- preserves fade-in but discards the fade-out
        #                      region (which lives in samples [N, N+M-1]
        #                      of the full convolution due to group delay),
        #                      causing an abrupt end-of-stimulus click.
        # See phase_b_calibration_plan.md for the empirical analysis.
        n_in = stereo.shape[0]
        if self._ir_left is not None or self._ir_right is not None:
            # Determine output length from whichever IR is present.
            ir_any = self._ir_left if self._ir_left is not None \
                                    else self._ir_right
            n_out = n_in + len(ir_any) - 1
            conv = np.zeros((n_out, 2), dtype=np.float64)
            if self._ir_left is not None:
                conv[:, 0] = fftconvolve(stereo[:, 0], self._ir_left,
                                         mode="full")
            else:
                conv[:n_in, 0] = stereo[:, 0]
            if self._ir_right is not None:
                conv[:, 1] = fftconvolve(stereo[:, 1], self._ir_right,
                                         mode="full")
            else:
                conv[:n_in, 1] = stereo[:, 1]
            stereo = conv

        # 4. Safety clip.
        peak = float(np.max(np.abs(stereo)))
        if peak > 1.0:
            warnings.warn(
                f"CalibrationManager: peak={peak:.3f} after calibration; "
                f"clamping to +/- 1.0. Check requested dB SPL vs max_spl.",
                stacklevel=2,
            )
            stereo = np.clip(stereo, -1.0, 1.0)

        return stereo

    def prepare_sound(self,
                      samples: np.ndarray,
                      fs: int,
                      pan: Optional[float] = None,
                      per_channel_gain: Optional[Tuple[float, float]] = None):
        """
        Apply the calibration pipeline and return a PsychoPy Sound object.

        Thin wrapper: delegates the math (steps 1-4) to `prepare_samples()`,
        then wraps the resulting ndarray in a psychopy.sound.Sound (step 5).
        See `prepare_samples()` for parameter documentation.

        Returns
        -------
        psychopy.sound.Sound
        """
        stereo = self.prepare_samples(samples, fs, pan=pan,
                                      per_channel_gain=per_channel_gain)

        # 5. Wrap in PsychoPy Sound. Lazy import so this module can be
        # used without pulling in PsychoPy (e.g. for offline tests).
        if self._sound_cls is None:
            from psychopy import sound as _psychopy_sound
            self._sound_cls = _psychopy_sound.Sound

        duration = stereo.shape[0] / fs
        return self._sound_cls(
            value=stereo,
            sampleRate=fs,
            stereo=True,
            secs=duration,
            hamming=False,
        )

    # ------------------------------------------------------------------
    # SPL conversion
    # ------------------------------------------------------------------

    def spl_to_amplitude(self, db_spl: float) -> Tuple[float, float]:
        """
        Convert dB SPL to peak amplitude, per-channel.

        Method: at amp=ref_amp, the measured SPL is ref_spl. For any target,
            amplitude = ref_amp * 10 ** ((target_spl - ref_spl) / 20)

        Returns
        -------
        (amp_L, amp_R) : tuple of float
            Peak amplitudes to produce `db_spl` at each ear.

        Raises
        ------
        CalibrationError if SPL calibration data is null.
        """
        if not self.spl_calibrated:
            raise CalibrationError(
                "SPL calibration data is null. Cannot convert dB SPL to "
                "amplitude. Populate config or run calibrate_spl.py."
            )

        if db_spl > self.max_spl:
            warnings.warn(
                f"Requested {db_spl:.1f} dB SPL exceeds safety limit "
                f"{self.max_spl:.1f} dB SPL. Clamping.",
                stacklevel=2,
            )
            db_spl = self.max_spl

        spl_cfg = self._profile["spl_calibration"]
        ref_amp = float(spl_cfg["reference_amplitude"])
        spl_L = float(spl_cfg["measured_spl_left"])
        spl_R = float(spl_cfg["measured_spl_right"])

        amp_L = ref_amp * 10.0 ** ((db_spl - spl_L) / 20.0)
        amp_R = ref_amp * 10.0 ** ((db_spl - spl_R) / 20.0)
        return amp_L, amp_R

    def amplitude_to_spl(self, amplitude: float, channel: str) -> float:
        """
        Convert peak amplitude back to dB SPL. For display/logging.

        Parameters
        ----------
        amplitude : float
            Peak amplitude (linear).
        channel : str
            'left' or 'right'. Must be explicit; no default.
        """
        if not self.spl_calibrated:
            raise CalibrationError("SPL calibration data is null.")
        if channel not in ("left", "right"):
            raise ValueError(
                f"channel must be 'left' or 'right', got {channel!r}"
            )

        spl_cfg = self._profile["spl_calibration"]
        ref_amp = float(spl_cfg["reference_amplitude"])
        if channel == "left":
            ref_spl = float(spl_cfg["measured_spl_left"])
        else:
            ref_spl = float(spl_cfg["measured_spl_right"])
        return ref_spl + 20.0 * np.log10(amplitude / ref_amp)

    # ------------------------------------------------------------------
    # HL conversion (optional; requires a 'retspl' block in the profile)
    # ------------------------------------------------------------------

    def spl_to_hl(self, db_spl: float, freq_hz: float) -> float:
        """
        Convert dB SPL to dB HL at a given frequency.

        Raises CalibrationError if no RETSPL table is loaded for this
        profile (i.e. hl_calibrated is False).
        """
        if self._hl_converter is None:
            raise CalibrationError(
                f"No RETSPL table loaded for profile '{self.active_profile}'; "
                f"cannot convert to dB HL."
            )
        return self._hl_converter.spl_to_hl(db_spl, freq_hz)

    def hl_to_spl(self, db_hl: float, freq_hz: float) -> float:
        """
        Convert dB HL to dB SPL at a given frequency.

        Raises CalibrationError if no RETSPL table is loaded for this
        profile (i.e. hl_calibrated is False).
        """
        if self._hl_converter is None:
            raise CalibrationError(
                f"No RETSPL table loaded for profile '{self.active_profile}'; "
                f"cannot convert from dB HL."
            )
        return self._hl_converter.hl_to_spl(db_hl, freq_hz)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def max_spl(self) -> float:
        """Hard SPL safety ceiling from profile config."""
        return float(self._profile.get("max_spl", 105.0))

    @property
    def active_profile(self) -> str:
        """Name of the currently loaded profile."""
        return self._profile_name

    @property
    def config_path(self) -> Path:
        """Resolved path to the calibration config JSON this manager loaded.

        Exposed so callers (e.g. the paradigm setup dialog's profile picker)
        can rebuild a CalibrationManager for a different profile without
        having to know where the config lives.
        """
        return self._config_path

    @property
    def available_profiles(self) -> list:
        """All profile names defined in the config, in file order.

        Canonical spelling as written in the JSON (see load_config for the
        case-insensitive lookup applied to user-supplied names).
        """
        return list(self._raw_config.get("profiles", {}).keys())

    @property
    def sample_rate(self) -> int:
        """System sample rate for this profile (Hz)."""
        return self._sample_rate

    @property
    def fir_calibrated(self) -> bool:
        """True if both left and right inverse filters loaded successfully."""
        return self._ir_left is not None and self._ir_right is not None

    @property
    def spl_calibrated(self) -> bool:
        """True if ref_amp, measured_spl_left, measured_spl_right all set."""
        spl_cfg = self._profile.get("spl_calibration", {})
        return (spl_cfg.get("reference_amplitude") is not None
                and spl_cfg.get("measured_spl_left") is not None
                and spl_cfg.get("measured_spl_right") is not None)

    @property
    def hl_converter(self):
        """The HLConverter for this profile, or None if dB HL is unavailable."""
        return self._hl_converter

    @property
    def hl_calibrated(self) -> bool:
        """True if a RETSPL table is loaded and dB HL conversion is possible."""
        return self._hl_converter is not None

    @property
    def is_calibrated(self) -> bool:
        """Convenience: True only when FIR AND SPL are both calibrated."""
        return self.fir_calibrated and self.spl_calibrated

    @property
    def ringout_seconds(self) -> float:
        """
        Length (in seconds) of the FIR convolution tail past the input's end.
        
        prepare_sound() returns audio of length N + M - 1, where M is the IR
        length. Callers that need to wait for the full convolved audio to
        complete (e.g. paradigms bypassing TrialPlayer) should add this to
        their nominal stimulus duration. Returns 0.0 when no FIR is loaded.
        """
        ir = self._ir_left if self._ir_left is not None else self._ir_right
        if ir is None:
            return 0.0
        return (len(ir) - 1) / self._sample_rate

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self) -> None:
        """Print a human-readable summary of calibration state."""
        print("=" * 60)
        print(f"CalibrationManager - profile '{self.active_profile}'")
        print("=" * 60)
        print(f"Config file:       {self._config_path}")
        print(f"Sample rate:       {self._sample_rate} Hz")
        print(f"Max SPL ceiling:   {self.max_spl:.1f} dB SPL")
        print(f"FIR calibrated:    {self.fir_calibrated}")
        if self._ir_left is not None:
            print(f"  left  IR taps:   {len(self._ir_left)}")
        if self._ir_right is not None:
            print(f"  right IR taps:   {len(self._ir_right)}")
        print(f"SPL calibrated:    {self.spl_calibrated}")
        if self.spl_calibrated:
            spl_cfg = self._profile["spl_calibration"]
            print(f"  reference amp:   {spl_cfg['reference_amplitude']} "
                  f"at {spl_cfg.get('reference_frequency_hz', '?')} Hz")
            print(f"  measured L:      {spl_cfg['measured_spl_left']} dB SPL")
            print(f"  measured R:      {spl_cfg['measured_spl_right']} dB SPL")
        print(f"HL calibrated:     {self.hl_calibrated}")
        if self.hl_calibrated:
            lo, hi = self._hl_converter.freq_range_hz
            print(f"  RETSPL source:   {self._hl_converter.source}")
            print(f"  RETSPL range:    {lo:g}-{hi:g} Hz")
        print("=" * 60)
