###### DEPRECATED --> SEE trial_player.py CLASS ######
###### GENERAL TRIAL PLAYER ######

audioLib = ['PTB'] # WORKS NOW!

import numpy as np
import event_gen
import matplotlib.pyplot as plt
import psychtoolbox as ptb
import psychopy.core as core
from psychopy import prefs
from pathlib import Path
# set the desired audio library before importing the sound module
prefs.hardware['audioLib'] = audioLib
prefs.hardware
from psychopy import sound

### instatiate EventGen class
eg = event_gen.EventGen()

fs = 48000 # TODO: MAYBE BE SMARTER ABOUT THIS? 
# (maybe via an input in gui?  should probably be a class variable as well)

### define delay_times and durations --> convert to function arguments...
# del_times = np.array(0.1)
# durations = np.array([1, 0.5, 0.25, 2])

# del_times = 1 + np.array(np.arange(10))
# durations = np.array([1, 0.1])

# del_times = [0.5]
# durations = [1.0, 0.1]

# del_times = [1, 2, 3, 4, 5, 6]
# durations = [1.0]

# del_times = [0, 0, 0] # ZERO DELAY TIMES
# durations = [1.0]

# del_times = [1, -2, 1] # NEGATIVE DELAY TIMES (overlapping tones)
# durations = [1.0, 2.0]

# del_times = [0.5, 2, 0.5]
# durations = [1.0, 0.1]

del_times = []
durations = [1.0]

fc = 440
# fc = [220, 440, 880, 1760]
amp = 1
fade_time = 0.05

def vec_expand(vals, len = 1):
    """scalar/vector expansion by wrapping the indexes via a modulo operation"""
    return np.asarray(vals).take(np.arange(len), mode='wrap')

def input_check(vals, allow_empty=False): # TODO: clean up this logic (add raise?)
    if allow_empty & (vals == None):
        print('HELLO!')
        vals = []
    return np.asarray(vals)

### force inputs to be arrays
del_times = input_check(del_times, True)
durations = input_check(durations)
fc = input_check(fc)
amp = input_check(amp)
# del_times = np.asarray(del_times)
# durations = np.asarray(durations)
# fc = np.asarray(fc)
# amp = np.asarray(amp)

print(f"del_times INPUT = {del_times}")
print(f"durations INPUT = {durations}")

### the total length of the trial sequence is whichever is greater: 
# - the number of durations
# - the number of delays + 1
# --> the shorter one is wrapped around to match the lenght of the other
num_events = max([del_times.size + 1, durations.size, fc.size, amp.size]) # compute how long the sequence should be
print(f"num_events = {num_events}")

if(del_times.size + 1 < durations.size):
    print('NOTE: wrapping del_times array')
elif(del_times.size + 1 > durations.size):
    print('NOTE: wrapping durations array')

# vectorize del_times and durations
del_times = vec_expand(del_times, num_events - 1)
# del_times = del_times.take(np.arange(num_events - 1), mode='wrap')
durations = vec_expand(durations, num_events)
# durations = durations.take(np.arange(num_events), mode='wrap')
print(f"del_times VECTOR = {del_times}")
print(f"durations VECTOR = {durations}")

### define bg delay and if a bg sound should be played
play_bg = True
bg_start_delay = 1
bg_end_delay = 2

### compute absolute start times
start_times = np.concatenate(([bg_start_delay],durations[:num_events - 1] + del_times)).cumsum()
print(f"start_times = {start_times}")

### compute absolute end times (useful for plotting)
end_times = start_times + durations
print(f"end_times = {end_times}")

bg_duration = bg_start_delay + np.sum(durations) + np.sum(del_times) + bg_end_delay
print(f"bg_duration = {np.round(bg_duration,3)}")

fc = vec_expand(fc, num_events)
print(f"fc = {fc}")

amp = vec_expand(amp, num_events)
print(f"amp = {amp}")

fade_time = vec_expand(fade_time, num_events)
print(f"fade_time = {fade_time}")

### pre-allocate, generate, and store all sounds in an array 
sound_list = [None] * num_events
for i in range(num_events):
    sound_list[i] = eg.sin(duration = durations[i], fc = fc[i], amp = amp[i], fade_time = fade_time[i])
    # sound_list[i] = temp['sound']

# sound_list

### play all sounds in sound_list
if play_bg:
    bg_sound = eg.white_noise(duration = bg_duration, amp = 0.25, fade_time = 0.5)


now = ptb.GetSecs() # get current time and...
# begin playback of
if play_bg: # bg
    bg_sound.play(when=now)
for i in range(num_events): # and events
    sound_list[i].play(when = now + start_times[i])

core.wait(bg_duration + 0.1) # NOTE: this will block most operations until everything is finished


###### NEXT STEPS (FOR TRIAL --> PARADIGM) ######
# DONE...
# - use duration array plus other info (event_type, freq, amp, mod_ind, etc.) to generate an array of events
# - feed start_times to the event scheduler
# - once everything is ready run the trial
# TO DO...
# - turn this into a function/class
# - collect responses from user (via keyboard for now)
# - log results
# - repeat (start next trial) based on experimental logic until paradigm is finished
# - CONVERT EVERYTHING TO CLASSES!


###### OTHER NOTES: 

### example of how to store all event_gen fcns in a dictionary for easy access:
### NOTE: ptbsound objects are now returned alone, not as part of a dict
# fcn = {'sin': event_gen.sin, 'white': event_gen.white_noise}
# (tmp := fcn['sin'](fc = 220))['sound'].play() # --> using the "walrus operator"
## or could do it on 2 lines like this
# tmp = fcn['sin'](fc = 220)
# tmp['sound'].play()

### example of passing in arbitrary arguments into a fcn as a dictionary:
# arg_test = {'fc': 220, 'duration': 3}
# event_gen.sin(**arg_test)

### dB_to_a / a_to_dB
# np.power(10, -6/20) # dB to amp = 0.5011872336272722
# 20 * np.log10(0.5) # amp to dB = -6.020599913279624
