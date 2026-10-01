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
# from event_gen import *

# Sampling rate
sampleRate = 48000  # Hz
duration = 6.0  # seconds

# FM parameters
# carrier_freq = 440.0  # Hz (Base frequency)
# mod_freq = 5.0  # Hz (Modulation frequency)
# mod_index = 100.0  # Hz (Frequency deviation)
carrier_freq = 1000.0  # Hz (Base frequency)
mod_freq = 4.0  # Hz (Modulation frequency)
# mod_index = 0.08  # Hz (Frequency deviation)
mod_index = 20.0  # Hz (Frequency deviation)

# Generate time vector
t = np.arange(0, duration, 1/sampleRate)

# Generate FM waveform
fm_wave = np.sin(2 * np.pi * carrier_freq * t + mod_index * np.sin(2 * np.pi * mod_freq * t))

# Create PsychoPy sound object using PTB engine
fm_sound = sound.Sound(value=fm_wave, sampleRate=sampleRate, stereo=True, secs=duration, hamming=True)

# Set PTB as the audio engine
sound.Sound.usePTB = True

# Play the sound
fm_sound.play()

# Keep the script running until sound is done playing
core.wait(duration)




