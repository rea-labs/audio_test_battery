# %load_ext autoreload
# %autoreload 2


audioLib = ['PTB'] # WORKS NOW!

# CHECK IF ALL OF THESE ARE NECESSARY...?
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

# TODO: add --> from config import DEFAULTS
from config.DEFAULTS import DEFAULTS
# DEFAULTS = { # TODO: expand this list...
#     "fs": 48000,
#     "verbose": False
# }

class EventGen:

    # fs = 48000 # TODO: grab this from a config file

    # def __init__(self, verbose = False):
    # def __init__(self, **kwargs):
    def __init__(self, fs=None, verbose=None):
        self.fs = fs if fs is not None else DEFAULTS["fs"]
        self.verbose = verbose if verbose is not None else DEFAULTS["verbose"] 
        # self.fs = kwargs.get("fs ", DEFAULTS["fs"])  # returns 48000
        # self.verbose = kwargs.get("verbose", DEFAULTS["verbose"])  # 
        # self.fs = EventGen.fs
        # self.verbose = verbose
        # pass

    def rms(self, signal):
        return np.sqrt(np.mean(signal**2))


    def apply_fades(self, wave, fade_time = 0.05): # MAYBE MODIFY TO BE AN "APPLY FADES" FUNCTION?
        """Create fade in and fade out arrays using a Hanning window"""
        fade_samps = int(fade_time * self.fs)
        full_win = np.hanning(2 * fade_samps)
        fade_in = full_win[:fade_samps]
        fade_out = full_win[-fade_samps:]

        wave[:fade_samps] *= fade_in
        wave[-fade_samps:] *= fade_out
        # print('generating fade...')

        return wave
        # return wave, fade_in, fade_out

    def sin(self, duration=1.0, fc=440.0, amp=1.0, fade_time = 0.05, return_dict = False):
        """Generate a sin tone PTB audio sound object"""
        if(self.verbose==True):
            print(f"duration = {duration}")
            print(f"fc = {fc} Hz")
            print(f"amp = {amp}")
            print(f"fs = {self.fs} Hz")

        # Generate time vector
        t = np.arange(0, duration, 1/self.fs)

        # Generate waveform
        wave = amp * np.sin(2 * np.pi * fc * t)

        # apply fade fades in/out (are the _underscores "correct" here?)
        wave = self.apply_fades(wave, fade_time)
        # _fade_in, _fade_out = self.apply_fades(fade_time)
        # _fade_len = _fade_in.size
        # wave[:_fade_len] *= _fade_in
        # wave[-_fade_len:] *= _fade_out 

        # Create PsychoPy sound object using PTB engine
        sound_obj = sound.Sound(value=wave, sampleRate=self.fs, stereo=True, secs=duration, hamming=False)
        
        if(self.verbose==True):
            print("DONE...")
        
        # return sound object and a dictionary with values and time index arrays
        if return_dict: # if requested, return a 2nd argurment w/ actual data in a dict
                return sound_obj, {"t": t, "values": wave} 
        else: # otherwise, just return the sound_obj by default
            return sound_obj
        
    def fm(self, duration=1.0, fc=440.0, fm = 8.0, mod_ind=8.0, amp=1.0, fade_time = 0.05, return_dict = False):
        """Generate a fm tone PTB audio sound object"""
        # if(verbose==True):
        #     print("duration = " + str(duration))
        #     print("fc = " + str(fc) + " Hz")
        #     print("fm = " + str(fm) + " Hz")
        #     print("mod_ind = " + str(mod_ind) + " Hz")
        #     print("fs = " + str(self.fs) + " Hz")

        # Generate time vector
        t = np.arange(0, duration, 1/self.fs)

        # Generate FM waveform
        wave = amp * np.sin(2 * np.pi * fc * t + mod_ind * np.sin(2 * np.pi * fm * t))

        # apply fade fades in/out
        wave = self.apply_fades(wave, fade_time)

        # Create PsychoPy sound object using PTB engine
        sound_obj = sound.Sound(value=wave, sampleRate=self.fs, stereo=True, secs=duration, hamming=False)
        
        if(self.verbose==True):
            print("DONE...")

        # return sound object and a dictionary with values and time index arrays
        if return_dict: # if requested, return a 2nd argurment w/ actual data in a dict
                return sound_obj, {"t": t, "values": wave} 
        else: # otherwise, just return the sound_obj by default
            return sound_obj
    
    def am(self, duration=1.0, fc=440.0, fm = 8.0, mod_ind=16.0, amp=0.84, fade_time = 0.05, return_dict = False):
        """Generate a fm tone PTB audio sound object"""
        # if(verbose==True):
        #     print("duration = " + str(duration))
        #     print("fc = " + str(fc) + " Hz")
        #     print("fm = " + str(fm) + " Hz")
        #     print("mod_ind = " + str(mod_ind) + " Hz")
        #     print("fs = " + str(self.fs) + " Hz")

        # Generate time vector
        t = np.arange(0, duration, 1/self.fs)

        # Generate AM waveform
        # wave = amp * np.sin(2 * np.pi * fc * t + mod_ind * np.sin(2 * np.pi * fm * t))
        # m is the modulation *depth* (0..1). e.g. 16% -> m = 0.16
        wave = amp * (1 + mod_ind/100 * np.sin(2 * np.pi * fm * t)) * np.sin(2 * np.pi * fc * t)

        # apply fade fades in/out
        wave = self.apply_fades(wave, fade_time)

        # Create PsychoPy sound object using PTB engine
        sound_obj = sound.Sound(value=wave, sampleRate=self.fs, stereo=True, secs=duration, hamming=False)
        
        if(self.verbose==True):
            print("DONE...")

        # return sound object and a dictionary with values and time index arrays
        if return_dict: # if requested, return a 2nd argurment w/ actual data in a dict
                return sound_obj, {"t": t, "values": wave} 
        else: # otherwise, just return the sound_obj by default
            return sound_obj


    def white_noise(self, duration = 1.0, amp=1.0, fade_time = 0.05, return_dict = False):
        n_samples = int(duration * self.fs)

        # Generate time vector (just for output, really)
        t = np.arange(0, duration, 1/self.fs)

        wave = np.random.normal(0, 1, n_samples)
        wave = self.apply_fades(wave, fade_time)
        wave = amp * np.tanh(wave / self.rms(wave)) # apply a soft-ish limiter to avoid clipping

        sound_obj = sound.Sound(value=wave, sampleRate=self.fs, stereo=True, secs=duration, hamming=False)
        
        # return sound object and a dictionary with values and time index arrays
        if return_dict: # if requested, return a 2nd argurment w/ actual data in a dict
                return sound_obj, {"t": t, "values": wave} 
        else: # otherwise, just return the sound_obj by default
            return sound_obj 


