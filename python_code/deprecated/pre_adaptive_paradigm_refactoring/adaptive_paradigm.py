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
from psychopy import core
import tkinter as tk
from tkinter import messagebox
import pandas as pd
from datetime import datetime
import time
from pathlib import Path
import itertools

from trial_player import TrialPlayer
from utils.varspec import VarSpec


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
    
    def __init__(self, params: dict[str, VarSpec], verbose=False):
        """
        Initialize adaptive paradigm.
        
        Args:
            params: Dictionary with keys "inner" and "outer_1", "outer_2", etc.
                   - "inner": VarSpec with adaptive parameter config (dict)
                   - "outer_*": VarSpec with lists of values to loop through
            verbose: Print debug information
        """
        self.params = params
        self.verbose = verbose
        self.tp = TrialPlayer(verbose=False)
        
        # === CORE ADAPTIVE STATE ===
        self.current_streak = 0           # Current correct/incorrect streak
        self.last_current_streak = 0      # Previous streak (for reversal detection)
        self.total_num_reversals = 0      # Total reversals in current config
        self.trials_remaining = None      # Trials to complete after first reversal
        self.direction = 0                # -1 = decreasing difficulty, 1 = increasing
        
        # === CATCH TRIAL STATE ===
        self.catch_trial_rate = [0.2, 0.1, 0.1, 0.5]  # [start, min, step, max]
        self._current_catch_trial_rate = self.catch_trial_rate[0]
        self.is_catch_trial = False
        
        # === TRIAL STATE ===
        self.config_num = 1              # Current config (1-based for logging)
        self.trial_num = 0               # Current trial within config (1-based)
        self.user_input = None           # User response (0, 1, or "repeat")
        self.correct_answer = None       # Classification: TP, FN, FP, TN
        self.trial_repeats = -1          # Number of times trial repeated
        self.test_cond = None            # Was stimulus present? (0=catch, 1=normal)
        
        # === FLAGS ===
        self.inc_difficulty = False      # Flag: make next trial harder
        self.dec_difficulty = False      # Flag: make next trial easier  
        self.end_config = False          # Flag: move to next config
        self.end_paradigm = False        # Flag: all configs complete
        
        # === CONFIGURATION ===
        self.target_streak_correct = 1   # Streak needed to increase difficulty
        self.target_streak_wrong = 1     # Streak needed to decrease difficulty
        self.trials_after_reversal = 10  # Trials to run after first reversal
        self.trial_ITI = 1.0             # Inter-trial interval (sec)
        
        # === GUI ===
        self.root = None                 # Tkinter root (created once in main())
        
        # === DATA LOGGING ===
        self.data = pd.DataFrame(columns=[
            "unix_time", "config_num", "trial_num", "correct_answer", 
            "trial_repeats", "is_catch_trial"
        ])
        
        # === PARSE PARAMS AND SETUP CONFIGS ===
        self._setup_variable_looping()
        
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
        
        # Create all combinations of outer variables
        if len(self.outer_vars) == 0:
            # No outer variables - single config
            self.unwrapped_params = [{}]
        else:
            names = [v.name for v in self.outer_vars]
            data = [v.data for v in self.outer_vars]
            self.unwrapped_params = [
                dict(zip(names, combo)) 
                for combo in itertools.product(*data)
            ]
        
        self.total_num_configs = len(self.unwrapped_params)
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
        2. Determine if catch trial (using self.is_catch_trial)
        3. Set self.test_cond (0 for catch, 1 for normal)
        4. Configure trial parameters based on current adaptive parameter
        5. Call self.tp.new_trial(...) with appropriate parameters
        
        Example for PTA:
            self.trial_num += 1
            if self.is_catch_trial:
                amp = 0.0
                self.test_cond = 0
            else:
                amp = self.trial_amp
                self.test_cond = 1
            self.tp.new_trial(wave_type="sin", fc=self.fc, amp=amp, ...)
        """
        raise NotImplementedError("Subclass must implement prepare_trial()")
    
    def adapt_difficulty(self, direction):
        """
        Adjust the adaptive parameter based on participant performance.
        
        Args:
            direction: "increase" or "decrease"
        
        Example for PTA (amplitude):
            if direction == "increase":
                self.trial_amp *= TrialPlayer.db2amp(-10)  # quieter = harder
            elif direction == "decrease":
                self.trial_amp *= TrialPlayer.db2amp(5)    # louder = easier
                self.trial_amp = min(self.trial_amp, 1.0)
        
        Example for GAP (gap duration):
            if direction == "increase":
                self.gap_duration *= 0.5  # shorter gap = harder
            elif direction == "decrease":
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
    
    # ============================================================
    # CORE ADAPTIVE LOGIC - Should not need to override
    # ============================================================
    
    def set_current_config(self, ind):
        """Set current configuration from unwrapped_params list."""
        if ind < len(self.unwrapped_params):
            for key, val in self.unwrapped_params[ind].items():
                setattr(self, key, val)
    
    def determine_catch_trial(self):
        """
        Determine if this trial should be a catch trial.
        
        Rules:
        - Trial 1: Never catch
        - Trial 2: Always catch
        - Others: Probabilistic based on adaptive catch rate
        """
        rng = np.random.default_rng()
        
        if self.trial_num == 1:
            self.is_catch_trial = False
        elif self.trial_num == 2:
            self.is_catch_trial = True
        else:
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
    
    def get_response(self):
        """
        Get user response via GUI.
        
        Returns:
            0, 1, or None (if repeat requested)
        """
        result = {'value': None}
        
        def respond(value):
            if value == "repeat":
                result['value'] = None
            else:
                result['value'] = value
            self.root.quit()
        
        def on_key(event):
            if event.char == '0':
                respond(0)
            elif event.char == '1':
                respond(1)
            elif event.char == 'r' or event.char == 'R':
                respond("repeat")
        
        # Create window (note: we'll fix this to create once in main())
        if self.root is None:
            self.root = tk.Tk()
            self.root.title("Response Window")
            self.root.geometry("500x150+100+100")
        
        # Clear previous widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        label = tk.Label(
            self.root, 
            text="Did you hear the stimulus? (0=No, 1=Yes)", 
            font=("Arial", 14)
        )
        label.pack(pady=20)
        
        button_frame = tk.Frame(self.root)
        button_frame.pack()
        
        button0 = tk.Button(button_frame, text="0 (No)", width=10, command=lambda: respond(0))
        button0.grid(row=0, column=0, padx=10)
        
        button1 = tk.Button(button_frame, text="1 (Yes)", width=10, command=lambda: respond(1))
        button1.grid(row=0, column=1, padx=10)
        
        button_repeat = tk.Button(button_frame, text="Repeat", width=10, command=lambda: respond("repeat"))
        button_repeat.grid(row=0, column=2, padx=10)
        
        self.root.bind("<KeyRelease>", on_key)
        self.root.update_idletasks()
        self.root.mainloop()
        self.root.withdraw()
        
        return result['value']
    
    def check_answer(self):
        """
        Classify response as TP (true positive), FN (false negative), 
        FP (false positive), or TN (true negative).
        """
        if self.test_cond == 1:  # Normal trial (stimulus presented)
            if self.user_input == 1:
                self.correct_answer = "TP"  # Heard it - correct
            elif self.user_input == 0:
                self.correct_answer = "FN"  # Didn't hear it - incorrect
        elif self.test_cond == 0:  # Catch trial (no stimulus)
            if self.user_input == 1:
                self.correct_answer = "FP"  # False alarm - caught!
            elif self.user_input == 0:
                self.correct_answer = "TN"  # Correct rejection
        
        if self.verbose:
            print(f"Answer: {self.correct_answer}")
    
    def show_false_positive_warning(self):
        """Show modal warning when participant gives false positive."""
        messagebox.showwarning(
            title="Warning",
            message="FALSE POSITIVE!\nPLEASE DON'T GUESS,\nONLY PRESS 1 IF YOU HEARD THE STIMULUS",
            parent=self.root
        )
    
    def update_counters(self):
        """
        Update streaks, reversals, and trials_remaining based on response.
        """
        self.last_current_streak = self.current_streak
        
        # Update streak based on response type
        if self.correct_answer == 'TP':
            self.current_streak = max(self.current_streak + 1, 1)
        elif self.correct_answer == 'FN':
            self.current_streak = min(self.current_streak - 1, -1)
        elif self.correct_answer == 'FP':
            # Don't change streak on false positive
            if self.verbose:
                print("FALSE POSITIVE! ~~~> Please don't guess")
            self.show_false_positive_warning()
        elif self.correct_answer == 'TN':
            # Don't change streak on correct rejection
            if self.verbose:
                print("Passed catch trial")
        
        # Detect reversal
        rev_test = abs(self.last_current_streak - self.current_streak)
        if rev_test > 1:
            self.total_num_reversals += 1
            if self.verbose:
                print(f"!!! REVERSAL !!! (total: {self.total_num_reversals})")
        
        self.direction = np.sign(self.current_streak)
        
        # Initialize or decrement trials_remaining
        if self.total_num_reversals == 0:
            self.trials_remaining = self.trials_after_reversal
        elif self.total_num_reversals > 0:
            if not self.is_catch_trial:  # Only count non-catch trials
                self.trials_remaining -= 1
            if self.verbose:
                print(f"Trials remaining: {self.trials_remaining}")
        
        # Debug output
        if self.verbose:
            print("=" * 50)
            print(f"Test condition: {self.test_cond} (0=catch, 1=normal)")
            print(f"User input: {self.user_input}")
            print(f"Current streak: {self.current_streak}")
            print(f"Total reversals: {self.total_num_reversals}")
            print("=" * 50)
    
    def check_trial_conds(self):
        """
        Check if difficulty should be adjusted based on current streak.
        Sets inc_difficulty or dec_difficulty flags.
        """
        # Only adjust difficulty on non-catch trials
        if not self.is_catch_trial:
            # Increase difficulty after target correct streak
            if self.current_streak > 0 and (self.current_streak % self.target_streak_correct == 0):
                self.inc_difficulty = True
                if self.verbose:
                    print("~~~> INCREASE DIFFICULTY <~~~")
            
            # Decrease difficulty after target wrong streak
            elif self.current_streak < 0 and (abs(self.current_streak) % self.target_streak_wrong == 0):
                self.dec_difficulty = True
                if self.verbose:
                    print("~~~> DECREASE DIFFICULTY <~~~")
        
        # Check if current config is complete
        if self.trials_remaining is not None and self.trials_remaining < 1:
            self.end_config = True
    
    def update_trial_params(self):
        """
        Update trial parameters based on flags set by check_trial_conds().
        """
        # Reset for next trial
        self.user_input = None
        self.trial_repeats = -1
        
        # Adjust difficulty if flagged
        if self.inc_difficulty:
            self.adapt_difficulty("increase")
            self.inc_difficulty = False
        elif self.dec_difficulty:
            self.adapt_difficulty("decrease")
            self.dec_difficulty = False
        
        # Move to next config if flagged
        if self.end_config:
            if self.config_num < self.total_num_configs:
                self.set_current_config(self.config_num)  # Note: using 1-based indexing
            self.config_num += 1
            
            # Reset for new config
            self.trial_num = 0
            self.current_streak = 0
            self.last_current_streak = 0
            self.total_num_reversals = 0
            self.trials_remaining = self.trials_after_reversal
            self._current_catch_trial_rate = self.catch_trial_rate[0]
            self.reset_adaptive_param()
            
            self.end_config = False
        
        # Update catch trial rate
        if self.correct_answer == 'FP':
            self._current_catch_trial_rate += self.catch_trial_rate[2]  # Increase
        elif self.correct_answer in ['TP', 'TN']:
            self._current_catch_trial_rate -= self.catch_trial_rate[2]  # Decrease
        
        # Clip to min/max
        self._current_catch_trial_rate = np.clip(
            self._current_catch_trial_rate,
            self.catch_trial_rate[1],  # min
            self.catch_trial_rate[3]   # max
        )
        
        if self.verbose:
            print(f"Catch trial rate: {self._current_catch_trial_rate:.2f}")
        
        # Wait between trials
        core.wait(self.trial_ITI)
    
    def check_paradigm_end_conds(self):
        """Check if all configs are complete."""
        if self.config_num > self.total_num_configs:
            self.end_paradigm = True
            if self.root is not None:
                self.root.destroy()
                self.root = None
    
    def log_data(self):
        """
        Log current trial data to DataFrame.
        Combines base data with paradigm-specific data from get_log_data().
        """
        # Get paradigm-specific data
        paradigm_data = self.get_log_data()
        
        # Combine with base data
        row_data = {
            "unix_time": time.time(),
            "config_num": self.config_num,
            "trial_num": self.trial_num,
            "correct_answer": self.correct_answer,
            "trial_repeats": self.trial_repeats,
            "is_catch_trial": self.is_catch_trial,
            **paradigm_data
        }
        
        # Append to DataFrame
        self.data = pd.concat([
            self.data, 
            pd.DataFrame([row_data])
        ], ignore_index=True)
    
    def write_data_to_disk(self):
        """Save data to timestamped CSV file."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_dir = Path(__file__).parent
        output_dir = base_dir / "test_data"
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = output_dir / f"results_{timestamp}.csv"
        self.data.to_csv(filename, index=False)
        print(f"Data saved to: {filename}")
    
    # ============================================================
    # MAIN LOOP
    # ============================================================
    
    def main(self):
        """
        Main experimental loop.
        Runs all configs until paradigm complete.
        """
        # Create GUI window once at start
        self.root = tk.Tk()
        self.root.title("Audiology Test")
        self.root.geometry("500x150+100+100")
        
        while not self.end_paradigm:
            # Determine if catch trial
            self.determine_catch_trial()
            
            # Prepare trial
            self.prepare_trial()
            
            # Execute trial until valid response
            while self.user_input is None:
                self.execute_trial()
                core.wait(0.5)  # Brief pause to avoid clicks
                self.user_input = self.get_response()
            
            # Process response
            self.check_answer()
            self.log_data()
            self.update_counters()
            self.check_trial_conds()
            self.update_trial_params()
            self.check_paradigm_end_conds()
        
        # Print results and save
        print("\n" + "=" * 60)
        print("PARADIGM COMPLETE")
        print("=" * 60)
        print(self.data)
        self.write_data_to_disk()
