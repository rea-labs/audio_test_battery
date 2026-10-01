# UPDATED ADAPTIVE VERSION BASED OFF OF: tEAS_absThreshold from USZmultiThreshold (MATLAB)
# NOTE: the general procedure is different than previously implemented version (based on Prague), i.e.
# - each trial can either be a normal trial or a catch trial (no stim presented)
#   - the first trial must ALWAYS be a "real" trial
#   - the second trial should ALWAYS be a catch trial 
#   - subsequent trial behavior is determined (adaptively) by catch_trial_rate 
#       - catch_trial_rate = [starting_rate, min_rate, step_size, max_rate]
#       - every time the participant is "caught", the rate increases by step_size (until max_rate)
#       - every time the participant answers "ok" (true positive or true negative), the rate decreases by step_size (until min_rate)
# - after the first reversal (self.total_num_reversals > 0), decrement TRIALS_REMAINING for every NON-CATCH trial
# - end_condition (move on to the next frequency) when TRIALS_REMAINING < 1
# 
# NOTE: don't delete all of the data/stats related to the old method (e.g. current_streak, etc.), 
# as they could be useful if this toolbox is ever expanded to include more paradigms in the future...


import numpy as np
from psychopy import core

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from trial_player import TrialPlayer

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk # maybe switch to this (to use more natural OS theme)?

import pandas as pd
from datetime import datetime
import time
from pathlib import Path

from paradigm import Paradigm

import itertools
from utils.varspec import VarSpec

