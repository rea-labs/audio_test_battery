# audio_playback_test
# demonstrates how to play sound files, tones, and noise with delays
# --> basis for the "stumulus_gen()" and "event_gen()" functions that will be at 
# the core of the new MultiThreshold python tool

###############################
###### PICK ONE OF THESE ######
audioLib = ['pygame'] # for the moment, it seems that only pygame is working on apple silicon macs...
# audioLib = 'PTB' # FAIL!
# audioLib = 'sounddevice' # FAIL!
# audioLib = 'pyo' # FAIL!
###############################

# NOTE: THERE SEEMS TO BE A SAMPLE RATE ISSUE, even just playing a fixed tone takes longer than expected
# (testing with a 100 second tone confirms this) 
# strange b/c both the device fs and well as fs of all of the created AudioClip objects are reported as 48 kHz, i.e.
# sound.AudioDeviceInfo().defaultSampleRate = 48000
# snd_01.sampleRate = 48000
# --> TODO: figure out how to change fs of the actual engine so it matches 

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
from python_code.deprecated.OLD_event_gen import *


test_stim = {
    "masker": {
        "dur": 1000,
        "freq": 220,
        "gain": 0.5,
        "ramp": 100
    },
    "gap": 300,
    "target": {
        "dur": 100,
        "freq": 440,
        "gain": 0.5,
        "ramp": 10
    }
}

### TEST IT USING THIS:
# test = event_gen(test_stim)
# test["mask"].play()
# core.wait(test["delay_time"])
# test["target"].play()


# SETUP PATH FILE PLAYBACK 
# this assumes that there there '02_audio' exists on the same level as the 'test_battery' folder
# and contains '/test_audio/numbers/01-16b.wav'
cwd = Path.cwd()
fname = cwd.parent.parent.joinpath('02_audio', 'test_audio', 'numbers', '01-16b.wav')

# it should resolve to (something like) this:
# fname = '/Users/spin3d/Documents/Projects/SpiN3D_DIZH/02_audio/test_audio/numbers/01-16b.wav'

# PLAY THE FIRST SOUND (440 Hz tone for 18 seconds)

myTone = sound.AudioClip.sine(duration=18.0, freqHz=440, gain=0.25)  # generate a tone
snd_01 = sound.Sound(myTone)
snd_01.play()
# return # uncomment to test sample rate issue...

# WAIT 3 SECONDS...
print("waiting 3 seconds...")
core.wait(3.0)

# IF THE FILE WAS FOUND, PLAY IT
if fname.exists():
    snd_02 = sound.Sound(fname)
else: # OTHERWISE PLAY A 220 Hz TONE FOR 12 SECONDS
    snd_02 = sound.Sound(sound.AudioClip.sine(duration=12.0, freqHz=220, gain=0.25)).play()
snd_02.play()

## PREPROCESS FADED VERSION OF snd_03 to avoid timing problems (should probbly do all of this at start)
# (not sure if this actually accomplishes what we need though...)
sin_432 = sound.AudioClip.sine(12,432,0.25)
samples = sin_432.samples # convert AudioClip into an numpy array

fs = sin_432.sampleRateHz # get fs
fade_time_ms = 4500 # define fade time in ms
fade_time_samps = int(fs * fade_time_ms / 1000) # compute fate time in samples

mask = np.ones(np.roll(samples.shape,1)) # fill the mask with 1s 
mask[:,0:fade_time_samps] = np.linspace(0,1,fade_time_samps) # fade in at the start
mask[:,-fade_time_samps:] = np.linspace(1,0,fade_time_samps) # fade out at the end
mask = mask.transpose() # this is a bit hacky, FIX IT...(?)
faded_samples = mask * samples

# snd_03 = sound.Sound(sin_432)
snd_03 = sound.Sound(sound.AudioClip(np.asarray(faded_samples)))

# WAIT 3 SECONDS...
core.wait(3.0)

# PLAY A SLIGHTLY DETUNED TONE (432 Hz) for 9 seconds --> results in beating
snd_03.play()

# WAIT 3 SECONDS...
core.wait(3.0)

# PLAY A SERIES OF 10 NOISE BURSTS WITH A DELAY RANGING FROM 0.1 - 1.0 SECONDS
for i in range(1, 11):
    pulse_length = i/10
    # print(pulse_length)
    
    noise_burst = sound.AudioClip.whiteNoise(duration=pulse_length/4)
    noise_burst.gain(0.1) # whiteNoise() has no gain argument, so need to set the AudioClip gain instead
    snd_04 = sound.Sound(noise_burst)
    snd_04.play()

    core.wait(pulse_length)


# core.quit() # this was in an example, but is causing problems here and doensn't seem to be necessary