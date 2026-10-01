"""
Gap Detection (GAP) Paradigm

Adaptive threshold detection for temporal gaps in white noise.
Measures the shortest gap a participant can detect.

Adaptive parameter: Gap duration (seconds, logged in milliseconds)
Outer variables: Noise level in dB SPL (noise_level_db)

Note on noise SPL: the white-noise generator produces tanh-soft-limited
Gaussian noise. At the same peak amplitude as a sine wave, this noise
has ~1.3 dB lower acoustic RMS, so a requested 65 dB SPL produces
~63.7 dB SPL acoustic. This bias is consistent across calibrated
playback. A future signal-type-aware spl_to_amplitude() can compensate.
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from trial_player import TrialPlayer
from utils.varspec import VarSpec
import random
import numpy as np


class ParadigmGAP(AdaptiveParadigm):
    """
    Gap Detection - detect silent gaps in continuous white noise.
    
    Adaptive behavior:
    - Start with detectable gap (e.g., 10 ms)
    - Large steps (+/- 5 ms) before first reversal
    - Small steps (+/- 1 ms) after first reversal
    - Midpoint reset after first reversal
    - Track gap detection threshold
    
    Stimulus: White noise with silent gap in middle (sample-accurate rendering)
    """
    
    def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None):
        """
        Initialize GAP paradigm.
        
        Args:
            params: Must include "inner" for gap_duration and "outer_*" for other params
            verbose: Print debug info
            gui_config: Optional GUI customization (uses good defaults if None)
        """
        # Set up GUI config if not provided
        if gui_config is None:
            gui_config = {
                'question': "Did you hear a GAP in the noise?",
                'options': ['No Gap (0)', 'Heard Gap (1)'],
                'keys': ['0', '1'],
                'window_title': "Gap Detection Test",
                'font_size': 16
            }
        
        # Call parent constructor
        # CRITICAL: Set paradigm code BEFORE calling super().__init__()
        self.paradigm_code = 'GAP'

        super().__init__(params, verbose=verbose, gui_config=gui_config, participant_id=participant_id)
        
        # GAP-specific settings
        self.sample_accurate = True   # CRITICAL: Required for sub-ms gap precision
        self.fade_time = 0.0001       # Very short fade to avoid masking the gap
        
        # Noise segment durations (gap occurs between these)
        self.noise_before_gap = 0.5   # 500 ms noise before gap
        self.noise_after_gap = 0.5    # 500 ms noise after gap
        
        # Track last two presented gap durations for midpoint calculation
        self.last_two_levels = []
    
    def initialize_adaptive_param(self):
        """
        Set initial gap duration from inner variable config with randomization.
        
        Per MultiThreshold protocol:
        - Start gap duration is randomized +/- half of initial step size
        - This ensures detectable start and prevents edge cases
        """
        if isinstance(self.inner_var.data, dict):
            base_start = self.inner_var.data.get('start', 0.010)  # Default 10 ms
            
            # Get initial step size to derive randomization range
            # Per MultiThreshold: randomize within +/- half of large step size
            step_down_initial = abs(self.inner_var.data.get('step_down_initial', -0.005))  # 5 ms
            randomize = step_down_initial / 2.0  # Half of initial step
            
            # Add random offset
            offset = random.uniform(-randomize, randomize)
            randomized_start = base_start + offset
            
            # Convert to seconds and clip to valid range
            self.gap_duration = randomized_start  # Already in seconds
            min_gap = self.inner_var.data.get('min', 0.001)  # 1 ms
            max_gap = self.inner_var.data.get('max', 0.020)  # 20 ms
            self.gap_duration = max(min_gap, min(max_gap, self.gap_duration))
            
            if self.verbose:
                print(f"Initial gap duration: {self.gap_duration*1000:.1f} ms")
                print(f"  (base: {base_start*1000:.1f} ms, offset: {offset*1000:+.1f} ms, range: +/-{randomize*1000:.1f} ms)")
        else:
            self.gap_duration = 0.010  # Default 10 ms
            if self.verbose:
                print(f"Initial gap duration: {self.gap_duration*1000:.1f} ms")
        
        # Reset tracking
        self.last_two_levels = []
    
    def prepare_trial(self):
        """
        Configure trial: white noise with gap at current adaptive duration.
        
        For catch trials: continuous noise (no gap)
        For normal trials: noise-gap-noise with adaptive gap duration
        
        Uses sample-accurate rendering to precisely control gap timing.
        Noise level is converted from dB SPL to per-ear digital amplitude
        via CalibrationManager.spl_to_amplitude(), then applied uniformly
        across the two noise events via TrialPlayer's per_channel_gain
        plumbing (uniform-gain mode in sample_accurate=True).
        """
        self.trial_num += 1
        
        # GAP requires a calibrated SPL profile.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "GAP requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )
        
        # Determine gap duration based on catch trial status
        if self.is_catch_trial:
            # Catch trial: continuous noise (no gap)
            gap = 0.0
            if self.verbose:
                print(f"  -> Catch trial (continuous noise, no gap)")
        else:
            # Normal trial: noise with gap
            gap = self.gap_duration
            
            # Track this presented level for midpoint calculation
            self.last_two_levels.append(self.gap_duration)
            if len(self.last_two_levels) > 2:
                self.last_two_levels.pop(0)  # Keep only last 2
            
            if self.verbose:
                print(f"  -> Normal trial: gap = {gap*1000:.2f} ms")
        
        # Noise level (dB SPL): outer variable, with sensible fallback.
        noise_level_db = self.noise_level_db if hasattr(self, 'noise_level_db') else 65.0
        
        # Convert dB SPL -> per-ear amplitude. Uniform across both noise
        # events; TrialPlayer applies it once to the concatenated buffer.
        amp_L, amp_R = self.calibration.spl_to_amplitude(noise_level_db)
        self._last_amp_L = amp_L
        self._last_amp_R = amp_R
        
        # Configure trial using TrialPlayer with sample-accurate rendering
        # Structure: [noise_before, gap, noise_after]
        # del_times specifies delays between segments (in seconds)
        
        self.tp.new_trial(
            wave_type="white",
            del_times=[gap],  # Delay after first noise segment = gap duration
            durations=[self.noise_before_gap, self.noise_after_gap],  # Two noise segments
            amp=1.0,                          # Unit amp; per_channel_gain handles SPL
            per_channel_gain=(amp_L, amp_R),  # Uniform across both noise events
            fade_time=self.fade_time,
            pan=0,  # Mono/center (prevents stereo dimension mismatch)
            sample_accurate=True,  # CRITICAL for precise gap timing
            verbose=False
        )
    
    def adapt_difficulty(self, direction):
        """
        Adjust gap duration to make detection harder or easier.
        
        Harder: Decrease gap duration (shorter gap = harder to detect)
        Easier: Increase gap duration (longer gap = easier to detect)
        
        Uses different step sizes before/after first reversal per MultiThreshold protocol.
        Note: Steps are LINEAR in ms, not multiplicative!
        """
        # Get step sizes from config or use defaults
        if isinstance(self.inner_var.data, dict):
            # Before first reversal - use initial (large) step sizes
            if self.total_num_reversals == 0:
                step_down = self.inner_var.data.get('step_down_initial', -0.005)  # -5 ms
                step_up = self.inner_var.data.get('step_up_initial', 0.005)       # +5 ms
            # After first reversal - use final (small) step sizes
            else:
                step_down = self.inner_var.data.get('step_down_final', -0.001)    # -1 ms
                step_up = self.inner_var.data.get('step_up_final', 0.001)         # +1 ms
            
            min_gap = self.inner_var.data.get('min', 0.001)  # 1 ms
            max_gap = self.inner_var.data.get('max', 0.020)  # 20 ms
        else:
            # Fallback defaults
            step_down = -0.005 if self.total_num_reversals == 0 else -0.001
            step_up = 0.005 if self.total_num_reversals == 0 else 0.001
            min_gap = 0.001
            max_gap = 0.020
        
        # Adjust gap duration (LINEAR steps in seconds)
        if direction == "harder":
            self.gap_duration += step_down  # Shorter gap (note: step_down is negative)
            self.gap_duration = max(self.gap_duration, min_gap)  # Floor
            if self.verbose:
                print(f"  -> Harder: {self.gap_duration*1000:.2f} ms (step: {step_down*1000:.1f} ms)")
        
        elif direction == "easier":
            self.gap_duration += step_up    # Longer gap
            self.gap_duration = min(self.gap_duration, max_gap)  # Ceiling
            if self.verbose:
                print(f"  -> Easier: {self.gap_duration*1000:.2f} ms (step: {step_up*1000:.1f} ms)")
    
    def reset_to_midpoint_gap(self):
        """
        Reset gap duration to midpoint between last two presented levels.
        Called after first reversal as per MultiThreshold protocol.
        """
        if len(self.last_two_levels) == 2:
            # Calculate midpoint (simple average for linear steps)
            midpoint = (self.last_two_levels[0] + self.last_two_levels[1]) / 2.0
            self.gap_duration = midpoint
            
            if self.verbose:
                print(f"  -> Reset to midpoint: {midpoint*1000:.2f} ms")
                print(f"     (between last two levels: {self.last_two_levels[0]*1000:.2f} ms and {self.last_two_levels[1]*1000:.2f} ms)")
        else:
            if self.verbose:
                print(f"  -> Warning: Cannot reset to midpoint (need 2 levels, have {len(self.last_two_levels)})")
    
    def update_trial_params(self):
        """
        Override to handle midpoint reset after first reversal.
        """
        # Handle midpoint reset if flagged
        if self.reset_to_midpoint:
            self.reset_to_midpoint_gap()
            self.reset_to_midpoint = False
            
            # Clear difficulty adjustment flags since we just reset to midpoint
            self.make_harder = False
            self.make_easier = False
        
        # Call parent implementation for normal difficulty adjustment
        super().update_trial_params()
    
    def get_log_data(self):
        """
        Return GAP-specific data for CSV logging.
        
        Per-row columns (universal metadata such as level_units and
        calibration_profile is in the CSV header, not per-row):
        - gap_duration: Adaptive gap duration parameter in ms (inner variable)
        - noise_level_db: Noise level in dB SPL (outer variable, if present)
        """
        log_dict = {
            "gap_duration": self.gap_duration * 1000  # Convert to ms for logging
        }
        
        # Add noise level (dB SPL) if it exists as an outer variable
        if hasattr(self, 'noise_level_db'):
            log_dict["noise_level_db"] = self.noise_level_db
        
        return log_dict

    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for GAP CSVs.

        noise_level_acoustic_bias_db captures the ~1.3 dB underestimate
        relative to a sine wave at the same calibrated peak amplitude
        (tanh-limited Gaussian has lower crest-factor RMS at same peak).
        Documented for downstream analysis; not corrected at this layer.
        """
        return {
            "noise_level_units": "dB SPL",
            "noise_level_acoustic_bias_db": -1.3,
        }
    
    def get_trial_description(self):
        """
        Return description for GUI display.
        
        Returns:
            String like "Config 2/5 (65 dB SPL noise), Trial 8"
        """
        noise_desc = (f"{self.noise_level_db:.0f} dB SPL"
                      if hasattr(self, 'noise_level_db') else "noise")
        return f"Config {self.config_num}/{self.total_num_configs} ({noise_desc}), Trial {self.trial_num}"


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("GAP Detection Paradigm Test")
    print("=" * 60)
    
    # Define parameters with initial/final step sizes
    params = {
        "inner": VarSpec(
            name="gap_duration",
            data={
                'start': 0.010,              # Start at 10 ms
                'step_down_initial': -0.005, # -5 ms before first reversal
                'step_down_final': -0.001,   # -1 ms after first reversal
                'step_up_initial': 0.005,    # +5 ms before first reversal
                'step_up_final': 0.001,      # +1 ms after first reversal
                'min': 0.001,                # Minimum 1 ms
                'max': 0.020                 # Maximum 20 ms
            }
        ),
        "outer_1": VarSpec(
            name="noise_level_db",
            data=[65]  # Single noise level in dB SPL for testing
        )
    }
    
    # Create and run paradigm
    gap = ParadigmGAP(params, verbose=True)
    
    print("\nStarting GAP paradigm...")
    print(f"Testing {gap.total_num_configs} configurations")
    print("\nPress Ctrl+C to abort\n")
    
    try:
        gap.main()
    except KeyboardInterrupt:
        print("\n\nTest aborted by user")
        if len(gap.data) > 0:
            print("\nPartial results:")
            print(gap.data)
