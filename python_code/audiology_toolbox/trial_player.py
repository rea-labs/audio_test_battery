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
# prefs.hardware.speaker.SpeakerDevice(latencyClass=3) # not sure how to set this...?
prefs.hardware
from psychopy import sound

# from config.DEFAULTS import DEFAULTS
DEFAULTS = { # TODO: move this to DEFAULTS.py (and sort out nested naming)
    "wave_type": ["sin"],
    "del_times": [],
    "durations": [1],
    "fc": [440],
    "fm": [8],
    "mod_ind": [8.0],
    "amp": [1],
    "bg": [1],
    "fs": 48000,
    "fade_time": 0.05,
    # "bg": {"play_bg": True, "bg_start_delay": 1,"bg_end_delay": 2},
    "bg": {"play_bg": False, 
           "bg_start_delay": 1,
           "bg_end_delay": 1, 
           "bg_amp": 0.25, 
           "bg_fade_time": 1
           },
    "sample_accurate": False,
    "verbose": False
}

class TrialPlayer:

    def __init__(self, wave_type=None, del_times=None, durations=None, fc=None, fm=None, mod_ind=None, amp=None, bg=None, fs=None, fade_time=None, sample_accurate=None, pan=None, play_now=False, verbose=None, calibration=None, per_channel_gain=None):
        self.eg = event_gen.EventGen() # where should this go?
        # calibration: optional CalibrationManager. If None, uncalibrated behavior (current/legacy).
        # If set, all sounds are routed through calibration.prepare_sound() which handles
        # mono->stereo conversion, pan, per-channel gain, and FIR inverse filter convolution.
        self.calibration = calibration
        # End time (ptb clock) of the last audible interval of the most recent
        # play_trial(); consumed by the base class for per-trial reaction_time_s.
        # Stamped in play_trial(); None until the first trial plays.
        self.stim_end_time = None
        self.new_trial(wave_type=wave_type, del_times=del_times, durations=durations, fc=fc, fm=fm, mod_ind=mod_ind, amp=amp, bg=bg, fade_time=fade_time, fs=fs, sample_accurate=sample_accurate, pan=pan, play_now=play_now, verbose=verbose, per_channel_gain=per_channel_gain)


        
    def new_trial(self, wave_type=None, del_times=None, durations=None, fc=None, fm=None, mod_ind=None, amp=None, bg=None, fs=None, fade_time=None, sample_accurate=None, pan=None, play_now=False, verbose=None, per_channel_gain=None):
        # if a value is supplied use it, otherwise, take the default from the DEFAULTS dictionary
        self.wave_type = wave_type if wave_type is not None else DEFAULTS["wave_type"]
        self.del_times = del_times if del_times is not None else DEFAULTS["del_times"]
        self.durations = durations if durations is not None else DEFAULTS["durations"]
        self.fc = fc if fc is not None else DEFAULTS["fc"]
        self.fm = fm if fm is not None else DEFAULTS["fm"]
        self.mod_ind = mod_ind if mod_ind is not None else DEFAULTS["mod_ind"]
        self.amp = amp if amp is not None else DEFAULTS["amp"]
        # pan: None or 0.0 = both ears, -1.0 = left only, 1.0 = right only
        self.pan = pan
        # per_channel_gain: optional per-event (gain_L, gain_R) tuples for
        # paradigms that drive per-ear amplitudes from dB SPL (IFMC, TMC).
        # Accepted forms:
        #   None                  -- no per-channel scaling (default)
        #   (gain_L, gain_R)      -- single tuple, applied to all events
        #   [(gL, gR), None, ...] -- per-event list; None entries skip scaling
        # Requires self.calibration to be set (otherwise raised at play_trial).
        # Not supported with sample_accurate=True (raised at play_trial).
        self.per_channel_gain = per_channel_gain
        # Shallow copy the default dict so we don't mutate it
        self.bg = DEFAULTS["bg"].copy()
        # If user provided a custom dictionary, update only the provided keys
        if bg is not None:
            self.bg.update(bg)
        self.fs = fs if fs is not None else DEFAULTS["fs"]
        self.fade_time = fade_time if fade_time is not None else DEFAULTS["fade_time"]
        self.sample_accurate = sample_accurate if sample_accurate is not None else DEFAULTS["sample_accurate"]
        self.verbose = verbose if verbose is not None else DEFAULTS["verbose"] 
    
        if self.verbose:
            print("~~~~~~")
            print(f"checking input: bg = {bg}")
        self.del_times = self.input_check(self.del_times, name="del_times", allow_empty=True)
        self.durations = self.input_check(self.durations, name="durations")
        self.fc = self.input_check(self.fc, name="fc")
        self.amp = self.input_check(self.amp, name="amp")
        if self.verbose:    
            print("~~~~~~")

        self.num_events = max([self.del_times.size + 1, self.durations.size, self.fc.size, self.amp.size]) # compute how long the sequence should be
        if self.verbose:
            print(f"num_events = {self.num_events}")
        # double-check that del_times is valid (i.e. can't be empty if the are more than one event in the trial)
        if self.num_events > 1 and (self.del_times.size == 0):
            raise ValueError("del_times can't be empty when total number of events in the trial > 1...")
        
        # expand all inputs to max_events
        self.del_times = self.vec_expand(self.del_times, self.num_events - 1)#, name="del_times")
        self.durations = self.vec_expand(self.durations, self.num_events)#, name="durations")
        self.fc = self.vec_expand(self.fc, self.num_events)#, name="fc")
        self.fm = self.vec_expand(self.fm, self.num_events)#, name="fm")
        self.mod_ind = self.vec_expand(self.mod_ind, self.num_events)#, name="mod_ind")
        self.amp = self.vec_expand(self.amp, self.num_events)#, name="amp")
        self.fade_time = self.vec_expand(self.fade_time, self.num_events)#, name="fade_time")
        if self.verbose:
            print(f"updated bg = {self.bg}")


        # if bg is not played, make sure delay times are set to 0
        if self.bg['play_bg'] == False:
            self.bg['bg_start_delay'] = 0
            self.bg['bg_end_delay'] = 0


        ### compute absolute start times
        self.start_times = np.concatenate(([self.bg['bg_start_delay']], self.durations[:self.num_events - 1] + self.del_times)).cumsum()
        if self.verbose:
            print(f"start_times = {self.start_times}")


        ### compute absolute end times (useful for plotting)
        self.end_times = self.start_times + self.durations
        if self.verbose:
            print(f"end_times = {self.end_times}")

        self.bg_duration = self.bg['bg_start_delay'] + np.sum(self.durations) + np.sum(self.del_times) + self.bg['bg_end_delay']
        if self.verbose:
            print(f"bg_duration = {np.round(self.bg_duration,3)}")

        if play_now: # NOTE: THIS MAY BE BROKEN B/C OF MISSING WAVE_TYPE!!!
            self.play_trial() # NOTE: MAYBE DON'T DO THIS AUTOMATICALLY (or figure out a way to decouple constructor from makign it happen)


    # , wave_type=["sin"]
    def play_trial(self):
        ### pre-allocate an array, then generate and store all sounds in it
        wave_type = self.vec_expand(self.wave_type, self.num_events)
        sound_list = [None] * self.num_events
        # Collect raw mono samples in parallel with sound_list. Needed for:
        #  (a) calibration path -- prepare_sound() operates on raw samples
        #  (b) sample_accurate path -- concatenation uses raw samples (so timing
        #      is preserved when calibration is applied to the full concat)
        wave_list = [None] * self.num_events

        # Normalize per_channel_gain to a per-event list (length = num_events).
        # Validate that calibration is present and sample_accurate is False.
        pcg_list = self._normalize_per_channel_gain(self.per_channel_gain)

        # sound_dict = [None] * self.num_events
        for i in range(self.num_events):
            if wave_type[i] == "sin":
                sound_list[i], wav_dict = self.eg.sin(duration=self.durations[i], fc=self.fc[i], amp=self.amp[i], fade_time=self.fade_time[i], return_dict=True)
            elif wave_type[i] == "fm":
                # def fm(self, duration=10.0, fc=440.0, fm = 5.0, mod_ind=8.0, amp=1.0, fade_time = 0.05, return_dict = False):
                sound_list[i], wav_dict = self.eg.fm(duration=self.durations[i], fc=self.fc[i], fm=self.fm[i], mod_ind=self.mod_ind[i], amp=self.amp[i], fade_time=self.fade_time[i], return_dict=True)
            elif wave_type[i] == "am":
                sound_list[i], wav_dict = self.eg.am(duration=self.durations[i], fc=self.fc[i], fm=self.fm[i], mod_ind=self.mod_ind[i], amp=self.amp[i], fade_time=self.fade_time[i], return_dict=True)
            elif wave_type[i] == "white":
                sound_list[i], wav_dict = self.eg.white_noise(duration=self.durations[i], amp=self.amp[i], fade_time=self.fade_time[i], return_dict=True)
            else:
                raise Exception("BAD WAVE_TYPE!")
            wave_list[i] = wav_dict["values"]

            if self.calibration is not None:
                # Calibration pipeline handles mono->stereo, pan, per-channel
                # gain, and FIR convolution. Replaces the uncalibrated pan
                # rebuild below.
                sound_list[i] = self.calibration.prepare_sound(
                    wave_list[i], self.fs,
                    pan=self.pan,
                    per_channel_gain=pcg_list[i]
                )
            elif self.pan is not None and self.pan != 0:
                # Apply pan: rebuild as stereo array with appropriate channel zeroed
                mono = wave_list[i]
                if self.pan < 0:   # left ear only
                    stereo = np.column_stack([mono, np.zeros_like(mono)])
                else:              # right ear only
                    stereo = np.column_stack([np.zeros_like(mono), mono])
                sound_list[i] = sound.Sound(value=stereo, sampleRate=self.fs, stereo=True, secs=self.durations[i], hamming=False)
    
        if self.sample_accurate:
            # Concatenate raw uncalibrated mono samples with inter-event silences.
            # Using wave_list (mono) rather than sound_list[i].sound preserves the
            # original nominal timing regardless of whether calibration is enabled.
            # After concatenation we apply calibration to the whole signal (which is
            # mathematically equivalent to per-event calibration + overlap-add,
            # because convolution is linear).
            tmp_snd = []
            del_array = np.concatenate((self.del_times*self.fs, [0]))
            del_array = np.int32(del_array)
            for i in range(self.num_events):
                tmp_snd = np.concatenate((tmp_snd, wave_list[i])) # add waveform (raw mono)
                tmp_snd = np.concatenate((tmp_snd,np.zeros(del_array[i]))) # add delay
            new_t = np.linspace(0, np.size(tmp_snd)/self.fs, np.size(tmp_snd))
            # print(tmp_snd)
            # print(self.del_times)
            # print(np.size(tmp_snd))
            # print(new_t[-1])

            if self.calibration is not None:
                # _normalize_per_channel_gain has validated that pcg_list is
                # uniform across events when sample_accurate=True, so taking
                # the first entry yields the (gain_L, gain_R) to apply to the
                # full concatenated buffer (or None for no per-channel gain).
                uniform_pcg = pcg_list[0] if pcg_list else None
                concat_snd = self.calibration.prepare_sound(
                    tmp_snd, self.fs, pan=self.pan,
                    per_channel_gain=uniform_pcg,
                )
            else:
                concat_snd = sound.Sound(value=tmp_snd, sampleRate=self.fs, stereo=True, secs=new_t[-1], hamming=False)


        ### generate bg sound, if necessary
        if self.bg['play_bg']: # TODO: update to play differnt types of sounds
            bg_sound, bg_dict = self.eg.white_noise(duration = self.bg_duration, amp = self.bg['bg_amp'], fade_time = self.bg['bg_fade_time'], return_dict=True)
            if self.calibration is not None:
                # bg is diotic (no pan): calibration applies to both channels identically
                bg_sound = self.calibration.prepare_sound(bg_dict["values"], self.fs)


        ### play all sounds in sound_list
        now = ptb.GetSecs() # get current time and...
        # begin playback of...
        print("Begin trial...")
        if self.bg['play_bg']: # bg...
            bg_sound.play(when=now)
        if self.sample_accurate:
            print("PLAYING CONCAT SOUND...")
            concat_snd.play(when = now + self.start_times[0])
        else:
            for i in range(self.num_events): # and events
                sound_list[i].play(when = now + self.start_times[i])


        # End of the last audible interval on the ptb clock (excludes the FIR
        # ringout tail + PTB margin added in the wait below). Consumed by the
        # base class for per-trial reaction_time_s. Uses the same expression as
        # the wait so a background/masker that outlasts the events is included.
        # Re-stamped every play_trial, so repeats reference the last playback.
        self.stim_end_time = now + max(self.bg_duration, max(self.end_times))

        ### pause core until everything is done
        # Include FIR ringout tail when calibration is active. prepare_sound()
        # extends each buffer by `ringout_seconds`, and that tail must be
        # given time to play out before the function returns (otherwise the
        # next prepare_trial() can begin loading audio while the previous
        # tail is still ringing out). The +0.1 is the baseline PTB scheduling
        # margin (preserved from prior behavior).
        ringout = self.calibration.ringout_seconds if self.calibration is not None else 0.0
        core.wait(max(self.bg_duration, max(self.end_times)) + ringout + 0.1) # NOTE: this will block most operations until everything is finished
        print("Trial finished...")



    #########################
    ### UTILITY FUNCTIONS ###
    ######################### 
    @staticmethod
    def input_check(vals, name=None, allow_empty=False): # TODO: clean up this logic (add raise?)
        # """check for valid inputs and convert everything to numpy arrays"""
        # print(f"checking input: {name} = {vals}")
        vals = np.asarray(vals)
        if not(allow_empty) and vals.size == 0:
            raise ValueError(f"input '{name}' can't be empty!")
        # print("~~~~~~")
        return vals
    
    @staticmethod
    def vec_expand(vals, len = 1, name=None):
        """scalar/vector expansion by wrapping the indexes via a modulo operation"""
        wrapped = np.asarray(vals).take(np.arange(len), mode='wrap')
        if name is not None:
            print(f'expanded {name} = {wrapped}')
        return wrapped
    
    @staticmethod
    def db2amp(db): # MAYBE THIS SHOULD BE MOVED TO A UTILITIES CLASS?
        return np.power(10, db/20) # dB to amp
    
    @staticmethod
    def amp2db(amp): # MAYBE THIS SHOULD BE MOVED TO A UTILITIES CLASS?
        return 20 * np.log10(amp) # amp to dB

    def _normalize_per_channel_gain(self, pcg):
        """
        Validate and expand per_channel_gain to a per-event list.

        Returns a list of length self.num_events whose entries are either
        a (gain_L, gain_R) tuple or None.

        Raises clear errors when per-channel gain is requested without
        calibration, or when per-event-different gains are requested in
        sample_accurate=True mode (step discontinuities at event boundaries
        would ring through the FIR convolution -- not mathematically clean).
        Uniform per_channel_gain in sample_accurate=True is permitted: it
        commutes with concatenation and is applied to the full concat buffer
        in play_trial.
        """
        if pcg is None:
            return [None] * self.num_events

        # Anything non-None requires a calibration manager (per-channel
        # scaling only makes physical sense when the calibration math has
        # produced (amp_L, amp_R) for the caller).
        if self.calibration is None:
            raise ValueError(
                "TrialPlayer.per_channel_gain requires a CalibrationManager. "
                "Either attach one via the `calibration` kwarg or omit "
                "per_channel_gain."
            )

        # Single tuple -> apply to every event (uniform gain).
        if isinstance(pcg, tuple) and len(pcg) == 2 \
                and all(isinstance(v, (int, float)) for v in pcg):
            normalized = [pcg] * self.num_events

        # List/sequence -> validate length and entry shape.
        elif isinstance(pcg, (list, tuple)):
            if len(pcg) != self.num_events:
                raise ValueError(
                    f"per_channel_gain list length {len(pcg)} does not "
                    f"match num_events {self.num_events}"
                )
            normalized = []
            for i, entry in enumerate(pcg):
                if entry is None:
                    normalized.append(None)
                elif (isinstance(entry, tuple) and len(entry) == 2
                      and all(isinstance(v, (int, float)) for v in entry)):
                    normalized.append(entry)
                else:
                    raise ValueError(
                        f"per_channel_gain[{i}] must be None or a "
                        f"(gain_L, gain_R) tuple of floats; got {entry!r}"
                    )
        else:
            raise ValueError(
                f"per_channel_gain must be None, a (gain_L, gain_R) tuple, "
                f"or a list of those; got {type(pcg).__name__}"
            )

        # sample_accurate=True concatenates events into one buffer before
        # calibration. Uniform gain across all events can be applied to the
        # concat post-hoc (gain commutes with concatenation). Per-event-
        # different gains, or a mix of None / non-None entries, would create
        # step discontinuities at event boundaries that ring through the
        # FIR convolution -- not mathematically clean. Reject those.
        if self.sample_accurate:
            non_none = [e for e in normalized if e is not None]
            if non_none and len(non_none) != len(normalized):
                raise ValueError(
                    "TrialPlayer.per_channel_gain in sample_accurate=True "
                    "mode does not support a mix of None and tuple entries "
                    "(would introduce a step discontinuity at the boundary "
                    "and ring through the FIR convolution). Either apply "
                    "the same gain uniformly across events, or use "
                    "sample_accurate=False so each event gets its own "
                    "Sound object."
                )
            if non_none and not all(e == non_none[0] for e in non_none):
                raise ValueError(
                    "TrialPlayer.per_channel_gain in sample_accurate=True "
                    "mode must be uniform across events (single tuple, or "
                    "list with all entries equal). Per-event-different "
                    "gains would create step discontinuities at event "
                    "boundaries, ringing through the FIR convolution. For "
                    "per-event-different gains, use sample_accurate=False "
                    "(each event gets its own Sound)."
                )

        return normalized
    






