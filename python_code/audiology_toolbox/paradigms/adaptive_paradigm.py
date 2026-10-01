"""
AdaptiveParadigm Base Class

This is the foundation for all adaptive audiology paradigms in the test battery.
It implements the core MultiThreshold UZH adaptive logic including:
- Adaptive catch trials with false-positive tracking
- Reversal-based difficulty adaptation  
- Trial countdown after first reversal
- Systematic looping through outer variable combinations
- TP/FN/FP/TN response classification

All specific paradigms (PTA, GAP, FM, AM, DLI, etc.) should inherit from this class
and override the abstract methods to define paradigm-specific behavior.
"""

import numpy as np
import random
from psychopy import core
import psychtoolbox as ptb
import tkinter as tk
from tkinter import messagebox
import pandas as pd
from datetime import datetime
import time
import sys
import platform
from collections import OrderedDict
from pathlib import Path
import itertools
import traceback

# PROLACTIN version (used in CSV provenance headers).
try:
    from version import __version__ as _PROLACTIN_VERSION
except ImportError:
    _PROLACTIN_VERSION = "unknown"

# Operator GUI (real-time monitoring)
try:
    from operator_gui import get_operator_display
    OPERATOR_GUI_AVAILABLE = True
except ImportError:
    OPERATOR_GUI_AVAILABLE = False

from trial_player import TrialPlayer
from utils.varspec import VarSpec
from config.DEFAULTS import DEFAULTS


# Minimum acceptable |k| for a fitted psychometric function (H1/M8).
#
# The theta-range check catches the classic runaway (theta ~ -1e5), but a fit
# can also land theta inside the level limits while k collapses to ~1e-5 --
# an essentially FLAT psychometric function, which carries no threshold
# information and must not be logged as if it did.
#
# 0.01 is deliberately permissive: Lecluyse & Meddis report k ~ 0.5 for normal
# hearing and ~1.0 for impaired, so this floor sits ~50x below the shallowest
# slope anyone expects to measure. It is there to separate numerical garbage
# from data, NOT to police shallow-but-real fits. Raise it only on evidence.
PSYCHOMETRIC_K_MIN = 0.01


