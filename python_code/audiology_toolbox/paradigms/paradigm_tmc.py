"""
TMC (Temporal Masking Curve) Paradigm

Measures auditory compression using forward masking.

A fixed-level probe tone follows a masker tone at the same frequency.
The masker level is adaptively varied to find the masked threshold of the probe.
This is repeated across different masker-probe gaps. The resulting curve (masker
threshold vs. gap duration) has a slope that reflects cochlear compression:
steeper slope = more compression = healthier cochlea.

Adaptive parameter: Masker level (dB SPL)
  - Probe heard  -> masker too weak  -> INCREASE masker (harder)
  - Probe masked -> masker too strong -> DECREASE masker (easier)

Outer variables: gap_duration, probe_freq
  - gap_duration: fixed per run, varied across runs (e.g. [0.005, 0.010, 0.020, 0.040] s)
  - probe_freq:   target frequency (Hz)
Derived (not an outer var):
  - probe_level:  probe amplitude = f(probe_freq) (PTA threshold + dB SL);
                  registered via set_probe_levels().

Key differences from IFMC:
  - Gap is the outer variable (not masker frequency ratio)
  - Masker frequency = probe frequency (on-frequency masker, ratio = 1.0)
  - Masker duration: 108 ms (same as IFMC)
  - Probe duration:  16 ms  (same as IFMC)

Based on:
  - Lecluyse & Meddis (2013) Int J Audiol
  - MultiThreshold toolbox (Essex/Zurich)
  - PROLACTIN paradigm plan (gaps: 5, 10, 20, 40 ms; frequencies: 500, 1000 Hz)
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from trial_player import TrialPlayer
from utils.varspec import VarSpec
import random
import numpy as np


class ParadigmTMC(AdaptiveParadigm):
    """
    TMC - measure auditory compression via forward masking.

    Stimulus structure per trial:
      [Masker 108 ms] -> [Gap N ms] -> [Probe 16 ms]

    Masker and probe have the SAME frequency (on-frequency masking).
    Gap is fixed within a run; masker level is adapted trial-by-trial.

    Task: "Did you hear the short tone (probe) after the louder tone?"
    Response: 1 = yes (heard probe), 0 = no (probe was masked)

    Expected output:
      Normal hearing:   steep TMC slope (~30-40 dB / 100 ms)
      Hearing impaired: shallow slope (compression reduced/absent)
    """

    # Pin the operator panel 39 x-axis linear (M3/M4, D6). TMC's gap_duration
    # spans 0.90 decades, just under the 1.0-decade log-inference threshold;
    # extending the gap set to 50 ms would reach exactly 1.0 and silently flip
    # the axis to log. Display only -- no adaptive logic, no logged values.
    threshold_plot_x_log = False

    # Forward-masking paradigm: the adaptive variable is the MASKER level, so
    # raising it MASKS the probe -- p(yes) falls with level and the fitted
    # psychometric slope k is necessarily NEGATIVE (see adapt_difficulty's
    # "REVERSED logic" note). The base class defaults to +1 for detection
    # paradigms; without this override the implausible-fit guard in
    # update_trial_params() rejects every correct TMC fit and logs NaN.
    psychometric_slope_sign = -1

    def __init__(self, params, verbose=False, gui_config=None, participant_id=None):
        """
        Args:
            params: Must include:
                "inner"   : masker_level (dB SPL) - adaptive parameter
                "outer_1" : gap_duration (s)       - varied across runs
                "outer_2" : probe_freq (Hz)        - test frequency
              probe_level is NOT an outer var; register it per probe_freq via
              set_probe_levels() (derived from PTA threshold + dB SL).
            verbose: Print debug output
            gui_config: Optional GUI customization dict
            participant_id: Participant identifier string
        """
        if gui_config is None:
            gui_config = {
                "question": "Did you hear the short tone at the end?",
                "options": ["No (0)", "Yes (1)"],
                "keys": ["0", "1"],
                "window_title": "TMC Test - Temporal Masking",
                "font_size": 14
            }

        # CRITICAL: must be set BEFORE super().__init__()
        self.paradigm_code = "TMC"

        # Also init BEFORE super(): _setup_variable_looping() runs inside
        # super().__init__() and calls set_current_config(0), which reads this
        # map. probe_level is NOT an outer var; it is f(probe_freq), registered
        # post-construction via set_probe_levels().
        self._probe_level_by_freq = {}

        super().__init__(params, verbose=verbose, gui_config=gui_config,
                         participant_id=participant_id)

        # Timing constants (Lecluyse 2013)
        self.masker_dur = 0.108   # 108 ms masker
        self.probe_dur  = 0.016   # 16 ms probe
        self.ramp_dur   = 0.004   # 4 ms raised-cosine ramps

        # gap_duration is read per-config from outer_1 (in seconds)
        # probe_freq    is read per-config from outer_2 (in Hz)
        # probe_level is NOT an outer var; it is f(probe_freq) and is registered
        # post-construction via set_probe_levels() (see set_current_config).

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

    # ------------------------------------------------------------------
    # Adaptive parameter initialisation
    # ------------------------------------------------------------------

    def initialize_adaptive_param(self):
        """
        Set initial masker level.

        Start LOW so the probe is clearly audible on the first trials,
        helping the participant understand the task.
        Randomise slightly around the start value (MultiThreshold protocol).
        """
        # Track the last two presented masker levels for the post-first-reversal
        # midpoint reset. Reset here so it is cleared both at construction and
        # at every per-config reset (reset_adaptive_param -> here).
        self.last_two_levels = []

        if isinstance(self.inner_var.data, dict):
            base_start = self.inner_var.data.get("start", 10.0)

            # Small randomisation: +/- half the large step size
            step_initial = abs(self.inner_var.data.get("step_up_initial", 10))
            half_step    = step_initial / 2.0
            offset       = self._rng.uniform(-half_step, half_step)

            start_level  = base_start + offset
            min_level    = self.inner_var.data.get("min", 0)
            max_level    = self.inner_var.data.get("max", 100)
            self.masker_level = max(min_level, min(max_level, start_level))
        else:
            self.masker_level = 10.0

        if self.verbose:
            print(f"  Initial masker level: {self.masker_level:.1f} dB SPL  "
                  f"(gap = {self.gap_duration * 1000:.0f} ms, "
                  f"probe = {self.probe_freq:.0f} Hz)")

    # ------------------------------------------------------------------
    # Trial generation
    # ------------------------------------------------------------------

    def prepare_trial(self):
        """
        Build the audio for one trial.

        Normal trial:  [masker 108 ms] -> [gap N ms] -> [probe 16 ms]
        Catch trial:   [masker 108 ms] -> [gap N ms]  (no probe)

        Masker and probe share the same frequency (on-frequency masking).
        """
        self.trial_num += 1

        # Masker level (dB SPL) -> amplitude via CalibrationManager.
        # TMC requires a calibrated SPL profile -- there is no meaningful
        # uncalibrated dB SPL conversion.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "TMC requires a CalibrationManager with valid SPL calibration "
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
        probe_amp  = self.probe_level         # derived from probe_freq via map
        freq       = self.probe_freq          # masker = probe frequency
        gap        = self.gap_duration        # seconds, from outer_1

        if self.is_catch_trial:
            if self.verbose:
                # H5 catch-audibility probe: silent catch shows as amp ~0
                # (zero gain), degenerate freq, or masker_level pinned at min.
                _min_lvl = (self.inner_var.data.get("min", 0)
                            if isinstance(self.inner_var.data, dict) else 0)
                print(
                    f"  -> Catch trial (no probe) | config {self.config_num}: "
                    f"gap={gap*1000:.0f} ms, masker_freq={freq:.0f} Hz, "
                    f"masker_level={self.masker_level:.1f} dB (min={_min_lvl:.1f}), "
                    f"amp_L={amp_L:.4f}, amp_R={amp_R:.4f}"
                )

            self.tp.new_trial(
                wave_type="sin",
                durations=self.masker_dur,
                fc=freq,
                amp=1.0,
                fade_time=self.ramp_dur,
                per_channel_gain=(amp_L, amp_R),
                verbose=False
            )

        else:
            # Track this presented masker level for the midpoint reset
            # (last two NORMAL trials only; catch trials have no probe and
            # do not advance the yes/no track).
            self.last_two_levels.append(self.masker_level)
            if len(self.last_two_levels) > 2:
                self.last_two_levels.pop(0)

            if self.verbose:
                print(f"  -> Normal trial: masker={self.masker_level:.1f} dB, "
                      f"gap={gap*1000:.0f} ms, freq={freq:.0f} Hz, "
                      f"probe amp={probe_amp:.4f}")

            self.tp.new_trial(
                wave_type=["sin", "sin"],
                durations=[self.masker_dur, self.probe_dur],
                del_times=gap,
                fc=[freq, freq],
                amp=[1.0, probe_amp],
                fade_time=self.ramp_dur,
                per_channel_gain=[(amp_L, amp_R), None],
                verbose=False
            )

    # ------------------------------------------------------------------
    # Response classification  (identical logic to IFMC)
    # ------------------------------------------------------------------

    def check_answer(self):
        """
        Classify response for catch vs. normal trials.

        Catch trial (probe absent):
          0 -> TN  (correct rejection)
          1 -> FP  (false alarm)

        Normal trial (probe present):
          1 -> TP  (probe detected)
          0 -> FN  (probe masked)
        """
        if self.user_input == "repeat":
            return

        response = int(self.user_input)

        if self.is_catch_trial:
            self.correct_answer = "TN" if response == 0 else "FP"
        else:
            self.correct_answer = "TP" if response == 1 else "FN"

        if self.verbose:
            label = "Yes" if response == 1 else "No"
            print(f"  User: {label} -> {self.correct_answer}")

    # ------------------------------------------------------------------
    # Adaptive difficulty update  (identical logic to IFMC)
    # ------------------------------------------------------------------

    def adapt_difficulty(self, direction):
        """
        Adjust masker level.

        REVERSED logic:
          harder -> increase masker level
          easier -> decrease masker level
        """
        if isinstance(self.inner_var.data, dict):
            if self.total_num_reversals == 0:
                step_up   = self.inner_var.data.get("step_up_initial",   10)
                step_down = self.inner_var.data.get("step_down_initial", -10)
            else:
                step_up   = self.inner_var.data.get("step_up_final",   2)
                step_down = self.inner_var.data.get("step_down_final", -2)
            min_level = self.inner_var.data.get("min",   0)
            max_level = self.inner_var.data.get("max", 100)
        else:
            step_up   =  10 if self.total_num_reversals == 0 else  2
            step_down = -10 if self.total_num_reversals == 0 else -2
            min_level, max_level = 0, 100

        if direction == "harder":
            self.masker_level = min(self.masker_level + step_up,   max_level)
            if self.verbose:
                print(f"  -> Harder: masker = {self.masker_level:.1f} dB")
        elif direction == "easier":
            self.masker_level = max(self.masker_level + step_down, min_level)
            if self.verbose:
                print(f"  -> Easier: masker = {self.masker_level:.1f} dB")

    # ------------------------------------------------------------------
    # Post-first-reversal midpoint reset  (MultiThreshold protocol)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def get_log_data(self):
        """Return TMC-specific columns for CSV."""
        return {
            "masker_level": self.masker_level,
            "gap_duration": self.gap_duration,
            "probe_freq":   self.probe_freq,
            "probe_level":  self.probe_level,
        }

    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for TMC CSVs."""
        return {
            "masker_level_units": "dB SPL",
            "probe_level_units": "linear amplitude (diotic shortcut)",
            "masker_dur_sec": self.masker_dur,
            "probe_dur_sec": self.probe_dur,
            "ramp_dur_sec": self.ramp_dur,
        }

    def get_trial_description(self):
        """Short description shown in operator display."""
        return (f"Config {self.config_num}/{self.total_num_configs} "
                f"(probe={self.probe_freq:.0f} Hz, "
                f"gap={self.gap_duration*1000:.0f} ms), "
                f"Trial {self.trial_num}")