###### SOME TEST INPUTS ######

    # # del_times = [0.5]
    # # durations = [1.0, 0.1]

    # # del_times = [1, 2, 3, 4, 5, 6]
    # # durations = [1.0]

    # # del_times = [0, 0, 0] # ZERO DELAY TIMES
    # # durations = [1.0]

    # # del_times = [1, -2, 1] # NEGATIVE DELAY TIMES (overlapping tones)
    # # durations = [1.0, 2.0]

    # del_times = [0.5, 2, 0.5]
    # durations = [1.0, 0.1]

    # # del_times = []
    # # durations = [1.0]

    # # fc = 440
    # fc = [220, 440, 880, 1760]
    # amp = 0.5
    # fade_time = 0.05




    ###### NEXT STEPS (FOR TRIAL --> PARADIGM) ######
    # DONE...
    # - use duration array plus other info (event_type, freq, amp, mod_ind, etc.) to generate an array of events
    # - feed start_times to the event scheduler
    # - once everything is ready run the trial
    # - turn this into a function/class
    # - sort out default args from a dictionary 
    # TODO... 
    # - sort out/clean up loading DEFAULT args from file (nested dictionaries? <-- json?)
    # - add more input checking (e.g. durations and bg_start_delay can't be negative)
    # - add choice of event type (see "walrus operator" note below)
    # - update play_trial() to handle other types of sounds (see dictionary example below)
    # (in another class)
    # - collect responses from user (via keyboard for now)
    # - log results
    # - display info on gui (using tkinter)
    # - repeat (start next trial) based on experimental logic until paradigm is finished
    # - define paradigm logic (load config details from json?)
    # - CONVERT EVERYTHING TO CLASSES!


    ###### OTHER NOTES: 

    ### AUTO-RELOAD ###
    # %load_ext autoreload
    # %autoreload 2

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

    ### getting timestamps (to add to log files):
    # from datetime import datetime
    # import time
    # print(f"timestamp: {datetime.now().isoformat()}"),  # Absolute calendar time
    # print(f"response_time: {time.time()}")        # Acceptable absolute time
    ## see also:
    # ptb.GetSecs() # relative time
    # time.perf_counter() # (platform dependent) relative time
## conversion info:
# Task	Function	Output Example
# Unix → local datetime	        datetime.fromtimestamp(ts)	    2024-05-22 14:54:10.123456
# Unix → UTC datetime	        datetime.utcfromtimestamp(ts)	2024-05-22 18:54:10.123456
# Format datetime → string	    .strftime(format_string)	    '2024-05-22 14:54:10'