eg = EventGen() # not necessary, just here for testing in interactive window atm - maybe add the if __main__ thing?
# s = eg.sin()
# w = eg.white_noise(amp=0.25)
# now = ptb.GetSecs() # get current time and...
# s.play(when=now)
# w.play(when=now+1.5)







    # def generate_pink_noise(duration, fs): # CLEAN THIS UP...
    #     n_samples = int(duration * fs)
    #     # Generate white noise in frequency domain
    #     white = np.random.randn(n_samples)
    #     fft = np.fft.rfft(white)
    #     freqs = np.fft.rfftfreq(n_samples, 1/fs)
    #     freqs[0] = 1.0  # avoid divide-by-zero
    #     fft /= np.sqrt(freqs)  # 1/sqrt(f) gives pink-like noise
    #     pink = np.fft.irfft(fft)
    #     pink = pink[:n_samples]
    #     return pink / np.max(np.abs(pink))  # normalize


    # def make_fm_signal(duration=10.0, fc=440.0, fm = 5.0, mod_ind=100.0, amp=1.0, fs=48000, verbose=False):
    #     if(verbose==True):
    #         print("duration = " + str(duration))
    #         print("fc = " + str(fc) + " Hz")
    #         print("fm = " + str(fm) + " Hz")
    #         print("mod_ind = " + str(mod_ind) + " Hz")
    #         print("fs = " + str(fs) + " Hz")


    #     # Generate time vector
    #     t = np.arange(0, duration, 1/fs)

    #     # Generate FM waveform
    #     fm_wave = amp * np.sin(2 * np.pi * fc * t + mod_ind * np.sin(2 * np.pi * fm * t))

    #     # Create PsychoPy sound object using PTB engine
    #     fm_sound = sound.Sound(value=fm_wave, sampleRate=fs, stereo=True, secs=duration, hamming=False)
        
    #     if(verbose==True):
    #         print("DONE...")

    #     return {"sound": fm_sound, "t": t, "values": fm_wave}

    # def make_am_signal(...):
        # ...


# # # # # # NOTE: EXAMPLE OF HOW TO STITCH TOGETHER SINE WAVES VERY PRECISELY... # # # # # #

# import numpy as np
# import matplotlib.pyplot as plt
# from psychopy import sound
# from event_gen import EventGen
# eg = EventGen()

# s, temp = eg.sin(fade_time=0.001, return_dict = True)
# t = temp["t"]
# x = temp["values"]

# new_wave = np.concatenate((x,np.zeros(4800),x))
# new_t = np.linspace(0, 2.1, np.size(new_wave))

# plt.plot(new_t,new_wave)
# # plt.plot(new_t[0:1000],new_wave[0:1000])

# sound_obj = sound.Sound(value=new_wave, sampleRate=48000, stereo=True, secs=2.1, hamming=False)

# sound_obj.play()