# Template for per-machine audio device overrides.
# Copy this file to DEFAULTS_local.py (same folder) and edit for your machine.
# DEFAULTS_local.py is gitignored -- each installation keeps its own copy.
#
# To find your device name, run:
#   python audio_devices.py
# from the audiology_toolbox/ directory. Then paste enough of the name
# to uniquely identify the output you want (all substrings must match,
# case-insensitive).
#
# Examples:
#   RME Fireface UCX II, Analog 3+4 output (Windows):
#       "audio_device_substrings": ("Analog (3+4)",),
#
#   RME Fireface UCX II, any output (Windows or macOS):
#       "audio_device_substrings": ("Fireface", "UCX"),
#
#   Focusrite Scarlett 2i2:
#       "audio_device_substrings": ("Scarlett", "2i2"),
#
#   Apple Silicon built-in speakers (macOS):
#       "audio_device_substrings": ("MacBook", "Speakers"),

DEFAULTS_LOCAL = {
    "audio_device_substrings": ("Analog (3+4)",),   # <-- edit this line
}
