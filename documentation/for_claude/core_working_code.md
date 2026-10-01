# Core working code

## Top level (mostly functional paradigm)

`python_code/paradigm_adaptive_PTA.py`
- this class correctly implements the general flow of the PTA (trial creation, execution, response collection, GUI, saving data, etc.)
- some of the details specific parameters are incorrect (mainly for testing purposes), e.g.
    - `self.trials_after_reversal = 3` and not 10, like it should be
- the specific way it progresses through configs is incorrect/random, e.g. it changes duration and pitch (details to follow about how a PTA paradigm should evolve)
- some of the parameters (class variables) are deprecated, just left over from old implementations
    - please help to clean this up
- the **goal** is to use this file as the basis for the new *adaptive paradigm base class*

## Underlying helper classes

`python_code/trial_player.py`
- creates a new trial to be executed
- it is called by the main paradigm
- trials can consist of a train of stimuli (events) and pauses
- the exact timing and values are specified by provided parameters
- it implements an "unwrapping" behavior for each parameter based on the longest list


`python_code/event_gen.py`
- creates PTB sound objects that can be played
- it is called by the trial_player class
- does sine tones, FM, AM, white noise 
- to add: 
    - pink noise (there's a commented out example at the bottom)
    - arbitrary file playback
- it handles fade in/out to avoid clicks


`python_code/utils/varspec.py`
- is a class that helps to enable the nested parameter looping behavior for configurations within a paradigm via inner and outer variables (parameters)
- passed into the a specific paradigm class
- should probably be expanded to be more thorough/complete (in order to define the various specific paradigms)


## Test files

`python_code/test_adaptive_PTA.py`
- example of how to run the `paradigm_adaptive_PTA.py` example
- the specific inner and outer variables are arbitrary/random