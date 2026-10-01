"""
Interaural Time Difference (ITD) Paradigm

Adaptive threshold detection for timing differences between ears.
Measures the smallest time delay between left and right ears that 
can be lateralized (heard as coming from one side).

Adaptive parameter: ITD (milliseconds) - time delay between ears
Outer variables: Carrier frequency (fc), signal type (tone/noise),
                 reference level in dB SPL (ref_level_db)

NOTE: ITD requires sample-accurate stereo generation for microsecond precision.
Bypasses TrialPlayer because per-channel timing offsets are not a TrialPlayer
concept; level scaling, however, uses the standard CalibrationManager
spl_to_amplitude + per_channel_gain pattern.

Note on noise SPL: white-noise stimuli use np.random.uniform(-1, 1) per
channel, which at the same calibrated peak as a sine wave has ~1.3 dB
lower acoustic RMS. Documented; not corrected at this layer (matches GAP).
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from utils.varspec import VarSpec
import random
import numpy as np


class ParadigmITD(AdaptiveParadigm):
    """
    ITD Detection - detect interaural time differences (spatial hearing cue).
    
    Adaptive behavior:
    - Start with easily detectable ITD (e.g., 10 ms)
    - Multiplicative steps (halve/double) initially, smaller steps after reversal
    - Track ITD threshold for different frequencies and signal types
    
    Stimulus: Tone or noise with time delay between ears
    Task: "Which side did the sound come from: Left, Right, or Center?"
    
    ITD creates perception of sound location:
    - Positive ITD → sound from right (right ear delayed)
    - Negative ITD → sound from left (left ear delayed)
    - Zero ITD → sound from center (simultaneous)
    
    NOTE: ITD is most effective for low frequencies (<1500 Hz) and broadband noise.
    """
    
    def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None):
        """
        Initialize ITD paradigm.
        
        Args:
            params: Must include "inner" for itd_ms and "outer_*" for fc, signal_type, etc.
            verbose: Print debug info
            gui_config: Optional GUI customization
        """
        if gui_config is None:
            gui_config = {
                'question': "Which SIDE did the sound come from?",
                'options': ['Equal/Center (0)', 'Left (1)', 'Right (2)'],
                'keys': ['0', '1', '2'],
                'window_title': "ITD Test - Interaural Time Difference",
                'font_size': 16
            }
        
        # CRITICAL: Set paradigm code BEFORE calling super().__init__()
        self.paradigm_code = 'ITD'
        self.demo_duration_attr = 'tone_dur'

        super().__init__(params, verbose=verbose, gui_config=gui_config, participant_id=participant_id)
        
        # ITD-specific settings
        self.sample_accurate = True   # CRITICAL: Required for precise timing
        self.fade_time = 0.05
        self.tone_dur = 0.5           # 500 ms
        
        # Track which side leads (for response checking)
        self.leading_side = None  # 0 (left), 1 (center), or 2 (right)
        
        # Track last two presented ITDs for midpoint
        self.last_two_levels = []
        
        # Sample rate for precise timing
        self.fs = 48000  # Hz
    
    def initialize_adaptive_param(self):
        """Set initial ITD from inner variable config with randomization."""
        if isinstance(self.inner_var.data, dict):
            base_start = self.inner_var.data.get('start', 50.0)  # Default 50 ms (very easy start)
            randomize_factor = self.inner_var.data.get('randomize_factor', 1.5)
            
            multiplier = random.uniform(1.0/randomize_factor, randomize_factor)
            randomized_start = base_start * multiplier
            
            min_itd = self.inner_var.data.get('min', 0.01)   # 0.01 ms = 10 μs (human threshold)
            max_itd = self.inner_var.data.get('max', 50.0)   # 50 ms
            self.itd_ms = max(min_itd, min(max_itd, randomized_start))
            
            if self.verbose:
                print(f"Initial ITD: {self.itd_ms:.3f} ms ({self.itd_ms*1000:.1f} μs)")
        else:
            self.itd_ms = 50.0
            if self.verbose:
                print(f"Initial ITD: {self.itd_ms:.3f} ms")
        
        self.last_two_levels = []
    
    def create_itd_stereo(self, mono_wave, itd_ms, fs, fade_samples=0):
        """
        Create stereo waveform with precise ITD using sample-accurate delays.

        Both channels have the same total length (len(mono_wave)) and end
        at the same sample. The delayed channel receives a truncated copy
        of the signal (missing the last delay_samples) preceded by silence,
        so only the onset ITD cue is present — no offset cue.

        Fade-out is applied per-channel after truncation so the delayed
        channel's fade-out is never cut off.

        Example (delay = D samples, signal length = N):
            Leading channel:  signal[0 : N]
            Delayed channel:  zeros[0 : D] | signal[0 : N-D]

        Args:
            mono_wave: 1D numpy array (mono signal, fade-in already applied)
            itd_ms: ITD in milliseconds (positive = right delayed / sound from left,
                    negative = left delayed / sound from right)
            fs: Sample rate (Hz)
            fade_samples: Number of samples for fade-out ramp (applied per channel)

        Returns:
            2D numpy array (N×2) — same length as mono_wave.
        """
        itd_seconds = itd_ms / 1000.0
        delay_samples = int(abs(itd_seconds) * fs)

        if delay_samples == 0:
            left = mono_wave.copy()
            right = mono_wave.copy()
        else:
            leading = mono_wave.copy()
            delayed = np.concatenate([np.zeros(delay_samples), mono_wave[:-delay_samples]])

            if itd_ms > 0:
                left, right = leading, delayed
            else:
                left, right = delayed, leading

        # Apply fade-out to each channel independently
        if fade_samples > 0:
            fade_out = np.hanning(2 * fade_samples)[fade_samples:]
            left[-fade_samples:]  *= fade_out
            right[-fade_samples:] *= fade_out

        return np.column_stack([left, right])

    def create_itd_stereo_noise(self, wave_L, wave_R, itd_ms, fs, fade_samples=0):
        """
        Create stereo noise waveform with ITD using two independent noise signals.

        Using two independent noise signals ensures that at zero ITD the percept
        is diffuse/central (IACC ≈ 0) rather than perfectly fused (IACC = 1),
        preventing catch trials from being identifiable by their sound quality.
        The ITD cue is carried by the onset delay of one channel.

        Args:
            wave_L: 1D numpy array — independent noise for left channel
                    (fade-in already applied)
            wave_R: 1D numpy array — independent noise for right channel
                    (fade-in already applied, same length as wave_L)
            itd_ms: ITD in milliseconds (positive = right delayed / sound from left,
                    negative = left delayed / sound from right)
            fs: Sample rate (Hz)
            fade_samples: Number of samples for fade-out ramp (applied per channel)

        Returns:
            2D numpy array (N×2) — same length as wave_L / wave_R.
        """
        itd_seconds = itd_ms / 1000.0
        delay_samples = int(abs(itd_seconds) * fs)

        if delay_samples == 0:
            left = wave_L.copy()
            right = wave_R.copy()
        else:
            if itd_ms > 0:
                # Left leads: delay right channel
                left = wave_L.copy()
                right = np.concatenate([np.zeros(delay_samples), wave_R[:-delay_samples]])
            else:
                # Right leads: delay left channel
                left = np.concatenate([np.zeros(delay_samples), wave_L[:-delay_samples]])
                right = wave_R.copy()

        # Apply fade-out to each channel independently
        if fade_samples > 0:
            fade_out = np.hanning(2 * fade_samples)[fade_samples:]
            left[-fade_samples:]  *= fade_out
            right[-fade_samples:] *= fade_out

        return np.column_stack([left, right])
    
    def prepare_trial(self):
        """
        Configure trial: tone/noise with ITD between ears.

        For catch trials: zero ITD (center) at ref_level_db on both ears.
        For normal trials: one ear randomly leads (timing-only cue).

        Both ears are presented at the same dB SPL by design (ITD is a
        timing-only cue; level differences would confound it). A single
        spl_to_amplitude() call yields (amp_L, amp_R) -- the per-ear
        amplitudes that produce the same SPL on each ear, absorbing
        per-ear headphone sensitivity correction. Stimulus is built at
        unit amplitude; per-ear scaling is applied via prepare_sound's
        per_channel_gain.

        Uses sample-accurate stereo generation for precise timing.
        """
        self.trial_num += 1

        # ITD requires a calibrated SPL profile.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "ITD requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )

        # Get signal type (sin or white noise) and reference level (dB SPL)
        signal_type = self.signal_type if hasattr(self, 'signal_type') else 'sin'
        ref_level_db = self.ref_level_db if hasattr(self, 'ref_level_db') else 60.0

        if self.is_catch_trial:
            # Catch trial: zero ITD (center)
            itd_val = 0.0
            self.leading_side = 0  # Correct answer: "Equal/Center"

            if self.verbose:
                print(f"  -> Catch trial (center: ITD=0 ms at {ref_level_db:.1f} dB SPL)")

        else:
            # Normal trial: create ITD by delaying one ear
            # Randomly choose which ear leads (arrives first)
            if random.choice([True, False]):
                # Left ear leads (right delayed) -> sound from left
                itd_val = self.itd_ms  # Positive ITD
                self.leading_side = 1  # Correct answer: "Left"
            else:
                # Right ear leads (left delayed) -> sound from right
                itd_val = -self.itd_ms  # Negative ITD
                self.leading_side = 2  # Correct answer: "Right"

            # Track this level
            self.last_two_levels.append(self.itd_ms)
            if len(self.last_two_levels) > 2:
                self.last_two_levels.pop(0)

            if self.verbose:
                side_name = "LEFT" if self.leading_side == 1 else "RIGHT"
                print(f"  -> Normal trial: ITD = {self.itd_ms:.3f} ms, from {side_name} "
                      f"@ {ref_level_db:.1f} dB SPL")

        # Generate signal at UNIT amplitude. Per-ear SPL scaling is applied
        # in prepare_sound via per_channel_gain.
        # Tone: single mono source. Noise: independent per-ear signals to
        # prevent catch trials being identifiable by IACC cue.
        if signal_type == 'sin':
            fc = self.fc if hasattr(self, 'fc') else 1000.0
            t = np.arange(0, self.tone_dur, 1/self.fs)
            mono_wave = np.sin(2 * np.pi * fc * t)

            # Apply fade-in
            fade_samples = int(self.fade_time * self.fs)
            fade_window = np.hanning(2 * fade_samples)
            mono_wave[:fade_samples] *= fade_window[:fade_samples]

            # Create stereo with ITD (fade-out applied per channel inside)
            stereo_wave = self.create_itd_stereo(mono_wave, itd_val, self.fs,
                                                 fade_samples=fade_samples)

        elif signal_type == 'white':
            n_samples = int(self.tone_dur * self.fs)
            wave_L = np.random.uniform(-1, 1, n_samples)
            wave_R = np.random.uniform(-1, 1, n_samples)

            # Apply fade-in to each channel independently
            fade_samples = int(self.fade_time * self.fs)
            fade_window = np.hanning(2 * fade_samples)
            wave_L[:fade_samples] *= fade_window[:fade_samples]
            wave_R[:fade_samples] *= fade_window[:fade_samples]

            # Create stereo with ITD using independent channels
            stereo_wave = self.create_itd_stereo_noise(wave_L, wave_R, itd_val,
                                                       self.fs,
                                                       fade_samples=fade_samples)

        # Convert ref_level_db to per-ear amplitudes. Both ears want the
        # same SPL, so a single spl_to_amplitude() call gives both values
        # directly. This absorbs per-ear headphone sensitivity correction
        # (left and right amps may differ slightly to produce equal SPL).
        amp_L, amp_R = self.calibration.spl_to_amplitude(ref_level_db)
        self._last_amp_L = amp_L
        self._last_amp_R = amp_R

        # Route through prepare_sound: per-channel FIR convolution and
        # per_channel_gain scaling. Stereo input bypasses pan logic; the
        # ITD itself is already encoded as the inter-channel sample shift.
        # NB: per-channel FIR convolution adds group delay to each channel.
        # If L and R inverse filters have *different* group delays at fc,
        # that introduces an extra phase-domain ITD on top of the requested
        # time-domain ITD. For min-phase IRs from physically similar drivers
        # this is sub-sample at typical fc; if ITD bias is observed,
        # measure both filters' group delays at fc and compensate.
        sound_obj = self.calibration.prepare_sound(
            stereo_wave, self.fs, per_channel_gain=(amp_L, amp_R)
        )

        # Store for playback (bypassing TrialPlayer's normal sound generation)
        self.itd_sound = sound_obj
    
    def execute_trial(self):
        """Override to play ITD sound directly (bypassing TrialPlayer)."""
        self.trial_repeats += 1
        
        if self.verbose:
            print(f"Playing ITD sound (trial repeat {self.trial_repeats})...")
        
        # Play the ITD sound directly
        self.itd_sound.play()
        
        # Wait for sound to finish. FIR convolution extends the buffer by ~85ms
        # (4096-tap IR @ 48kHz); pad the wait when calibration is active.
        import time
        ringout_pad = self.calibration.ringout_seconds if self.calibration else 0.0
        time.sleep(self.tone_dur + ringout_pad + 0.1)

    def play_demo_trial(self, demo_vals: dict) -> None:
        """Override to use execute_trial (ITD bypasses TrialPlayer)."""
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

    
    def check_answer(self):
        """
        Override to handle 3-response format (left/center/right).
        """
        if self.user_input == "repeat":
            return
        
        response = int(self.user_input)
        
        if self.is_catch_trial:
            if response == 0:  # Equal/Center
                self.correct_answer = 'TN'
            else:
                self.correct_answer = 'FP'
        else:
            if response == self.leading_side:
                self.correct_answer = 'TP'
            else:
                self.correct_answer = 'FN'
        
        if self.verbose:
            side_names = ['Equal/Center', 'Left', 'Right']
            print(f"User: {side_names[response]}, Correct: {side_names[self.leading_side]}, Class: {self.correct_answer}")
    
    def adapt_difficulty(self, direction):
        """Adjust ITD (multiplicative steps)."""
        if isinstance(self.inner_var.data, dict):
            # Use different step sizes before/after first reversal
            if self.total_num_reversals == 0:
                step_down_factor = self.inner_var.data.get('step_down_initial', 0.5)   # Halve
                step_up_factor = self.inner_var.data.get('step_up_initial', 2.0)       # Double
            else:
                # Smaller steps after first reversal for fine resolution
                step_down_factor = self.inner_var.data.get('step_down_final', 0.7)     # Smaller decrease
                step_up_factor = self.inner_var.data.get('step_up_final', 1.4)         # Smaller increase
            
            min_itd = self.inner_var.data.get('min', 0.01)   # 10 μs
            max_itd = self.inner_var.data.get('max', 50.0)
        else:
            step_down_factor = 0.5 if self.total_num_reversals == 0 else 0.7
            step_up_factor = 2.0 if self.total_num_reversals == 0 else 1.4
            min_itd = 0.01
            max_itd = 50.0
        
        if direction == "harder":
            self.itd_ms *= step_down_factor
            self.itd_ms = max(self.itd_ms, min_itd)
            if self.verbose:
                print(f"  -> Harder: {self.itd_ms:.3f} ms ({self.itd_ms*1000:.1f} μs)")
        elif direction == "easier":
            self.itd_ms *= step_up_factor
            self.itd_ms = min(self.itd_ms, max_itd)
            if self.verbose:
                print(f"  -> Easier: {self.itd_ms:.3f} ms ({self.itd_ms*1000:.1f} μs)")
    
    def reset_to_midpoint_itd(self):
        """Reset ITD to geometric mean."""
        if len(self.last_two_levels) == 2:
            midpoint = np.sqrt(self.last_two_levels[0] * self.last_two_levels[1])
            self.itd_ms = midpoint
            if self.verbose:
                print(f"  -> Reset to midpoint: {midpoint:.3f} ms")
    
    def update_trial_params(self):
        """Override to handle midpoint reset."""
        if self.reset_to_midpoint:
            self.reset_to_midpoint_itd()
            self.reset_to_midpoint = False
            self.make_harder = False
            self.make_easier = False
        super().update_trial_params()
    
    def get_log_data(self):
        """
        Return ITD-specific data for CSV logging.

        Per-row columns (universal metadata such as ref_level_units and
        calibration_profile is in the CSV header, not per-row):
        - itd_ms, itd_us: Adaptive ITD in ms / us
        - leading_side: 0=center, 1=left, 2=right
        - fc: Carrier frequency in Hz (outer variable, if present)
        - signal_type: 'sin' or 'white' (outer variable, if present)
        - ref_level_db: Reference level in dB SPL (outer variable, if present)
        """
        log_dict = {
            "itd_ms": self.itd_ms,
            "itd_us": self.itd_ms * 1000,  # Also log in microseconds
            "leading_side": self.leading_side
        }

        if hasattr(self, 'fc'):
            log_dict["fc"] = self.fc
        if hasattr(self, 'signal_type'):
            log_dict["signal_type"] = self.signal_type
        if hasattr(self, 'ref_level_db'):
            log_dict["ref_level_db"] = self.ref_level_db

        return log_dict

    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for ITD CSVs.

        ref_level is the absolute reference (dB SPL); itd_ms is a duration
        (encoded in the column name's _ms suffix).

        ref_level_acoustic_bias_db captures the ~1.3 dB underestimate when
        signal_type='white' (uniform noise vs sine at same calibrated peak).
        Sine trials have no bias; analysis can branch on signal_type.
        """
        return {
            "ref_level_units": "dB SPL",
            "ref_level_acoustic_bias_db_white_noise": -1.3,
        }
    
    def get_trial_description(self):
        """Return description for GUI display."""
        if hasattr(self, 'signal_type') and self.signal_type == 'white':
            desc = "White Noise"
        elif hasattr(self, 'fc'):
            desc = f"{self.fc:.0f} Hz"
        else:
            desc = "ITD"
        
        return f"Config {self.config_num}/{self.total_num_configs} ({desc}), Trial {self.trial_num}"


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("ITD Detection Paradigm Test")
    print("=" * 60)
    
    # Test with 1 kHz tone and white noise
    params = {
        "inner": VarSpec(
            name="itd_ms",
            data={
                'start': 10.0,               # 10 ms (very detectable)
                'step_down_initial': 0.5,    # Halve before first reversal
                'step_down_final': 0.7,      # Smaller steps after
                'step_up_initial': 2.0,      # Double before first reversal
                'step_up_final': 1.4,        # Smaller steps after
                'min': 0.01,                 # 10 μs (human threshold)
                'max': 50.0,                 # 50 ms
                'randomize_factor': 1.5
            }
        ),
        "outer_1": VarSpec(
            name="signal_type",
            data=['sin', 'white']  # Test both tone and noise
        ),
        "outer_2": VarSpec(
            name="fc",
            data=[1000]  # 1 kHz (for tone trials)
        ),
        "outer_3": VarSpec(
            name="ref_level_db",
            data=[60.0]  # Reference level in dB SPL
        )
    }
    
    itd = ParadigmITD(params, verbose=True)
    
    print("\nStarting ITD paradigm...")
    print(f"Testing {itd.total_num_configs} configurations")
    print("\nPress Ctrl+C to abort\n")
    
    try:
        itd.main()
    except KeyboardInterrupt:
        print("\n\nTest aborted")
