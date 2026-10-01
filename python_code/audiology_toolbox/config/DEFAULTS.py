# TODO: break this up into different dictionaries (or make it multilevel?)
DEFAULTS = { # TODO: expand this list...
    "fs": 48000,
    "verbose": False,

    # ------------------------------------------------------------------
    # Audio output device selection (used by audio_devices.py).
    # ALL substrings must appear in the device name (case-insensitive)
    # for a match. The defaults below identify the RME Fireface UCX II
    # across both macOS and Windows.
    #
    # Examples of device names this matches:
    #   macOS:   "RME Fireface UCX II"
    #   Windows: "Speakers (2- RME Fireface UCX II)"
    #
    # NOTE: On Windows, PortAudio prefixes the device name with a
    # number (e.g. "(2- ...)"). That number can change when devices
    # are added/removed -- avoid hardcoding it. The substrings below
    # are robust to that.
    #
    # For other interfaces, adjust to e.g. ("Babyface",) for an RME
    # Babyface, or ("Scarlett", "2i2") for a Focusrite Scarlett 2i2.
    # ------------------------------------------------------------------
    "audio_device_substrings": ("Fireface", "UCX"),

    # ------------------------------------------------------------------
    # Default headphone calibration profile (used by CalibrationManager
    # when no profile= is passed). Must match a key in the "profiles"
    # dict of calibration_data/calibration_config.json.
    #
    # This is the DEFAULT only -- the operator can pick a different
    # profile per run from the dropdown in the paradigm setup dialog
    # (that selection is transient and does not change this value).
    #
    # Named specifically ("headphone") to leave room for other profile
    # types later (e.g. a TotalMix snapshot profile).
    #
    # Override per machine in config/DEFAULTS_local.py.
    # ------------------------------------------------------------------
    "default_headphone_calibration_profile": "beyerdynamic_dt250_a_ucx2",
    # "audio_device_substrings": ("MacBook", "Speakers"),
    # "audio_device_substrings": ("External", "Headphones"),

    # Debug: per-trial resource + crash logging (all paradigms).
    # See PROLACTIN_resource_logging_handoff.md. Flip to False after the campaign.
    "resource_logging": True,
    "resource_scan_every": 0,   # 0 = off; N = deep gc scan every Nth trial
}

# ------------------------------------------------------------------
# Per-machine local overrides (never committed to version control).
# Create config/DEFAULTS_local.py on each installation with only
# the keys you need to override. See DEFAULTS_local.example.py.
# ------------------------------------------------------------------
try:
    from config.DEFAULTS_local import DEFAULTS_LOCAL  # type: ignore
    DEFAULTS.update(DEFAULTS_LOCAL)
except ImportError:
    pass
