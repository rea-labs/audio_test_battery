audioLib = ['PTB'] # WORKS NOW!

# CHECK IF ALL OF THESE ARE NECESSARY...?
import numpy as np
import matplotlib.pyplot as plt
import psychtoolbox as ptb
import psychopy.core as core
from psychopy import prefs
from pathlib import Path
# set the desired audio library before importing the sound module
prefs.hardware['audioLib'] = audioLib
prefs.hardware
from psychopy import sound
# from helper_functions import event_gen
from deprecated.OLD_event_gen import *
# from python_code.deprecated.OLD_event_gen import *


def make_fm_signal(duration=10.0, fc=440.0, fm = 5.0, mod_ind=100.0, amp=1.0, fs=48000, verbose=False):
    if(verbose==True):
        print("duration = " + str(duration))
        print("fc = " + str(fc) + " Hz")
        print("fm = " + str(fm) + " Hz")
        print("mod_ind = " + str(mod_ind) + " Hz")
        print("fs = " + str(fs) + " Hz")


    # Generate time vector
    t = np.arange(0, duration, 1/fs)

    # Generate FM waveform
    fm_wave = amp * np.sin(2 * np.pi * fc * t + mod_ind * np.sin(2 * np.pi * fm * t))

    # Create PsychoPy sound object using PTB engine
    fm_sound = sound.Sound(value=fm_wave, sampleRate=fs, stereo=True, secs=duration, hamming=False)
    
    if(verbose==True):
        print("DONE...")

    return {"sound": fm_sound, "t": t, "values": fm_wave}
