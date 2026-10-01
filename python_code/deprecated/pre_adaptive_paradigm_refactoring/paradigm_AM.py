import numpy as np
from psychopy import core

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from trial_player import TrialPlayer

import tkinter as tk
from tkinter import ttk # maybe switch to this (to use more natural OS theme)?

import pandas as pd
from datetime import datetime
import time
from pathlib import Path

from paradigm import Paradigm

class ParadigmAM(Paradigm):
    def __init__(self, play_now = False, verbose=None):
        self.tp = TrialPlayer(verbose=False) # instantiate TrialPlayer object
        ### DEFINE ALL ATTRIBUTES # TODO: get (most of?) these falues from paradigm_defaults.py config file
        self.total_num_configs = 3
        self.total_num_correct = 0
        self.total_num_wrong = 0
        self.current_streak = 0
        self.last_current_streak = 0
        self.target_streak_correct = 2
        self.target_streak_wrong = 1
        self.reversal = False
        self.max_reversals = 2
        self.total_num_reversals = 0
        self.config_num = 1
        self.trial_num = 0
        self.direction = 0 # -1 = decreasing, 1 = increasing (use for reversal checks?)
        self.correct_answer = None
        self.trial_repeats = -1
        self.trial_active = False # is this necessary?
        self.dec_amp = False
        self.inc_amp = False
        self.dec_mod_ind = False
        self.inc_mod_ind = False
        self.next_freq = False
        self.end_config = False
        self.end_paradigm = False
        self.user_input = None
        self.num_beeps = 2
        self.trial_dur = 2.0
        self.trial_ISI = 0.2
        self.trial_ITI = 2.0
        self.trial_amp = 1.0
        self.fc = 1000
        self.trial_fm = 8.0
        self.trial_mod_ind = 8.0
        self.dB_down = -10
        self.dB_up = 5
        # move this outside of the class later
        self.data = pd.DataFrame(columns=["unix_time","config_num","trial_num", "fc", "fm", "mod_ind", "amplitude", "correct_answer", "trial_repeats"]) # add more colums later
        
        
    ### RANDOMIZE RELEVANT TRIAL PARAMETER(S) AND USE RESULT TO DEFINE THE TRIAL
    def prepare_trial(self):
        # increment trial_num
        self.trial_num += 1

        self.trial_order = np.random.choice([1,2]) # = position of FM stimulus
        stim_order = ["sin", "am"]
        stim_order = np.roll(stim_order, self.trial_order)

        # setup the trial
        self.tp.new_trial(wave_type=stim_order, del_times=self.trial_ISI, durations=self.trial_dur, fc=self.fc, fm=self.trial_fm, mod_ind=self.trial_mod_ind, amp=self.trial_amp, verbose=False) # , bg={"play_bg": False})


    ### PLAY TRIAL - run the most recently defined trial
    def execute_trial(self):
        self.trial_repeats += 1
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
            root.quit()  # Ends the mainloop

        def on_key(event):
            if event.char == '1':
                respond(1)
            elif event.char == '2':
                respond(2)
            elif event.char == 'r' or event.char == 'R':
                respond("repeat")

        root = tk.Tk()
        root.title("Response Window")
        root.geometry("500x150+100+100")

        label = tk.Label(root, text="Was the AM tone played first or second?", font=("Arial", 14))
        label.pack(pady=20)

        button_frame = tk.Frame(root)
        button_frame.pack()

        button1 = tk.Button(button_frame, text="1", width=10, command=lambda: respond(1))
        button1.grid(row=0, column=0, padx=10)

        button2 = tk.Button(button_frame, text="2", width=10, command=lambda: respond(2))
        button2.grid(row=0, column=1, padx=10)

        button3 = tk.Button(button_frame, text="repeat", width=10, command=lambda: respond("repeat"))
        button3.grid(row=0, column=2, padx=10)

        root.bind("<KeyRelease>", on_key) # use <KeyRelease> to avoid held keys (but adds some lag)
        # TODO: update to use KeyPress but filter out repeats?

        root.update_idletasks()   # Force immediate draw/update

        root.mainloop()
        root.destroy()

        return result['value']


    ### check the answer (right/wrong)
    def check_answer(self):
        # self.last_current_streak = self.current_streak # CAN PROBLY MOVE THIS to update counters(?)...
        self.correct_answer = (self.user_input == self.trial_order)


    ### update counters
    ## e.g. total_num_correct/wrong, current_streak, last_current_streak, etc.
    def update_counters(self): # NOTE: THIS CAN PROBLY MOVE BACK TO THE PARENT CLASS
        self.last_current_streak = self.current_streak # CAN PROBLY MOVE THIS to update counters(?)...
        # self.trial_num += 1 # TODO: add this in somewhere else
        if self.correct_answer:
            self.total_num_correct += 1 # maybe this isn't so necessary to keep track of?
            self.current_streak = max(self.current_streak + 1, 1)
        else:
            self.total_num_wrong += 1 # maybe this isn't so necessary to keep track of?
            self.current_streak = min(self.current_streak - 1, -1)
        
        # if self.current_streak == 0: # this doesn't work
        rev_test = abs(self.last_current_streak - self.current_streak)
        # print(f'rev test = {rev_test}')
        if rev_test > 1:
            self.reversal = True
            self.total_num_reversals += 1

        self.direction = np.sign(self.current_streak) # maybe this isn't so necessary to keep track of?

        # TODO: add verbose mode to control how much is printed
        print("~~~~~~~~~~~~~~~~~~")
        print(f"FM PLAYED: {self.trial_order}")
        print(f"PARTICIPANT HEARD: {self.user_input}")
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
        # start new trial with lower amplitude
        if self.current_streak > 0 and (self.current_streak % self.target_streak_correct == 0): 
            self.dec_mod_ind = True
            # self.trial_amp *= TrialPlayer.db2amp(-1*abs(self.dB_down))
            print("~~~> REDUCE MOD IND <~~~")
        # double amplitude (but not more than 1) and start new trial
        elif self.current_streak < 0 and (abs(self.current_streak) % abs(self.target_streak_wrong) == 0):
            self.inc_mod_ind = True
            # self.trial_amp *= TrialPlayer.db2amp(abs(self.dB_up))
            # self.trial_amp = min(self.trial_amp, 1.0) # make sure it can't get louder than 1
            print("~~~> INCREASE MOD IND <~~~")

        # end the current configuration:
        if self.total_num_reversals >= self.max_reversals: # NOTE: these variables will be updated before logging occurs!
            self.end_config = True
            self.next_freq = True
            self.trial_num = 0
            self.total_num_correct = 0 # maybe move this to an separate reset function?
            self.total_num_wrong = 0
            self.current_streak = 0
            self.last_current_streak = 0
            self.total_num_reversals = 0
            self.trial_mod_ind = 8.0
    
    ### check if the entire paradign is finished 
    ## (must happen at the end of the loop)
    def check_paradigm_end_conds(self):
        if self.config_num > self.total_num_configs: # this shouldn't be hardcoded...!?
            self.end_paradigm = True

    ### save data TODO: move function outside of class
    def log_data(self):
        # columns=["time", "config_num","trial_num", "freq", "amplitude", "correct_answer", "trial_repeats"]
        self.data.loc[len(self.data)] = [time.time(),
                                         self.config_num, 
                                         self.trial_num, 
                                         self.fc, 
                                         self.trial_fm,
                                         self.trial_mod_ind,
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

        # reset input and counter
        self.user_input = None
        self.trial_repeats = -1

        # update amplitude
        if self.dec_mod_ind:
            self.trial_mod_ind *= 0.5
            self.dec_mod_ind = False # reset flag
        elif self.inc_mod_ind:
            self.trial_mod_ind *= 2.0
            # self.trial_amp = min(self.trial_amp, 1.0) # make sure it can't get louder than 1
            self.inc_mod_ind = False # reset flag

        # update config (--> frequency)
        if self.end_config:
            self.config_num += 1
            self.total_num_reversals = 0
            self.end_config = False # reset flag

        # update frequency
        if self.next_freq: # TODO: un-hardcode the frequency range
            # # self.fc = np.random.uniform(100,2000) # should this be uniform or logarithmic??
            # # self.fc = np.random.loguniform(100,2000) # logarithmic distribution - DOESN'T WORK!
            # rng = np.random.default_rng()  # new Generator
            # f_min, f_max = 100, 2000 # TODO: move this somewhere else(?)
            # self.fc = np.exp(np.random.uniform(np.log(f_min), np.log(f_max))) # or w/ a rng generator...
            self.trial_fm *= 0.5 # go fm = 8 Hz --> 4 Hz --> 2 Hz TODO: make this smarter (randomize order?)
            print(f'UPDATED FREQUENCY: {self.trial_fm}')
            self.next_freq = False # reset flag

        # add a pause before the next trial
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