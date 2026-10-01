"""
Interaural Level Difference (ILD) Paradigm

Adaptive threshold detection for intensity differences between ears.
Measures the smallest level difference between left and right ears that
can be lateralized (heard as coming from one side).

Adaptive parameter: ILD (dB) - level difference between ears
Outer variables: Carrier frequency (fc), reference level in dB SPL (ref_level_db)

Stimulus structure: pure tone presented diotically. Per-ear SPL targets:
    louder ear  = ref_level_db + ild_dB/2  (dB SPL)
    quieter ear = ref_level_db - ild_dB/2  (dB SPL)
This is a symmetric +/-ild_dB/2 split around the reference, preserving
mean dB SPL across ears regardless of ild_dB.
"""

from paradigms.adaptive_paradigm import AdaptiveParadigm
from utils.varspec import VarSpec
import random
import numpy as np


class ParadigmILD(AdaptiveParadigm):
    """
    ILD Detection - detect interaural level differences (spatial hearing cue).

    Adaptive behavior:
    - Start with detectable ILD (e.g., 15 dB)
    - Multiplicative steps (halve/double)
    - Track ILD threshold for different frequencies

    Stimulus: Pure tone presented diotically. Per-ear SPL targets:
        louder ear  = ref_level_db + ild_dB/2  (dB SPL)
        quieter ear = ref_level_db - ild_dB/2  (dB SPL)
    Task: "Which side was louder: Left, Right, or Center?"

    Implementation: TrialPlayer with pan=0 (both ears active) and
    per_channel_gain=(amp_L, amp_R). Two spl_to_amplitude() calls (one
    per ear) absorb the per-ear headphone sensitivity correction.
    This separates:
      (1) ILD ratio = pure dB-space arithmetic, independent of headphones
      (2) Per-ear sensitivity correction = absorbed into per_channel_gain
    """

    def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None):
        """
        Initialize ILD paradigm.

        Args:
            params: Must include "inner" for ild_dB and "outer_*" for fc, etc.
            verbose: Print debug info
            gui_config: Optional GUI customization (uses good defaults if None)
        """
        if gui_config is None:
            gui_config = {
                'question': "Which SIDE did the sound come from?",
                'options': ['Equal/Center (0)', 'Left (1)', 'Right (2)'],
                'keys': ['0', '1', '2'],
                'window_title': "ILD Test - Interaural Level Difference",
                'font_size': 16
            }

        # CRITICAL: Set paradigm code BEFORE calling super().__init__()
        self.paradigm_code = 'ILD'
        self.demo_duration_attr = 'tone_dur'

        super().__init__(params, verbose=verbose, gui_config=gui_config, participant_id=participant_id)

        # ILD-specific settings
        self.sample_accurate = False
        self.fade_time = 0.05
        self.tone_dur = 0.5

        # Track which side is louder (for response checking)
        self.louder_side = None  # 0=center, 1=left, 2=right

        self.last_two_levels = []

    def initialize_adaptive_param(self):
        """Set initial ILD from inner variable config with randomization."""
        if isinstance(self.inner_var.data, dict):
            base_start = self.inner_var.data.get('start', 15.0)
            randomize_factor = self.inner_var.data.get('randomize_factor', 1.5)
            multiplier = random.uniform(1.0 / randomize_factor, randomize_factor)
            randomized_start = base_start * multiplier
            min_ild = self.inner_var.data.get('min', 0.5)
            max_ild = self.inner_var.data.get('max', 32.0)
            self.ild_dB = max(min_ild, min(max_ild, randomized_start))
        else:
            self.ild_dB = 8.0

        if self.verbose:
            print(f"Initial ILD: {self.ild_dB:.2f} dB")

        self.last_two_levels = []

    def prepare_trial(self):
        """
        Configure trial: tone with ILD between ears.

        For catch trials: equal levels both ears (center, both at ref_level_db).
        For normal trials: per-ear SPL targets:
            louder ear  = ref_level_db + ild_dB/2  (dB SPL)
            quieter ear = ref_level_db - ild_dB/2  (dB SPL)

        Implementation: identical mono signal in both stereo channels at unit
        amplitude (TrialPlayer handles construction); per-ear scaling lives
        entirely in per_channel_gain. Two spl_to_amplitude() calls (one per
        ear, taking only the channel-appropriate value from each) absorb the
        per-ear headphone sensitivity correction. This separates the ILD
        ratio (pure dB arithmetic) from the per-ear correction.
        """
        self.trial_num += 1

        # ILD requires a calibrated SPL profile.
        if self.calibration is None or not self.calibration.spl_calibrated:
            raise RuntimeError(
                "ILD requires a CalibrationManager with valid SPL calibration "
                "data. Construct one from a populated calibration_config.json "
                "and attach it via paradigm.set_calibration(cm)."
            )

        ref_level_db = self.ref_level_db if hasattr(self, 'ref_level_db') else 60.0
        fc = self.fc if hasattr(self, 'fc') else 1000.0

        # Per-ear SPL targets
        if self.is_catch_trial:
            target_spl_L = ref_level_db
            target_spl_R = ref_level_db
            self.louder_side = 0  # "Equal/Center"
            if self.verbose:
                print(f"  -> Catch trial (center: ILD=0 dB at {ref_level_db:.1f} dB SPL)")
        else:
            half_ild = self.ild_dB / 2.0
            if random.choice([True, False]):
                target_spl_L = ref_level_db + half_ild   # louder
                target_spl_R = ref_level_db - half_ild   # quieter
                self.louder_side = 1  # "Left"
            else:
                target_spl_L = ref_level_db - half_ild
                target_spl_R = ref_level_db + half_ild
                self.louder_side = 2  # "Right"

            self.last_two_levels.append(self.ild_dB)
            if len(self.last_two_levels) > 2:
                self.last_two_levels.pop(0)

            if self.verbose:
                side_name = "LEFT" if self.louder_side == 1 else "RIGHT"
                print(f"  -> Normal trial: ILD = {self.ild_dB:.2f} dB, louder = {side_name}")
                print(f"     L: {target_spl_L:.1f} dB SPL, R: {target_spl_R:.1f} dB SPL")

        # Convert per-ear SPL targets to per-ear amplitudes. Each
        # spl_to_amplitude() call returns (amp_L, amp_R) -- the amplitudes
        # needed to hit the *same* requested SPL on each ear. To produce
        # different per-ear SPLs, we make two calls and take the
        # channel-appropriate value from each.
        amp_L, _ = self.calibration.spl_to_amplitude(target_spl_L)
        _, amp_R = self.calibration.spl_to_amplitude(target_spl_R)
        self._last_amp_L = amp_L
        self._last_amp_R = amp_R

        # Route through TrialPlayer with pan=0 (both ears active). The L/R
        # asymmetry lives entirely in per_channel_gain.
        self.tp.new_trial(
            wave_type="sin",
            durations=self.tone_dur,
            fc=fc,
            amp=1.0,
            pan=0,
            per_channel_gain=(amp_L, amp_R),
            fade_time=self.fade_time,
            sample_accurate=False,
            verbose=False,
        )

    def check_answer(self):
        """
        Override to handle 3-response format (left/center/right).

        Response classification:
        - Normal trial: answer matches louder_side -> TP
        - Normal trial: wrong side -> FN
        - Catch trial: answer = center -> TN
        - Catch trial: answer = left or right -> FP
        """
        if self.user_input == "repeat":
            return

        response = int(self.user_input)  # 0, 1, or 2

        if self.is_catch_trial:
            if response == 0:
                self.correct_answer = 'TN'
            else:
                self.correct_answer = 'FP'
        else:
            if response == self.louder_side:
                self.correct_answer = 'TP'
            else:
                self.correct_answer = 'FN'

        if self.verbose:
            side_names = ['Equal/Center', 'Left', 'Right']
            print(f"User: {side_names[response]}, Correct: {side_names[self.louder_side]}, Class: {self.correct_answer}")

    def adapt_difficulty(self, direction):
        """Adjust ILD using multiplicative steps (same pattern as DLI)."""
        if isinstance(self.inner_var.data, dict):
            if self.total_num_reversals == 0:
                step_down_factor = self.inner_var.data.get('step_down_initial', 0.5)
                step_up_factor   = self.inner_var.data.get('step_up_initial',   2.0)
            else:
                step_down_factor = self.inner_var.data.get('step_down_final', 0.5)
                step_up_factor   = self.inner_var.data.get('step_up_final',   2.0)
            min_ild = self.inner_var.data.get('min', 0.5)
            max_ild = self.inner_var.data.get('max', 32.0)
        else:
            step_down_factor = 0.5
            step_up_factor   = 2.0
            min_ild = 0.5
            max_ild = 32.0

        if direction == "harder":
            self.ild_dB = max(self.ild_dB * step_down_factor, min_ild)
            if self.verbose:
                print(f"  -> Harder: {self.ild_dB:.2f} dB")
        elif direction == "easier":
            self.ild_dB = min(self.ild_dB * step_up_factor, max_ild)
            if self.verbose:
                print(f"  -> Easier: {self.ild_dB:.2f} dB")

    def reset_to_midpoint_ild(self):
        """Reset ILD to geometric mean of last two levels."""
        if len(self.last_two_levels) == 2:
            midpoint = np.sqrt(self.last_two_levels[0] * self.last_two_levels[1])
            self.ild_dB = midpoint
            if self.verbose:
                print(f"  -> Reset to midpoint: {midpoint:.2f} dB")

    def update_trial_params(self):
        """Override to handle midpoint reset."""
        if self.reset_to_midpoint:
            self.reset_to_midpoint_ild()
            self.reset_to_midpoint = False
            self.make_harder = False
            self.make_easier = False
        super().update_trial_params()

    def get_log_data(self):
        """
        Return ILD-specific data for CSV logging.

        Per-row columns (universal metadata such as ref_level_units and
        calibration_profile is in the CSV header, not per-row):
        - ild_dB: Adaptive ILD in dB (relative)
        - louder_side: 0=center, 1=left, 2=right
        - fc: Carrier frequency in Hz (outer variable, if present)
        - ref_level_db: Reference level in dB SPL (outer variable, if present)
        """
        log_dict = {
            "ild_dB":      self.ild_dB,
            "louder_side": self.louder_side,  # 0=center, 1=left, 2=right
        }
        if hasattr(self, 'fc'):
            log_dict["fc"] = self.fc
        if hasattr(self, 'ref_level_db'):
            log_dict["ref_level_db"] = self.ref_level_db
        return log_dict

    def _get_paradigm_metadata(self) -> dict:
        """Header metadata for ILD CSVs.

        ref_level is the absolute reference (dB SPL); ild_dB is relative
        dB (encoded in the column name's _dB suffix).
        """
        return {
            "ref_level_units": "dB SPL",
        }

    def get_trial_description(self):
        """Return description for GUI display."""
        fc_desc = f"{self.fc:.0f} Hz" if hasattr(self, 'fc') else "ILD"
        return f"Config {self.config_num}/{self.total_num_configs} ({fc_desc}), Trial {self.trial_num}"


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("ILD Detection Paradigm Test")
    print("=" * 60)

    params = {
        "inner": VarSpec(
            name="ild_dB",
            data={
                'start': 8.0,
                'step_down_initial': 0.5,
                'step_down_final':   0.5,
                'step_up_initial':   2.0,
                'step_up_final':     2.0,
                'min': 0.5,
                'max': 32.0,
                'randomize_factor': 1.5
            }
        ),
        "outer_1": VarSpec(name="fc",        data=[1000, 2000]),
        "outer_2": VarSpec(name="ref_level_db", data=[60.0]),  # dB SPL
    }

    ild = ParadigmILD(params, verbose=True)

    print(f"\nStarting ILD paradigm...")
    print(f"Testing {ild.total_num_configs} configurations")
    print("\nPress Ctrl+C to abort\n")

    try:
        ild.main()
    except KeyboardInterrupt:
        print("\n\nTest aborted")
