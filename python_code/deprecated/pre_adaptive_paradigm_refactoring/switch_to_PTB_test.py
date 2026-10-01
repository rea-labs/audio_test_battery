# audio_playback_test
# demonstrates how to play sound files, tones, and noise with delays
# --> basis for the "stumulus_gen()" and "event_gen()" functions that will be at
# the core of the new MultiThreshold python tool
###############################
###### PICK ONE OF THESE ######
# audioLib = 'pygame' # for the moment, it seems that only pygame is working on apple silicon macs...
audioLib = ['PTB'] # WORKS NOW!
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
sample_rate = 48000
myTone = sound.AudioClip.sine(duration=10.0, freqHz=220, gain=0.25)  # generate a tone
snd_01 = sound.Sound(myTone,sampleRate=sample_rate)
snd_01.play()


mySound = sound.Sound('C', secs = 3, volume = 0.25)
now = ptb.GetSecs()
mySound.play(when=now+1.5)

core.wait(12.0)

# return # uncomment to test sample rate issue...
# core.quit() # this was in an example, but is causing problems here and doensn't seem to be necessary

# just testing that git is still working before making too many changes...