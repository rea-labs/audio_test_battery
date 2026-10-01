"""
Speech Recognition Threshold (SRT) Paradigm

Adaptive threshold detection for speech intelligibility in quiet, using
single-word stimuli loaded from WAV files (e.g. Freiburger Einsilber).

Adaptive parameter : trial_amp (dB SPL) -- name kept for CSV compatibility
Outer variables    : Pan (typically [0.0] for diotic)
Stimulus source    : *.wav files in a folder

The participant repeats each spoken word aloud. The EXAMINER (operator) rates
the response as correct (1) or incorrect (0). Amplitude adapts:
  correct   -> quieter (harder)
  incorrect -> louder (easier)

Words are RMS-normalised to 1/sqrt(2) at load time so that requested dB SPL
matches acoustic dB SPL on the calibrated headphone (sine-referenced
spl_to_amplitude expects unit-peak / RMS = 1/sqrt(2) input).

Catch trials are disabled: examiner-rated tests don't need them.

Requires a CalibrationManager with valid SPL calibration (clinical paradigm).
SRT bypasses TrialPlayer (single WAV-driven event per trial; mirrors the
ITD pattern of routing samples through CalibrationManager.prepare_sound
directly and storing the resulting Sound for execute_trial to play).
"""

import time
from math import gcd
from pathlib import Path

import numpy as np
import tkinter as tk
from scipy.io import wavfile
from scipy.signal import resample_poly

from paradigms.adaptive_paradigm import AdaptiveParadigm
from utils.varspec import VarSpec


