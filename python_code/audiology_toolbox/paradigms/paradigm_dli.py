"""
Difference Limen for Intensity (DLI) Paradigm

Adaptive threshold detection for intensity (loudness) differences.
Measures the smallest intensity difference a participant can detect.

Adaptive parameter: Level difference in dB (relative)
Outer variables: Carrier frequency (fc), reference level in dB SPL (ref_level_db)

Stimulus structure: two sequential tones. The "louder" tone is presented
at the reference level (ref_level_db); the "quieter" tone is presented
at ref_level_db - level_diff_dB. Catch trials present both tones at
ref_level_db (no difference).
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from utils.varspec import VarSpec
import random
import numpy as np


class ParadigmDLI(AdaptiveParadigm):
    """
    DLI Detection - detect intensity differences between two tones.
    
    Adaptive behavior:
    - Start with detectable difference (e.g., 8 dB per Prague)
    - Multiplicative steps (halve/double) per Prague protocol
    - Track DLI threshold
    
    Stimulus: Two sequential tones, one randomly louder
    Task: "Which was louder: 1st, 2nd, or Same?"
    
    NOTE: This paradigm uses 3-response format (1/2/Same) instead of binary (Yes/No)
    """
    
    def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None):
        """
        Initialize DLI paradigm.
        
        Args:
            params: Must include "inner" for level_diff_dB and "outer_*" for fc, etc.
            verbose: Print debug info
            gui_config: Optional GUI customization (uses good defaults if None)
        """
        # Set up GUI config if not provided
        if gui_config is None:
            gui_config = {
                'question': "Which tone was LOUDER?",
                'options': ['Same Volume (0)', '1st Louder (1)', '2nd Louder (2)'],
                'keys': ['0', '1', '2'],
                'window_title': "DLI Test - Intensity Difference Detection",
                'font_size': 16
            }
        
        # Call parent constructor
        # CRITICAL: Set paradigm code BEFORE calling super().__init__()
        self.paradigm_code = 'DLI'
        self.demo_duration_attr = 'tone_dur'

        super().__init__(params, verbose=verbose, gui_config=gui_config, participant_id=participant_id)
        
        # DLI-specific settings
        self.sample_accurate = False  # Not needed for DLI
        self.fade_time = 0.05         # Standard fade time
        self.tone_dur = 0.5           # 500 ms per tone (Prague protocol)
        self.isi = 0.2                # 200 ms between tones (Prague protocol)
        
        # Track which tone is louder (for response checking)
        self.louder_tone = None  # Will be 1, 2, or 0 (same)
        
        # Track last two presented level differences for midpoint calculation
        self.last_two_levels = []
    
    def initialize_adaptive_param(self):
        """
        Set initial level difference from inner variable config with randomization.
        
        Per MultiThreshold protocol:
        - Start level_diff is randomized within a range
        - For multiplicative params, randomize in log space
        """
        if isinstance(self.inner_var.data, dict):
            base_start = self.inner_var.data.get('start', 8.0)  # Default 8 dB (Prague)
            
            # For multiplicative parameters, randomize in log space
            randomize_factor = self.inner_var.data.get('randomize_factor', 1.5)
            
            # Random multiplier
            multiplier = random.uniform(1.0/randomize_factor, randomize_factor)
            randomized_start = base_start * multiplier
            
            # Clip to valid range
            min_diff = self.inner_var.data.get('min', 0.5)    # 0.5 dB
            max_diff = self.inner_var.data.get('max', 32.0)   # 32 dB
            self.level_diff_dB = max(min_diff, min(max_diff, randomized_start))
            
            if self.verbose:
                print(f"Initial level difference: {self.level_diff_dB:.2f} dB")
                print(f"  (base: {base_start:.2f} dB, multiplier: {multiplier:.2f}x, range: {1/randomize_factor:.2f}x to {randomize_factor:.2f}x)")
        else:
            self.level_diff_dB = 8.0  # Default 8 dB
            if self.verbose:
                print(f"Initial level difference: {self.level_diff_dB:.2f} dB")
        
        # Reset tracking
        self.last_two_levels = []
    
    def prepare_trial(self):
        """
        Configure trial: two sequential tones with level difference (dB SPL).

        For catch trials: both tones at ref_level_db (correct = "Same")
        For normal trials: louder tone at ref_level_db, quieter at
            ref_level_db - level_diff_dB. Random which is presented first.

        Per-tone dB SPL is converted to per-ear digital amplitude via
        CalibrationManager.spl_to_amplitude() and passed as a per-event
        list `[(t1L, t1R), (t2L, t2R)]` to TrialPlayer's per_channel_gain
        plumbing (sample_accurate=False; each tone gets its own Sound).
        """
        self.trial_num += 1

        # DLI requires a calibrated SPL profile.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "DLI requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )

        # Reference level (dB SPL): outer variable, with sensible fallback.
        ref_level_db = self.ref_level_db if hasattr(self, 'ref_level_db') else 60.0

        if self.is_catch_trial:
            # Catch trial: both tones same level
            spl1 = ref_level_db
            spl2 = ref_level_db
            self.louder_tone = 0  # Correct answer: "Same"

            if self.verbose:
                print(f"  -> Catch trial (both same: {ref_level_db:.1f} dB SPL)")

        else:
            # Normal trial: one tone louder. Louder tone fixed at ref_level_db,
            # quieter tone at ref_level_db - level_diff_dB.
            if random.choice([True, False]):
                # First tone louder
                spl1 = ref_level_db
                spl2 = ref_level_db - self.level_diff_dB
                self.louder_tone = 1
            else:
                # Second tone louder
                spl1 = ref_level_db - self.level_diff_dB
                spl2 = ref_level_db
                self.louder_tone = 2

            # Track this presented level for midpoint calculation
            self.last_two_levels.append(self.level_diff_dB)
            if len(self.last_two_levels) > 2:
                self.last_two_levels.pop(0)

            if self.verbose:
                print(f"  -> Normal trial: diff = {self.level_diff_dB:.2f} dB, louder = {self.louder_tone}")
                print(f"     Tone 1: {spl1:.1f} dB SPL, Tone 2: {spl2:.1f} dB SPL")

        # Convert per-tone dB SPL -> per-ear amplitudes.
        tone1_amp_L, tone1_amp_R = self.calibration.spl_to_amplitude(spl1)
        tone2_amp_L, tone2_amp_R = self.calibration.spl_to_amplitude(spl2)
        self._last_tone1_amp_L = tone1_amp_L
        self._last_tone1_amp_R = tone1_amp_R
        self._last_tone2_amp_L = tone2_amp_L
        self._last_tone2_amp_R = tone2_amp_R

        # Configure trial using TrialPlayer with per-event per_channel_gain.
        # sample_accurate=False -> each event gets its own Sound; per-event
        # different gains are applied independently. PTB mixer handles inter-
        # event playback in hardware (with each event's own fade-in/out).
        self.tp.new_trial(
            wave_type="sin",
            del_times=self.isi,                            # Delay between tones
            durations=[self.tone_dur, self.tone_dur],      # Both tones same duration
            fc=self.fc,                                    # Carrier frequency
            amp=1.0,                                       # Unit amp; per_channel_gain handles SPL
            per_channel_gain=[(tone1_amp_L, tone1_amp_R),
                              (tone2_amp_L, tone2_amp_R)],
            fade_time=self.fade_time,
            sample_accurate=False,
            verbose=False
        )
    
    def check_answer(self):
        """
        Override to handle 3-response format (1, 2, or 0 for "same").
        
        Response classification:
        - Normal trial (louder_tone = 1 or 2):
          - Answer matches louder_tone → TP (correct discrimination)
          - Answer = other tone → FN (wrong choice)
          - Answer = 0 ("same") → FN (missed the difference)
        - Catch trial (louder_tone = 0):
          - Answer = 0 ("same") → TN (correct rejection)
          - Answer = 1 or 2 → FP (false alarm - heard difference when none existed)
        """
        if self.user_input == "repeat":
            return  # Don't classify repeats
        
        # Convert user_input to int for comparison
        response = int(self.user_input)
        
        if self.is_catch_trial:
            # Catch trial: both tones were same
            if response == 0:
                self.correct_answer = 'TN'  # Correctly said "same"
            else:
                self.correct_answer = 'FP'  # Falsely heard a difference
        else:
            # Normal trial: one tone was louder
            if response == self.louder_tone:
                self.correct_answer = 'TP'  # Correctly identified louder tone
            else:
                self.correct_answer = 'FN'  # Wrong (either picked wrong tone or said "same")
        
        if self.verbose:
            print(f"User response: {response}, Correct answer: {self.louder_tone}, Classification: {self.correct_answer}")
    
    def adapt_difficulty(self, direction):
        """
        Adjust level difference to make detection harder or easier.
        
        Harder: Decrease level_diff_dB (smaller difference = harder to detect)
        Easier: Increase level_diff_dB (larger difference = easier to detect)
        
        Uses MULTIPLICATIVE steps (halve/double) per Prague protocol.
        """
        # Get step factors from config or use Prague defaults
        if isinstance(self.inner_var.data, dict):
            # Prague protocol uses halve/double throughout
            if self.total_num_reversals == 0:
                step_down_factor = self.inner_var.data.get('step_down_initial', 0.5)   # Halve
                step_up_factor = self.inner_var.data.get('step_up_initial', 2.0)       # Double
            else:
                step_down_factor = self.inner_var.data.get('step_down_final', 0.5)     # Halve
                step_up_factor = self.inner_var.data.get('step_up_final', 2.0)         # Double
            
            min_diff = self.inner_var.data.get('min', 0.5)    # 0.5 dB
            max_diff = self.inner_var.data.get('max', 32.0)   # 32 dB
        else:
            # Fallback to Prague defaults
            step_down_factor = 0.5
            step_up_factor = 2.0
            min_diff = 0.5
            max_diff = 32.0
        
        # Adjust level difference (MULTIPLICATIVE steps)
        if direction == "harder":
            self.level_diff_dB *= step_down_factor  # Smaller difference (e.g., 8 -> 4 dB)
            self.level_diff_dB = max(self.level_diff_dB, min_diff)  # Floor
            if self.verbose:
                print(f"  -> Harder: {self.level_diff_dB:.2f} dB (factor: {step_down_factor}x)")
        
        elif direction == "easier":
            self.level_diff_dB *= step_up_factor    # Larger difference (e.g., 4 -> 8 dB)
            self.level_diff_dB = min(self.level_diff_dB, max_diff)  # Ceiling
            if self.verbose:
                print(f"  -> Easier: {self.level_diff_dB:.2f} dB (factor: {step_up_factor}x)")
    
    def reset_to_midpoint_level_diff(self):
        """
        Reset level difference to midpoint between last two presented levels.
        Called after first reversal as per MultiThreshold protocol.
        
        For multiplicative parameters, midpoint is GEOMETRIC MEAN.
        """
        if len(self.last_two_levels) == 2:
            # Geometric mean for multiplicative parameters
            midpoint = np.sqrt(self.last_two_levels[0] * self.last_two_levels[1])
            self.level_diff_dB = midpoint
            
            if self.verbose:
                print(f"  -> Reset to midpoint: {midpoint:.2f} dB")
                print(f"     (geometric mean of {self.last_two_levels[0]:.2f} dB and {self.last_two_levels[1]:.2f} dB)")
        else:
            if self.verbose:
                print(f"  -> Warning: Cannot reset to midpoint (need 2 levels, have {len(self.last_two_levels)})")
    
    def update_trial_params(self):
        """
        Override to handle midpoint reset after first reversal.
        """
        # Handle midpoint reset if flagged
        if self.reset_to_midpoint:
            self.reset_to_midpoint_level_diff()
            self.reset_to_midpoint = False
            
            # Clear difficulty adjustment flags
            self.make_harder = False
            self.make_easier = False
        
        # Call parent implementation for normal difficulty adjustment
        super().update_trial_params()
    
    def get_log_data(self):
        """
        Return DLI-specific data for CSV logging.
        
        Per-row columns (universal metadata such as level_units and
        calibration_profile is in the CSV header, not per-row):
        - <inner_var.name>: Adaptive level difference in dB (relative)
        - louder_tone: Which tone was louder (1, 2, or 0 for same)
        - fc: Carrier frequency in Hz (outer variable, if present)
        - ref_level_db: Reference level in dB SPL (outer variable, if present)
        """
        log_dict = {
            self.inner_var.name: self.level_diff_dB,  # dB (relative)
            "louder_tone": self.louder_tone           # 1, 2, or 0
        }
        
        # Add carrier frequency if it exists
        if hasattr(self, 'fc'):
            log_dict["fc"] = self.fc
        
        # Add reference level (dB SPL) if it exists
        if hasattr(self, 'ref_level_db'):
            log_dict["ref_level_db"] = self.ref_level_db
        
        return log_dict

    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for DLI CSVs.

        ref_level is the absolute reference (dB SPL); level_diff_dB is
        relative dB (encoded in the column name's _dB suffix).
        """
        return {
            "ref_level_units": "dB SPL",
        }
    
    def get_trial_description(self):
        """
        Return description for GUI display.
        
        Returns:
            String like "Config 1/1 (1000 Hz), Trial 8"
        """
        fc_desc = f"{self.fc:.0f} Hz" if hasattr(self, 'fc') else "DLI"
        return f"Config {self.config_num}/{self.total_num_configs} ({fc_desc}), Trial {self.trial_num}"


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("DLI Detection Paradigm Test")
    print("=" * 60)
    
    # Define parameters (Prague protocol)
    params = {
        "inner": VarSpec(
            name="level_diff_dB",
            data={
                'start': 8.0,                # Start at 8 dB difference (Prague)
                'step_down_initial': 0.5,    # Halve
                'step_down_final': 0.5,      # Halve
                'step_up_initial': 2.0,      # Double
                'step_up_final': 2.0,        # Double
                'min': 0.5,                  # Minimum 0.5 dB
                'max': 32.0,                 # Maximum 32 dB
                'randomize_factor': 1.5
            }
        ),
        "outer_1": VarSpec(
            name="fc",
            data=[1000]  # 1 kHz carrier
        ),
        "outer_2": VarSpec(
            name="ref_level_db",
            data=[60.0]  # Reference level in dB SPL
        )
    }
    
    # Create and run paradigm
    dli = ParadigmDLI(params, verbose=True)
    
    print("\nStarting DLI paradigm...")
    print(f"Testing {dli.total_num_configs} configuration(s)")
    print("\nPress Ctrl+C to abort\n")
    
    try:
        dli.main()
    except KeyboardInterrupt:
        print("\n\nTest aborted by user")
        if len(dli.data) > 0:
            print("\nPartial results:")
            print(dli.data)