class ParadigmPTA_adaptive(Paradigm):
    def __init__(self, params: dict[str, VarSpec], play_now = False, verbose=None): # TODO: add a VarSpec params argument to the input list...
        self.params = params
        self.tp = TrialPlayer(verbose=False) # instantiate TrialPlayer object
        ### DEFINE ALL ATTRIBUTES # TODO: get (most of?) these falues from paradigm_defaults.py config file
        # self.total_num_configs = 3 # TODO - DEPRECATE(?) --> computed below
        self.total_num_correct = 0 # DEPRECATE(?)
        self.total_num_wrong = 0 # DEPRECATE(?)
        self.current_streak = 0
        self.last_current_streak = 0
        self.target_streak_correct = 1 # only need one correct answer to increase difficulty
        self.target_streak_wrong = 1 # only need one wrong answer to decrease difficulty
        self.reversal = False
        self.catch_trial_rate = [0.2, 0.1, 0.1, 0.5] # [starting_rate, min_rate, step_size, max_rate]
        self.__current_catch_trial_rate = self.catch_trial_rate[0]
        self.is_catch_trial = False
        self.max_reversals = 2 # DEPRECATE(?)
        self.total_num_reversals = 0
        self.config_num = 1 # use 1 based indexing for the sake of the log(?)
        self.trial_num = 0 # use 1 based indexing for the sake of the log (++ happens at start of trial)
        self.trials_after_reversal = 3 # 10
        self.trials_remaining = None
        self.direction = 0 # -1 = decreasing, 1 = increasing (use for reversal checks?)
        self.correct_answer = None
        self.trial_repeats = -1
        self.trial_active = False # is this necessary? DEPRECATE(?)
        self.dec_amp = False # DEPRECATE(?) --> change to self.inc_difficulty
        self.inc_amp = False # DEPRECATE(?) --> change to self.dec_difficulty
        self.inc_difficulty = False
        self.dec_difficulty = False
        self.next_freq = False # DEPRECATE(?) --> change to self.next_config? maybe just use self.end_config?!
        self.end_config = False # merge with self.next_freq
        self.end_paradigm = False
        self.user_input = None
        self.test_cond = None # = num_beeps (in this case) --> TODO: add a description variable for this...
        self.trial_dur = 0.5
        self.trial_ISI = 0.25 #0.25 # 0.01
        self.trial_ITI = 1.0
        self.fade_time = 0.05 #0.0001 #0.05
        self.trial_amp = 1.0
        self.fc = 1000
        self.dB_down = -10 # DEPRECATE(?) --> delta_difficulty = [before_rev, after_rev]
        self.dB_up = 5 # DEPRECATE(?) -->
        self.sample_accurate = False
        # move this outside of the class later
        self.data = pd.DataFrame(columns=["unix_time","config_num","trial_num", "freq", "amplitude", "correct_answer", "trial_repeats"]) # add more colums later
        self.root = None # for tkinter...
        self._this_is_a_test = 42
        self.__and_so_is_this = -1 # but this one is private(ish)

        # # # ~~~~~~> MAYBE MOVE THIS INTO A FUNCTION???
        # Make attributes using their key names --> self.inner, self.outer_1, ... NOTE: this may break things!
        for key, spec in params.items(): # .items() returns the name and associated data as a "dict_items" object
            # key is the variable name (e.g. var_1, var_2, ...)
            # spec is the associated VarSpec object 
            # e.g. VarSpec(name='frequency', data=[100, 200])
            setattr(self, key, spec)

        # # Make attributes like self.frequency, self.amplitude, ... NOTE: this may break things!
        # for spec in params.values(): # .values() only returns the data as a "dict_values" object
        #     setattr(self, spec.name, spec.data)

        # Loop role extraction
        self.inner_var = params["inner"] # gets the dict_value that has a loop_role of "inner"
        self.outer_vars = [ # gets the dict_values that has a loop_role of "outer_*"
            params[k] for k in params 
            if k.startswith("outer_")
        ]

        self.unwrapped_params = []
        names = [v.name for v in self.outer_vars]
        data = [v.data for v in self.outer_vars]
        for combo in itertools.product(*data):
            self.unwrapped_params.append(dict(zip(names, combo)))
        
        self.total_num_configs = len(self.unwrapped_params)
        self.set_current_config(0) # select the first configuration

    ### SOME UTITLTY FUNCTIONS
    def set_current_config(self, ind):
        for key, val in self.unwrapped_params[ind].items():
            setattr(self, key, val)

    def make_new_data(self, data):
        setattr(self,"new_data",data)

    def print_all(self):
        for k,v in self.__dict__.items():
            print(f"{str(k)} = {str(v)}") 

    def show_false_positive_warning(self):
        """
        Show a modal warning dialog that blocks until the user clicks OK.
        """
        messagebox.showwarning(
            title="Warning",
            message="FALSE POSITIVE!\nPLEASE DON'T GUESS,\nONLY PRESS 1 IF YOU HEARD A TONE",
            parent=self.root
        )
    
    # def adjust_catch_trial_rate(self, dir):
    #     pass

    ### RANDOMIZE RELEVANT TRIAL PARAMETER(S) AND USE RESULT TO DEFINE THE TRIAL
    def prepare_trial(self):
        # increment trial_num
        self.trial_num += 1

        # self.test_cond = np.random.choice([1,2]) # pick 1 or 2 beeps
        # dt = [] if self.test_cond < 2 else [self.trial_ISI] # create the corresponding delay array
        dt = [] # create the corresponding delay array (always 1 beep to make timing easier, but adjust amplitude...)

        # determine catch trial
        rng = np.random.default_rng() # random number generator for catch trials
        print(f"TRIAL NUM: {self.trial_num}")
        # print(f"CATCH TRIAL RATE: {self.catch_trial_rate}")
        if self.trial_num == 1: # first trial can NEVER be a catch trial
            self.is_catch_trial = False
        elif self.trial_num == 2: # second trial should ALWAYS be a catch trial
            self.is_catch_trial = True
        else: # the rest are determined randomly (self.catch_trial_rate = [starting_rate, min_rate, step_size, max_rate])
            self.is_catch_trial = rng.choice([False, True], p=[1 - self.__current_catch_trial_rate, self.__current_catch_trial_rate])
            
        if self.is_catch_trial:
            amp = 0.0
            self.test_cond = 0
            print("catch trial: True")
        else:
            amp = self.trial_amp
            self.test_cond = 1
            print("catch trial: False")

        # setup the trial - TODO: maybe allow this to be passed in?  or sort out a way to manage defaults?
        # TODO: SEE trial_player.py 
        self.tp.new_trial(wave_type="sin", del_times=dt, durations=self.trial_dur, fc=self.fc, amp=amp, fade_time=self.fade_time, sample_accurate=self.sample_accurate, verbose=False) # , bg={"play_bg": False})


    ### PLAY TRIAL - run the most recently defined trial
    def execute_trial(self):
        self.trial_repeats += 1 # repeat returns None, so the main while control loop causes this to execute again
        self.tp.play_trial()


    ### GET USER INPUT
    def get_response(self): ### TODO: move this to its own (configurable) class and call it from here
        # NOTE: this fucntion (class) should be passed in from outside
        result = {'value': None}  # Mutable container to store the response

        def respond(value):
            if value == "repeat":
                result['value'] = None
            else:
                result['value'] = value
            self.root.quit()  # Ends the mainloop TODO!!! FIX THIS!

        def on_key(event):
            if event.char == '0':
                respond(0)
            elif event.char == '1':
                respond(1)
            elif event.char == 'r' or event.char == 'R':
                respond("repeat")

        self.root = tk.Tk() # TODO!!! FIX THIS - this should not happen repeatedly on every call to get response!
        self.root.title("Response Window")
        self.root.geometry("500x150+100+100")

        label = tk.Label(self.root, text="Did you hear 0 or 1 tone?", font=("Arial", 14))
        label.pack(pady=20)

        button_frame = tk.Frame(self.root)
        button_frame.pack()

        button1 = tk.Button(button_frame, text="0", width=10, command=lambda: respond(0))
        button1.grid(row=0, column=0, padx=10)

        button2 = tk.Button(button_frame, text="1", width=10, command=lambda: respond(1))
        button2.grid(row=0, column=1, padx=10)

        button3 = tk.Button(button_frame, text="repeat", width=10, command=lambda: respond("repeat"))
        button3.grid(row=0, column=2, padx=10)

        self.root.bind("<KeyRelease>", on_key) # use <KeyRelease> to avoid held keys (but adds some lag)
        # TODO: update to use KeyPress but filter out repeats?

        self.root.update_idletasks()   # Force immediate draw/update

        self.root.mainloop() # TODO!!! FIX THIS
        self.root.withdraw()
        # self.root.destroy()

        return result['value']


    ### check the answer (right/wrong)
    def check_answer(self):
        # NOTE: updated this to keep track of: TP, FN, FP, and TN
        # --> then also need to update the correct_answer logic accordingly
        # self.correct_answer = (self.user_input == self.test_cond) # OLD VERSION
        if self.test_cond == 1: # stimulus played (normal trial)
            if self.user_input == 1: # stimulus heard
                self.correct_answer = "TP" # TRUE-POSITIVE - correct (make next trial harder)
            elif self.user_input == 0: # stimulus not heard
                self.correct_answer = "FN" # FALSE-NEGATIVE - incorrect (make next trial easier)

        elif self.test_cond == 0: # stimulus not played (catch trial)
            if self.user_input == 1: # stimulus heard
                self.correct_answer = "FP" # FALSE-POSITIVE - caught! (warn participant)
            elif self.user_input == 0: # stimulus not heard
                self.correct_answer = "TN" # TRUE-NEGATIVE - not caught (do nothing)
        
        print(f"ANSWER CLASSIFICATION: {self.correct_answer}")


    ### update counters
    ## e.g. total_num_correct/wrong, current_streak, last_current_streak, etc.
    def update_counters(self):
        self.last_current_streak = self.current_streak
        # self.trial_num += 1 # TODO: add this in somewhere else
        # TODO - update the conditions here (also include pass/failed catch trials)
        # if self.correct_answer:
        #     self.total_num_correct += 1 # maybe this isn't so necessary to keep track of?
        #     self.current_streak = max(self.current_streak + 1, 1)
        # else:
        #     self.total_num_wrong += 1 # maybe this isn't so necessary to keep track of?
        #     self.current_streak = min(self.current_streak - 1, -1)
        
        # TODO: maybe these should just directly set flags???
        if self.correct_answer == 'TP':
            self.current_streak = max(self.current_streak + 1, 1)
        elif self.correct_answer == 'FN':
            self.current_streak = min(self.current_streak - 1, -1)
        elif self.correct_answer == 'FP':
            self.current_streak = self.current_streak
            # self.current_streak = min(self.current_streak - 1, -1) # (maybe) do nothing?
            print("FALSE POSITIVE! ~~~> PLEASE DON'T GUESS, ONLY PRESS 1 IF YOU HEARD A TONE")
            self.show_false_positive_warning()
        elif self.correct_answer == 'TN':
            self.current_streak = self.current_streak
            # self.current_streak = min(self.current_streak - 1, -1) # (maybe) do nothing?
            print("PASSED THE CATCH TEST...")
        else:
            self.current_streak = None
            print("BAD 'CORRECT_ANSWER' CODE")
        
        # if self.current_streak == 0: # this doesn't work
        rev_test = abs(self.last_current_streak - self.current_streak) # TODO: double check this logic... --> SEEMS OK!
        # print(f'rev test = {rev_test}') 
        if rev_test > 1:
            self.reversal = True
            self.total_num_reversals += 1

        self.direction = np.sign(self.current_streak) # maybe this isn't so necessary to keep track of?

        # after first reversal, decrement self.trials_remaining
        if self.total_num_reversals == 0:
            self.trials_remaining = self.trials_after_reversal
            print("~~~~~~~~> no reversals yet...")
        elif self.total_num_reversals > 0:
            if not self.is_catch_trial:
                self.trials_remaining -= 1
            print(f"~~~~~~~~> trials remaining = {self.trials_remaining}")

        # TODO: add verbose mode to control how much is printed
        print("~~~~~~~~~~~~~~~~~~")
        print(f"NUMBER OF BEEPS PLAYED: {self.test_cond}")
        print(f"NUMBER OF BEEPS PARTICIPANT HEARD: {self.user_input}")
        print("~~~~~~~~~~~~~~~~~~")
        # print(f"NUMBER OF CORRECT ANSWERS: {self.total_num_correct}")
        # print(f"NUMBER OF WRONG ANSWERS: {self.total_num_wrong}")
        print(f"CURRENT STREAK: {self.current_streak}")
        # print(f"LAST CURRENT STREAK: {self.last_current_streak}")
        print(f"REVERSAL: {self.reversal}")
        print(f"TOTAL NUM REVERSAL: {self.total_num_reversals}")
        print("~~~~~~~~~~~~~~~~~~")


    ### check CS (or other relevant data) against condition(s) and set relevant flags
    ## e.g. CS > 1, total_num_reversals >1
    def check_trial_conds(self): # this only sets flags (there's a separate update_trial_params() fcn)
        # make next trial harder...
        if not self.is_catch_trial: # only change difficulty if NOT a catch trial
            if self.current_streak > 0 and (self.current_streak % self.target_streak_correct == 0): 
                # self.dec_amp = True # TODO: CHANGE TO INCREASE DIFICULTY
                self.inc_difficulty = True # UPDATED
                print("~~~> INCREASE DIFICULTY <~~~")
            # make next trial easier...
            elif self.current_streak < 0 and (abs(self.current_streak) % abs(self.target_streak_wrong) == 0):
                # self.inc_amp = True # TODO: CHANGE TO DECREASE DIFICULTY
                self.dec_difficulty = True # UPDATED
                print("~~~> DECREASE DIFICULTY <~~~")

        # end the current configuration:
        # TODO - UPDATE LOGIC!!! (maybe make this allow this condition to be set via an external function...?)
        # if self.total_num_reversals >= self.max_reversals: # NOTE: these variables will be updated before logging occurs!
        if self.trials_remaining < 1:
            self.end_config = True
            self.trials_remaining = self.trials_after_reversal
            # self.next_freq = True # TODO - UPDATE VARIABLE? (redundant... same as end_config?)
            self.trial_num = 0
            self.total_num_correct = 0 # DEPRECATE(?) - maybe move this to an separate reset function? 
            self.total_num_wrong = 0 # DEPRECATE(?)
            self.current_streak = 0
            self.last_current_streak = 0
            self.total_num_reversals = 0
            self.trial_amp = 1 # TODO: UPDATE THIS LOGIC?! --> maybe add some sort of a initial_state?
            self.__current_catch_trial_rate = self.catch_trial_rate[0]
    

