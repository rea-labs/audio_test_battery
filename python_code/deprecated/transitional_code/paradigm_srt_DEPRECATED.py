"""
Speech Recognition Threshold (SRT) Paradigm — Freiburg Einsilber variant

Adaptive threshold detection for speech intelligibility in quiet.
Measures the quietest level at which a participant can correctly repeat
a spoken word aloud. The examiner (operator) rates each response.

Adaptive parameter : Amplitude (dB FS)
Outer variable     : Ear  (pan = -1.0 left / +1.0 right)
Words              : WAV files from a folder, RMS-normalised at load,
                     drawn in shuffled order, pool reshuffled per config

No background noise is used.  Catch trials play silence (operator should
press 0); they verify the examiner is not guessing.
"""

import numpy as np
import soundfile as sf
import tkinter as tk
from math import gcd
from pathlib import Path

import psychtoolbox as ptb
import psychopy.core as core
from psychopy import sound

from paradigms.adaptive_paradigm import AdaptiveParadigm
from trial_player import TrialPlayer
from utils.varspec import VarSpec


class ParadigmSRT(AdaptiveParadigm):
    """
    Speech Recognition Threshold — single-word adaptive, examiner-rated.

    Trial flow
    ----------
    1. Word WAV is played at the current adaptive amplitude to one ear.
    2. Participant repeats the word aloud.
    3. Examiner presses 1 (correct) or 0 (incorrect / not heard).
    4. Correct  → amplitude decreases (harder, quieter)
       Incorrect → amplitude increases (easier, louder)

    Word files
    ----------
    Must be *.wav, mono or stereo (first channel used), any sample rate
    (resampled to 48 kHz automatically).  Each file is RMS-normalised to
    amplitude 1.0 at load time, then scaled to the adaptive amplitude
    before playback.
    """

    def __init__(self, params: dict, wav_dir: str | Path,
                 verbose: bool = False, gui_config: dict = None,
                 participant_id: str = None):
        """
        Parameters
        ----------
        params         : Must contain 'inner' (amplitude VarSpec) and
                         'outer_1' (pan VarSpec, typically [-1.0, 1.0]).
        wav_dir        : Path to folder containing word WAV files.
        verbose        : Print debug information.
        gui_config     : Optional GUI overrides (uses sensible defaults).
        participant_id : Used for output CSV file naming.
        """
        # CRITICAL: set paradigm_code before super().__init__()
        self.paradigm_code = 'SRT'
        self.fs = 48000

        self.wav_dir = Path(wav_dir)

        # Load and normalise all words before base class init
        self._word_pool_all: list[tuple[str, np.ndarray]] = self._load_words()
        self._word_pool: list[tuple[str, np.ndarray]] = []
        self._current_word_name: str = ""
        self._sound_obj = None
        self.trial_dur: float = 0.5   # Updated per-trial from WAV length

        if gui_config is None:
            gui_config = {
                'question':        "Participant repeated correctly?\n(Examiner response)",
                'options':         ['0 — Incorrect', '1 — Correct'],
                'keys':            ['0', '1'],
                'allow_repeat':    True,
                'window_title':    "SRT — Examiner Interface",
                'window_geometry': "640x360+100+100",
                'font_size':       15,
            }

        super().__init__(params, verbose=verbose, gui_config=gui_config,
                         participant_id=participant_id)

        # Override base-class default (10) to ensure ≥ 20 total trials and
        # more reversals for a reliable SRT threshold estimate.
        # After the first reversal, 20 fine-step (±2 dB) trials run.
        # Typical total: ~5–10 coarse trials + 20 fine trials = 25–30 trials,
        # producing ~6–12 reversals in the fine phase.
        self.trials_after_reversal = 20

    # ------------------------------------------------------------------
    # Word loading
    # ------------------------------------------------------------------

    def _load_words(self) -> list[tuple[str, np.ndarray]]:
        """
        Load all *.wav files from wav_dir.

        Each file is:
          - Mixed to mono  (first channel taken if stereo)
          - Resampled to 48 kHz if needed
          - Normalised to RMS = 1.0

        Returns list of (filename_stem, float32_samples).
        Raises FileNotFoundError if the folder contains no WAV files.
        """
        wavs = sorted(self.wav_dir.glob("*.wav"))
        if not wavs:
            raise FileNotFoundError(
                f"[SRT] No WAV files found in '{self.wav_dir}'.\n"
                f"      Set WAV_DIR in test_srt.py to your stimulus folder.")

        pool = []
        for p in wavs:
            data, file_fs = sf.read(str(p), dtype='float32', always_2d=True)
            mono = data[:, 0]                               # first channel

            # Resample if sample rate does not match
            if file_fs != self.fs:
                from scipy.signal import resample_poly
                g    = gcd(self.fs, file_fs)
                mono = resample_poly(mono, self.fs // g,
                                     file_fs // g).astype(np.float32)

            # RMS normalise
            rms_val = float(np.sqrt(np.mean(mono ** 2)))
            if rms_val > 1e-9:
                mono = mono / rms_val

            pool.append((p.stem, mono))

        print(f"[SRT] Loaded {len(pool)} words from '{self.wav_dir}'")
        return pool

    # ------------------------------------------------------------------
    # AdaptiveParadigm overrides
    # ------------------------------------------------------------------

    def initialize_adaptive_param(self):
        """
        Randomised start amplitude — same logic as PTA.
        Also reshuffles the word pool for the new config.
        """
        if isinstance(self.inner_var.data, dict):
            base_start        = self.inner_var.data.get('start', 0.5)
            step_down_initial = abs(self.inner_var.data.get('step_down_initial', -10))
            randomize_dB      = step_down_initial / 2.0

            base_dB  = TrialPlayer.amp2db(base_start)
            offset   = float(self._rng.uniform(-randomize_dB, randomize_dB))
            start_dB = base_dB + offset

            min_amp = self.inner_var.data.get('min', 0.000001)
            max_amp = self.inner_var.data.get('max', 1.0)
            self.trial_amp = float(np.clip(
                TrialPlayer.db2amp(start_dB), min_amp, max_amp))

            if self.verbose:
                print(f"Initial amplitude: {self.trial_amp:.4f} "
                      f"({TrialPlayer.amp2db(self.trial_amp):.1f} dB FS)")
                print(f"  (base: {base_dB:.1f} dB, offset: {offset:+.1f} dB, "
                      f"range: +/-{randomize_dB:.1f} dB)")
        else:
            self.trial_amp = 0.5

        # Shuffle word pool once — words are NOT reused across the test
        self._word_pool = list(self._word_pool_all)
        self._rng.shuffle(self._word_pool)
        self._current_word_name = ""
        if self.verbose:
            print(f"[SRT] Word pool shuffled ({len(self._word_pool)} words, no repeats)")

    def prepare_trial(self):
        """
        Pick the next word from the pool, scale to current amplitude,
        apply ear routing (pan), and create the PsychoPy Sound object.
        """
        self.trial_num += 1

        # No refill — each word is used exactly once
        if not self._word_pool:
            print("[SRT] Word pool exhausted — ending config.")
            self.end_config = True
            # Silent placeholder so execute_trial() has something to play
            self._current_word_name = "[no words left]"
            silence = np.zeros(int(0.5 * self.fs), dtype=np.float32)
            self._sound_obj = sound.Sound(
                value=np.column_stack([silence, silence]),
                sampleRate=self.fs, stereo=True, secs=0.5, hamming=False)
            self.trial_dur = 0.5
            return

        name, samples = self._word_pool.pop(0)

        if self.is_catch_trial:
            self._current_word_name = f"[catch:{name}]"
            scaled = np.zeros_like(samples)
            if self.verbose:
                print(f"  -> Catch trial (silence), word slot: {name}")
        else:
            self._current_word_name = name
            scaled = (samples * self.trial_amp).astype(np.float32)
            if self.verbose:
                print(f"  -> Word: '{name}' @ "
                      f"{TrialPlayer.amp2db(self.trial_amp):.1f} dB FS")

        # Mono → stereo with ear routing
        pan = getattr(self, 'pan', 0.0)
        zeros = np.zeros_like(scaled)
        if pan < 0:        # Left ear only
            stereo = np.column_stack([scaled, zeros])
        elif pan > 0:      # Right ear only
            stereo = np.column_stack([zeros, scaled])
        else:              # Diotic
            stereo = np.column_stack([scaled, scaled])

        self.trial_dur  = len(scaled) / self.fs
        self._sound_obj = sound.Sound(
            value=stereo.astype(np.float32),
            sampleRate=self.fs,
            stereo=True,
            secs=self.trial_dur,
            hamming=False,
        )

    def execute_trial(self):
        """Play the prepared word via PsychoPy/PTB and wait for completion."""
        self.trial_repeats += 1
        if self._sound_obj is None:
            raise RuntimeError("execute_trial() called before prepare_trial()")
        now = ptb.GetSecs()
        self._sound_obj.play(when=now)
        core.wait(self.trial_dur + 0.1)     # Wait for playback + small tail
        print("Trial finished...")

    def play_demo_trial(self, demo_vals: dict) -> None:
        """
        Override: use execute_trial() instead of tp.play_trial() because
        SRT bypasses TrialPlayer entirely.
        """
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

    def adapt_difficulty(self, direction: str):
        """
        Adjust amplitude — identical step logic to PTA.
        Harder = quieter (lower amplitude), Easier = louder (higher amplitude).
        Large steps before first reversal, fine steps after.
        """
        if isinstance(self.inner_var.data, dict):
            if self.total_num_reversals == 0:
                step_down = self.inner_var.data.get('step_down_initial', -10)
                step_up   = self.inner_var.data.get('step_up_initial',    10)
            else:
                step_down = self.inner_var.data.get('step_down_final',   -2)
                step_up   = self.inner_var.data.get('step_up_final',      2)
            min_amp = self.inner_var.data.get('min', 0.000001)
            max_amp = self.inner_var.data.get('max', 1.0)
        else:
            step_down, step_up = (-10, 10) if self.total_num_reversals == 0 else (-2, 2)
            min_amp, max_amp   = 0.000001, 1.0

        if direction == "harder":
            self.trial_amp = max(
                self.trial_amp * TrialPlayer.db2amp(step_down), min_amp)
            if self.verbose:
                print(f"  -> Harder: {TrialPlayer.amp2db(self.trial_amp):.1f} dB "
                      f"(step: {step_down} dB)")
        elif direction == "easier":
            self.trial_amp = min(
                self.trial_amp * TrialPlayer.db2amp(step_up), max_amp)
            if self.verbose:
                print(f"  -> Easier: {TrialPlayer.amp2db(self.trial_amp):.1f} dB "
                      f"(step: +{step_up} dB)")

    # ------------------------------------------------------------------
    # GUI overrides — show the target word on the examiner screen
    # ------------------------------------------------------------------

    @property
    def _display_word(self) -> str:
        """
        Word label shown on the examiner GUI.
        Returns '---' for catch trials so the examiner isn't tipped off.
        """
        if self._current_word_name.startswith("[catch:"):
            return "---"
        return self._current_word_name or "..."

    def update_gui_state(self, trial_playing: bool = True):
        """
        Override: add a large word label so the examiner can see what
        was played while rating the participant's response.

        Layout (playing)  : status line  /  BIG WORD
        Layout (rating)   : BIG WORD  /  question  /  buttons
        """
        if self.root is None:
            return

        for widget in self.root.winfo_children():
            widget.destroy()

        font_size  = self.gui_config.get('font_size', 15)
        num_options = len(self.gui_config['options'])
        allow_repeat = self.gui_config['allow_repeat']

        if trial_playing:
            # ── Playing phase ──────────────────────────────────────────
            tk.Label(self.root,
                     text="▶  Playing...",
                     font=("Arial", font_size - 2),
                     fg="grey").pack(pady=(12, 4))

            tk.Label(self.root,
                     text=self._display_word,
                     font=("Arial", font_size + 14, "bold"),
                     fg="#1a1a1a",
                     bg="#e8f4e8",
                     relief="ridge",
                     padx=24, pady=10).pack(pady=(0, 12))
        else:
            # ── Rating phase ───────────────────────────────────────────
            tk.Label(self.root,
                     text=self._display_word,
                     font=("Arial", font_size + 14, "bold"),
                     fg="#1a1a1a",
                     bg="#e8f4e8",
                     relief="ridge",
                     padx=24, pady=10).pack(pady=(12, 6))

            tk.Label(self.root,
                     text=self.gui_config['question'],
                     font=("Arial", font_size)).pack(pady=(0, 6))

            button_frame = tk.Frame(self.root)
            button_frame.pack()
            for i, option_text in enumerate(self.gui_config['options']):
                tk.Button(button_frame,
                          text=option_text,
                          width=14).grid(row=0, column=i, padx=10)
            if allow_repeat:
                tk.Button(button_frame,
                          text="Repeat (R)",
                          width=14).grid(row=1, column=0,
                                         columnspan=num_options, pady=(8, 0))

        self.root.update()

    def get_response(self, trial_playing: bool = True) -> int | None:
        """
        Override: same logic as the base class but with the target word
        shown prominently above the question and buttons.
        """
        if self.root is None:
            return None

        result               = {'value': None}
        response_registered  = {'flag': False}
        num_options          = len(self.gui_config['options'])
        allow_repeat         = self.gui_config['allow_repeat']
        font_size            = self.gui_config.get('font_size', 15)

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

        # ── Build layout ───────────────────────────────────────────────
        for widget in self.root.winfo_children():
            widget.destroy()

        # Large word label
        tk.Label(self.root,
                 text=self._display_word,
                 font=("Arial", font_size + 14, "bold"),
                 fg="#1a1a1a",
                 bg="#e8f4e8",
                 relief="ridge",
                 padx=24, pady=10).pack(pady=(12, 6))

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
                      ).grid(row=1, column=0,
                             columnspan=num_options, pady=(8, 0))

        # Flush any queued events before binding keyboard
        self.root.update()
        self.root.update_idletasks()
        self.root.bind("<KeyRelease>", on_key)
        self.root.update_idletasks()
        self.root.mainloop()
        self.root.unbind("<KeyRelease>")

        return result['value']

    def get_log_data(self) -> dict:
        """SRT-specific columns written to the CSV."""
        return {
            "trial_amp": TrialPlayer.amp2db(self.trial_amp),
            "word":      self._current_word_name,
            "trial_dur": round(self.trial_dur, 4),
        }

    def get_trial_description(self) -> str:
        pan = getattr(self, 'pan', 0.0)
        ear = "Left" if pan < 0 else ("Right" if pan > 0 else "Both")
        return (f"Config {self.config_num}/{self.total_num_configs} "
                f"({ear} ear), Trial {self.trial_num}")

    # ------------------------------------------------------------------
    # Catch trial disable
    # ------------------------------------------------------------------

    def determine_catch_trial(self):
        """SRT uses no catch trials — examiner-rated tests don't need them."""
        self.is_catch_trial = False

    # (Interleaved ear logic removed — test is now diotic, single config,
    #  base class main() handles everything.)

    # base class main() is used directly — no override needed.
