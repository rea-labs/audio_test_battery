# Python audiology test battery

## General goals / overview
i would like to create a class to manage an audiology tool kit using python with psychopy and the PTB audio class. it need to be able to do the following things: 
1) run multiple different paradigms, e.g. pure-tone audiograms (PTA), IFMC, TMC, gap detection, DLI, FM, AM, ITD, ILD, LDL --> in order to do that it needs to be able to define timing for each paradigm, generate pure tones, white noise, FM tones, AM tones, playback samples, etc. 
2) run experiments based on "templates" 
3) accept user input for responses for each paradigm and use the results to modify the paradigm in an adaptive manner --> also, use results from previous paradigms to set parameters in subsequent paradigms
4) plot results in real time for the operator to follow along 
5) record results in csv files and generate plots and reports 
6) calibrate/characterize the system using microphones, etc. --> this may need to happen (partially) offline, at least in part, i.e. i think i will only need to be able to convolve my output with an inverse filter in the form of an impulse response

most of the test battery is strongly based on the [MultiThreshold matlab toolbox](https://github.com/rmeddis/MAP) from the Hearing Research Lab at the University of Essex, although the original version has been modified for the University of Zurich (UZH), as described in a subsequent document.

I'm developing on a mac, but the code ultimately needs to run on windows.  this has caused some problems with psychopy, but it seems that we've found a stable configuration (see the `environment.yml` file)

### (Multiple) paradigm sources 
as stated, the core behavior is derived from the MultiThreshold toolbox, but some of the paradigms are not found there, but rather in the "Prague toolbox" (e.g. AM, FM, and perhaps some others) - i will provide documentation for how these paradigms should function in an additional file.  but regardless of which toolbox the paradigms come from, our implementation should *ALWAYS FOLLOW THE SAME GENERAL LOGIC* (derived from the the MultiThreshold toolbox).

***For reference, the incorrect logic generally works like this (in old Prague pattern in GAP, AM, FM, etc.):***
- uses fixed staircases
- doesn't loop through variables
- ... check for more problems ...

### Current state
I initially built many of the paradigms following the wrong logic (from the Prague box), so I only recently began to rework things to follow the correct logic.  the file `paradigm_adaptive_PTA.py` implements the correct *general* control flow (although the actual test it is running was only meant as a proof of concept, so it is a bit nonsense and doesn't actually implement PTA).  The other (non-adaptive) versions of the paradigms generally play the right types of sounds, but do not follow the correct control logic.

i have implemented the following, although there is certainly room for improvement:
- code to generate various types of test stimuli, including both defining duration and timing of signals
- basic user response handling
    - gui to manage user responses
    - processing user input to update trial parameters
- basic paradigm control (although the underlying logic is currently incorrect in most cases)
- logging data to csv files

### To do
what i would like to achieve is clean up, streamline, and improve the code i have so far and produce a working, testable version of the test battery *ASAP*!  the priority order is as follows (from highest to lowest)

1. Implement base paradigm class from adaptive_PTA pattern
    - this should probably be as generic as possible
2. Re-implement all existing paradigms by providing a "param" input and overriding any necessary methods in the base paradigm (PTA, GAP, DLI, AM, FM, PTA)
    - perhaps add class variables as necessary
3. improve/finalize data logging and make sure that paradigms can grab info that they need from previous results
4. add new paradigms (IFMC, TMC, LDL)
5. flesh out/implement the rest of the classes/behavior (I/O, UI, Data manager, etc.)
6. Advanced features (headphone correction, calibration)

**NOTE:** a testable version means that i can run multiple paradigm correctly, it will log the data ot a CSV file, the gui works for the participants (it can just use keyboard input for now, e.g. "press 0 or 1" or click on the right button) and (a basic version) presents real-time progress (and ideally stats) for the operator

In general, as i said, the underlying code is fairly solid at this point, what i'm missing/need help on most is putting everything together, e.g. making classes and connecting them, defining all of the paradigms from a single base class + config params

## High level structural overview
I think that the entire project should be a single class, made up of several sub classes.  looking back on my initial plan, i'm not 100% convinced of the division b/w all of the classes, but i think they at least cover the basic core functionality:

- ***paradigm base class*** that contains the general logic for how a paradigm should work.  as noted they should all follow the same logic, namely:
    1) a stimulus is presented
    2) the user responds
    3) depending on their response, a new stimulus is presented (more difficult if they got the last one right)
    4) when they get on wrong, the next trial get easier.
        - the first reversal triggers a countdown of 10 more trials
    5) when the countdown ends, a new combination of variables (e.g. a different frequency, stimuli duration, etc.) is defined and the next group of trials begins
        - there can be multiple loops of variables to iterate through
    6) when all combinations are finished, the paradigm is over and the results are saved
    - in general, each trial will either be an event happening or not, in the case of PTA, either a sound is played or not, in FM it would be the tone is either modulated or not.  *the default case is that the even usually happens* and the participants should be honest about if they perceived it (unlike in the original MultiThreshold, there is always only this one choice, either true or false, yes or no, etc. (in the original PTA there would be either 1 or 2 tones played))
    - as a result of this, "catch trials" where a nothing happens are implemented to make sure that the participant understands the paradigm and is not cheating.  in a catch trial, the event does not happen, and if they say that it did, they get a warning.
        - the catch trial rate varies adaptively (up or down based on how often the participant is "caught out")

