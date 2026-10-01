"""
Amplitude Modulation (AM) Detection Paradigm

Adaptive threshold detection for amplitude modulation in tones.
Measures the smallest AM modulation index a participant can detect.

Adaptive parameter: Modulation index (percent amplitude modulation depth)
Outer variables: Modulation frequency (fm), carrier frequency (fc)
Carrier level (tone_level_db, dB SPL) is a per-fc target level co-indexed with
fc -- NOT an outer variable (see _build_target_level_map / set_target_levels /
_derive_dependent_params).
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from trial_player import TrialPlayer
from utils.varspec import VarSpec
import random
import numpy as np


class ParadigmAM(AdaptiveParadigm):
    """
    AM Detection - detect amplitude modulation in tones.
    
    Adaptive behavior:
    - Start with detectable AM (e.g., 16% modulation index per Prague)
    - Multiplicative steps (halve/double) per Prague protocol
    - Track AM detection threshold for different modulation frequencies
    
    Stimulus: Tone with amplitude modulation
    AM formula: A(t) = A0 * [1 + (mod_ind/100) * sin(2*pi*fm*t)]
    where:
        A0 = carrier amplitude
        fm = modulation frequency (e.g., 2, 4, 8 Hz)
        mod_ind = modulation index in percent (adaptive parameter)
    """
    
    def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None):
        """
        Initialize AM paradigm.
        
        Args:
            params: Must include "inner" for mod_ind and "outer_*" for fm, fc.
                    May include a "target_level" VarSpec: a per-fc carrier level
                    array (dB SPL) co-indexed with the fc outer var. NOT an
                    outer var (it zips with fc, it is not crossed). Absent ->
                    every fc defaults to 60 dB SPL.
            verbose: Print debug info
            gui_config: Optional GUI customization (uses good defaults if None)
        """
        # Set up GUI config if not provided
        if gui_config is None:
            gui_config = {
                'question': "Did you hear AMPLITUDE MODULATION (tremolo/pulsing)?",
                'options': ['No AM (0)', 'Heard AM (1)'],
                'keys': ['0', '1'],
                'window_title': "AM Detection Test",
                'font_size': 16
            }
        
        # Call parent constructor
        # CRITICAL: Set paradigm code BEFORE calling super().__init__()
        self.paradigm_code = 'AM'
        self.demo_duration_attr = 'trial_dur'

        # Carrier level is a per-fc target level (dB SPL), NOT an outer var.
        # Build the fc -> dB map BEFORE super().__init__(): the base runs
        # set_current_config(0) -> _derive_dependent_params() during
        # construction, which reads this map. Populated from the optional
        # co-indexed "target_level" array in params (zipped with fc); defaults
        # to 60 dB per fc when absent. See set_target_levels() for the runtime
        # override hook (mirrors IFMC probe_level).
        self._target_level_by_freq = self._build_target_level_map(params)

        # Optional demo-only carrier level. When a Play Demo preview supplies an
        # explicit level (via play_demo_trial), _derive_dependent_params honours
        # it instead of the per-fc map. None during a normal run.
        self._demo_tone_level = None

        super().__init__(params, verbose=verbose, gui_config=gui_config, participant_id=participant_id)
        
        # AM-specific settings
        self.sample_accurate = False  # Not needed for AM
        self.fade_time = 0.05         # Standard fade time
        self.trial_dur = 2.0          # 2 second tone per Prague protocol
        
        # Track last two presented modulation indices for midpoint calculation
        self.last_two_levels = []

    @staticmethod
    def _build_target_level_map(params):
        """Build the fc -> carrier level (dB SPL) map from params.

        The carrier level is a length-n array co-indexed with the fc outer
        variable (level[i] pairs with fc[i]), supplied under the dedicated
        "target_level" params key -- NOT an outer_* slot. An outer var would be
        crossed with fc via itertools.product; this must ZIP with fc, so it is
        kept out of the product. When no array is supplied, every fc defaults to
        60 dB SPL. A supplied array whose length does not match the fc list is a
        fail-fast error.
        """
        fc_vs = next((params[k] for k in params
                      if k.startswith("outer_")
                      and getattr(params[k], "name", None) == "fc"),
                     None)
        fc_list = list(fc_vs.data) if fc_vs is not None else []

        target_vs = params.get("target_level")
        if target_vs is None:
            return {fc: 60.0 for fc in fc_list}

        levels = target_vs.data if isinstance(target_vs, VarSpec) else target_vs
        if len(levels) != len(fc_list):
            raise ValueError(
                f"target_level length ({len(levels)}) must match the number of "
                f"fc values ({len(fc_list)})."
            )
        return {fc: float(lv) for fc, lv in zip(fc_list, levels)}

    def set_target_levels(self, freq_to_db):
        """Register the fc -> carrier level (dB SPL) map at runtime.

        Optional override hook mirroring IFMC set_probe_levels(): lets a caller
        (e.g. a future loader that reads thresholds from a file or another
        paradigm) replace the config-supplied levels after construction.
        Fail-fast: every fc in the built config set must have an entry.
        """
        self._target_level_by_freq = dict(freq_to_db)
        needed = {cfg["fc"] for cfg in self.unwrapped_params if "fc" in cfg}
        missing = needed - set(self._target_level_by_freq)
        if missing:
            raise ValueError(
                f"set_target_levels: no target level for fc(s) {sorted(missing)}"
            )
        # Apply to the config already selected at construction (config 0): the
        # base ran set_current_config(0) inside super().__init__(), and main()
        # enters config 0 without re-selecting. Derive now so config 0 is right.
        if getattr(self, "fc", None) is not None:
            self.tone_level_db = self._target_level_by_freq[self.fc]

    def _derive_dependent_params(self):
        """Derive the carrier level (tone_level_db) from fc after outer vars set.

        Called by the base at the end of set_current_config (normal run) and
        after demo values are applied in play_demo_trial. A Play Demo preview may
        pin an explicit carrier level via _demo_tone_level; that wins so the demo
        tone-level field is not overwritten by the per-fc map. Otherwise the level
        is taken from the map, falling back to 60 dB when the map has no entry for
        the current fc (e.g. an unconfigured demo freq), matching prepare_trial.
        """
        fc = getattr(self, "fc", None)
        if fc is None:
            return
        demo_level = getattr(self, "_demo_tone_level", None)
        if demo_level is not None:
            try:
                self.tone_level_db = float(demo_level)
                return
            except (TypeError, ValueError):
                pass
        self.tone_level_db = self._target_level_by_freq.get(fc, 60.0)

    def initialize_adaptive_param(self):
        """
        Set initial modulation index from inner variable config with randomization.
        
        Per MultiThreshold protocol:
        - Start mod_ind is randomized within a range
        - For multiplicative params, randomize in log space
        """
        if isinstance(self.inner_var.data, dict):
            base_start = self.inner_var.data.get('start', 16.0)  # Default 16% per Prague
            
            # For multiplicative parameters, randomize in log space
            randomize_factor = self.inner_var.data.get('randomize_factor', 1.5)  # e.g., 1.5x or /1.5
            
            # Random multiplier between 1/factor and factor
            multiplier = random.uniform(1.0/randomize_factor, randomize_factor)
            randomized_start = base_start * multiplier
            
            # Clip to valid range
            min_mod = self.inner_var.data.get('min', 1.0)    # 1%
            max_mod = self.inner_var.data.get('max', 64.0)   # 64%
            self.mod_ind = max(min_mod, min(max_mod, randomized_start))
            
            if self.verbose:
                print(f"Initial modulation index: {self.mod_ind:.2f}%")
                print(f"  (base: {base_start:.2f}%, multiplier: {multiplier:.2f}x, range: {1/randomize_factor:.2f}x to {randomize_factor:.2f}x)")
        else:
            self.mod_ind = 16.0  # Default 16%
            if self.verbose:
                print(f"Initial modulation index: {self.mod_ind:.2f}%")
        
        # Reset tracking
        self.last_two_levels = []
    
    def prepare_trial(self):
        """
        Configure trial: tone with AM at current adaptive modulation index.

        For catch trials: pure tone (no AM, mod_ind = 0) at the carrier SPL
        For normal trials: AM tone with adaptive mod_ind at the carrier SPL

        Carrier level is interpreted as the dB SPL of the unmodulated carrier
        (mod_ind=0 case). The AM modulation rides on top: peak SPL exceeds
        carrier SPL by 20*log10(1 + mod_ind/100). For mod_ind=100% this is
        +6 dB peak; for mod_ind=16% (Prague typical) +1.3 dB peak.
        """
        self.trial_num += 1

        # AM requires a calibrated SPL profile -- there is no meaningful
        # uncalibrated dB SPL conversion.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "AM requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )

        # Determine modulation index based on catch trial status
        if self.is_catch_trial:
            # Catch trial: pure tone (no modulation)
            mod_ind = 0.0
            if self.verbose:
                print(f"  -> Catch trial (pure tone, no AM)")
        else:
            # Normal trial: AM tone
            mod_ind = self.mod_ind

            # Track this presented level for midpoint calculation
            self.last_two_levels.append(self.mod_ind)
            if len(self.last_two_levels) > 2:
                self.last_two_levels.pop(0)  # Keep only last 2

            if self.verbose:
                fc_str = f"{self.fc:.0f} Hz" if hasattr(self, 'fc') else "?"
                fm_str = f"{self.fm:.1f} Hz" if hasattr(self, 'fm') else "?"
                print(f"  -> Normal trial: mod_ind = {mod_ind:.2f}%, fm = {fm_str}, fc = {fc_str}")

        # Carrier level (dB SPL): per-fc target level derived from fc via
        # _derive_dependent_params, with a sensible fallback.
        tone_level_db = self.tone_level_db if hasattr(self, 'tone_level_db') else 60.0
        fc = self.fc if hasattr(self, 'fc') else 1000.0
        fm = self.fm if hasattr(self, 'fm') else 8.0

        # Convert dB SPL -> per-ear amplitude. Same pattern as PTA: generate
        # at unit amplitude (amp=1.0), let prepare_sound apply per-channel gain.
        amp_L, amp_R = self.calibration.spl_to_amplitude(tone_level_db)
        self._last_amp_L = amp_L
        self._last_amp_R = amp_R

        self.tp.new_trial(
            wave_type="am",              # Amplitude modulated tone
            durations=self.trial_dur,    # 2 sec per Prague protocol
            fc=fc,                       # Carrier frequency (from outer var, default 1000 Hz)
            fm=fm,                       # Modulation frequency (from outer var, default 8 Hz)
            mod_ind=mod_ind,             # Modulation index (adaptive parameter)
            amp=1.0,                     # Unit amp; per_channel_gain handles SPL
            per_channel_gain=(amp_L, amp_R),
            fade_time=self.fade_time,
            sample_accurate=False,
            verbose=False
        )
    
    def adapt_difficulty(self, direction):
        """
        Adjust modulation index to make detection harder or easier.
        
        Harder: Decrease mod_ind (less amplitude variation = harder to detect)
        Easier: Increase mod_ind (more amplitude variation = easier to detect)
        
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
            
            min_mod = self.inner_var.data.get('min', 1.0)    # 1%
            max_mod = self.inner_var.data.get('max', 64.0)   # 64%
        else:
            # Fallback to Prague defaults (halve/double)
            step_down_factor = 0.5
            step_up_factor = 2.0
            min_mod = 1.0
            max_mod = 64.0
        
        # Adjust modulation index (MULTIPLICATIVE steps)
        if direction == "harder":
            self.mod_ind *= step_down_factor  # Smaller mod_ind (e.g., 16% -> 8%)
            self.mod_ind = max(self.mod_ind, min_mod)  # Floor
            if self.verbose:
                print(f"  -> Harder: {self.mod_ind:.2f}% (factor: {step_down_factor}x)")
        
        elif direction == "easier":
            self.mod_ind *= step_up_factor    # Larger mod_ind (e.g., 8% -> 16%)
            self.mod_ind = min(self.mod_ind, max_mod)  # Ceiling
            if self.verbose:
                print(f"  -> Easier: {self.mod_ind:.2f}% (factor: {step_up_factor}x)")
    
    def reset_to_midpoint_mod_ind(self):
        """
        Reset modulation index to midpoint between last two presented levels.
        Called after first reversal as per MultiThreshold protocol.
        
        For multiplicative parameters, midpoint is GEOMETRIC MEAN (not arithmetic).
        """
        if len(self.last_two_levels) == 2:
            # Geometric mean for multiplicative parameters
            midpoint = np.sqrt(self.last_two_levels[0] * self.last_two_levels[1])
            self.mod_ind = midpoint
            
            if self.verbose:
                print(f"  -> Reset to midpoint: {midpoint:.2f}%")
                print(f"     (geometric mean of {self.last_two_levels[0]:.2f}% and {self.last_two_levels[1]:.2f}%)")
        else:
            if self.verbose:
                print(f"  -> Warning: Cannot reset to midpoint (need 2 levels, have {len(self.last_two_levels)})")
    
    def update_trial_params(self):
        """
        Override to handle midpoint reset after first reversal.
        """
        # Handle midpoint reset if flagged
        if self.reset_to_midpoint:
            self.reset_to_midpoint_mod_ind()
            self.reset_to_midpoint = False
            
            # Clear difficulty adjustment flags since we just reset to midpoint
            self.make_harder = False
            self.make_easier = False
        
        # Call parent implementation for normal difficulty adjustment
        super().update_trial_params()
    
    def get_log_data(self):
        """
        Return AM-specific data for CSV logging.
        
        Per-row columns (universal metadata such as level_units and
        calibration_profile is in the CSV header, not per-row):
        - mod_ind: Adaptive modulation index in percent (inner variable)
        - fm: Modulation frequency in Hz (outer variable)
        - fc: Carrier frequency in Hz (outer variable, if present)
        - tone_level_db: Carrier level in dB SPL (per-fc target level, if present)
        """
        log_dict = {
            "mod_ind": self.mod_ind  # Modulation index in percent
        }
        
        # Add modulation frequency (should always be present)
        if hasattr(self, 'fm'):
            log_dict["fm"] = self.fm
        
        # Add carrier frequency if it exists as an outer variable
        if hasattr(self, 'fc'):
            log_dict["fc"] = self.fc
        
        # Add carrier level (dB SPL) if it exists
        if hasattr(self, 'tone_level_db'):
            log_dict["tone_level_db"] = self.tone_level_db
        
        return log_dict

    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for AM CSVs."""
        return {
            "tone_level_units": "dB SPL",
        }
    
    def get_trial_description(self):
        """
        Return description for GUI display.
        
        Returns:
            String like "Config 2/5 (fm=4 Hz), Trial 8"
        """
        fm_desc = f"fm={self.fm:.0f} Hz" if hasattr(self, 'fm') else "AM"
        return f"Config {self.config_num}/{self.total_num_configs} ({fm_desc}), Trial {self.trial_num}"


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("AM Detection Paradigm Test")
    print("=" * 60)
    
    # Define parameters with multiplicative step factors (Prague protocol)
    params = {
        "inner": VarSpec(
            name="mod_ind",
            data={
                'start': 16.0,               # Start at 16% modulation (Prague)
                'step_down_initial': 0.5,    # Halve before first reversal
                'step_down_final': 0.5,      # Halve after first reversal
                'step_up_initial': 2.0,      # Double before first reversal
                'step_up_final': 2.0,        # Double after first reversal
                'min': 1.0,                  # Minimum 1%
                'max': 64.0,                 # Maximum 64%
                'randomize_factor': 1.5      # Randomize start by 1.5x or /1.5
            }
        ),
        "outer_1": VarSpec(
            name="fm",
            data=[8, 4, 2]  # Modulation frequencies per Prague protocol
        ),
        "outer_2": VarSpec(
            name="fc",
            data=[1000]  # Carrier frequency (1 kHz)
        )
        # Carrier level (tone_level_db) is no longer an outer var; it defaults
        # to 60 dB SPL per fc. Supply a co-indexed "target_level" array to
        # override (see _build_target_level_map).
    }
    
    # Create and run paradigm
    am = ParadigmAM(params, verbose=True)
    
    print("\nStarting AM paradigm...")
    print(f"Testing {am.total_num_configs} configurations")
    print("\nPress Ctrl+C to abort\n")
    
    try:
        am.main()
    except KeyboardInterrupt:
        print("\n\nTest aborted by user")
        if len(am.data) > 0:
            print("\nPartial results:")
            print(am.data)
