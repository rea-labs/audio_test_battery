"""
Audio device discovery utility.

Provides cross-platform selection of audio output devices for PsychoPy.
Uses substring matching on device names to handle OS-specific differences,
e.g.:
    Mac:     "RME Fireface UCX II"
    Windows: "Speakers (2- RME Fireface UCX II)"

Default substrings are read from config.DEFAULTS["audio_device_substrings"].
A device is considered a match if ALL substrings appear in its name
(case-insensitive). Callers may override per-call via the `substrings` arg.

Typical use (call BEFORE `from psychopy import sound`):

    from audio_devices import find_and_configure
    find_and_configure(verbose=True)
    from psychopy import sound  # now uses the resolved device

Idempotent: safe to call multiple times. Once PsychoPy's audio backend
has been initialized (typically at first sound.Sound() call), subsequent
attempts to change the device will have no effect -- so call early.
"""

from typing import Iterable, Optional, List
import warnings


# --------------------------------------------------------------------------
# Device enumeration
# --------------------------------------------------------------------------

def list_output_devices() -> List[dict]:
    """
    Return all output-capable audio devices visible to sounddevice/PortAudio.

    Each entry: {"index": int, "name": str, "max_output_channels": int}.
    Returns an empty list if sounddevice is not installed.
    """
    try:
        import sounddevice as sd
    except ImportError:
        warnings.warn(
            "sounddevice not available; cannot enumerate audio devices. "
            "Install sounddevice or rely on PsychoPy default device.",
            stacklevel=2,
        )
        return []

    devices = sd.query_devices()
    return [
        {
            "index": i,
            "name": d["name"],
            "max_output_channels": d["max_output_channels"],
        }
        for i, d in enumerate(devices)
        if d.get("max_output_channels", 0) > 0
    ]


# --------------------------------------------------------------------------
# Substring resolution
# --------------------------------------------------------------------------

def _get_default_substrings() -> tuple:
    """Read substring list from config.DEFAULTS, with a fallback."""
    try:
        from config.DEFAULTS import DEFAULTS
        subs = DEFAULTS.get("audio_device_substrings", ("Fireface", "UCX"))
        return tuple(subs)
    except ImportError:
        return ("Fireface", "UCX")


def find_audio_device(
    substrings: Optional[Iterable[str]] = None,
) -> Optional[str]:
    """
    Find the first output-capable device whose name contains ALL substrings
    (case-insensitive). Returns the full device name as reported by the OS,
    or None if no match is found.

    Parameters
    ----------
    substrings : iterable of str, optional
        Substrings that must all appear in the device name. If None,
        reads from config.DEFAULTS["audio_device_substrings"].
    """
    if substrings is None:
        substrings = _get_default_substrings()

    subs_lower = tuple(s.lower() for s in substrings)
    devices = list_output_devices()

    matches = [
        d for d in devices
        if all(s in d["name"].lower() for s in subs_lower)
    ]

    if not matches:
        return None

    if len(matches) > 1:
        # Common on Windows where the same hardware appears under multiple
        # host APIs (MME, WASAPI, DirectSound). First match is usually fine
        # but warn so the operator can verify.
        names = ", ".join(repr(m["name"]) for m in matches)
        warnings.warn(
            f"Multiple devices matched {tuple(substrings)!r}: {names}. "
            f"Using the first: {matches[0]['name']!r}.",
            stacklevel=2,
        )

    return matches[0]["name"]


# --------------------------------------------------------------------------
# PsychoPy configuration
# --------------------------------------------------------------------------

def configure_psychopy_device(device_name: Optional[str]) -> bool:
    """
    Set the PsychoPy audio output device via prefs.hardware['audioDevice'].

    Must be called BEFORE `from psychopy import sound` for the setting to
    take effect. After the audio backend has initialized, this is a no-op.

    Returns True if a device name was set, False otherwise.
    """
    if device_name is None:
        return False

    from psychopy import prefs
    prefs.hardware["audioDevice"] = device_name
    return True


def get_current_device() -> Optional[str]:
    """
    Return the audio device currently configured in PsychoPy prefs,
    or None if no device has been set (PsychoPy will use system default).
    """
    try:
        from psychopy import prefs
        dev = prefs.hardware.get("audioDevice", None)
        if isinstance(dev, str) and dev:
            return dev
        # PsychoPy sometimes stores as a list
        if isinstance(dev, (list, tuple)) and dev:
            return dev[0]
        return None
    except Exception:
        return None


def find_and_configure(
    substrings: Optional[Iterable[str]] = None,
    verbose: bool = False,
) -> Optional[str]:
    """
    Convenience wrapper: find an output device by substring match and
    configure PsychoPy to use it.

    Returns the device name that was set, or None if no match.
    """
    if substrings is None:
        substrings = _get_default_substrings()

    name = find_audio_device(substrings=substrings)

    if name is not None:
        configure_psychopy_device(name)
        if verbose:
            print(f"[audio_devices] Selected output device: {name!r}")
    else:
        if verbose:
            print(
                f"[audio_devices] No device matched substrings="
                f"{tuple(substrings)!r}; PsychoPy will use system default. "
                f"Edit config/DEFAULTS.py -> 'audio_device_substrings' "
                f"to adjust."
            )

    return name


if __name__ == "__main__":
    # Quick CLI for inspecting devices on the current machine.
    print("Output-capable devices visible to sounddevice/PortAudio:")
    devs = list_output_devices()
    if not devs:
        print("  (none -- sounddevice may not be installed)")
    for d in devs:
        print(f"  [{d['index']:>2}] {d['name']!r}  "
              f"(out channels: {d['max_output_channels']})")

    print()
    subs = _get_default_substrings()
    print(f"Default substrings: {subs!r}")
    match = find_audio_device()
    print(f"Match: {match!r}")