- ***specific classes*** that inherit the base class.  their behavior (which variables are looped through) is determined by a data structure that specifies the variables and their values

- ***trial_player class*** that organizes specific trials based on parameters passed to it

- ***event_gen class*** that generates actual stimuli that are stitched together by the trial_player class

- ***(G)UI class*** that presents information with both the participant and the experiment operator. should receive info from the HID (via the I/O class?)

- ***I/O (config?) class*** defines and configures the HID that interfaces with the HID to collect data from the participant via some sort of a "response box" (e.g. a keyboard, tablet, or midi controller).  it should probably also handle volume levels, headphone correction via convolution with impulse responses, etc.
    - i'm not totally convinced of how separate from the UI class this should be

- ***Data_manager class*** should parse incoming data, generate logs and reports, and *maybe* also help to manage the specification of specific paradigms based on the defining data structure?

- ***Experimental_controller class*** ties everything together: it talks to the (G)UI class, data_manager class, I/O_(config?) class, and the paradigm being run

i'll provide pdfs of the original notes/block diagrams i generated in miro in a subsequent prompt, but as i said, i think some of the structure has/should evolve from that vision...

## Existing code overview

### functional code

- `paradigm_adaptive_PTA.py` --> the actual progression for PTA is wrong, but this is the first proof of concept for the correct paradigm structure with looping through multiple variables
    - run it using `test_Adaptive_PTA.py` --> this will detail what the input data structure looks like
- `varspec.py` --> this organizes the param config files for the new adaptive paradigms
- `trial_player.py` --> this puts together and actual trial (different stimuli and pauses) based on the parameters it receives
- `event_gen.py` --> this creates a single stimulus event (e.g. sine tone, FM tone, AM tone, white/pink noise, etc.)

### slightly deprecated / semi functional code

these are all from the original version of the test battery i was working on where the trial control logic was all wrong.  NOTE: each of the `paradigm_TYPE.py` has a corresponding `test_TYPE.py` file to run it, which i've included in the upload, but wont explicitly mention in this list
- `paradigm_GAP.py` --> reduces the gap between two stimuli to see when they fuse into one for the participant.  NOTE that timing in psychopy wasn't good enough, so i had to render a sample accurate version of the trial for this one
- `paradigm_DLI.py` --> detect level difference(?)
- `paradigm_AM.py` --> detect amplitude modulation
- `paradigm_FM.py` --> detect frequency modulation
- `paradigm_PTA.py` --> pure tone audiogram

### other code

- `environment.yml` --> ...

## Missing code overview

### paradigms

(descriptions to follow later...)
- `IFMC` --> ...
- `TMC` --> ...
- `LDL` --> ...

### other (classes)
- all the classes described above, although the base class can be derived from `paradigm_adaptive_PTA.py`

## Some other questions

I'll add to this list later, but for now here are some questions i would like to specifically address:

- how to handle paradigm (& general) presets
- how to handle threshold fitting with a sigmodal bolzman function
- general advice on how best to structure/define classes/this test battery --> i'll think more about this in the meantime to address the questions about how i think things should be structured
- where/how to convolve the headphone response with the output signal

i'd also like you be able to explain all of the code in the existing files, as some of it was generated with help from a LLM, so it can extend a bit beyond what i'm really comfortable with in python.