class ParadigmSRT(AdaptiveParadigm):
    """
    Speech Recognition Threshold -- single-word adaptive, examiner-rated.

    Trial flow
    ----------
    1. Word WAV is played at the current adaptive level (dB SPL) to one ear
       (or both, depending on pan).
    2. Participant repeats the word aloud.
    3. Examiner presses 1 (correct) or 0 (incorrect / not heard).
    4. Correct  -> level decreases (quieter)
       Incorrect -> level increases (louder)

    Word files
    ----------
    Must be *.wav, mono or stereo (first channel used), any sample rate
    (resampled to self.fs automatically). Each file is RMS-normalised to
    1/sqrt(2) at load time.
    """

    def __init__(self, params: dict, wav_dir, verbose=False,
                 gui_config=None, participant_id=None):
        """
        Args:
            params:         Must include 'inner' (trial_amp VarSpec, dB SPL).
                            Optionally 'outer_*' for pan, etc.
            wav_dir:        Path to folder containing word WAV files.
            verbose:        Print debug info.
            gui_config:     Optional GUI customization (uses good defaults).
            participant_id: Participant ID for data file naming.
        """
        # CRITICAL: set paradigm_code before super().__init__()
        self.paradigm_code = 'SRT'
        self.demo_duration_attr = 'trial_dur'

        # Hardcoded sample rate. TODO: replace with project-wide constant
        # (DEFAULTS["fs"]) once the experimental manager refactor lands.
        self.fs = 48000

        # WAV pool: loaded once at __init__, shuffled per config
        self.wav_dir = Path(wav_dir)
        self._word_pool_all = self._load_words()    # [(name, mono_samples), ...]
        self._word_pool = []                        # current config's working list
        self._current_word_name = ""                # set per trial
        self._srt_sound = None                      # PTB Sound from prepare_sound
        self.trial_dur = 0.5                        # updated per trial from WAV length

        # Set up GUI config if not provided
        if gui_config is None:
            gui_config = {
                'question': "Participant repeated correctly?",
                'options': ['No (0)', 'Yes (1)'],
                'keys': ['0', '1'],
                'window_title': "Speech Recognition Threshold",
                'window_geometry': "640x360+100+100",
                'font_size': 15,
            }

        # Call parent constructor
        super().__init__(params, verbose=verbose, gui_config=gui_config,
                         participant_id=participant_id)

        # Track last two presented levels for midpoint reset (Lecluyse & Meddis 2009)
        self.last_two_levels = []

        # Per-ear amplitudes (audit trail; populated in prepare_trial)
        self._last_amp_L = None
        self._last_amp_R = None

    # ==================================================================
    # WAV loading
    # ==================================================================

    def _load_words(self):
        """
        Load all *.wav files from self.wav_dir.

        Each file is:
          - Mixed to mono (first channel taken if stereo)
          - Converted to float32 in [-1, 1]
          - Resampled to self.fs if needed
          - RMS-normalised to 1/sqrt(2)
            (so a unit-peak sine and a unit-RMS-after-norm signal produce
            the same SPL through spl_to_amplitude, which is sine-referenced)

        Returns:
            list of (filename_stem, float32_mono_samples).

        Raises:
            FileNotFoundError if folder contains no WAV files.
        """
        wavs = sorted(self.wav_dir.glob("*.wav"))
        if not wavs:
            raise FileNotFoundError(
                f"[SRT] No WAV files found in '{self.wav_dir}'. "
                f"Set wav_dir to your stimulus folder."
            )

        target_rms = 1.0 / np.sqrt(2.0)
        pool = []
        for p in wavs:
            file_fs, data = wavfile.read(str(p))

            # Convert to float32 in [-1, 1] based on integer dtype range.
            # scipy.io.wavfile returns int16/int32/uint8/float32 depending on file.
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0
            elif data.dtype == np.uint8:
                # uint8 WAV is offset-binary (centered at 128)
                data = (data.astype(np.float32) - 128.0) / 128.0
            elif data.dtype == np.float32:
                data = data.copy()
            elif data.dtype == np.float64:
                data = data.astype(np.float32)
            else:
                raise ValueError(
                    f"[SRT] Unsupported WAV dtype {data.dtype} in '{p.name}'"
                )

            # Mono-mix (first channel if stereo)
            if data.ndim == 2:
                data = data[:, 0]

            # Resample to target fs
            if file_fs != self.fs:
                g = gcd(self.fs, file_fs)
                data = resample_poly(data, self.fs // g, file_fs // g
                                     ).astype(np.float32)

            # RMS-normalise to 1/sqrt(2)
            rms_val = float(np.sqrt(np.mean(data ** 2)))
            if rms_val > 1e-9:
                data = (data * (target_rms / rms_val)).astype(np.float32)

            pool.append((p.stem, data))

        print(f"[SRT] Loaded {len(pool)} words from '{self.wav_dir}'")
        return pool

    # ==================================================================
    # AdaptiveParadigm overrides -- adaptive logic
    # ==================================================================

    def initialize_adaptive_param(self):
        """
        Set initial level (dB SPL) from inner variable config with randomization.
        Also reshuffles the word pool for the new config.

        Per MultiThreshold protocol: randomize start within +/- half of
        initial step size to ensure supra-threshold start.
        """
        if isinstance(self.inner_var.data, dict):
            base_start = self.inner_var.data.get('start', 50.0)             # dB SPL
            step_down_initial = abs(self.inner_var.data.get('step_down_initial', -10))
            randomize_dB = step_down_initial / 2.0

            offset_dB = float(self._rng.uniform(-randomize_dB, randomize_dB))
            self.trial_amp = base_start + offset_dB

            min_level = self.inner_var.data.get('min', 0.0)
            max_level = self.inner_var.data.get('max', 90.0)
            self.trial_amp = max(min_level, min(max_level, self.trial_amp))

            if self.verbose:
                print(f"Initial level: {self.trial_amp:.1f} dB SPL")
                print(f"  (base: {base_start:.1f} dB SPL, "
                      f"offset: {offset_dB:+.1f} dB, "
                      f"range: +/-{randomize_dB:.1f} dB)")
        else:
            self.trial_amp = 50.0
            if self.verbose:
                print(f"Initial level: {self.trial_amp:.1f} dB SPL")

        # Reset midpoint tracker
        self.last_two_levels = []

        # Shuffle word pool (no repeats within config)
        self._word_pool = list(self._word_pool_all)
        self._rng.shuffle(self._word_pool)
        self._current_word_name = ""
        if self.verbose:
            print(f"[SRT] Word pool shuffled "
                  f"({len(self._word_pool)} words, no repeats)")

    def prepare_trial(self):
        """
        Pick the next word, scale to current level (dB SPL), and prepare
        the Sound object via CalibrationManager.

        SRT bypasses TrialPlayer (single WAV-driven event per trial);
        the path mirrors ITD: build stereo numpy array, route through
        prepare_sound for FIR + per-channel gain, store the resulting
        Sound for execute_trial.
        """
        self.trial_num += 1

        # SRT requires a calibrated SPL profile.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "SRT requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )

        # Sanity check: calibration profile sample rate must match self.fs,
        # otherwise prepare_sound raises. (Words are pre-resampled to self.fs
        # at load time; if the profile is at a different rate we have no way
        # to recover here.)
        if self.calibration.sample_rate != self.fs:
            raise RuntimeError(
                f"SRT: calibration profile sample rate "
                f"{self.calibration.sample_rate} Hz does not match "
                f"paradigm fs {self.fs} Hz. Words were pre-resampled to "
                f"{self.fs} Hz at load and cannot be re-resampled here."
            )

        # Word pool exhausted -> end the config gracefully.
        if not self._word_pool:
            print("[SRT] Word pool exhausted -- ending config.")
            self.end_config = True
            self._current_word_name = "[no words left]"
            # Build a short silent placeholder so execute_trial has something
            # to play (avoids None-handling further down the call chain).
            silent_mono = np.zeros(int(0.2 * self.fs), dtype=np.float32)
            self._srt_sound = self.calibration.prepare_sound(
                silent_mono, self.fs,
                pan=getattr(self, 'pan', 0.0),
                per_channel_gain=None,
            )
            self.trial_dur = 0.2
            self._last_amp_L = 0.0
            self._last_amp_R = 0.0
            return

        # Pull next word from the shuffled pool
        name, samples = self._word_pool.pop(0)
        self._current_word_name = name
        self.trial_dur = len(samples) / self.fs

        # Convert dB SPL -> per-ear amplitudes (both ears want same SPL,
        # single call returns (amp_L, amp_R) absorbing per-ear sensitivity).
        amp_L, amp_R = self.calibration.spl_to_amplitude(self.trial_amp)
        self._last_amp_L = amp_L
        self._last_amp_R = amp_R

        # Track this presented level for midpoint reset
        self.last_two_levels.append(self.trial_amp)
        if len(self.last_two_levels) > 2:
            self.last_two_levels.pop(0)

        if self.verbose:
            print(f"  -> Word: '{name}' @ {self.trial_amp:.1f} dB SPL "
                  f"(dur={self.trial_dur:.3f} s)")

        # Route through calibration: mono samples + pan + per_channel_gain
        # (prepare_sound handles mono->stereo, pan zeroing, per-ear gain,
        # FIR convolution, and PTB Sound wrapping).
        self._srt_sound = self.calibration.prepare_sound(
            samples, self.fs,
            pan=getattr(self, 'pan', 0.0),
            per_channel_gain=(amp_L, amp_R),
        )

    def execute_trial(self):
        """
        Override: play the prepared SRT Sound directly (bypassing TrialPlayer).
        Mirrors the ITD bypass pattern.
        """
        self.trial_repeats += 1

        if self._srt_sound is None:
            raise RuntimeError("execute_trial() called before prepare_trial()")

        if self.verbose:
            print(f"Playing SRT word (trial repeat {self.trial_repeats})...")

        self._srt_sound.play()

        # Wait for playback. FIR convolution extends the buffer by ringout
        # tail (~85 ms with current 4096-tap @ 48 kHz IRs); pad the wait
        # when calibration is active.
        ringout_pad = (self.calibration.ringout_seconds
                       if self.calibration is not None else 0.0)
        time.sleep(self.trial_dur + ringout_pad + 0.1)

    def play_demo_trial(self, demo_vals: dict) -> None:
        """Override: use execute_trial (SRT bypasses TrialPlayer)."""
        saved = {k: getattr(self, k, None) for k in demo_vals}
        try:
            for k, v in demo_vals.items():
                setattr(self, k, v)
            self.is_catch_trial = False
            self.prepare_trial()
            self.execute_trial()
        finally:
            for k, v in saved.items():
                setattr(self, k, v)
            self._reset_trial_state()

    def adapt_difficulty(self, direction):
        """
        Adjust level (dB SPL) -- additive math, PTA pattern.
        Harder = quieter, easier = louder.
        """
        if isinstance(self.inner_var.data, dict):
            if self.total_num_reversals == 0:
                step_down = self.inner_var.data.get('step_down_initial', -10)
                step_up = self.inner_var.data.get('step_up_initial', 10)
            else:
                step_down = self.inner_var.data.get('step_down_final', -2)
                step_up = self.inner_var.data.get('step_up_final', 2)
            min_level = self.inner_var.data.get('min', 0.0)
            max_level = self.inner_var.data.get('max', 90.0)
        else:
            step_down = -10 if self.total_num_reversals == 0 else -2
            step_up = 10 if self.total_num_reversals == 0 else 2
            min_level = 0.0
            max_level = 90.0

        if direction == "harder":
            self.trial_amp += step_down
            self.trial_amp = max(self.trial_amp, min_level)
            if self.verbose:
                print(f"  -> Harder: {self.trial_amp:.1f} dB SPL "
                      f"(step: {step_down} dB)")
        elif direction == "easier":
            self.trial_amp += step_up
            self.trial_amp = min(self.trial_amp, max_level)
            if self.verbose:
                print(f"  -> Easier: {self.trial_amp:.1f} dB SPL "
                      f"(step: {step_up} dB)")

    def reset_to_midpoint_amplitude(self):
        """
        Reset level to midpoint between last two presented levels.
        Called after first reversal per MultiThreshold protocol
        (Lecluyse & Meddis 2009).
        """
        if len(self.last_two_levels) == 2:
            midpoint_dB = (self.last_two_levels[0] + self.last_two_levels[1]) / 2.0
            self.trial_amp = midpoint_dB
            if self.verbose:
                print(f"  -> Reset to midpoint: {midpoint_dB:.1f} dB SPL "
                      f"(between {self.last_two_levels[0]:.1f} and "
                      f"{self.last_two_levels[1]:.1f})")
        else:
            if self.verbose:
                print(f"  -> Warning: cannot reset to midpoint "
                      f"(need 2 levels, have {len(self.last_two_levels)})")

    def update_trial_params(self):
        """Handle midpoint reset before normal difficulty adjustment (PTA pattern)."""
        if self.reset_to_midpoint:
            self.reset_to_midpoint_amplitude()
            self.reset_to_midpoint = False
            self.make_harder = False
            self.make_easier = False
        super().update_trial_params()

    def determine_catch_trial(self):
        """SRT uses no catch trials -- examiner-rated tests don't need them."""
        self.is_catch_trial = False

    # ==================================================================
    # GUI overrides -- show the target word on the examiner's screen
    # ==================================================================

    @property
    def _display_word(self) -> str:
        """Word label shown to the examiner."""
        return self._current_word_name or "..."

    def update_gui_state(self, trial_playing=True):
        """
        Override: show a big word label so the examiner sees the target
        while playback is happening (and while rating).
        """
        if self.root is None:
            return

        for widget in self.root.winfo_children():
            widget.destroy()

        font_size = self.gui_config['font_size']

        if trial_playing:
            tk.Label(self.root,
                     text="Playing...",
                     font=("Arial", font_size - 2),
                     fg="grey").pack(pady=(12, 4))
            tk.Label(self.root,
                     text=self._display_word,
                     font=("Arial", font_size + 14, "bold"),
                     fg="#1a1a1a", bg="#e8f4e8",
                     relief="ridge", padx=24, pady=10).pack(pady=(0, 12))
        else:
            # Rating phase: word label + question (buttons rebuilt by get_response)
            tk.Label(self.root,
                     text=self._display_word,
                     font=("Arial", font_size + 14, "bold"),
                     fg="#1a1a1a", bg="#e8f4e8",
                     relief="ridge", padx=24, pady=10).pack(pady=(12, 6))
            tk.Label(self.root,
                     text=self.gui_config['question'],
                     font=("Arial", font_size)).pack(pady=(0, 6))

        self.root.update()

    def get_response(self, trial_playing=True):
        """
        Override: same response collection as the base class but with the
        target word shown prominently above the question and buttons.
        """
        if self.root is None:
            return None

        result = {'value': None}
        response_registered = {'flag': False}
        num_options = len(self.gui_config['options'])
        allow_repeat = self.gui_config['allow_repeat']
        font_size = self.gui_config['font_size']

        def respond(value):
            if response_registered['flag']:
                return
            response_registered['flag'] = True
            for widget in self.root.winfo_children():
                widget.destroy()
            tk.Label(self.root,
                     text="...",
                     font=("Arial", font_size)).pack(pady=20)
            self.root.update()
            result['value'] = None if value == "repeat" else value
            self.root.quit()

        def on_key(event):
            if response_registered['flag']:
                return
            for i, key in enumerate(self.gui_config['keys']):
                if event.char == key:
                    respond(i)
                    return
            if allow_repeat and event.char.lower() == 'r':
                respond("repeat")

        # Build layout
        for widget in self.root.winfo_children():
            widget.destroy()

        # Big word label
        tk.Label(self.root,
                 text=self._display_word,
                 font=("Arial", font_size + 14, "bold"),
                 fg="#1a1a1a", bg="#e8f4e8",
                 relief="ridge", padx=24, pady=10).pack(pady=(12, 6))

        # Question
        tk.Label(self.root,
                 text=self.gui_config['question'],
                 font=("Arial", font_size)).pack(pady=(0, 6))

        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack()
        for i, option_text in enumerate(self.gui_config['options']):
            tk.Button(button_frame,
                      text=option_text,
                      width=14,
                      command=lambda idx=i: respond(idx)
                      ).grid(row=0, column=i, padx=10)
        if allow_repeat:
            tk.Button(button_frame,
                      text="Repeat (R)",
                      width=14,
                      command=lambda: respond("repeat")
                      ).grid(row=1, column=0, columnspan=num_options,
                             pady=(8, 0))

        # Flush any queued events before binding keyboard
        self.root.update()
        self.root.update_idletasks()
        self.root.bind("<KeyRelease>", on_key)
        self.root.update_idletasks()
        self.root.mainloop()
        self.root.unbind("<KeyRelease>")

        return result['value']

    # ==================================================================
    # Logging / metadata
    # ==================================================================

    def get_log_data(self):
        """
        SRT-specific per-row log columns.

        Per-row:
        - trial_amp: Adaptive level in dB SPL (no conversion -- like PTA)
        - word: Filename stem of the played word
        - trial_dur: Word duration in seconds
        - pan: -1.0 / 0.0 / +1.0
        """
        return {
            "trial_amp": self.trial_amp,
            "word": self._current_word_name,
            "trial_dur": round(self.trial_dur, 4),
            "pan": getattr(self, 'pan', 0.0),
        }

    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for SRT CSVs."""
        return {
            "level_units": "dB SPL",
            # HL = PTA only (team decision 2026-06-11). Also invalid for a broadband
            # speech threshold anyway: needs a speech RETSPL (IEC 60645), not the
            # pure-tone RETSPL(fc). Suppressed explicitly.
            "hl_reportable": False,
            "wav_dir": str(self.wav_dir),
            "wav_count": len(self._word_pool_all),
            "wav_rms_norm": "1/sqrt(2)",
        }

    def get_trial_description(self) -> str:
        pan = getattr(self, 'pan', 0.0)
        ear = "Left" if pan < 0 else ("Right" if pan > 0 else "Both")
        return (f"Config {self.config_num}/{self.total_num_configs} "
                f"({ear} ear), Trial {self.trial_num}")


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("SRT Paradigm -- shape reference (not runnable here)")
    print("=" * 60)
    print("\nThis __main__ block does not run the paradigm directly because")
    print("SRT requires a CalibrationManager and a WAV folder. Run")
    print("test_srt.py instead.")
