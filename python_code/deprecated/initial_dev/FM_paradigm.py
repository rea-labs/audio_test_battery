############################
###### DECREMENTED!!! ######
############################

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import psychtoolbox as ptb
# import psychopy.core as core
from psychopy import prefs
from pathlib import Path
from psychopy.hardware import keyboard
from psychopy import core, visual, event # NOTE: this is whats causing the pygame message

import python_code.deprecated.make_fm_signal as make_fm_signal

# set the desired audio library before importing the sound module
audioLib = ['PTB'] # WORKS NOW!
prefs.hardware['audioLib'] = audioLib
prefs.hardware
from psychopy import sound
# from helper_functions import event_gen
# from event_gen import *

# Sampling rate
SAMPLE_RATE = 48000  # Hz

test_sig_dur = 2.0
ISI = 0.2
ITI = 2.0
test_sig_gain = 0.5

# SET INITIAL VALUES
f_c = 1000.0  # Hz (carrier frequency)
f_m = 4.0  # Hz (Modulation frequency)
mod_percent = 0.08 # = 8%
# mod_ind = (mod_percent * f_c) / f_m # replace this with a function
compute_mod_ind = lambda _f_c, _f_m, _mod_percent: (_mod_percent * _f_c) / _f_m
mod_ind = compute_mod_ind(f_c, f_m, mod_percent)

signals = [-1, -1]

def setup_window():
    win = visual.Window(size=(800, 600))

    # Initialize the keyboard
    kb = keyboard.Keyboard()

    # Display text
    text_stim = visual.TextStim(win, text="1 or 2?", height=0.25)
    text_stim.draw()
    win.flip()

    return win, kb

# GENERATE TEST SIGNALS
def generate_test_signals(signals, test_sig_dur, f_c, f_m, mod_ind, test_sig_gain, SAMPLE_RATE):
    # static signal:
    sin_temp = sound.AudioClip.sine(duration=test_sig_dur, freqHz=f_c, gain=test_sig_gain)
    signals[0] = sound.Sound(sin_temp, sampleRate=SAMPLE_RATE)
    # FM signal:
    fm_temp = make_fm_signal.make_fm_signal(test_sig_dur,f_c, f_m, mod_ind, test_sig_gain,SAMPLE_RATE)
    signals[1] = fm_temp['sound']

    # CHOOSE WHAT ORDER TO PLAY THEM
    play_ind = np.random.randint(0,2)

    return signals, play_ind

# PLAY BOTH SOUNDS
def play_stimuli(signals, play_ind, test_sig_dur, ISI):
    now = ptb.GetSecs()
    signals[play_ind].play(when = now)
    signals[(play_ind + 1) % 2].play(when = now + test_sig_dur + ISI)

def get_answer(kb):
    # Wait for a key press
    keys = kb.waitKeys() # TO DO: add error checking 

    # maybe change this to the keyup version?
    if keys:
        key_name = keys[0].name
        # reaction_time = keys[0].rt
        print(f"Key pressed: {key_name}...")
        if key_name.isdigit():
            key_int = int(key_name)
        else:
            print(f"'{key_name}' is not a number...")
            key_int = 0

    key_int -= 1 # convert [1,2] to [0,1]

    return key_name, key_int

# CHECK ANSWER AND UPDATE COUNTERS
def check_answer(key_name, play_ind):
    # answer_check = not(key_int == play_ind) # this is a bit too simple, entering 6 will also say true...
    if key_name == "1":
        if play_ind == 0:
            print("WRONG --> you said FM was first, but it was second")
            answer_check = 0
        elif play_ind == 1:
            print("CORRECT --> you said FM was first, and it played first")
            answer_check = 1
    elif key_name == "2":
        if play_ind == 0:
            print("CORRECT --> you said FM was second, and it was second")
            answer_check = 1
        elif play_ind == 1:
            print("WRONG --> you said FM was second, but it played first")
            answer_check = 0
    elif key_name == 'x':  # Exit if 'x' is pressed
            print("escape")
            answer_check = -1

    return answer_check



def main():
    global signals, ITI, mod_ind
    # CREATE A WINDOW
    win, kb = setup_window()


    # LOOP START
    correct_responses = 0
    reversals = 0
    current_direction = 1
    trial_num = 0

    data = pd.DataFrame(columns=["trial_num", "mod_ind", "answer_check"])

    while reversals < 2:

        # GET VARIABLES --> SET PARAMS
        trial_num += 1

        # GENERATE TEST SIGNALS
        signals, play_ind = generate_test_signals(signals, test_sig_dur, f_c, f_m, mod_ind, test_sig_gain, SAMPLE_RATE)

        # PLAY BOTH SOUNDS
        play_stimuli(signals, play_ind, test_sig_dur, ISI)
        # now = ptb.GetSecs()
        # signals[play_ind].play(when = now)
        # signals[(play_ind + 1) % 2].play(when = now + test_sig_dur + ISI)

        # WAIT FOR KEYBOARD INPUT
        key_name, key_int = get_answer(kb)

        answer_check = check_answer(key_name, play_ind)
        if answer_check == -1:
            break

        correct_responses += answer_check
        print(f"mod_ind = {mod_ind}")
        print(f"correct_responses = {correct_responses}")

        mod_mult = 1.0
        if answer_check == 0:
            mod_mult = 2
        elif correct_responses >= 2:
            mod_mult = 0.5

        if correct_responses >= 2:
            # mod_ind /= 2
            correct_responses = 0
            print("------> mod_ind reduced")

        if answer_check != current_direction:
            reversals += 1
            # mod_ind *= 2
            current_direction = (current_direction + 1) % 2
            print("------> WRONG")


        data.loc[len(data)] = [trial_num, mod_ind, answer_check] # save data before modifying mod_ind
        mod_ind *= mod_mult

        print(f"answers_check = {answer_check}")
        print(f"current_direction = {current_direction}")
        print(f"number of reversals = {reversals}")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


        core.wait(ITI)

        # RESTART LOOP IF NECESSARY


    # ELSE, SAVE RESULTS

    print("DONE!")
    print(data)

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
    data.to_csv(filename, index=False)

    # Enable interactive mode
    # plt.ion()


    # Plot results # ["trial_num", "mod_ind", "answer_check"]
    plt.plot(data["trial_num"], data["mod_ind"], label="mod_ind", marker="o")
    plt.plot(data["trial_num"], data["answer_check"], label="answer_check", marker="s")

    plt.xlabel("trial num")
    plt.ylabel("data")
    plt.legend()
    plt.title("test results")
    plt.grid(True)
    # plt.pause(0.1)

    # plt.ioff()
    plt.show()
    # plt.show(block=False)

    # CLEAN UP
    # core.wait(6.0) # need to make this smarter in the future...
    core.wait(1.0) # can be shorter if the keyboard input blocks execution...
    win.close()
    core.wait(1.0)


if __name__ == "__main__":
    main()  # Runs only when executed directly

# If you want to obtain key-presses during the wait, be sure to use pyglet 
# and to hogCPU for the entire time, and then call psychopy.event.getKeys() 
# after calling ~.psychopy.core.wait()


