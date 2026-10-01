##################################################################
###### NOTE: DEPRECATED - see Paradigm class in paradigm.py ######
##################################################################

###### EXPERIMENTAL LOOP CONTROLLER ######
### --> maybe should be the paradigm (evtl. base?) class
### NOTE: for now start with the PTA case, then make it more general...]

import numpy as np
from psychopy import core
from trial_player import TrialPlayer

import tkinter as tk
from tkinter import ttk

class ExperimentalLoop:

    def __init__(self, play_now = False, verbose=None):
        self.tp = TrialPlayer() # instantiate TrialPlayer object
        ### DEFINE ALL ATTRIBUTES
        self.num_correct = 0
        self.num_wrong = 0
        self.current_streak = 0
        self.last_current_streak = 0
        self.reversals = 0
        self.trial_num = 1
        self.direction = 0 # -1 = decreasing, 1 = increasing (use for reversal checks?)
        self.correct_answer = None
        self.trial_active = False
        self.end_cond = False
        self.user_input = None
        self.num_beeps = None
        self.trial_dur = 0.5
        self.trial_ISI = 0.25
        self.trial_amp = 1
        self.fc = 1000
        self.dB_down = -10
        self.dB_up = 5
        # self.new_trial(del_times=del_times, durations=durations, fc=fc, amp=amp, bg=bg, fade_time=fade_time, fs=fs, play_now = play_now, verbose=verbose)

    ### RANDOMIZE RELEVANT TRIAL PARAMETER(S) AND USE RESULT TO DEFINE THE TRIAL
    def prepare_trial(self):
        self.num_beeps = np.random.choice([1,2]) # pick 1 or 2 beeps
        dt = [] if self.num_beeps < 2 else [self.trial_ISI] # create the corresponding delay array
        
        # setup the trial
        self.tp.new_trial(del_times=dt, durations=self.trial_dur, fc=self.fc, amp=self.trial_amp) # , bg={"play_bg": False})

    ### PLAY TRIAL - run the most recently defined trial
    def execute_trial(self):
        self.tp.play_trial()


    ### GET USER INPUT
    def get_response(self): ### TODO: move this to its own (configurable) class and call it from here
        result = {'value': None}  # Mutable container to store the response

        def respond(value):
            result['value'] = value
            root.quit()  # Ends the mainloop

        def on_key(event):
            if event.char == '1':
                respond(1)
            elif event.char == '2':
                respond(2)

        root = tk.Tk()
        root.title("Response Window")
        root.geometry("300x150+100+100")

        label = tk.Label(root, text="Did you hear 1 or 2 tones?", font=("Arial", 14))
        label.pack(pady=20)

        button_frame = tk.Frame(root)
        button_frame.pack()

        button1 = tk.Button(button_frame, text="1", width=10, command=lambda: respond(1))
        button1.grid(row=0, column=0, padx=10)

        button2 = tk.Button(button_frame, text="2", width=10, command=lambda: respond(2))
        button2.grid(row=0, column=1, padx=10)

        root.bind("<Key>", on_key)

        root.mainloop()
        root.destroy()

        return result['value']


    ### check the answer (right/wrong)
    def check_answer(self):
        self.last_current_streak = self.current_streak # probably don't need this...
        self.correct_answer = (self.user_input == self.num_beeps)

    ### update counters
    ## e.g. num_correct/wrong, current_streak, last_current_streak, etc.
    def update_counters(self):
        self.trial_num += 1
        if self.correct_answer:
            self.num_correct += 1
            self.num_wrong = 0
            self.current_streak += 1
        else:
            self.num_wrong += 1
            self.num_correct = 0
            self.current_streak = 0
        
        # self.reversals = 0 # TODO: add logic here

        print("~~~~~~~~~~~~~~~~~~")
        print(f"NUMBER OF BEEPS PLAYED: {self.num_beeps}")
        print(f"NUMBER OF BEEPS PARTICIPANT HEARD: {self.user_input}")
        print("~~~~~~~~~~~~~~~~~~")
        print(f"NUMBER OF CORRECT ANSWERS: {self.num_correct}")
        print(f"NUMBER OF WRONG ANSWERS: {self.num_wrong}")
        print(f"CURRENT STREAK: {self.current_streak}")
        print(f"LAST CURRENT STREAK: {self.last_current_streak}")
        print("~~~~~~~~~~~~~~~~~~")


    ### check CS (or other relevant data) against condition(s)
    ## e.g. CS > 1, reversals >1
    def check_conds(self): # --> TODO: update this to only set flags (add a separate update_trial_params() fcn)
        if self.current_streak > 1: # start new trial with lower amplitude
            self.current_streak = 0
            # self.trial_amp *= 0.5
            self.trial_amp *= TrialPlayer.db2amp(-1*abs(self.dB_down))
            self.prepare_trial()
        elif self.num_wrong > 0: # double amplitude (but not more than 1) and start new trial
            # self.trial_amp *= 2
            self.trial_amp *= TrialPlayer.db2amp(abs(self.dB_up))
            self.trial_amp = min(self.trial_amp, 1.0) # make sure it can't get louder than 1
            self.prepare_trial()

        if self.trial_num > 24:
            self.end_cond = True

        core.wait(1.0) # too long TODO: sort this out

    ### IF condition met, UPDATE trial params, RESET CS, UPDATE other relevant counters (e.g. reversals)
    ## set end_cond flag

    ### IF end_cond flag is set, finish paradigm and clean up (save and plot results, etc.)
    ## ELSE restart loop w/ new trial params

    ### MAIN LOOP (called below for testing) TODO: consider renaming (to run_paradigm?)
    def main(self):
        # el = ExperimentalLoop()
        ## all of this can probably be put into some sort of main_loop() function? (or just remove el = ExpLoop()?)
        while not self.end_cond:
            self.prepare_trial()
            self.execute_trial()
            core.wait(0.5) # to avoid a click at the end
            self.user_input = self.get_response()
            self.check_answer()
            self.update_counters()
            self.check_conds()


### FOR TESTING (when the file is run directly, TODO: remove this later?)
if __name__ == "__main__": # this allows the file to be run directly
    # root = tk.Tk() # make a window
    # root.title("Simple App") # add a title
    # root.after(100, main) # run experiment 100 ms after mainloop starts
    # root.mainloop() # start the applications main loop to keep the window open
    el = ExperimentalLoop()
    el.main()