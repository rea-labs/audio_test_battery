"""
LDL (Loudness Discomfort Level) Paradigm

Measures the dB SPL level at which pure tones become uncomfortably loud.

Refactored to inherit from AdaptiveParadigm so it gains:
  - Operator GUI display
  - Standard data logging / CSV output
  - Future ExperimentController compatibility

Protocol (MultiThreshold manual section 5.4 "discomfort"):
  - Single pure tone per trial, no cue
  - Level increases every trial; step size depends on the rating (see below)
  - Participant rates: Comfortable / Loud / Uncomfortable
  - Run ends immediately when "Uncomfortable" is reported
  - Frequencies and ear (L/R) are outer variables

Response mapping onto AdaptiveParadigm logic:
  - Comfortable (1) or Loud (2)  --> TP  --> "harder" --> level goes UP
  - Uncomfortable (3)            --> FN  --> reversal --> config ends immediately

Step-size rule (team decision 2026-07-17, open issue M9/T4):
  The first "Loud" rating is treated as a soft reversal: it signals that the
  participant is approaching discomfort, so the ascent switches to a finer
  step for the remainder of the config.

  - Before any "Loud"  --> step_up_initial (default +5 dB)
  - From the first "Loud" onwards --> step_up_final (default +3 dB)

  The switch LATCHES: a later "Comfortable" rating does NOT restore the coarse
  step. Ratings jitter near the LDL (Loud -> Comfortable -> Loud is common) and
  re-widening to +5 dB would push an already-close participant toward
  discomfort, defeating the purpose of the reduction. This mirrors
  MultiThreshold, where step reduction at a reversal is one-way.

  Note on key reuse: `step_up_initial` / `step_up_final` keep their usual
  meaning here (coarse early, fine once close to the target). Only the
  selector differs -- other paradigms switch on `total_num_reversals`, LDL
  switches on the first "Loud" rating, because LDL's single real reversal
  ends the config and could never select `step_up_final`.

Key settings:
  - trials_after_reversal = 1   --> config ends on first reversal
  - catch_trial_rate = [0,0,0,0,0] --> no catch trials
  - No midpoint reset on reversal (overridden)

Outer variables:
  - fc:  carrier frequency (Hz)
  - pan: ear selection (-1.0 = left, 1.0 = right)

Levels: all user-facing levels are in dB SPL via CalibrationManager.
Internal tracking variable is `self.trial_amp` (dB SPL, name retained
for consistency with PTA / threshold-fit base-class plumbing).

Based on:
  - MultiThreshold toolbox section 5.4
  - PROLACTIN paradigm plan
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from utils.varspec import VarSpec
import numpy as np


class ParadigmLDL(AdaptiveParadigm):
    """
    LDL - Loudness Discomfort Level.

    Inherits from AdaptiveParadigm. The level-ascending protocol is
    shoehorned into the adaptive framework as follows:

      Comfortable / Loud  -> TP -> harder -> level up
      Uncomfortable       -> FN -> reversal -> config ends (trials_after_reversal=1)

    Step size is coarse (step_up_initial) until the first "Loud" rating, then
    latches to fine (step_up_final) for the rest of the config. See the module
    docstring for the rationale.

    No catch trials. No midpoint reset. One reversal ends each config.
    """

    paradigm_code = "LDL"

    def __init__(self, params: dict[str, VarSpec], verbose=False,
                 gui_config=None, participant_id=None):

        if gui_config is None:
            gui_config = {
                'question':     "Is the tone comfortable, loud, or uncomfortable?",
                'options':      ["Comfortable (1)", "Loud (2)", "Uncomfortable (3)"],
                'keys':         ["1", "2", "3"],
                'window_title': "LDL - Loudness Discomfort Level",
                'font_size':    16,
                'allow_repeat': True,
            }

        # CRITICAL: set paradigm_code before super().__init__()
        self.paradigm_code = "LDL"

        super().__init__(params, verbose=verbose, gui_config=gui_config,
                         participant_id=participant_id)

        # LDL-specific settings
        self.tone_dur   = 0.5    # 500 ms per MultiThreshold spec
        self.fade_time  = 0.004  # 4 ms ramp

        # Protocol overrides
        self.trials_after_reversal = 1      # End config immediately after first reversal
        self.catch_trial_rate      = [0, 0, 0, 0, 0]  # No catch trials
        self._current_catch_trial_rate = 0.0

    # ------------------------------------------------------------------
    # Disable catch trials entirely
    # ------------------------------------------------------------------

    def determine_catch_trial(self):
        """LDL has no catch trials — always False."""
        self.is_catch_trial = False
        if self.verbose:
            print(f"Trial {self.trial_num}: catch_trial = False (LDL: no catch trials)")

    # ------------------------------------------------------------------
    # Adaptive parameter
    # ------------------------------------------------------------------

    def initialize_adaptive_param(self):
        """
        Set starting level (dB SPL) from inner var config.

        Also resets the "Loud" step-size latch. This method is the per-config
        reset hook (_reset_trial_state() -> reset_adaptive_param() -> here),
        so the latch is cleared at the start of every frequency/ear config.
        """
        if isinstance(self.inner_var.data, dict):
            start = self.inner_var.data.get('start', 60.0)  # dB SPL
        else:
            start = 60.0

        self.trial_amp = float(start)  # dB SPL (name retained for base-class compat)

        # Step-size latch: False = coarse ascent, True = fine ascent.
        # Set by check_answer() on the first "Loud" rating; never unset within
        # a config.
        self._loud_reported = False

        # Last raw rating index (0/1/2), for get_log_data(). Cleared here so a
        # rating cannot leak across configs.
        self._last_rating = None

        if self.verbose:
            print(f"Initial level: {self.trial_amp:.1f} dB SPL")

    def adapt_difficulty(self, direction):
        """
        Adjust level (dB SPL) up/down. LDL is normally ascending only:
        'harder' = louder (level up). 'easier' is handled gracefully but
        should never trigger in standard LDL operation.

        Step size depends on the latch set by check_answer():
          - no "Loud" reported yet -> step_up_initial (coarse, default +5 dB)
          - "Loud" reported        -> step_up_final   (fine,   default +3 dB)

        Arithmetic is in dB SPL space (simple addition).
        """
        if isinstance(self.inner_var.data, dict):
            if getattr(self, '_loud_reported', False):
                step_up = self.inner_var.data.get('step_up_final',    3.0)   # dB
            else:
                step_up = self.inner_var.data.get('step_up_initial',  5.0)   # dB
            step_down = self.inner_var.data.get('step_down_final', -3.0)   # dB
            min_level = self.inner_var.data.get('min',              30.0)  # dB SPL
            max_level = self.inner_var.data.get('max',             105.0)  # dB SPL
        else:
            step_up   = 3.0 if getattr(self, '_loud_reported', False) else 5.0
            step_down = -3.0
            min_level, max_level = 30.0, 105.0

        if direction == "harder":
            self.trial_amp += step_up
        elif direction == "easier":
            self.trial_amp += step_down

        self.trial_amp = float(np.clip(self.trial_amp, min_level, max_level))

        if self.verbose:
            if direction == "harder":
                mode = "fine" if getattr(self, '_loud_reported', False) else "coarse"
                step_str = f" (step {step_up:+.1f} dB, {mode})"
            elif direction == "easier":
                step_str = f" (step {step_down:+.1f} dB)"
            else:
                step_str = ""
            print(f"  -> {direction.capitalize()}: "
                  f"{self.trial_amp:.1f} dB SPL{step_str}")

    # ------------------------------------------------------------------
    # Trial preparation
    # ------------------------------------------------------------------

    def prepare_trial(self):
        """
        Play a single pure tone at current level (dB SPL).

        Level is converted to per-ear digital amplitude via
        CalibrationManager.spl_to_amplitude() and passed through
        TrialPlayer's per_channel_gain plumbing. LDL has no catch
        trials.
        """
        self.trial_num += 1

        # LDL requires a calibrated SPL profile -- there is no meaningful
        # uncalibrated dB SPL conversion.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "LDL requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )

        fc  = self.fc  if hasattr(self, 'fc')  else 1000.0
        pan = self.pan if hasattr(self, 'pan') else 0.0

        # Convert dB SPL -> per-ear amplitude. Same pattern as PTA: generate
        # at unit amplitude, let prepare_sound apply per-channel gain. Pan
        # zeros the unused channel before per-channel gain is applied, so
        # only the targeted ear receives sound at the requested SPL.
        amp_L, amp_R = self.calibration.spl_to_amplitude(self.trial_amp)
        self._last_amp_L = amp_L
        self._last_amp_R = amp_R

        if self.verbose:
            ear = "LEFT" if pan < 0 else ("RIGHT" if pan > 0 else "BOTH")
            print(f"  -> Trial {self.trial_num}: {fc:.0f} Hz @ "
                  f"{self.trial_amp:.1f} dB SPL  [{ear}]")

        self.tp.new_trial(
            wave_type="sin",
            durations=self.tone_dur,
            fc=fc,
            amp=1.0,
            pan=pan,
            per_channel_gain=(amp_L, amp_R),
            fade_time=self.fade_time,
            sample_accurate=False,
            verbose=False,
        )

    # ------------------------------------------------------------------
    # Response classification
    # ------------------------------------------------------------------

    # Rating index -> human-readable label. Shared by check_answer() (verbose
    # output) and get_log_data() (CSV column), so the two cannot drift apart.
    RATING_LABELS = {0: "Comfortable", 1: "Loud", 2: "Uncomfortable"}

    def check_answer(self):
        """
        Map 3-option response onto TP/FN.

        get_response() returns the button INDEX (0-based):
          0 = Comfortable  -> TP  (level goes up, coarse step)
          1 = Loud         -> TP  (level goes up, fine step; latches)
          2 = Uncomfortable -> FN (triggers reversal -> end config)

        Also records the rating itself (`self._last_rating`), because TP alone
        cannot distinguish Comfortable from Loud -- and that distinction now
        drives both the step size and the CSV response_label column.
        """
        if self.user_input == "repeat":
            return

        response = int(self.user_input)  # 0, 1, or 2
        self._last_rating = response

        if response in (0, 1):
            self.correct_answer = 'TP'   # Continue raising level
        else:  # response == 2
            self.correct_answer = 'FN'   # Uncomfortable -> reversal -> end

        # First "Loud" latches the ascent to the fine step for this config.
        if response == 1:
            self._loud_reported = True

        if self.verbose:
            print(f"  Response: {self.RATING_LABELS.get(response, '?')} "
                  f"-> {self.correct_answer}")

    # ------------------------------------------------------------------
    # End config on first Uncomfortable response
    # ------------------------------------------------------------------

    def check_trial_conds(self):
        """
        For LDL, end the config immediately on any FN (Uncomfortable).
        Also trigger 'harder' (level up) on any TP (Comfortable/Loud).
        Bypasses reversal-based counting entirely.
        """
        if self.is_catch_trial:
            return

        if self.correct_answer == 'FN':
            self.end_config = True
            if self.verbose:
                print("  -> Uncomfortable: ending config")
        elif self.correct_answer == 'TP':
            self.make_harder = True
            if self.verbose:
                print("  -> Comfortable/Loud: raising level")

    # ------------------------------------------------------------------

    def update_trial_params(self):
        """
        Override to suppress the midpoint reset that AdaptiveParadigm
        normally applies after the first reversal. For LDL the config
        ends immediately, so no reset is needed or wanted.
        """
        self.reset_to_midpoint = False   # Suppress before calling super()
        super().update_trial_params()

    # ------------------------------------------------------------------
    # Data logging
    # ------------------------------------------------------------------

    def get_log_data(self):
        """
        Per-row CSV data. Universal metadata (level_units, calibration_profile,
        prolactin_version, etc.) lives in the CSV header, not per-row.

        `response_label` reports the rating as given (Comfortable / Loud /
        Uncomfortable), taken from `self._last_rating`. It is NOT derived from
        `correct_answer`: TP collapses Comfortable and Loud together, and since
        that distinction now determines the step size, the trial-by-trial
        ascent would not be reconstructable from the CSV. Falls back to the
        TP/FN code if no rating was recorded (e.g. a repeat).
        """
        fallback_map = {
            'TP': 'Comfortable/Loud',
            'FN': 'Uncomfortable',
            'TN': 'TN',
            'FP': 'FP',
        }
        rating = getattr(self, '_last_rating', None)
        if rating is not None:
            response_label = self.RATING_LABELS.get(rating, '')
        else:
            response_label = fallback_map.get(self.correct_answer, '')

        log_dict = {
            self.inner_var.name: self.trial_amp,                # dB SPL
            "response_label":    response_label,
        }
        if hasattr(self, 'fc'):
            log_dict["fc"] = self.fc
        if hasattr(self, 'pan'):
            log_dict["pan"] = self.pan
        return log_dict

    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for LDL CSVs."""
        return {
            "level_units": "dB SPL",
            # HL = PTA only (team decision 2026-06-11). LDL HL is technically valid
            # (level at fc) but out of agreed scope; suppressed explicitly.
            "hl_reportable": False,
        }

    def get_trial_description(self):
        """Return description for operator GUI."""
        fc_str  = f"{self.fc:.0f} Hz"  if hasattr(self, 'fc')  else "?"
        pan_str = "L" if getattr(self, 'pan', 0) < 0 else ("R" if getattr(self, 'pan', 0) > 0 else "B")
        return (f"Config {self.config_num}/{self.total_num_configs} "
                f"({fc_str}, {pan_str}), Trial {self.trial_num}")
