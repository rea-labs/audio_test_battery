"""
IFMC (Iso-Forward Masking Contour) Paradigm

Measures frequency selectivity (cochlear tuning) using forward masking.
Tracks how much a masker tone at different frequencies is needed to mask 
a fixed-level, fixed-frequency probe tone.

Adaptive parameter: Masker level (dB SPL)
Outer variables: Masker frequency ratio (fm/fp), probe frequency

Based on:
- Lecluyse & Meddis (2013) - Int J Audiol
- MultiThreshold toolbox (Essex/Zurich)
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from trial_player import TrialPlayer
from utils.varspec import VarSpec
import random
import numpy as np


class ParadigmIFMC(AdaptiveParadigm):
    """
    IFMC - measure frequency selectivity via forward masking.
    
    Stimulus sequence:
    [Masker tone 108ms] → [Gap 10ms] → [Probe tone 16ms]
    
    Adaptive parameter: Masker level (dB SPL)
    - Probe heard → masker too weak → INCREASE masker level
    - Probe not heard → masker masks it → DECREASE masker level
    
    Task: "Did you hear the probe tone (the short click at the end)?"
    
    Expected results:
    - Normal hearing: V-shaped contour (sharp frequency selectivity)
    - Hearing loss: Broad/flat contour (poor frequency selectivity)
    """

    # Forward-masking paradigm: the adaptive variable is the MASKER level, so
    # raising it MASKS the probe -- p(yes) falls with level and the fitted
    # psychometric slope k is necessarily NEGATIVE (see adapt_difficulty's
    # "REVERSED LOGIC" note). The base class defaults to +1 for detection
    # paradigms; without this override the implausible-fit guard in
    # update_trial_params() rejects every correct IFMC fit and logs NaN.
    psychometric_slope_sign = -1
    
    def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None):
        """
        Initialize IFMC paradigm.
        
        Args:
            params: Must include:
                - "inner": masker_level (dB SPL)
                - "outer_1": masker_freq_ratio (fm/fp ratios)
                - "outer_2": probe_freq (Hz)
              probe_level is NOT an outer var; register it per probe_freq via
              set_probe_levels() (derived from PTA threshold + dB SL).
            verbose: Print debug info
            gui_config: Optional GUI customization
        """
        if gui_config is None:
            gui_config = {
                'question': "Did you hear the PROBE tone (short click at the end)?",
                'options': ['No (0)', 'Yes (1)'],
                'keys': ['0', '1'],
                'window_title': "IFMC Test - Frequency Selectivity",
                'font_size': 14
            }
        
        # CRITICAL: Set paradigm code BEFORE calling super().__init__()
        self.paradigm_code = 'IFMC'

        # Also init BEFORE super(): _setup_variable_looping() runs inside
        # super().__init__() and calls set_current_config(0), which reads this
        # map. probe_level is NOT an independent outer var; it is
        # f(probe_freq) = threshold + db_above, populated post-construction via
        # set_probe_levels().
        self._probe_level_by_freq = {}

        super().__init__(params, verbose=verbose, gui_config=gui_config, participant_id=participant_id)
        
        # IFMC-specific timing (from Lecluyse 2013)
        self.masker_dur = 0.108   # 108 ms
        self.gap_dur = 0.010      # 10 ms gap
        self.probe_dur = 0.016    # 16 ms (short probe)
        self.ramp_dur = 0.004     # 4 ms raised-cosine ramps
        
        # Not sample-accurate (normal timing is fine)
        self.sample_accurate = False

    def set_probe_levels(self, freq_to_amp):
        """Register the probe_freq -> amplitude map (threshold + dB SL per freq).

        Fail-fast: every probe_freq in the built config set must have an entry,
        so a missing level aborts at setup rather than mid-session.
        """
        self._probe_level_by_freq = dict(freq_to_amp)
        needed = {cfg["probe_freq"] for cfg in self.unwrapped_params
                  if "probe_freq" in cfg}
        missing = needed - set(self._probe_level_by_freq)
        if missing:
            raise ValueError(
                f"set_probe_levels: no probe level for probe_freq(s) "
                f"{sorted(missing)}"
            )

        # Apply to the config already selected at construction: the base ran
        # set_current_config(0) inside super().__init__() before this map
        # existed, and main() enters config 0 without re-calling it (the loop
        # only re-selects on advance to config 1+). Derive probe_level now so
        # the first config's prepare_trial has it.
        if getattr(self, "probe_freq", None) is not None:
            self.probe_level = self._probe_level_by_freq[self.probe_freq]

    def _derive_dependent_params(self):
        """Derive probe_level from probe_freq after the base sets outer vars.

        Called by the base at the end of set_current_config (normal run) and
        after demo values are applied in play_demo_trial. Guard on the map being
        populated: the base calls set_current_config(0) during __init__ (before
        set_probe_levels), where the map is still empty.
        """
        if getattr(self, "probe_freq", None) is not None and self._probe_level_by_freq:
            self.probe_level = self._probe_level_by_freq[self.probe_freq]

    def initialize_adaptive_param(self):
        """Set initial masker level from inner variable config."""
        # Track the last two presented masker levels for the post-first-reversal
        # midpoint reset. Reset here so it is cleared both at construction and
        # at every per-config reset (reset_adaptive_param -> here).
        self.last_two_levels = []

        if isinstance(self.inner_var.data, dict):
            base_start = self.inner_var.data.get('start', 20.0)  # Start low
            
            # Could randomize start level slightly
            randomize_factor = self.inner_var.data.get('randomize_factor', 1.2)
            multiplier = self._rng.uniform(1.0/randomize_factor, randomize_factor)
            randomized_start = base_start * multiplier
            
            min_level = self.inner_var.data.get('min', 0)
            max_level = self.inner_var.data.get('max', 100)
            self.masker_level = max(min_level, min(max_level, randomized_start))
            
            if self.verbose:
                print(f"Initial masker level: {self.masker_level:.1f} dB SPL")
        else:
            self.masker_level = 20.0
            if self.verbose:
                print(f"Initial masker level: {self.masker_level:.1f} dB SPL")
    
    def prepare_trial(self):
        """
        Configure trial: masker tone → gap → probe tone.
        
        For catch trials (20%): No probe tone (masker + gap only)
        For normal trials: Masker + gap + probe
        
        Task: "Did you hear the probe?"
        """
        self.trial_num += 1
        
        # Calculate actual masker frequency from ratio
        masker_freq = self.probe_freq * self.masker_freq_ratio
        
        # Convert masker level (dB SPL) to amplitude via CalibrationManager.
        # IFMC requires a calibrated SPL profile -- there is no meaningful
        # uncalibrated dB SPL conversion.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "IFMC requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )
        # spl_to_amplitude() returns (amp_L, amp_R) -- different per ear because
        # measured headphone sensitivity differs slightly between L and R. To
        # honour both values exactly, we generate the masker waveform at unit
        # amplitude (amp=1.0) and pass per_channel_gain=(amp_L, amp_R) so the
        # calibration gateway applies the per-ear gain *after* stereo
        # duplication. This yields true per-ear dB SPL with no L/R asymmetry.
        amp_L, amp_R = self.calibration.spl_to_amplitude(self.masker_level)
        # Stash for logging (get_log_data() reads these)
        self._last_masker_amp_L = amp_L
        self._last_masker_amp_R = amp_R
        
        # Probe level is directly specified as amplitude (0-1)
        probe_amp = self.probe_level
        
        if self.is_catch_trial:
            # Catch trial: masker + gap, NO probe
            # User should respond "No" (did not hear probe)
            
            if self.verbose:
                # H5 catch-audibility probe: a silent catch shows here as
                # amp ~0 (zero gain), a degenerate masker_freq (bad freq), or
                # masker_level pinned at min (expected-quiet, not a bug).
                _min_lvl = (self.inner_var.data.get('min', 0)
                            if isinstance(self.inner_var.data, dict) else 0)
                print(
                    f"  -> Catch trial (no probe) | config {self.config_num}: "
                    f"ratio={self.masker_freq_ratio:.2f}, "
                    f"masker_freq={masker_freq:.0f} Hz, "
                    f"masker_level={self.masker_level:.1f} dB (min={_min_lvl:.1f}), "
                    f"amp_L={amp_L:.4f}, amp_R={amp_R:.4f}"
                )
            
            # Just masker, no probe. amp=1.0; per_channel_gain carries SPL.
            self.tp.new_trial(
                wave_type="sin",
                durations=self.masker_dur,
                fc=masker_freq,
                amp=1.0,
                fade_time=self.ramp_dur,
                per_channel_gain=(amp_L, amp_R),
                verbose=False
            )
            
        else:
            # Normal trial: masker + gap + probe

            # Track this presented masker level for the midpoint reset
            # (last two NORMAL trials only; catch trials have no probe and
            # do not advance the yes/no track).
            self.last_two_levels.append(self.masker_level)
            if len(self.last_two_levels) > 2:
                self.last_two_levels.pop(0)

            if self.verbose:
                print(f"  -> Normal trial: masker={self.masker_level:.1f} dB at {masker_freq:.0f} Hz, probe at {self.probe_freq:.0f} Hz")
            
            # Masker (per-ear SPL via per_channel_gain) followed by probe
            # (direct amplitude, no per-channel gain).
            self.tp.new_trial(
                wave_type=["sin", "sin"],
                durations=[self.masker_dur, self.probe_dur],
                del_times=self.gap_dur,  # Gap between masker and probe
                fc=[masker_freq, self.probe_freq],
                amp=[1.0, probe_amp],
                fade_time=self.ramp_dur,
                per_channel_gain=[(amp_L, amp_R), None],
                verbose=False
            )
    
    def check_answer(self):
        """
        Check response for catch vs normal trials.
        
        Catch trial (no probe):
          - Response "No" (0) → TN (correct - didn't hear non-existent probe)
          - Response "Yes" (1) → FP (false alarm - claimed to hear absent probe)
        
        Normal trial (probe present):
          - Response "Yes" (1) → TP (heard probe)
          - Response "No" (0) → FN (missed probe)
        
        NOTE: We don't know "correct" answer for normal trials a priori
        because we're adaptively finding the masker threshold.
        Use TP/FN to track probe detection.
        """
        if self.user_input == "repeat":
            return
        
        response = int(self.user_input)  # 0 or 1
        
        if self.is_catch_trial:
            # Catch trial: probe absent
            if response == 0:  # Said "No"
                self.correct_answer = 'TN'  # Correct - no probe present
            else:  # Said "Yes"
                self.correct_answer = 'FP'  # False alarm
        else:
            # Normal trial: probe present
            # We're trying to find masker threshold, so we track detection
            if response == 1:  # Heard probe
                self.correct_answer = 'TP'  # Detected probe
            else:  # Didn't hear probe
                self.correct_answer = 'FN'  # Probe was masked
        
        if self.verbose:
            print(f"User: {'Yes' if response == 1 else 'No'}, Classification: {self.correct_answer}")
    
    def adapt_difficulty(self, direction):
        """
        Adjust masker level to find masking threshold.
        
        REVERSED LOGIC (compared to typical threshold):
        - Harder = INCREASE masker level (makes probe harder to hear)
        - Easier = DECREASE masker level (makes probe easier to hear)
        
        Uses LINEAR steps in dB (not multiplicative).
        """
        if isinstance(self.inner_var.data, dict):
            if self.total_num_reversals == 0:
                step_down = self.inner_var.data.get('step_down_initial', -10)  # Decrease masker
                step_up = self.inner_var.data.get('step_up_initial', 10)       # Increase masker
            else:
                step_down = self.inner_var.data.get('step_down_final', -2)     # Finer steps
                step_up = self.inner_var.data.get('step_up_final', 2)
            
            min_level = self.inner_var.data.get('min', 0)
            max_level = self.inner_var.data.get('max', 100)
        else:
            step_down = -10 if self.total_num_reversals == 0 else -2
            step_up = 10 if self.total_num_reversals == 0 else 2
            min_level = 0
            max_level = 100
        
        if direction == "harder":
            # Probe was heard → masker too weak → INCREASE masker
            self.masker_level += step_up
            self.masker_level = min(self.masker_level, max_level)
            if self.verbose:
                print(f"  -> Harder: masker = {self.masker_level:.1f} dB (increased)")
        
        elif direction == "easier":
            # Probe was masked → masker too strong → DECREASE masker
            self.masker_level += step_down  # Note: step_down is negative
            self.masker_level = max(self.masker_level, min_level)
            if self.verbose:
                print(f"  -> Easier: masker = {self.masker_level:.1f} dB (decreased)")
    
    def reset_to_midpoint_masker(self):
        """
        Reset the masker level to the midpoint of the last two presented
        levels.

        Per the MultiThreshold protocol (Lecluyse & Meddis 2009; Zurich
        manual section 3.2.1): after the first reversal the within-runs
        variable is set to the midpoint of the most recent yes/no pair, and
        small steps continue from there. Masker level is linear in dB SPL, so
        the midpoint is the arithmetic mean (same as PTA; contrast DLI, which
        uses the geometric mean for its multiplicative parameter).
        """
        if len(self.last_two_levels) == 2:
            midpoint = (self.last_two_levels[0] + self.last_two_levels[1]) / 2.0
            self.masker_level = midpoint
            if self.verbose:
                print(f"  -> Reset to midpoint: {midpoint:.1f} dB SPL "
                      f"(between {self.last_two_levels[0]:.1f} and "
                      f"{self.last_two_levels[1]:.1f})")
        elif self.verbose:
            print(f"  -> Warning: cannot reset to midpoint "
                  f"(need 2 levels, have {len(self.last_two_levels)})")

    def update_trial_params(self):
        """
        Apply the post-first-reversal midpoint reset before the normal
        difficulty adjustment (mirrors PTA).

        On the reversal trial the masker is set to the midpoint and the
        harder/easier flags are cleared, so a step is NOT also applied that
        trial (preventing a double adjustment of midpoint + step).
        """
        if self.reset_to_midpoint:
            self.reset_to_midpoint_masker()
            self.reset_to_midpoint = False
            self.make_harder = False
            self.make_easier = False

        super().update_trial_params()

    def get_log_data(self):
        """Return IFMC-specific data for CSV logging."""
        log_dict = {
            "masker_level": self.masker_level,
            "masker_freq": self.probe_freq * self.masker_freq_ratio,
            "masker_freq_ratio": self.masker_freq_ratio,
            "probe_freq": self.probe_freq,
            "probe_level": self.probe_level,
        }
        
        return log_dict
    
    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for IFMC CSVs."""
        return {
            "masker_level_units": "dB SPL",
            "probe_level_units": "linear amplitude (diotic shortcut)",
            "masker_dur_sec": self.masker_dur,
            "probe_dur_sec": self.probe_dur,
            "gap_dur_sec": self.gap_dur,
            "ramp_dur_sec": self.ramp_dur,
        }
    
    def get_trial_description(self):
        """Return description for GUI display."""
        return f"Config {self.config_num}/{self.total_num_configs} (probe={self.probe_freq:.0f} Hz, ratio={self.masker_freq_ratio:.1f}), Trial {self.trial_num}"


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("IFMC Paradigm Test")
    print("=" * 60)
    
    # Configuration based on Lecluyse 2013
    params = {
        "inner": VarSpec(
            name="masker_level",
            data={
                'start': 20.0,           # Start masker low
                'step_down_initial': -10, # Decrease masker by 10 dB
                'step_down_final': -2,    # Then by 2 dB after reversal
                'step_up_initial': 10,    # Increase masker by 10 dB
                'step_up_final': 2,       # Then by 2 dB after reversal
                'min': 0,                 # Cannot go below 0 dB SPL
                'max': 100,               # Reasonable maximum
                'randomize_factor': 1.2
            }
        ),
        "outer_1": VarSpec(
            name="masker_freq_ratio",
            data=[0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6],  # fm/fp ratios
            # Random order handled by shuffling configs
        ),
        "outer_2": VarSpec(
            name="probe_freq",
            data=[1000]  # Test at 1 kHz
        )
    }
    
    ifmc = ParadigmIFMC(params, verbose=True)
    # probe_level is derived from probe_freq via the map, not an outer var.
    ifmc.set_probe_levels({1000: 0.1})
    
    print("\nStarting IFMC paradigm...")
    print(f"Testing {ifmc.total_num_configs} configurations")
    print("\nPress Ctrl+C to abort\n")
    
    try:
        ifmc.main()
    except KeyboardInterrupt:
        print("\n\nTest aborted")