class AdaptiveParadigm:
    """
    Base class for adaptive audiology paradigms following MultiThreshold UZH logic.
    
    Subclasses must implement:
    - prepare_trial(): Set up trial-specific parameters and call TrialPlayer
    - adapt_difficulty(direction): Adjust the adaptive parameter (amp, gap, mod_ind, etc.)
    - get_log_data(): Return dict of paradigm-specific data for CSV logging
    
    Optionally override:
    - initialize_adaptive_param(): Set starting value for inner variable
    - get_trial_description(): Return string describing current trial for GUI
    """

    # Name of the instance attribute the demo "Duration (s)" field overrides.
    # Subclasses set this to their single-duration attr (e.g. "trial_dur" or
    # "tone_dur"). None disables the demo duration field -- used where there is
    # no single trial duration (GAP: two noise segments around the gap) or where
    # only a masker duration exists (IFMC/TMC).
    demo_duration_attr = None

    # Operator panel 39 (previous thresholds): force the x-axis scale instead
    # of inferring it. None = infer (log iff the outer_1 values span at least
    # _THRESHOLD_PLOT_LOG_DECADES decades); True/False = force log/linear.
    # Display only -- never touches adaptive logic or logged values.
    #
    # The inference exists so PTA's fc (1.51 decades) renders as a proper
    # audiogram without every paradigm having to opt in. It is a heuristic on
    # config values, though, so any paradigm sitting near the threshold should
    # pin this rather than let a config edit silently flip its axis: TMC's
    # gap_duration spans 0.90 decades today, and widening the gap set to 50 ms
    # would reach exactly 1.0. See M3/M4.
    threshold_plot_x_log = None   # None = infer (see M3/M4)

    # Expected SIGN of the fitted psychometric slope k, used by the
    # implausible-fit guard in update_trial_params().
    #
    # +1 (default): a DETECTION paradigm. Raising the adaptive variable makes
    #    the target easier to detect, so p(yes) rises with level and k > 0.
    #    PTA, GAP, AM, FM, DLI, ILD, ITD.
    # -1: a forward-MASKING paradigm. The adaptive variable is the MASKER
    #    level, so raising it masks the probe: p(yes) FALLS with level and k
    #    is necessarily negative. IFMC, TMC (both document this as "REVERSED
    #    LOGIC" in their adapt_difficulty docstrings).
    #
    # This is a property of the paradigm, never inferred from a single noisy
    # config: the point of the guard is to catch a fit whose slope runs the
    # wrong way, which is impossible if the expected direction is read from
    # the same data being validated.
    psychometric_slope_sign = 1

    def __init__(self, params: dict[str, VarSpec], verbose=False, gui_config=None, participant_id=None, show_operator_display=True, randomize_config_order=True, calibration=None, operator_units="dB SPL"):
        """
        Initialize adaptive paradigm.
        
        Args:
            params: Dictionary with keys "inner" and "outer_1", "outer_2", etc.
                   - "inner": VarSpec with adaptive parameter config (dict)
                   - "outer_*": VarSpec with lists of values to loop through

                   ORDER IS MEANINGFUL. "outer_1" is the paradigm's PRIMARY
                   outer variable: the one the thresholds are naturally read
                   against, and the one the operator's previous-thresholds
                   panel uses as its x-axis (PTA fc -> audiogram; IFMC
                   masker_freq_ratio -> the conventional IFMC curve).
                   outer_2..N are secondary and become plot series. This is a
                   convention, not a schema-enforced field -- position already
                   encodes primacy -- so a paradigm whose outer_1 is not its
                   natural x-axis will simply plot against the wrong variable.
                   Each VarSpec may also carry optional label/units display
                   metadata; see utils.varspec. (M3/M4)
            verbose: Print debug information
            gui_config: Optional dict with GUI configuration:
                       {
                           'question': "Did you hear the stimulus?",
                           'options': ['0 (No)', '1 (Yes)'],  # Button labels
                           'keys': ['0', '1'],  # Keyboard shortcuts
                           'allow_repeat': True,
                           'window_title': "Audiology Test"
                       }
            participant_id: Participant ID for data file naming (e.g., "P001")
            show_operator_display: Show operator monitoring GUI (default True)
            calibration: Optional CalibrationManager. If None, paradigm runs
                         uncalibrated (legacy behavior). If provided, all
                         TrialPlayer-routed audio is run through the
                         FIR + SPL calibration pipeline. May also be set
                         post-construction via set_calibration().
        """
        # Store participant ID and paradigm code for file naming
        self.participant_id = participant_id or "P000"
        
        # CRITICAL: paradigm_code MUST be set by subclass before calling super().__init__()
        # This will be checked when writing data
        if not hasattr(self, 'paradigm_code'):
            self.paradigm_code = None  # Subclass must set this!
        
        self.params = params
        self.verbose = verbose
        self.randomize_config_order = randomize_config_order
        self.calibration = calibration
        self.tp = TrialPlayer(verbose=False, calibration=calibration)
        # Session-scoped metadata (e.g. from ThresholdSetupDialog: source CSV,
        # db_above_threshold, max_amplitude). Written to CSV header verbatim.
        self.session_metadata: dict = {}
        
        # === OPERATOR DISPLAY ===
        self.show_operator_display = show_operator_display and OPERATOR_GUI_AVAILABLE
        self.operator_display = None  # Will be initialized in main()

        # === RESOURCE / CRASH LOGGING (debug; default OFF) ===
        # Per-trial RSS/handle logger for memory-leak diagnosis ("Test 2").
        # Constructed in main() only when resource_logging is True, so normal
        # runs pay nothing. resource_scan_every gates the heavy gc object scan
        # (0 = never; N = also count live Sound/ndarray/Figure objects every
        # Nth trial). Toggle from the test_*.py entry point.
        # Central toggle: set "resource_logging" / "resource_scan_every" in
        # config/DEFAULTS.py (one switch for all paradigms). Falls back to off
        # if the keys are absent.
        self.resource_logging = DEFAULTS.get("resource_logging", False)
        self.resource_scan_every = DEFAULTS.get("resource_scan_every", 0)
        self.resource_logger = None
        # Operator-facing level unit for this run: "dB SPL" or "dB HL". Fixed
        # per run, set from the paradigm config (constructor arg), NOT changed
        # from the GUI. Governs how operator-entered levels (start/min/max) are
        # interpreted AND how levels are shown on the operator display. Stored
        # data are ALWAYS dB SPL regardless; dB HL is derived. dB HL mode
        # requires an HL-calibrated CalibrationManager (profile with a 'retspl'
        # table), enforced at config entry by _resolve_level().
        self.operator_units = self._normalize_operator_units(operator_units)
        
        # === GUI CONFIGURATION ===
        self.gui_config = gui_config or {}
        self._setup_default_gui_config()
        
        # === CORE ADAPTIVE STATE ===
        self.current_streak = 0           # Current correct/incorrect streak
        self.last_current_streak = 0      # Previous streak (for reversal detection)
        self.total_num_reversals = 0      # Total reversals in current config
        self.trials_remaining = None      # Trials to complete after first reversal
        self.direction = 0                # -1 = decreasing difficulty, 1 = increasing
        
        # === PERFORMANCE TRACKING ===
        self.total_TP = 0                 # True positives (heard when present)
        self.total_FN = 0                 # False negatives (missed when present)
        self.total_FP = 0                 # False positives (heard when absent)
        self.total_TN = 0                 # True negatives (correct rejection)

        # === CATCH TRIAL PER-RUN TRACKING ===
        self._had_false_positive_this_run = False  # Track if FP occurred in current run
        
        # === CATCH TRIAL STATE ===
        self.catch_trial_rate = [0.2, 0.1, 0.3, 2.0, 0.05]  # [start, baseRate, max, tau, increment]
        self._current_catch_trial_rate = self.catch_trial_rate[0]
        self.is_catch_trial = False

        # === REACTION TIME STATE ===
        # reaction_time_s = t_response - stim_end (end of last audible interval).
        # Recomputed every get_response(); NaN until first response. See note in
        # get_response re: the fixed dead interval baked into this value.
        self.reaction_time_s = np.nan
        self._resp_time = None
        
        # === TRIAL STATE ===
        self.config_num = 1              # Current config (1-based for logging)
        self.trial_num = 0               # Current trial within config (1-based)
        self.user_input = None           # User response (0, 1, or "repeat")
        self.correct_answer = None       # Classification: TP, FN, FP, TN
        self.trial_repeats = -1          # Number of times trial repeated
        
        # === FLAGS ===
        self.make_harder = False         # Flag: make next trial harder
        self.make_easier = False         # Flag: make next trial easier  
        self.end_config = False          # Flag: move to next config
        self.end_paradigm = False        # Flag: all configs complete
        self.reset_to_midpoint = False   # Flag: reset to midpoint after first reversal
        self._at_wrv_limit = False       # Flag: adaptive param hit min/max this trial
        self._aborted_by_operator = False  # Flag: operator chose abort paradigm (no save)
        self._mulligan_available = True    # Option A: forgive first-trial FN once per config
        self._mulligan_used = False        # Option A: True if mulligan was granted this config
        self._has_stepped_down = False     # Option B: True once first "harder" step has been taken
        # True once main() begins (calibration guaranteed attached). Lets
        # _resolve_level() defer dB HL conversion during __init__ priming
        # (when no CalibrationManager is attached yet) instead of raising.
        self._run_started = False
        
        # === THRESHOLD ESTIMATION ===
        self.threshold_dB = None          # Estimated threshold from psychometric fit
        self.slope_k = None               # Estimated slope parameter from psychometric fit
        
        # === CONFIGURATION ===
        self.target_streak_correct = 1   # Streak needed to increase difficulty
        self.target_streak_wrong = 1     # Streak needed to decrease difficulty
        self.trials_after_reversal = 10  # Total trials for threshold estimation (Per Lecluyse & Meddis 2009: includes the trial immediately before first reversal plus subsequent trials)
        self.trial_ITI = 1.0             # Inter-trial interval (sec)
        self.post_stim_pause = 0.1       # Pause after stimulus end, before response GUI (sec); anti-click. TODO: move to DEFAULTS.py
        self.pre_first_trial_pause = 5.0 # Countdown pause before first trial (sec); 0 disables
        self.inter_config_pause = 5.0    # Countdown pause between outer-var configs (sec); 0 disables
        self.fade_time = 0.05            # Fade in/out to avoid clicks
        self.sample_accurate = False     # Don't need sample accuracy for PTA
        self.pan = 0.0                   # Stereo pan: -1=left, 0=centre, 1=right
        self.block_outer_var_name = "pan"  # Outer var to BLOCK (not globally
                                         # shuffle): all configs for one of its
                                         # values run before the next. Makes
                                         # single-ear paradigms (PTA, LDL) do one
                                         # ear fully, then the other. No-ops when
                                         # the var is absent or single-valued
                                         # (all diotic paradigms). Set None to off.
        self.debug_amps = False          # H2: console-print per-ear amp audit when True (never logged)
        self._rng = np.random.default_rng()  # Single RNG instance, seeded once at init
        
        # === GUI ===
        self.root = None                 # Tkinter root (created once in main())
        
        # === DATA LOGGING ===
        # DataFrame stores all trial data with columns in order:
        # 1. Trial info: unix_time, config_num, trial_num
        # 2. Trial outcomes: is_catch_trial, trial_repeats, correct_answer
        # 3. Paradigm variables: Named after params (e.g., trial_amp, fc, trial_dur for PTA)
        #    - Inner variable (adaptive parameter)
        #    - Outer variables (looped parameters)
        # 4. Threshold estimates: threshold_dB, slope_k (filled only on last trial of each config)
        # Columns determined dynamically from first logged trial.
        # Rows are accumulated in _data_rows (list of dicts) and flushed
        # to self.data as a single DataFrame operation to avoid O(n²) concat.
        self._data_rows = []
        self.data = pd.DataFrame()
        
        # === PARSE PARAMS AND SETUP CONFIGS ===
        self._setup_variable_looping()
    
    def set_calibration(self, calibration):
        """
        Attach (or detach) a CalibrationManager after construction.
        
        Wires the calibration through to the underlying TrialPlayer so that
        subsequent trials are routed through the FIR + SPL pipeline. Pass
        None to revert to uncalibrated behavior.
        
        Use this when a paradigm subclass is constructed before the
        CalibrationManager (e.g. so a test script can do:
            paradigm = ParadigmIFMC(params)
            paradigm.set_calibration(cm)
        without needing to change every subclass __init__ signature).
        """
        self.calibration = calibration
        self.tp.calibration = calibration

    def set_session_metadata(self, metadata: dict) -> None:
        """
        Attach session-scoped metadata to be written into the CSV header.
        Typical caller: a setup dialog passing through its own parameters
        (e.g. db_above_threshold, max_amplitude, source CSV path).
        Subsequent calls update / overwrite existing keys.
        """
        if metadata:
            self.session_metadata.update(metadata)

    @staticmethod
    def _normalize_operator_units(units) -> str:
        """Validate/normalize the operator-units setting to 'dB SPL' or
        'dB HL'. Accepts a few spellings; raises ValueError otherwise."""
        s = (units or "dB SPL").strip().lower().replace(" ", "")
        if s in ("dbspl", "spl"):
            return "dB SPL"
        if s in ("dbhl", "hl"):
            return "dB HL"
        raise ValueError(
            f"operator_units must be 'dB SPL' or 'dB HL', got {units!r}"
        )

    def _resolve_level(self, value) -> float:
        """
        Interpret an inner-variable level (start/min/max) in the operator's
        units and return it in dB SPL, the canonical internal unit.

        - operator_units == 'dB SPL': returns value unchanged.
        - operator_units == 'dB HL': converts via
          calibration.hl_to_spl(value, self.fc).

        Step sizes are NOT levels and must not be passed here: a dB step is
        unit-agnostic (2 dB is 2 dB in either scale).

        Raises RuntimeError if dB HL mode is active but no HL-calibrated
        CalibrationManager is attached, or no carrier frequency (self.fc) is
        set for the current config.
        """
        if self.operator_units != "dB HL":
            return float(value)
        cal = self.calibration
        fc = getattr(self, "fc", None)
        ready = (cal is not None
                 and getattr(cal, "hl_calibrated", False)
                 and fc is not None)
        if not ready:
            # During __init__ priming the CalibrationManager / fc may not be
            # attached yet. Defer: return the raw value (it will be re-resolved
            # at run start once calibration is present). Only raise once the
            # run has actually started, where an unconvertible level is a real
            # configuration error.
            if not self._run_started:
                return float(value)
            if cal is None or not getattr(cal, "hl_calibrated", False):
                raise RuntimeError(
                    "operator_units='dB HL' requires an HL-calibrated "
                    "CalibrationManager (a profile with a 'retspl' table). "
                    "None is available; cannot interpret levels in dB HL."
                )
            raise RuntimeError(
                "Cannot convert a dB HL level to dB SPL: no carrier frequency "
                "(self.fc) is set for the current config."
            )
        return cal.hl_to_spl(float(value), float(fc))

    def _setup_default_gui_config(self):
        """Set default GUI configuration if not provided."""
        defaults = {
            'question': "Did you hear the stimulus?",
            'options': ['0 (No)', '1 (Yes)'],
            'keys': ['0', '1'],
            'allow_repeat': True,
            'window_title': "Audiology Test",
            'window_geometry': "600x250+100+100",
            'font_size': 14
        }
        
        # Merge user config with defaults
        for key, value in defaults.items():
            if key not in self.gui_config:
                self.gui_config[key] = value
        
    def _setup_variable_looping(self):
        """Extract inner/outer variables and create config combinations."""
        # Store VarSpec objects as attributes
        for key, spec in self.params.items():
            setattr(self, key, spec)
        
        # Extract inner and outer variables
        if "inner" not in self.params:
            raise ValueError("params must contain 'inner' key with adaptive parameter")
        
        self.inner_var = self.params["inner"]
        self.outer_vars = [
            self.params[k] for k in self.params 
            if k.startswith("outer_")
        ]
        
        # Create all combinations of outer variables.
        #
        # One outer var may be designated a BLOCKING var (default "pan", via
        # self.block_outer_var_name). It is NOT part of the global shuffle:
        # all configs for one of its values are presented before moving to the next
        # value. This makes single-ear paradigms (PTA, LDL) run one ear fully,
        # then the other -- each ear internally randomized, and the ear (block)
        # order itself randomized to counterbalance across participants. No-ops
        # when the blocking var is absent or single-valued (e.g. all diotic
        # paradigms), preserving the original flat-product + flat-shuffle behavior.
        block_var = None
        if self.block_outer_var_name is not None:
            for v in self.outer_vars:
                if v.name == self.block_outer_var_name and len(v.data) > 1:
                    block_var = v
                    break

        rest_vars = [v for v in self.outer_vars if v is not block_var]
        rest_names = [v.name for v in rest_vars]
        rest_data = [v.data for v in rest_vars]

        def _build_block(block_assignment):
            # Product of the non-blocking outer vars, optionally shuffled, with
            # block_assignment (e.g. {"pan": -1.0}) merged into every config.
            if rest_vars:
                combos = [
                    dict(zip(rest_names, combo))
                    for combo in itertools.product(*rest_data)
                ]
            else:
                combos = [{}]
            if self.randomize_config_order and len(combos) > 1:
                random.shuffle(combos)
            for c in combos:
                c.update(block_assignment)
            return combos

        self.unwrapped_params = []
        self._ear_block_start = []           # True at the first config of each block
        self._blocking_active = block_var is not None
        if block_var is None:
            # Single implicit block = full product (original behavior).
            block = _build_block({})
            self.unwrapped_params = block
            self._ear_block_start = [i == 0 for i in range(len(block))]
        else:
            block_values = list(block_var.data)
            if self.randomize_config_order and len(block_values) > 1:
                random.shuffle(block_values)  # randomize ear (block) order
            for bv in block_values:
                block = _build_block({block_var.name: bv})
                self._ear_block_start.extend([True] + [False] * (len(block) - 1))
                self.unwrapped_params.extend(block)

        self.total_num_configs = len(self.unwrapped_params)

        if self.verbose:
            if self._blocking_active:
                print(f"Config order: blocked by '{block_var.name}' "
                      f"({len(block_var.data)} blocks), randomized within block "
                      f"({self.total_num_configs} configs)")
            elif self.randomize_config_order and self.total_num_configs > 1:
                print(f"Config order randomized ({self.total_num_configs} configs)")
        
        self.set_current_config(0)
        
        # Initialize the adaptive parameter
        self.initialize_adaptive_param()
    
    # ============================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # ============================================================
    
    def prepare_trial(self):
        """
        Prepare the next trial - configure stimuli and call TrialPlayer.
        
        This method must:
        1. Increment self.trial_num
        2. Check self.is_catch_trial (set by base class)
        3. Configure trial parameters accordingly (catch vs. normal)
        4. Call self.tp.new_trial(...) with appropriate parameters
        
        Example for PTA:
            self.trial_num += 1
            
            if self.is_catch_trial:
                amp = 0.0  # No sound for catch trial
            else:
                amp = self.trial_amp  # Use current adaptive amplitude
                
            self.tp.new_trial(wave_type="sin", fc=self.fc, amp=amp, ...)
        """
        raise NotImplementedError("Subclass must implement prepare_trial()")
    
    def adapt_difficulty(self, direction):
        """
        Adjust the adaptive parameter based on participant performance.
        
        Args:
            direction: "harder" or "easier"
        
        Example for PTA (amplitude):
            if direction == "harder":
                self.trial_amp *= TrialPlayer.db2amp(-10)  # quieter = harder
            elif direction == "easier":
                self.trial_amp *= TrialPlayer.db2amp(5)    # louder = easier
                self.trial_amp = min(self.trial_amp, 1.0)
        
        Example for GAP (gap duration):
            if direction == "harder":
                self.gap_duration *= 0.5  # shorter gap = harder
            elif direction == "easier":
                self.gap_duration *= 2.0  # longer gap = easier
        """
        raise NotImplementedError("Subclass must implement adapt_difficulty()")
    
    def get_log_data(self):
        """
        Return paradigm-specific data for logging.
        
        Returns:
            dict with keys matching desired CSV columns
            
        Example for PTA:
            return {
                "freq": self.fc,
                "amplitude": TrialPlayer.amp2db(self.trial_amp)
            }
            
        Example for GAP:
            return {
                "gap_duration_ms": self.gap_duration * 1000
            }
        """
        raise NotImplementedError("Subclass must implement get_log_data()")
    
    # ============================================================
    # OPTIONAL METHODS - Can be overridden by subclasses
    # ============================================================
    
    def initialize_adaptive_param(self):
        """
        Initialize the adaptive parameter from inner variable config.
        
        Default: Does nothing (subclass should set initial value)
        
        Example for PTA:
            # inner_var.data = {start: 1.0, step_down: -10, step_up: 5, ...}
            self.trial_amp = self.inner_var.data.get('start', 1.0)
        """
        pass
    
    def get_trial_description(self):
        """
        Return a description of the current trial for GUI display.
        
        Returns:
            String describing trial (default: generic description)
        """
        return f"Config {self.config_num}/{self.total_num_configs}, Trial {self.trial_num}"
    
    def reset_adaptive_param(self):
        """
        Reset adaptive parameter to initial value (called when starting new config).
        
        Default: Calls initialize_adaptive_param()
        """
        self.initialize_adaptive_param()

    def _reset_trial_state(self):
        """
        Reset all volatile trial-level state to initial values.

        Called between configs during a normal run, and after a demo trial
        to ensure the paradigm starts in a clean state.
        Does NOT touch config order, participant_id, or data log.
        """
        self.trial_num = 0
        self.current_streak = 0
        self.last_current_streak = 0
        self.total_num_reversals = 0
        self.trials_remaining = None
        self.total_TP = 0
        self.total_FN = 0
        self.total_FP = 0
        self.total_TN = 0
        self._had_false_positive_this_run = False
        self.threshold_dB = None
        self.slope_k = None
        self.make_harder = False
        self.make_easier = False
        self.end_config = False
        self.end_paradigm = False
        self.reset_to_midpoint = False
        self._at_wrv_limit = False
        self._aborted_by_operator = False
        self._mulligan_available = True    # Reset: mulligan available for new config
        self._mulligan_used = False        # Reset: no mulligan used yet this config
        self._has_stepped_down = False     # Reset: no descent yet this config
        self.user_input = None
        self.trial_repeats = -1
        self.is_catch_trial = False
        self.reset_adaptive_param()

    def play_demo_trial(self, demo_vals: dict) -> None:
        """
        Play a single demo trial with the given parameter values.

        Temporarily applies demo_vals as instance attributes (mirroring
        set_current_config), calls prepare_trial() and tp.play_trial(),
        then resets all trial state so the real run starts clean.

        Args:
            demo_vals: dict mapping attribute names to values, e.g.
                       {'fc': 1000.0, 'pan': -1.0, 'trial_amp': 0.5}
                       Keys should match outer var names plus the inner
                       var name (adaptive parameter).
        """
        # Save current attribute values so we can restore them
        saved = {k: getattr(self, k, None) for k in demo_vals}

        try:
            # Apply demo values
            for k, v in demo_vals.items():
                setattr(self, k, v)

            # Derive any outer-var-dependent attrs (e.g. IFMC/TMC probe_level
            # from probe_freq); mirrors the end of set_current_config so the
            # demo path matches a real trial.
            self._derive_dependent_params()

            # Never a catch trial
            self.is_catch_trial = False

            # Play the trial (prepare_trial increments trial_num as side effect)
            self.prepare_trial()
            self.tp.play_trial()

        finally:
            # Restore saved attributes and wipe all trial state
            for k, v in saved.items():
                setattr(self, k, v)
            self._reset_trial_state()

    # ============================================================
    # CORE ADAPTIVE LOGIC - Should not need to override
    # ============================================================
    
    def set_current_config(self, ind):
        """Set current configuration from unwrapped_params list."""
        if ind < len(self.unwrapped_params):
            for key, val in self.unwrapped_params[ind].items():
                setattr(self, key, val)
        self._derive_dependent_params()

    def _derive_dependent_params(self):
        """Hook: derive attributes that depend on outer vars, after they are set.

        Called at the end of set_current_config (normal run) AND after demo
        values are applied in play_demo_trial, so paradigms that compute a
        derived attribute from an outer var (e.g. IFMC/TMC probe_level from
        probe_freq) have it in BOTH paths. Base implementation is a no-op.
        """
        pass
    
    def determine_catch_trial(self):
        """
        Determine if this trial should be a catch trial.
        
        Rules:
        - Trial 0 (first): Never catch
        - Trial 1 (second): Always catch
        - Others: Probabilistic based on adaptive catch rate
        
        Note: trial_num hasn't been incremented yet when this is called
        """
        rng = self._rng
        
        if self.trial_num == 0:  # First trial
            self.is_catch_trial = False
        elif self.trial_num == 1:  # Second trial
            self.is_catch_trial = True
        else:  # Subsequent trials
            self.is_catch_trial = rng.choice(
                [False, True], 
                p=[1 - self._current_catch_trial_rate, self._current_catch_trial_rate]
            )
        
        if self.verbose:
            print(f"Trial {self.trial_num}: catch_trial = {self.is_catch_trial}")
    
    def execute_trial(self):
        """Play the trial using TrialPlayer."""
        self.trial_repeats += 1
        self.tp.play_trial()

    def update_gui_state(self, trial_playing=True):
        """
        Update GUI to show trial playing state without waiting for response.
        
        Args:
            trial_playing: If True, show "Playing..." and disable buttons
        """
        if self.root is None:
            return
        
        # Clear previous widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Display status
        question_text = "Playing stimulus..." if trial_playing else self.gui_config['question']
        label = tk.Label(
            self.root, 
            text=question_text, 
            font=("Arial", self.gui_config['font_size'])
        )
        label.pack(pady=20)
        
        # Create button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack()
        
        num_options = len(self.gui_config['options'])
        allow_repeat = self.gui_config['allow_repeat']
        
        # Create option buttons (only show if trial NOT playing)
        if not trial_playing:
            for i, option_text in enumerate(self.gui_config['options']):
                btn = tk.Button(
                    button_frame, 
                    text=option_text, 
                    width=12
                )
                btn.grid(row=0, column=i, padx=10)
            
            # Add repeat button if enabled (on second row so it's always visible)
            if allow_repeat:
                repeat_btn = tk.Button(
                    button_frame, 
                    text="Repeat (R)", 
                    width=12
                )
                repeat_btn.grid(row=1, column=0, columnspan=num_options, pady=(8,0))
        
        # Force GUI update
        self.root.update()

    def get_response(self, trial_playing=True):
        """
        Get user response via GUI.
        
        Args:
            trial_playing: If True, disable all buttons (trial in progress)
        
        Uses self.gui_config to determine question text, button labels, and keys.
        
        Returns:
            Integer index of chosen option (0, 1, 2, ...) or None (if repeat requested)
        """
        result = {'value': None}
        response_registered = {'flag': False}  # Prevent multiple responses
        self._resp_time = None  # ptb timestamp of the accepted response
        
        num_options = len(self.gui_config['options'])
        allow_repeat = self.gui_config['allow_repeat']
        
        def respond(value):
            if response_registered['flag']:
                return  # Ignore if already responded

            response_registered['flag'] = True
            self._resp_time = ptb.GetSecs()  # earliest accepted-response stamp (ptb clock)

            # Immediately clear buttons so participant can't click again,
            # and show a brief holding message while the trial is processed.
            for widget in self.root.winfo_children():
                widget.destroy()
            tk.Label(self.root,
                     text="...",
                     font=("Arial", self.gui_config['font_size'])
                     ).pack(pady=20)
            self.root.update()

            if value == "repeat":
                result['value'] = None
            else:
                result['value'] = value
            self.root.quit()
        
        def on_key(event):
            if response_registered['flag']:
                return  # Ignore if already responded
            
            # Check for option keys
            for i, key in enumerate(self.gui_config['keys']):
                if event.char == key:
                    respond(i)
                    return
            
            # Check for repeat key
            if allow_repeat and event.char.lower() == 'r':
                respond("repeat")
        
        # Create window if it doesn't exist
        if self.root is None:
            self.root = tk.Tk()
            self.root.title(self.gui_config['window_title'])
            self.root.geometry(self.gui_config['window_geometry'])
        
        # Clear previous widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Display question
        label = tk.Label(
            self.root, 
            text=self.gui_config['question'], 
            font=("Arial", self.gui_config['font_size'])
        )
        label.pack(pady=20)
        
        # Create button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack()
        
        # Create option buttons
        for i, option_text in enumerate(self.gui_config['options']):
            btn = tk.Button(
                button_frame, 
                text=option_text, 
                width=12, 
                command=lambda idx=i: respond(idx)
            )
            btn.grid(row=0, column=i, padx=10)
        
        # Add repeat button if enabled (on second row so it's always visible)
        if allow_repeat:
            repeat_btn = tk.Button(
                button_frame, 
                text="Repeat (R)", 
                width=12, 
                command=lambda: respond("repeat")
            )
            repeat_btn.grid(row=1, column=0, columnspan=num_options, pady=(8,0))
        
        # CRITICAL: Flush any pending events before binding keyboard
        self.root.update()  # Process any queued events
        
        # NOW bind keyboard shortcuts (after flushing queue)
        self.root.bind("<KeyRelease>", on_key)
        
        self.root.update_idletasks()
        self.root.mainloop()
        
        # Unbind keyboard after response to prevent carryover
        self.root.unbind("<KeyRelease>")

        # Per-trial reaction time, referenced to the end of the last audible
        # interval (self.tp.stim_end_time). NOTE: this INCLUDES a fixed dead
        # interval where the participant cannot yet respond -- FIR ringout tail
        # (~85 ms calibrated / 0 ms uncalibrated) + PTB margin + the 0.5 s
        # anti-click wait + GUI build. The ringout component makes this offset
        # calibration-dependent. Accepted (single-column decision, 2026-06-30).
        # On a "repeat" this is recomputed on the next get_response() call, so
        # the logged value references the last (responded) playback.
        _se = getattr(self.tp, "stim_end_time", None)
        if self._resp_time is not None and _se is not None:
            self.reaction_time_s = self._resp_time - _se
        else:
            self.reaction_time_s = np.nan

        return result['value']
    
    def check_answer(self):
        """
        Classify response as TP (true positive), FN (false negative), 
        FP (false positive), or TN (true negative).
        
        Default behavior: option 0 = "No/Not detected", option 1 = "Yes/Detected"
        Override this method if your paradigm needs different response logic.
        """
        # Default: 0 = No, 1 = Yes
        detected = (self.user_input == 1)
        
        if not self.is_catch_trial:  # Normal trial (stimulus presented)
            if detected:
                self.correct_answer = "TP"  # Heard it - correct
            else:
                self.correct_answer = "FN"  # Didn't hear it - incorrect
        else:  # Catch trial (no stimulus)
            if detected:
                self.correct_answer = "FP"  # False alarm - caught!
            else:
                self.correct_answer = "TN"  # Correct rejection
        
        if self.verbose:
            print(f"Answer: {self.correct_answer}")
    
    def show_false_positive_warning(self):
        """Show FP warning inside the existing participant GUI (no new windows).

        Spawning a messagebox while PTB audio is active causes a segfault on
        macOS due to CoreAudio/tkinter thread conflicts. Instead we update the
        label in the existing root window and pause briefly.
        """
        if self.root is None:
            return

        # Clear current widgets and show warning text in-place
        for widget in self.root.winfo_children():
            widget.destroy()

        warning_label = tk.Label(
            self.root,
            text="FALSE POSITIVE!\nPlease only respond\nif you heard the stimulus.",
            font=("Arial", self.gui_config.get('font_size', 20), "bold"),
            fg="red",
            bg=self.root.cget('bg')
        )
        warning_label.pack(expand=True)
        self.root.update()

        # Brief pause so the operator/participant can read it
        core.wait(2.0)

        # GUI will be rebuilt on next update_gui_state() call

    def _ear_block_label(self, upcoming_config_num):
        """Announcement string for the start of an ear block, else "".

        Returns "Beginning LEFT ear" / "Beginning RIGHT ear" only when blocking
        is active, the blocking var is 'pan', the upcoming config is the first of
        its block, and pan resolves to a lateralized value (<0 / >0). Centre
        (pan==0), non-pan blocking, out-of-range index, or no blocking -> "".
        """
        if not getattr(self, "_blocking_active", False):
            return ""
        if self.block_outer_var_name != "pan":
            return ""  # only pan maps to an "ear"; keep wording honest
        starts = getattr(self, "_ear_block_start", [])
        idx = upcoming_config_num - 1
        if not (0 <= idx < len(starts)) or not starts[idx]:
            return ""
        pan = self.unwrapped_params[idx].get(self.block_outer_var_name)
        if pan is None:
            return ""
        if pan < 0:
            return "Beginning LEFT ear"
        if pan > 0:
            return "Beginning RIGHT ear"
        return ""  # centre / both -> no announcement

    def _show_pause(self, duration, upcoming_config_num, is_pre_first=False):
        """Show a countdown pause screen between configs (or before first trial).

        Participant/examiner can press SPACE or click "Begin Now" to advance
        immediately, otherwise the pause auto-advances when the countdown
        reaches zero.

        No-ops if there is no GUI (headless) or duration <= 0.

        Args:
            duration: Countdown length in seconds. <= 0 disables the pause.
            upcoming_config_num: 1-based index of the config that is about to start.
            is_pre_first: If True, this is the very first pause (before any
                          trial of the paradigm) — heading text differs.
        """
        if self.root is None:
            return
        if duration is None or duration <= 0:
            return

        # --- Build pause screen ---
        for widget in self.root.winfo_children():
            widget.destroy()

        if is_pre_first:
            heading_text = "Ready to begin"
        else:
            heading_text = "Ready to continue"

        font_size = self.gui_config.get('font_size', 20)

        heading_label = tk.Label(
            self.root,
            text=heading_text,
            font=("Arial", font_size, "bold"),
        )
        heading_label.pack(pady=(20, 10))

        subline_label = tk.Label(
            self.root,
            text="Press SPACE or click button to start, or wait...",
            font=("Arial", max(10, font_size - 6)),
        )
        subline_label.pack(pady=(0, 10))

        # Ear-block announcement (single-ear paradigms): name the ear at the
        # first config of each block. "" for centre/diotic/non-pan blocking.
        ear_text = self._ear_block_label(upcoming_config_num)
        if ear_text:
            ear_label = tk.Label(
                self.root,
                text=ear_text,
                font=("Arial", max(12, font_size - 2), "bold"),
            )
            ear_label.pack(pady=(0, 10))

        remaining = {'sec': int(round(duration))}
        countdown_label = tk.Label(
            self.root,
            text=f"Starting in {remaining['sec']}",
            font=("Arial", font_size),
        )
        countdown_label.pack(pady=10)

        # --- Mutable state for tick / early-exit ---
        after_id = {'id': None}
        finished = {'flag': False}

        def finish():
            if finished['flag']:
                return
            finished['flag'] = True
            if after_id['id'] is not None:
                try:
                    self.root.after_cancel(after_id['id'])
                except Exception:
                    pass
                after_id['id'] = None
            self.root.quit()

        def tick():
            if finished['flag']:
                return
            remaining['sec'] -= 1
            if remaining['sec'] <= 0:
                countdown_label.config(text="Starting in 0")
                self.root.update_idletasks()
                finish()
            else:
                countdown_label.config(text=f"Starting in {remaining['sec']}")
                after_id['id'] = self.root.after(1000, tick)

        def on_space(event):
            finish()

        begin_btn = tk.Button(
            self.root,
            text="Begin Now",
            width=14,
            command=finish,
        )
        begin_btn.pack(pady=10)

        self.root.bind("<KeyRelease-space>", on_space)
        after_id['id'] = self.root.after(1000, tick)
        # Bring window to foreground. lift()/focus_force() alone is unreliable
        # on macOS; the topmost-toggle pattern works more consistently.
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.update()
        self.root.attributes('-topmost', False)
        self.root.focus_force()
        self.root.update_idletasks()
        self.root.mainloop()
        self.root.unbind("<KeyRelease-space>")

        # --- Clean up screen before next stimulus prep ---
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.update()
    
    def update_counters(self):
        """
        Update streaks, reversals, and trials_remaining based on response.
        """
        self.last_current_streak = self.current_streak
        
        # Update performance counters
        if self.correct_answer == 'TP':
            self.total_TP += 1
            self.current_streak = max(self.current_streak + 1, 1)
            self._mulligan_available = False  # Consumed: first non-catch trial was a hit
        elif self.correct_answer == 'FN':
            self.total_FN += 1
            self.current_streak = min(self.current_streak - 1, -1)
            # --- Option A: Mulligan ---
            # If this is the first non-catch trial and the participant missed,
            # forgive the streak hit to prevent a premature reversal on the next
            # TP. The level still steps up: make_easier is set explicitly here
            # because streak=0 would not trigger it in check_trial_conds().
            if self._mulligan_available:
                self.current_streak = 0
                self._mulligan_available = False
                self._mulligan_used = True
                self.make_easier = True   # step up still fires
                # Retroactively mark this trial in the already-written log row
                if not self.data.empty:
                    last_idx = self.data.index[-1]
                    self.data.loc[last_idx, 'is_mulligan'] = True
                    self._data_rows[-1]['is_mulligan'] = True
                if self.verbose:
                    print("  *** MULLIGAN granted: first-trial FN forgiven, streak stays 0 ***")
        elif self.correct_answer == 'FP':
            self.total_FP += 1

            self._had_false_positive_this_run = True  # Mark that FP occurred            # Don't change streak on false positive
            if self.verbose:
                print("FALSE POSITIVE! ~~~> Please don't guess")
            self.show_false_positive_warning()
        elif self.correct_answer == 'TN':
            self.total_TN += 1
            # Don't change streak on correct rejection
            if self.verbose:
                print("Passed catch trial")
        
        # Detect reversal
        rev_test = abs(self.last_current_streak - self.current_streak)
        if rev_test > 1 and self._has_stepped_down:  # Option B: only count after first descent
            self.total_num_reversals += 1
            if self.verbose:
                print(f"!!! REVERSAL !!! (total: {self.total_num_reversals})")
            
            # Start countdown after FIRST reversal
            if self.total_num_reversals == 1:
                # Set countdown to include trial before reversal
                # Per Lecluyse 2009: "counting from trial immediately before first no-response"
                self.trials_remaining = self.trials_after_reversal - 1
                
                # Set flag to reset to midpoint (paradigm will handle this)
                self.reset_to_midpoint = True
                
                if self.verbose:
                    print(f"!!! FIRST REVERSAL !!! - Starting {self.trials_after_reversal} trial countdown (includes trial before reversal)")
                    print(f"    Next trial will reset adaptive parameter to midpoint")
        
        self.direction = np.sign(self.current_streak)
        
        # Decrement trials_remaining (only if countdown has started and not a catch trial)
        if self.trials_remaining is not None and self.trials_remaining > 0:
            if not self.is_catch_trial:  # Only count non-catch trials
                self.trials_remaining -= 1
            if self.verbose:
                print(f"Trials remaining: {self.trials_remaining}")
        
        # Debug output
        if self.verbose:
            print("=" * 50)
            print(f"Catch trial: {self.is_catch_trial}")
            print(f"User input: {self.user_input}")
            print(f"Current streak: {self.current_streak}")
            print(f"Total reversals: {self.total_num_reversals}")
            print("=" * 50)
    
    def check_trial_conds(self):
        """
        Check if difficulty should be adjusted based on current streak.
        Sets make_harder or make_easier flags.
        """
        # Only adjust difficulty on non-catch trials
        if not self.is_catch_trial:
            # Increase difficulty after target correct streak
            if self.current_streak > 0 and (self.current_streak % self.target_streak_correct == 0):
                self.make_harder = True
                if self.verbose:
                    print("~~~> MAKE HARDER <~~~")
            
            # Decrease difficulty after target wrong streak
            elif self.current_streak < 0 and (abs(self.current_streak) % self.target_streak_wrong == 0):
                self.make_easier = True
                if self.verbose:
                    print("~~~> MAKE EASIER <~~~")
        
        # Check if current config is complete
        if self.trials_remaining is not None and self.trials_remaining < 1:
            self.end_config = True

    def _clip_adaptive_param(self):
        """
        Check whether the adaptive parameter is at its min/max boundary
        and set _at_wrv_limit accordingly.

        Uses inner_var.name to locate the attribute (e.g. 'trial_amp',
        'masker_level') and inner_var.data['min'/'max'] for the limits.
        Subclasses already enforce clipping in adapt_difficulty(); this
        method just detects whether a clip occurred so the operator can
        be notified — it does NOT apply a second clip.
        """
        if not isinstance(self.inner_var.data, dict):
            return  # No limits defined for non-dict inner vars

        attr = self.inner_var.name
        if not hasattr(self, attr):
            return

        val = getattr(self, attr)
        min_val = self.inner_var.data.get('min')
        max_val = self.inner_var.data.get('max')

        at_min = (min_val is not None and val <= min_val)
        at_max = (max_val is not None and val >= max_val)
        self._at_wrv_limit = at_min or at_max

        if self._at_wrv_limit and self.verbose:
            which = 'min' if at_min else 'max'
            limit = min_val if at_min else max_val
            print(f"  *** WRV LIMIT HIT ({which}={limit}) — adaptive param stuck at {val}")

    def notify_wrv_limit(self):
        """
        Notify operator that the adaptive parameter has hit its boundary.
        Always logs to console. If operator GUI is available, shows a blocking
        modal overlay with three options:
          - 'abort_paradigm': stop everything, discard data
          - 'abort_config':   end current config, write partial data, continue
          - 'continue':       do nothing
        If no GUI, defaults to abort_paradigm.
        """
        attr = self.inner_var.name
        val = getattr(self, attr, '?')
        min_val = self.inner_var.data.get('min') if isinstance(self.inner_var.data, dict) else None
        max_val = self.inner_var.data.get('max') if isinstance(self.inner_var.data, dict) else None

        at_min = (min_val is not None and val <= min_val)
        which = 'MIN' if at_min else 'MAX'
        limit = min_val if at_min else max_val

        msg = (f"Config {self.config_num}/{self.total_num_configs}: "
               f"{attr} at {which} boundary ({limit}). Track may be stuck.")
        print(f"\n{'!'*60}\nWRV LIMIT HIT — {msg}\n{'!'*60}")

        if self.operator_display is not None:
            choice = self.operator_display.show_wrv_warning(msg)
        else:
            choice = 'abort_paradigm'
            print("  No operator GUI — aborting paradigm by default.")

        if choice == 'abort_paradigm':
            print("  Operator chose ABORT PARADIGM — stopping without saving.")
            self._aborted_by_operator = True
            self.end_paradigm = True
            # Destroy participant GUI cleanly
            if self.root is not None:
                self.root.destroy()
                self.root = None
        elif choice == 'abort_config':
            print("  Operator chose ABORT CONFIG — ending config, writing partial data.")
            self.end_config = True
        else:
            print("  Operator chose CONTINUE.")

    def update_trial_params(self):
        """
        Update trial parameters based on flags set by check_trial_conds().
        """
        # Reset per-trial flags
        self.user_input = None
        self.trial_repeats = -1
        self._at_wrv_limit = False
        
        # Adjust difficulty if flagged
        if self.make_harder:
            self._has_stepped_down = True   # Option B: record first descent
            self.adapt_difficulty("harder")
            self.make_harder = False
        elif self.make_easier:
            self.adapt_difficulty("easier")
            self.make_easier = False
        
        # Check if adaptive param hit its boundary after adjustment
        self._clip_adaptive_param()
        if self._at_wrv_limit:
            self.notify_wrv_limit()
        
        # Move to next config if flagged
        if self.end_config:
            print("\n" + "/" * 60)
            print(f"CONFIG {self.config_num}/{self.total_num_configs} COMPLETE")
            print("-" * 60)
            if self.verbose:
                print(f"Performance Summary:")
                print(f"  True Positives (TP):  {self.total_TP}")
                print(f"  False Negatives (FN): {self.total_FN}")
                print(f"  False Positives (FP): {self.total_FP}")
                print(f"  ~~> False Positive FLAG: {self._had_false_positive_this_run}")
                print(f"  True Negatives (TN):  {self.total_TN}")
            
            # Estimate threshold from logged data
            # Filter data: current config, non-catch trials, last trials_after_reversal trials
            config_data = self.data[self.data['config_num'] == self.config_num]
            non_catch_data = config_data[config_data['is_catch_trial'] == False]
            
            # Get last trials_after_reversal trials (includes trial before first reversal)
            threshold_data = non_catch_data.tail(self.trials_after_reversal)
            
            if len(threshold_data) >= 3:
                # Extract levels from inner variable column (adaptive parameter in dB)
                # Column name comes from inner_var.name (e.g., 'trial_amp' for PTA)
                inner_col = self.inner_var.name
                
                if inner_col not in threshold_data.columns:
                    if self.verbose:
                        print(f"\n*** THRESHOLD ESTIMATION SKIPPED ***")
                        print(f"  Inner variable column '{inner_col}' not found in data")
                    self.threshold_dB = np.nan
                    self.slope_k = np.nan
                    continue_estimation = False
                else:
                    continue_estimation = True
                    levels_dB = threshold_data[inner_col].values
                
                if continue_estimation:
                    # Response: 1 if heard (TP), 0 if not heard (FN)
                    responses = (threshold_data['correct_answer'] == 'TP').astype(int).values
                    
                    result = self.fit_psychometric_function(levels_dB, responses)

                    # Reject implausible fits before accepting them. An
                    # unbracketed or near-separable staircase can let the
                    # unbounded curve_fit converge on a garbage solution
                    # (e.g. theta ~ -1e5 with k ~ 1e-5). Guard: theta must
                    # lie within this paradigm's level limits, and the slope
                    # must run in the paradigm's expected direction and be
                    # steep enough to mean anything.
                    #
                    # The slope test is SIGNED. For a detection paradigm more
                    # level means more detection, so k > 0. For the forward-
                    # masking paradigms the adaptive variable is the MASKER
                    # level, so more level means the probe is masked and k is
                    # necessarily NEGATIVE -- see psychometric_slope_sign.
                    # A bare "k > 0" test rejected every physically correct
                    # IFMC/TMC fit and logged NaN.
                    if result['success']:
                        _theta = result['threshold_dB']
                        _k = result['slope_k']
                        _lo = self.inner_var.data.get('min', -np.inf)
                        _hi = self.inner_var.data.get('max', np.inf)
                        _sign = getattr(self, 'psychometric_slope_sign', 1)
                        _signed_k = _k * _sign
                        if not (_lo <= _theta <= _hi
                                and _signed_k >= PSYCHOMETRIC_K_MIN):
                            _want = 'k>0' if _sign > 0 else 'k<0'
                            result['success'] = False
                            result['implausible'] = True
                            result['error'] = (
                                f"Implausible fit rejected: theta={_theta:.1f} "
                                f"(limits [{_lo}, {_hi}]), k={_k:.2e} "
                                f"(need {_want} with |k| >= {PSYCHOMETRIC_K_MIN})"
                            )
                
                    if result['success']:
                        self.threshold_dB = result['threshold_dB']
                        self.slope_k = result['slope_k']
                    
                        # Update the last row of this config with threshold values
                        config_mask = self.data['config_num'] == self.config_num
                        last_idx = self.data[config_mask].index[-1]
                        self.data.loc[last_idx, 'threshold_dB'] = self.threshold_dB
                        self.data.loc[last_idx, 'slope_k'] = self.slope_k
                        # Keep _data_rows in sync
                        self._data_rows[last_idx]['threshold_dB'] = self.threshold_dB
                        self._data_rows[last_idx]['slope_k'] = self.slope_k
                        # Optional dB HL summary (only when an HL table is
                        # loaded and the level is dB SPL at a defined fc).
                        threshold_hl = self._threshold_to_hl(self.threshold_dB)
                        if threshold_hl is not None:
                            self.data.loc[last_idx, 'threshold_dB_HL'] = threshold_hl
                            self._data_rows[last_idx]['threshold_dB_HL'] = threshold_hl
                        
                        if self.verbose:
                            print(f"\n*** THRESHOLD ESTIMATE ***")
                            print(f"  Threshold (theta): {self.threshold_dB:.2f} dB")
                            print(f"  Slope (k): {self.slope_k:.3f}")
                            print(f"  Data points: {len(threshold_data)}")
                    else:
                        if result.get('implausible'):
                            # Non-blocking operator warning, always shown:
                            # this config's threshold is being discarded.
                            print("\n" + "!" * 60)
                            print(f"IMPLAUSIBLE THRESHOLD REJECTED - config "
                                  f"{self.config_num}/{self.total_num_configs}")
                            print(f"  {result.get('error', '')}")
                            print("  Threshold logged as NaN. Consider "
                                  "re-running this config.")
                            print("!" * 60)
                        elif self.verbose:
                            print(f"\n*** THRESHOLD ESTIMATION FAILED ***")
                            print(f"  Reason: {result.get('error', 'Unknown')}")
                        self.threshold_dB = np.nan
                        self.slope_k = np.nan
            else:
                if self.verbose:
                    print(f"\n*** THRESHOLD ESTIMATION SKIPPED ***")
                    print(f"  Insufficient data: {len(threshold_data) if len(threshold_data) > 0 else 0} points (need >= 3)")
                self.threshold_dB = np.nan
                self.slope_k = np.nan
            print("/" * 60)
            
            # Write temp CSV after each config (crash recovery)
            self._write_temp_data()

            # Refresh the operator display while the just-completed config is
            # still the current state (open issue M2). This is the ONLY moment
            # the fitted psychometric curve can be drawn: self.threshold_dB /
            # self.slope_k are set by the fit above, but _reset_trial_state()
            # below clears them back to None, and self.config_num is about to
            # be incremented past the config the data belongs to. Without this
            # call the operator's fitted curve was unreachable - main()'s
            # post-trial update_display() only ever saw the reset state.
            #
            # Placed before _show_pause() below so the curve is on screen for
            # the whole inter-config pause, which is when the operator has time
            # to look at it. It is cleared naturally on the first trial of the
            # next config.
            if self.operator_display is not None:
                self.operator_display.update_display()
            
            if self.config_num < self.total_num_configs:
                self.set_current_config(self.config_num)  # Note: using 0-based indexing (so +1 for display...)
                print(f"\nStarting CONFIG {self.config_num + 1}/{self.total_num_configs}...")
                print("=" * 60)
                print()
            
            
            # Update catch trial rate PER-RUN (not per-trial)
            # Adjust based on whether this run had false positives
            if self._had_false_positive_this_run:
                # Increase rate if participant was caught out
                self._current_catch_trial_rate += self.catch_trial_rate[4]
                if self.verbose:
                    print(f"  False positive detected - increasing catch rate")
            else:
                # Decrease rate if participant was NOT caught (perfect run).
                # Exponential relaxation toward baseRate (UZH MultiThreshold):
                #   rate_new = base + (rate_old - base) * (1 - exp(-tau))
                base = self.catch_trial_rate[1]
                tau = self.catch_trial_rate[3]
                self._current_catch_trial_rate = (
                    base + (self._current_catch_trial_rate - base) * (1.0 - np.exp(-tau))
                )
                if self.verbose:
                    print(f"  No false positives - decreasing catch rate")
            
            # Clip to baseRate/max
            self._current_catch_trial_rate = np.clip(
                self._current_catch_trial_rate,
                self.catch_trial_rate[1],  # baseRate (floor)
                self.catch_trial_rate[2]   # max
            )
            
            if self.verbose:
                print(f"  New catch trial rate: {self._current_catch_trial_rate:.2f}")
            
            self.config_num += 1
            
            # Reset for new config
            self._reset_trial_state()
            
            self.end_config = False

            # Inter-config pause (skipped on the final transition, since we
            # are about to exit the paradigm rather than start a new config).
            if self.config_num <= self.total_num_configs:
                self._show_pause(
                    duration=self.inter_config_pause,
                    upcoming_config_num=self.config_num,
                    is_pre_first=False,
                )
        
                # NOTE: Catch trial rate adjustment moved to end-of-run (see config completion above)
        
        # Wait between trials.
        # Show "Playing stimulus..." partway through the ITI so the participant
        # sees it before the next stimulus plays (random 20-50% of ITI delay).
        iti_pre = self.trial_ITI * random.uniform(0.20, 0.50)
        iti_post = self.trial_ITI - iti_pre
        core.wait(iti_pre)
        self.update_gui_state(trial_playing=True)
        core.wait(iti_post)
    
    def check_paradigm_end_conds(self):
        """Check if all configs are complete."""
        if self.config_num > self.total_num_configs:
            self.end_paradigm = True
            if self.root is not None:
                self.root.destroy()
                self.root = None
    

    
    def fit_psychometric_function(self, levels_dB, responses):
        """
        Fit logistic psychometric function to threshold data.
        
        Per Lecluyse & Meddis (2009):
        "A psychometric function... is fitted to the responses using a 
        least-squares, best-fit procedure, with θ and k as free parameters."
        
        The psychometric function (Equation 1):
            p(L) = 1 / (1 + exp(-k(L - θ)))
        
        Where:
            p(L) = probability of "yes" response at level L
            L = stimulus level (dB)
            k = slope parameter (typically 0.5 for normal hearing, ~1.0 for impaired)
            θ (theta) = threshold (dB) where p(L) = 0.5

        The SIGN of k depends on the paradigm and is not validated here: this
        method fits whatever the data say. A detection paradigm yields k > 0
        (more level -> more detection); a forward-masking paradigm adapting the
        MASKER level yields k < 0 (more level -> probe masked). The caller
        checks the sign against AdaptiveParadigm.psychometric_slope_sign.
        
        Args:
            levels_dB: List/array of stimulus levels in dB
            responses: List/array of binary responses (1 = yes/heard, 0 = no/not heard)
        
        Returns:
            dict with keys:
                'threshold_dB': Estimated threshold (θ)
                'slope_k': Estimated slope parameter (k)
                'success': True if fit converged, False otherwise
                'p_curve': Function to evaluate fitted psychometric curve (if successful)
        """
        import numpy as np
        from scipy.optimize import curve_fit
        
        # Define logistic psychometric function (Equation 1 from Lecluyse 2009)
        def logistic(L, theta, k):
            """Logistic psychometric function."""
            return 1.0 / (1.0 + np.exp(-k * (L - theta)))
        
        # Convert to numpy arrays
        levels_dB = np.array(levels_dB, dtype=float)
        responses = np.array(responses, dtype=float)
        
        # Need at least 3 data points to fit 2 parameters
        if len(levels_dB) < 3:
            return {
                'threshold_dB': np.nan,
                'slope_k': np.nan,
                'success': False,
                'p_curve': None,
                'error': 'Insufficient data points (need >= 3)'
            }
        
        # Check for valid data
        if np.all(responses == 0) or np.all(responses == 1):
            return {
                'threshold_dB': np.nan,
                'slope_k': np.nan,
                'success': False,
                'p_curve': None,
                'error': 'No variation in responses'
            }
        
        try:
            # Initial guesses: theta = median(levels), k = 0.5 (per Lecluyse 2009)
            theta_init = np.median(levels_dB)
            k_init = 0.5
            
            # Fit using nonlinear least-squares
            params, covariance = curve_fit(
                logistic,
                levels_dB,
                responses,
                p0=[theta_init, k_init],
                maxfev=10000
            )
            
            theta_fit, k_fit = params
            
            def p_curve(L):
                return logistic(L, theta_fit, k_fit)
            
            return {
                'threshold_dB': theta_fit,
                'slope_k': k_fit,
                'success': True,
                'p_curve': p_curve,
                'covariance': covariance
            }
            
        except (RuntimeError, ValueError) as e:
            return {
                'threshold_dB': np.nan,
                'slope_k': np.nan,
                'success': False,
                'p_curve': None,
                'error': f'Fit failed: {str(e)}'
            }

    def log_data(self):
        """
        Log current trial data to DataFrame.
        Combines base data with paradigm-specific data from get_log_data().
        """
        # Get paradigm-specific data
        paradigm_data = self.get_log_data()

        
        # Combine with base data
        # Threshold values default to NaN (will be filled on last trial of config)
        row_data = {
            "unix_time": time.time(),
            "config_num": self.config_num,
            "trial_num": self.trial_num,
            "correct_answer": self.correct_answer,
            "trial_repeats": self.trial_repeats,
            "is_catch_trial": self.is_catch_trial,
            "is_mulligan": False,       # May be retroactively set True in update_counters()
            "pan": getattr(self, "pan", 0.0),   # H2: always-present laterality column
            "reaction_time_s": getattr(self, "reaction_time_s", np.nan),  # RT from end of last audible interval
            **paradigm_data,
            "threshold_dB": np.nan,
            "slope_k": np.nan,
        }

        # H2: auto-log every outer variable by name. Outer values are set
        # per-config via setattr in set_current_config, so reading them here
        # makes the missing-outer-var class of bug structurally impossible
        # (e.g. PTA's ear-selecting `pan`), independent of whether a paradigm
        # hand-lists it in get_log_data. Assigning an already-present key
        # updates in place (no column reorder, no duplicate column).
        for _outer in self.outer_vars:
            row_data[_outer.name] = getattr(self, _outer.name, None)

        # Per-row dB HL column (H3). Convert this trial's inner-variable level
        # (e.g. trial_amp for PTA) to dB HL through the same gated path as the
        # threshold_dB_HL summary column. _threshold_to_hl returns None unless
        # the paradigm is hl_reportable, HL-calibrated, and has a defined fc, so
        # the column is emitted ONLY for HL paradigms (PTA) and omitted entirely
        # elsewhere -- mirroring threshold_dB_HL. The inner variable of a
        # difference paradigm (ILD dB, ITD us) is not an absolute SPL; the
        # hl_reportable gate keeps those out, so no nonsensical HL is logged.
        _inner_name = self.inner_var.name
        _level_hl = self._threshold_to_hl(row_data.get(_inner_name))
        if _level_hl is not None:
            row_data[f"{_inner_name}_HL"] = _level_hl

        # H2: per-ear amp values are audit-only and are NEVER written to the
        # data file. On request (debug_amps), print the commanded per-ear gains
        # to the console. Reads the existing _last_*amp* instance attrs only;
        # does not touch the logged row.
        if getattr(self, "debug_amps", False):
            _amps = {k: v for k, v in self.__dict__.items()
                     if k.startswith("_last") and "amp" in k}
            if _amps:
                print(f"  [amp debug] cfg {self.config_num} tr {self.trial_num}: "
                      + ", ".join(f"{k}={v}" for k, v in _amps.items()))

        # Accumulate row in list, then rebuild DataFrame once.
        # Avoids O(n²) copies from repeated pd.concat.
        self._data_rows.append(row_data)
        self.data = pd.DataFrame(self._data_rows)
    
    def write_data_to_disk(self):
        """
        Save data to properly named CSV file.
        
        Filename format: {participant_id}_{paradigm_code}_{timestamp}.csv
        Example: P001_PTA_2026-02-16_14-30-45.csv
        
        CSV column order:
        1. Trial info: unix_time, config_num, trial_num
        2. Trial outcomes: is_catch_trial, trial_repeats, correct_answer
        3. Paradigm variables: Named after params (e.g., trial_amp, fc, trial_dur)
           - Inner variable (adaptive parameter)
           - Outer variables (looped parameters)
        4. Threshold estimates: threshold_dB, slope_k (filled only on last trial of each config)
        
        Raises:
            ValueError: If paradigm_code not set by subclass
        """
        # CRITICAL CHECK: Ensure subclass set paradigm_code
        if self.paradigm_code is None:
            raise ValueError(
                f"Paradigm code not set! "
                f"Subclass {self.__class__.__name__} must set self.paradigm_code in __init__ "
                f"BEFORE calling super().__init__(). "
                f"Example codes: 'PTA', 'FM', 'AM', 'GAP', 'DLI', 'ILD', 'ITD', 'IFMC', etc."
            )
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Use working directory so path is correct regardless of install structure
        # (test scripts are always run from the project root)
        output_dir = Path.cwd() / "test_data"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # New filename format: {participant_id}_{paradigm_code}_{timestamp}.csv
        filename = output_dir / f"{self.participant_id}_{self.paradigm_code}_{timestamp}.csv"
        
        self._write_csv_with_header(filename, timestamp)
        print(f"\nData saved to: {filename}")
        
        return filename  # Return path for potential use

    def _temp_data_path(self) -> Path:
        """Return path for temporary in-progress CSV."""
        output_dir = Path.cwd() / "test_data"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{self.participant_id}_{self.paradigm_code}_temp.csv"

    def _debug_log_dir(self) -> Path:
        """Return (and create) the folder for debug artifacts (per-trial
        resource CSV, crash tracebacks). Kept as a sibling of test_data/ so
        debug output does not mingle with participant results."""
        d = Path.cwd() / "debug_logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _write_temp_data(self):
        """
        Write current data to a temp CSV after each config completes.
        Overwrites the previous temp file. Allows data recovery on crash.
        """
        if self.data.empty:
            return
        path = self._temp_data_path()
        # Use a stable timestamp for temp files (current write time);
        # rewriting the header on each temp dump is cheap.
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._write_csv_with_header(path, timestamp)
        if self.verbose:
            print(f"  Temp data written to: {path.name}")

    # ==================================================================
    # CSV header / metadata
    # ==================================================================

    def _write_csv_with_header(self, filepath: Path, timestamp: str) -> None:
        """
        Write self.data to filepath, prepending a `#`-prefixed metadata
        header. Reader-side: pd.read_csv(..., comment="#") skips header
        lines automatically; legacy CSVs without headers parse identically.
        """
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            for line in self._build_csv_header(timestamp):
                f.write(line + "\n")
            self.data.to_csv(f, index=False)

    def _build_csv_header(self, timestamp: str) -> list:
        """
        Return list of `# key: value` strings to prepend to CSV files.
        Composed of universal metadata + paradigm-specific overrides.
        """
        md = self._get_metadata_dict(timestamp)
        # Add a delimiter line for visual scanability when grepping.
        return [f"# {k}: {v}" for k, v in md.items()]

    def _get_metadata_dict(self, timestamp: str) -> "OrderedDict":
        """
        Build the metadata dict written to the CSV header.

        Universal fields are populated here. Paradigm-specific fields
        (e.g. level_units, masker_units) come from the
        _get_paradigm_metadata() hook, which subclasses override.
        Paradigm-specific fields are merged AFTER the universal ones,
        so a paradigm can override a universal value if needed.
        """
        md: "OrderedDict[str, object]" = OrderedDict()

        # --- Provenance ---
        md["prolactin_version"] = _PROLACTIN_VERSION
        md["paradigm"] = self.paradigm_code
        md["participant_id"] = self.participant_id
        md["datetime_created"] = timestamp
        md["python_version"] = sys.version.split()[0]
        md["platform"] = platform.platform()
        md["operator_units"] = self.operator_units

        # --- Calibration (only if attached) ---
        if self.calibration is not None:
            cal = self.calibration
            md["calibration_profile"] = cal.active_profile
            md["sample_rate_hz"] = cal.sample_rate
            md["fir_calibrated"] = cal.fir_calibrated
            md["spl_calibrated"] = cal.spl_calibrated
            md["max_spl_ceiling_dB"] = cal.max_spl
            if cal.spl_calibrated:
                # Reach into the profile for the SPL ref details. These are
                # informational only; the canonical conversion is via
                # cal.spl_to_amplitude().
                spl = cal._profile.get("spl_calibration", {})
                if "reference_amplitude" in spl:
                    md["spl_reference_amplitude"] = spl["reference_amplitude"]
                if "measured_spl_left" in spl:
                    md["spl_measured_left_dB"] = spl["measured_spl_left"]
                if "measured_spl_right" in spl:
                    md["spl_measured_right_dB"] = spl["measured_spl_right"]
            # HL conversion provenance (only if an HL table is loaded).
            if getattr(cal, "hl_calibrated", False):
                md["hl_calibrated"] = True
                conv = getattr(cal, "hl_converter", None)
                if conv is not None:
                    md["retspl_source"] = conv.source
            else:
                md["hl_calibrated"] = False
        else:
            md["calibration_profile"] = "none"

        # --- Variable structure ---
        try:
            md["inner_var"] = self.inner_var.name
            outer_summary = ", ".join(
                f"{v.name}={v.data}" for v in self.outer_vars
            )
            md["outer_vars"] = outer_summary if outer_summary else "(none)"
            md["n_configs"] = self.total_num_configs
        except AttributeError:
            # Robustness: don't crash header writing on incomplete state.
            pass

        # --- Paradigm-specific overrides ---
        md.update(self._get_paradigm_metadata())

        # --- Session metadata (from setup dialog, etc.) ---
        # Written last so it can override prior fields if needed.
        md.update(self.session_metadata)

        return md

    def _threshold_to_hl(self, threshold_db_spl):
        """
        Convert a dB SPL threshold to dB HL for the current config's
        frequency, for the threshold_dB_HL summary column.

        Returns None (column left as NaN) when HL conversion is not
        applicable: no HL-calibrated CalibrationManager, paradigm not
        flagged hl_reportable, no defined carrier frequency (self.fc),
        or a NaN/None threshold. Never raises.
        """
        if threshold_db_spl is None:
            return None
        try:
            if np.isnan(threshold_db_spl):
                return None
        except TypeError:
            return None
        cal = self.calibration
        if cal is None or not getattr(cal, "hl_calibrated", False):
            return None
        # HL is reported only for paradigms that explicitly opt in via the
        # hl_reportable metadata flag. Per team decision (2026-06-11) this is
        # PTA only: HL is meaningful for an absolute single-ear dB SPL level at
        # one pure-tone fc. Inferring eligibility from level_units == "dB SPL"
        # over-fired for LDL (out of scope) and SRT (broadband speech -> invalid).
        if self._get_paradigm_metadata().get("hl_reportable") is not True:
            return None
        fc = getattr(self, "fc", None)
        if fc is None:
            return None
        try:
            return cal.spl_to_hl(float(threshold_db_spl), float(fc))
        except Exception:
            return None

    def _get_paradigm_metadata(self) -> dict:
        """
        Hook for subclasses to inject paradigm-specific metadata into
        the CSV header. Returns an empty dict by default.

        Common entries to override with:
        - level_units: e.g. "dB SPL", "dB FS", "dB SL"
        - masker_units (IFMC/TMC): e.g. "dB SPL"
        - probe_offset_dB: e.g. 10.0 (dB above threshold)
        """
        return {}

    def _delete_temp_data(self):
        """Delete temp CSV on clean paradigm completion."""
        path = self._temp_data_path()
        try:
            if path.exists():
                path.unlink()
                if self.verbose:
                    print(f"  Temp file deleted: {path.name}")
        except OSError:
            pass  # Non-critical — ignore if deletion fails
    
    # ============================================================
    # MAIN LOOP
    # ============================================================
    
    def main(self):
        """
        Main experimental loop.
        Runs all configs until paradigm complete.
        """
        # The run is starting; calibration is attached by now. In dB HL mode,
        # (re)initialize the first config's adaptive parameter so start/min/max
        # resolve to dB SPL at the current frequency (the __init__ priming ran
        # before any CalibrationManager was attached). SPL-mode runs were fully
        # primed at construction and are left untouched.
        self._run_started = True
        if self.operator_units == "dB HL":
            self.initialize_adaptive_param()

        # Initialize operator display (if enabled)
        if self.show_operator_display:
            self.operator_display = get_operator_display()
            self.operator_display.attach_paradigm(self)
            self.operator_display.show()

        # Initialize per-trial resource logger (debug; only when enabled).
        # Lazy import + try/except so a missing resource_logger.py or absent
        # psutil never blocks a run.
        if self.resource_logging:
            try:
                from utils.resource_logger import ResourceLogger
                self.resource_logger = ResourceLogger(
                    self._debug_log_dir(),
                    self.participant_id,
                    self.paradigm_code,
                    enabled=True,
                    object_scan_every=self.resource_scan_every,
                )
            except Exception as _rl_exc:
                print(f"[resource_logger] init failed, continuing without it: {_rl_exc}")
                self.resource_logger = None

        # Create GUI window once at start
        self.root = tk.Tk()
        self.root.title(self.gui_config['window_title'])
        self.root.geometry(self.gui_config['window_geometry'])
        self.root.lift()
        self.root.focus_force()

        print("=" * 60)
        print(f"Starting CONFIG 1/{self.total_num_configs}...")
        print("=" * 60)
        print()
        
        # Pre-first-trial countdown pause (cushions the dialog/demo -> first
        # trial transition). No-op if duration <= 0.
        self._show_pause(
            duration=self.pre_first_trial_pause,
            upcoming_config_num=1,
            is_pre_first=True,
        )
        
        try:
            while not self.end_paradigm:
                # Determine if catch trial
                self.determine_catch_trial()
            
                # Prepare trial
                self.prepare_trial()

                # Refresh the operator's stimulus panel now that self.tp holds
                # the UPCOMING trial, so the timing diagram shows what the
                # participant is about to hear rather than the previous trial.
                # The data panels (track / thresholds / psychometric) are
                # refreshed after the response instead - see update_display()
                # below.
                if self.operator_display is not None:
                    self.operator_display.update_stimulus()

                # Execute trial until valid response
                while self.user_input is None:
                    # Play the trial (GUI already shows "Playing stimulus..."
                    # from the ITI update_gui_state call above, except on the
                    # very first trial — ensure it's shown here too)
                    self.update_gui_state(trial_playing=True)
                    self.execute_trial()
                    core.wait(self.post_stim_pause)  # anti-click pause before response GUI
                
                    # Enable GUI and get response
                    self.user_input = self.get_response(trial_playing=False)
            
                # Process response
                self.check_answer()
                self.log_data()
                self.update_counters()
                self.check_trial_conds()
                self.update_trial_params()
                self.check_paradigm_end_conds()
            
                # Update the operator's text + data panels after each trial.
                # The stimulus panel is NOT redrawn here - it was already
                # updated after prepare_trial() above, and self.tp still holds
                # the trial that just played.
                if self.operator_display is not None:
                    self.operator_display.update_display()

                # Per-trial resource sample (debug; no-op unless enabled)
                if self.resource_logger is not None:
                    self.resource_logger.log(self.config_num, self.trial_num)
        
        except Exception:
            # Crash mid-run: persist partial data + a timestamped traceback
            # so the failure is diagnosable. A traceback file present => a
            # software crash (deterministic line). Temp CSV present but NO
            # crash file => the process was killed externally (OS OOM or
            # thermal), because SIGKILL cannot run this handler.
            try:
                self._write_temp_data()
            except Exception as _tmp_exc:
                print(f"[crash handler] temp save failed: {_tmp_exc}")
            try:
                _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                _crash_path = self._debug_log_dir() / (
                    f"{self.participant_id}_{self.paradigm_code}_crash_{_ts}.txt"
                )
                with open(_crash_path, "w") as _cf:
                    _cf.write(traceback.format_exc())
                print(f"[crash handler] traceback written to {_crash_path}")
            except Exception as _crash_exc:
                print(f"[crash handler] crash-file write failed: {_crash_exc}")
            raise
        finally:
            if self.resource_logger is not None:
                self.resource_logger.close()
        # Print performance summary
        if self._aborted_by_operator:
            print("\n" + "=" * 60)
            print("PARADIGM ABORTED BY OPERATOR — data not saved.")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("PARADIGM COMPLETE")
            print("-" * 60)
            print("\nResults:")
            print(self.data)
            self.write_data_to_disk()
            self._delete_temp_data()
