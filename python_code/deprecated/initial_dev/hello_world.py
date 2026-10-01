print("This line will be printed.")

# # SOUNDDEVICES SEEMS TO BE BROKEN (AT LEAST ON M2 + 13.6.6)
# # see also: https://discussions.apple.com/thread/254865537?sortBy=best
# import sounddevice as sd
# import soundfile as sf

# data, fs = sf.read('/Users/elarrieu/nrt-help.wav')

# sd.play(data, fs)