# PTB_test
# test to see if PTB works
# IMPORTANT: in order to see if PsychPortAudio loads, you need to comment out:
# line 28 in __init__.py --> from .PsychHID import PsychHID and change the audioLib (comment below)


import psychtoolbox as ptb

# NOTE: NOT SURE WHY THIS IS NECESSARY WHEN IT ALREADY SEEMS TO HAPPEN IN THE psychtoolbox IMPORT ABOVE
import psychopy.core as core
from psychopy import prefs
prefs.hardware['audioLib'] = 'pygame'
prefs.hardware
from psychopy import sound

mySound = sound.Sound('A')
now = ptb.GetSecs()
# WHY DOESN'T THIS WORK?! (perhaps only available when using the SoundPTB engine?)
# as a (less precise) work around, use core.wait() <-- which wont take loading times into account...
mySound.play(when = now + 3)  # play in EXACTLY 3 seconds


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # NOTE: NEED TO MODIFY __init__.py TO THE FOLLOWING FOR PSYCHTOOLBOX TO LOAD! # # # 
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 


# __init__.py
#
# Import Psychtoolbox-3 "mex files" for use in Python and make them available
# under the same names and syntax as people are used to from Octave and Matlab.
#
# Usage in Python script/module:
#
#           from psychtoolbox import *
#
# Copyright (c) 2018 Mario Kleiner. Licensed under MIT license.
#
# 
# 
# from ._version import __version__
# import sys
# is_64bits = sys.maxsize > 2**32
# 
# 
# 
# 
# # Import all PTB modules already ported to Python extension modules:
# # Extract their "main" function, which is named just like the module,
# # and assign its function handle to a variable named just like the module.
# # This will cause the function handles to shadow the original module, so
# # now the module can be called with (almost) identical syntax as one is
# # used to from Octave or Matlab:
# from .WaitSecs import WaitSecs
# from .GetSecs import GetSecs
# # from .PsychHID import PsychHID # BROKEN!!!
# from .IOPort import IOPort
# if is_64bits:
#     # from .PsychPortAudio import PsychPortAudio # BROKEN!!!
#     from psychopy import prefs
#     prefs.hardware['audioLib'] = 'pygame'
#     prefs.hardware
#     from psychopy import sound
# else:
#     PsychPortAudio = None
