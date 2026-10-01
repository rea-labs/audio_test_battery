# (Slightly) deprecated / semi functional code in need of major refactoring

these are all from the original version of the test battery i was working on where ***the trial control logic was all wrong***, i.e. they generally present two stimuli, one with and one without the condition under test (E.g. AM, FM).  the new versions should always play the one with the condition under test, unless it's a catch trial --> perhaps this will require a bit more thought for DLI, please consult me so we can discuss that when we get to that step.  difficulty should be adapted with the same type logic as demonstrated in `python_code/paradigm_adaptive_PTA.py`

NOTE: each of the `paradigm_TYPE.py` has a corresponding `test_TYPE.py` file to run it

## Base parent class
`python_code/paradigm.py`
- this base class was based on PTA (i think)
- all of the other paradigms "extend" it, but really just overwrite most things, so it's not a great use of OOP

## Individual children/sub-classes
`paradigm_GAP.py` 
- reduces the gap between two stimuli to see when they fuse into one for the participant.  
- NOTE that timing in psychopy wasn't good enough, so i had to render a sample accurate version of the trial for this one

`paradigm_DLI.py` 
- detect level difference between two tones

`paradigm_AM.py` 
- detect amplitude modulation between two tones

`paradigm_FM.py` 
- detect frequency modulation

`paradigm_PTA.py` 
- pure tone audiogram


## Test files

`paradigm_GAP.py` 
- run gap detection

`test_DLI.py` 
- run DLI

`test_AM.py` 
- run AM

`test_FM.py` 
- run FM

`test_PTA.py` 
- run PTA