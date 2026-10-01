# from psychopy.sound import Sound

# devices = Sound.getDevices(kind='output')  # List output devices
# print(devices)

import sounddevice as sd

print(sd.query_devices())  # Lists all audio input/output devices
