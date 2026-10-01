"""
Pure Tone Audiogram (PTA) Paradigm

Adaptive threshold detection for pure tones at different frequencies.
Measures the quietest tone a participant can detect.

Adaptive parameter: trial_amp (dB SPL) -- name kept for CSV compatibility
Outer variables: Frequency (Hz), Duration (sec), Pan (-1/0/+1)

Requires a CalibrationManager with valid SPL calibration. Uncalibrated
PTA is not supported (would produce dB FS thresholds with no physical
meaning).
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from utils.varspec import VarSpec
import random


class ParadigmPTA(AdaptiveParadigm):
    """
    Pure Tone Audiogram - detect tones at threshold across frequencies.
    
    Adaptive behavior:
    - Start at comfortable level with randomization (per MultiThreshold protocol)
    - Large steps (+/- 10 dB) before first reversal
    - Small steps (±2 dB) after first reversal  
    - Midpoint reset after first reversal (using last two presented levels)
    - Track threshold for each frequency
    
    Levels are in dB SPL throughout. The CalibrationManager attached via
    set_calibration() converts dB SPL to per-channel digital amplitude
    using the active headphone profile's measured offset.
    """
    
    def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None, operator_units="dB HL"):
        """
        Initialize PTA paradigm.
        
        Args:
            params: Must include "inner" for trial_amp (dB SPL) and
                    "outer_*" for frequencies/durations/pan
            verbose: Print debug info
            gui_config: Optional GUI customization (uses good defaults if None)
            participant_id: Participant ID for data file naming
        """
        # CRITICAL: Set paradigm code BEFORE calling super().__init__()
        self.paradigm_code = 'PTA'
        self.demo_duration_attr = 'trial_dur'
        
        # Set up GUI config if not provided
        if gui_config is None:
            gui_config = {
                'question': "Did you hear a tone?",
                'options': ['No (0)', 'Yes (1)'],
                'keys': ['0', '1'],
                'window_title': "Pure Tone Audiogram",
                'font_size': 16
            }
        
        # Call parent constructor. PTA defaults to operating in dB HL (the
        # clinical convention); pass operator_units="dB SPL" from the test
        # script to run/report in dB SPL instead. The unit is fixed for the
        # run and shown read-only on the operator display.
        super().__init__(params, verbose=verbose, gui_config=gui_config, participant_id=participant_id, operator_units=operator_units)
        
        # Default for optional outer variable (overridden if trial_dur is in params)
        if not hasattr(self, 'trial_dur'):
            self.trial_dur = 0.5         # Default tone duration (sec)

        # Track last two presented levels for midpoint calculation
        # (per Lecluyse & Meddis 2009: midpoint between last two levels)
        self.last_two_levels = []
    
    def initialize_adaptive_param(self):
        """
        Set initial level (dB SPL) from inner variable config with randomization.
        
        Per MultiThreshold protocol:
        - Start level is randomized +/- half of initial step size
        - This ensures supra-threshold start and prevents edge cases
        """
        if isinstance(self.inner_var.data, dict):
            # Levels (start/min/max) are entered in operator_units; resolve
            # each to dB SPL for the current frequency. Step sizes stay as-is
            # (a dB step is unit-agnostic).
            base_start = self._resolve_level(self.inner_var.data.get('start', 60.0))
            
            # Get initial step size to derive randomization range
            # Per MultiThreshold: randomize within +/- half of large step size
            step_down_initial = abs(self.inner_var.data.get('step_down_initial', -10))
            randomize_dB = step_down_initial / 2.0  # Half of initial step
            
            # Add random offset directly in dB SPL space
            offset_dB = random.uniform(-randomize_dB, randomize_dB)
            self.trial_amp = base_start + offset_dB
            
            # Clip to valid range (resolved to dB SPL)
            min_level = self._resolve_level(self.inner_var.data.get('min', -10.0))
            max_level = self._resolve_level(self.inner_var.data.get('max', 90.0))
            # Never let the adaptive ceiling exceed the hardware SPL safety
            # ceiling (the hard clamp in spl_to_amplitude still applies too).
            if self.calibration is not None:
                max_level = min(max_level, self.calibration.max_spl)
            self.trial_amp = max(min_level, min(max_level, self.trial_amp))
            
            if self.verbose:
                print(f"Initial level: {self.trial_amp:.1f} dB SPL")
                print(f"  (base: {base_start:.1f} dB SPL, offset: {offset_dB:+.1f} dB, range: +/-{randomize_dB:.1f} dB)")
        else:
            self.trial_amp = 60.0  # dB SPL
            if self.verbose:
                print(f"Initial level: {self.trial_amp:.1f} dB SPL")
        
        # Reset tracking
        self.last_two_levels = []

    def prepare_trial(self):
        """
        Configure trial: pure tone at current frequency and adaptive level (dB SPL).
        
        For catch trials, amp = 0 (silence).
        For normal trials, level (dB SPL) is converted to per-ear digital
        amplitude via CalibrationManager.spl_to_amplitude() and passed
        through TrialPlayer's per_channel_gain plumbing.
        """
        self.trial_num += 1
        
        # PTA requires a calibrated SPL profile -- there is no meaningful
        # uncalibrated dB SPL conversion.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "PTA requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )
        
        if self.is_catch_trial:
            # Silence -- bypass per_channel_gain (no SPL conversion needed)
            self._last_amp_L = 0.0
            self._last_amp_R = 0.0
            if self.verbose:
                print(f"  -> Catch trial (silence)")
            self.tp.new_trial(
                wave_type="sin",
                durations=self.trial_dur,
                fc=self.fc,
                amp=0.0,
                fade_time=self.fade_time,
                sample_accurate=self.sample_accurate,
                pan=self.pan,
                per_channel_gain=None,
                verbose=False
            )
        else:
            # Normal trial: convert dB SPL -> per-ear amplitude.
            # spl_to_amplitude() returns (amp_L, amp_R) -- different per ear
            # because measured headphone sensitivity differs slightly between
            # L and R. Generate the waveform at unit amplitude (amp=1.0) and
            # pass per_channel_gain so the calibration gateway applies the
            # per-ear gain after stereo duplication. This yields true per-ear
            # dB SPL with no L/R asymmetry. Pan (if non-zero) zeros the
            # unused channel before per-channel gain is applied.
            amp_L, amp_R = self.calibration.spl_to_amplitude(self.trial_amp)
            self._last_amp_L = amp_L
            self._last_amp_R = amp_R
            
            # Track this presented level for midpoint calculation
            self.last_two_levels.append(self.trial_amp)
            if len(self.last_two_levels) > 2:
                self.last_two_levels.pop(0)  # Keep only last 2
            
            if self.verbose:
                print(f"  -> Normal trial: {self.fc:.0f} Hz @ {self.trial_amp:.1f} dB SPL")
            
            self.tp.new_trial(
                wave_type="sin",
                durations=self.trial_dur,
                fc=self.fc,
                amp=1.0,
                fade_time=self.fade_time,
                sample_accurate=self.sample_accurate,
                pan=self.pan,
                per_channel_gain=(amp_L, amp_R),
                verbose=False
            )
    
    def adapt_difficulty(self, direction):
        """
        Adjust level (dB SPL) to make detection harder or easier.
        
        Harder: Decrease level (quieter tone)
        Easier: Increase level (louder tone)
        
        Uses different step sizes before/after first reversal per MultiThreshold protocol.
        All arithmetic is in dB SPL space (simple addition).
        """
        # Get step sizes from config or use defaults
        if isinstance(self.inner_var.data, dict):
            # Before first reversal - use initial (large) step sizes
            if self.total_num_reversals == 0:
                step_down = self.inner_var.data.get('step_down_initial', -10)  # dB
                step_up = self.inner_var.data.get('step_up_initial', 10)       # dB
            # After first reversal - use final (small) step sizes
            else:
                step_down = self.inner_var.data.get('step_down_final', -2)     # dB
                step_up = self.inner_var.data.get('step_up_final', 2)          # dB
            
            min_level = self._resolve_level(self.inner_var.data.get('min', -10.0))
            max_level = self._resolve_level(self.inner_var.data.get('max', 90.0))
            if self.calibration is not None:
                max_level = min(max_level, self.calibration.max_spl)
        else:
            # Fallback defaults (dB SPL)
            step_down = -10 if self.total_num_reversals == 0 else -2
            step_up = 10 if self.total_num_reversals == 0 else 2
            min_level = -10.0
            max_level = 90.0
        
        # Adjust level (additive in dB SPL space)
        if direction == "harder":
            self.trial_amp += step_down                       # Quieter (step_down is negative)
            self.trial_amp = max(self.trial_amp, min_level)   # Floor
            if self.verbose:
                print(f"  -> Harder: {self.trial_amp:.1f} dB SPL (step: {step_down} dB)")
        
        elif direction == "easier":
            self.trial_amp += step_up                         # Louder
            self.trial_amp = min(self.trial_amp, max_level)   # Ceiling
            if self.verbose:
                print(f"  -> Easier: {self.trial_amp:.1f} dB SPL (step: {step_up} dB)")
    
    def reset_to_midpoint_amplitude(self):
        """
        Reset level to midpoint between last two presented levels.
        Called after first reversal as per MultiThreshold protocol.
        
        Per Lecluyse & Meddis (2009): "the stimulus level is set to the 
        mid-point between the two previous levels"
        
        Trivial in dB SPL space: arithmetic mean of two values.
        """
        if len(self.last_two_levels) == 2:
            midpoint_dB = (self.last_two_levels[0] + self.last_two_levels[1]) / 2.0
            self.trial_amp = midpoint_dB
            
            if self.verbose:
                print(f"  -> Reset to midpoint: {midpoint_dB:.1f} dB SPL")
                print(f"     (between last two levels: {self.last_two_levels[0]:.1f} and {self.last_two_levels[1]:.1f} dB SPL)")
        else:
            if self.verbose:
                print(f"  -> Warning: Cannot reset to midpoint (need 2 levels, have {len(self.last_two_levels)})")
    
    def update_trial_params(self):
        """
        Override to handle midpoint reset after first reversal.
        """
        # Handle midpoint reset if flagged
        if self.reset_to_midpoint:
            self.reset_to_midpoint_amplitude()
            self.reset_to_midpoint = False
            
            # Clear difficulty adjustment flags since we just reset to midpoint
            # This prevents double adjustment (midpoint + step)
            self.make_harder = False
            self.make_easier = False
        
        # Call parent implementation for normal difficulty adjustment
        super().update_trial_params()
    
    def get_log_data(self):
        """
        Return PTA-specific data for CSV logging.
        
        Per-row columns (universal metadata such as level_units and
        calibration_profile is in the CSV header, not per-row):
        - trial_amp: Adaptive level in dB SPL (inner variable)
        - fc: Frequency in Hz (outer variable 1)
        - trial_dur: Duration in seconds (outer variable 2 if present)
        """
        return {
            "trial_amp": self.trial_amp,                       # dB SPL (no conversion)
            "fc": self.fc,                                     # Hz
            "trial_dur": self.trial_dur,                       # sec
        }
    
    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for PTA CSVs."""
        return {
            "level_units": "dB SPL",
            "hl_reportable": True,  # PTA is the only paradigm that reports dB HL (team decision 2026-06-11)
        }
    
    def get_trial_description(self):
        """
        Return description for GUI display.
        
        Returns:
            String like "Config 2/5 (1000 Hz), Trial 8"
        """
        return f"Config {self.config_num}/{self.total_num_configs} ({self.fc:.0f} Hz), Trial {self.trial_num}"


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("PTA Paradigm Test")
    print("=" * 60)
    
    # Define parameters with initial/final step sizes (all levels in dB SPL)
    params = {
        "inner": VarSpec(
            name="trial_amp",
            data={
                'start': 60.0,                # Start at 60 dB SPL (comfortable)
                'step_down_initial': -10,     # Large step before first reversal
                'step_down_final': -2,        # Small step after first reversal
                'step_up_initial': 10,        # Large step before first reversal
                'step_up_final': 2,           # Small step after first reversal
                'min': -10.0,                 # Floor (dB SPL; below normal threshold)
                'max': 90.0                   # Ceiling (dB SPL; safe paradigm soft cap)
            }
        ),
        "outer_1": VarSpec(
            name="fc",
            data=[500, 1000, 2000, 4000]  # Test frequencies
        ),
        "outer_2": VarSpec(
            name="trial_dur",
            data=[0.5, 1.0]  # Test durations
        )
    }
    
    # NOTE: This __main__ block is NOT runnable without a CalibrationManager.
    # Use test_pta.py for the real entry point. This block remains as a
    # config-shape reference.
    print("\nThis __main__ block does not run the paradigm directly because")
    print("PTA now requires a CalibrationManager. Run test_pta.py instead.")
