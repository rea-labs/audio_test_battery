audioLib = ['PTB'] # WORKS NOW!

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

# Sampling rate
sampleRate = 48000  # Hz
duration = 6.0  # seconds

# AM parameters
carrier_freq = 440.0  # Hz (Base frequency)
mod_freq = 1.0  # Hz (Modulation frequency)
mod_index = 0.16  # Hz (amplitude deviation)

# Generate time vector
t = np.arange(0, duration, 1/sampleRate)

# Generate AM waveform
am_wave = np.sin(2 * np.pi * carrier_freq * t)
am_mod = mod_index * np.sin(2 * np.pi * mod_freq * t)
# am_mod = 0.5 + np.sin(2 * np.pi * mod_freq * t)/2
am_wave = am_mod * am_wave
# am_wave = np.sin(2 * np.pi * carrier_freq * t + mod_index * np.sin(2 * np.pi * mod_freq * t))

# Create PsychoPy sound object using PTB engine
am_sound = sound.Sound(value=am_wave, sampleRate=sampleRate, stereo=True, secs=duration, hamming=False)

# Set PTB as the audio engine
sound.Sound.usePTB = True

# Play the sound
am_sound.play()

# Keep the script running until sound is done playing
core.wait(duration)