# ~~~~~~~~~~~~~ RESUME HERE! ~~~~~~~~~~~~~ #
# TODO - update to include: 
#   - (1x) within_run_var
#   - (2x) between_run_vars
#       --> num_configs = size(brv1) * size(brv2)

    ### check if the entire paradigm is finished 
    ## (must happen at the end of the loop)
    def check_paradigm_end_conds(self): # TODO - make this smarter...
        if self.config_num > self.total_num_configs: # OK - total_num_configs is now computed from "outer_*" params
        # if self.trials_remaining < 1: # 
            self.end_paradigm = True
            self.root.destroy()

    ### save data TODO: move function outside of class
    def log_data(self):
        # columns=["time", "config_num","trial_num", "freq", "amplitude", "correct_answer", "trial_repeats"]
        self.data.loc[len(self.data)] = [time.time(),
                                         self.config_num, 
                                         self.trial_num, 
                                         self.fc, 
                                         TrialPlayer.amp2db(self.trial_amp), 
                                         self.correct_answer,
                                         self.trial_repeats]
        
    def write_data_to_disk(self):
        # save data to csv
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Define the subdirectory
        # Ensure the script's directory is the base path
        base_dir = Path(__file__).parent  # Gets the directory where this script is located
        output_dir = Path("test_data")
        # output_dir = Path("test_data")
        output_dir.mkdir(parents=True, exist_ok=True)  # Create directory if needed

        # Create the full file path
        filename = base_dir / output_dir / f"results_{timestamp}.csv"

        # # Create filename with timestamp
        # filename = f"results_{timestamp}.csv"

        # save file
        self.data.to_csv(filename, index=False)

    ### update trial parameters based on previously set flags    
    def update_trial_params(self):
        # # increment trial_num
        # self.trial_num += 1

        # reset input and counter [ALWAYS]
        self.user_input = None
        self.trial_repeats = -1

        # update amplitude [PARADIGM SPECIFIC] --> MAYBE this should be a function passed in from outside?
        # # # # # # TODO: modify this to include before/after first reversal logic # # # # # #
        # # # # # # ALSO need to reset the current level to halfway b/w the previous two... # # # # # #
        if self.inc_difficulty: # make it harder
            self.trial_amp *= TrialPlayer.db2amp(-1*abs(self.dB_down))
            self.inc_difficulty = False # reset flag
        elif self.dec_difficulty: # make it easier
            self.trial_amp *= TrialPlayer.db2amp(abs(self.dB_up))
            self.trial_amp = min(self.trial_amp, 1.0) # make sure it can't get louder than 1
            self.dec_difficulty = False # reset flag

        # update config (--> frequency) [ALWAYS]
        if self.end_config:
            if self.config_num < self.total_num_configs:
                self.set_current_config(self.config_num) # NOTE this is "out of order" b/c using 1 based indexing (for the sake of the log)
            self.config_num += 1
            self.total_num_reversals = 0
            self.end_config = False # reset flag
        
        # update catch rate # catch_Trial_rate = [starting_rate, min_rate, step_size, max_rate]
        if self.correct_answer == 'FP':
            self.__current_catch_trial_rate += self.catch_trial_rate[2]
        elif self.correct_answer == 'TN':
            self.__current_catch_trial_rate -= self.catch_trial_rate[2]
        self.__current_catch_trial_rate = np.clip(self.__current_catch_trial_rate, self.catch_trial_rate[1], self.catch_trial_rate[3])
        print(f"~.~.~.~.~.~.> catch trial rate = {self.__current_catch_trial_rate:.2f}")

        # # # # # # DEPRECATED! # # # # # #
        # update frequency [PARADIGM SPECIFIC] --> use recursive logic from modular_paradigm_test.py
        if self.next_freq: # TODO: needs to (randomly) pick from a list (WRV)
            # self.fc = np.random.uniform(100,2000) # should this be uniform or logarithmic??
            # self.fc = np.random.loguniform(100,2000) # logarithmic distribution - DOESN'T WORK!
            rng = np.random.default_rng()  # new Generator
            f_min, f_max = 100, 2000 # TODO: move this somewhere else(?)
            self.fc = np.exp(np.random.uniform(np.log(f_min), np.log(f_max))) # or w/ a rng generator...
            print(f'UPDATED FREQUENCY: {self.fc}')
            self.next_freq = False # reset flag

        # add a pause before the next trial [ALWAYS]
        core.wait(self.trial_ITI) # too long TODO: sort this out (?)



    ### MAIN LOOP (called below for testing) TODO: consider renaming (to run_paradigm?)
    def main(self):
        while not self.end_paradigm:
            self.prepare_trial()
            while self.user_input == None:
                self.execute_trial()
                core.wait(0.5) # to avoid a click at the end
                self.user_input = self.get_response()
            self.check_answer()
            self.log_data() # TODO: this should come from outside...
            self.update_counters()
            self.check_trial_conds()
            self.update_trial_params()
            self.check_paradigm_end_conds()
            # core.wait(0.1) # TODO: check timing...
        
        # print out results
        print(self.data)
        self.write_data_to_disk()


# ### FOR TESTING (when the file is run directly, TODO: remove this later?)
# if __name__ == "__main__": # this allows the file to be run directly
#     pta = Paradigm(verbose=False)
#     pta.main()




### getting timestamps (to add to log files):
# from datetime import datetime
# import time
# print(f"timestamp: {datetime.now().isoformat()}"),  # Absolute calendar time
# print(f"response_time: {time.time()}")        # Acceptable absolute time
## see also:
# ptb.GetSecs() # relative time
# time.perf_counter() # (platform dependent) relative time
## conversion info:
# Task	Function	Output Example
# Unix → local datetime	        datetime.fromtimestamp(ts)	    2024-05-22 14:54:10.123456
# Unix → UTC datetime	        datetime.utcfromtimestamp(ts)	2024-05-22 18:54:10.123456
# Format datetime → string	    .strftime(format_string)	    '2024-05-22 14:54:10'