"""
Test script for SRT (Speech Recognition Threshold) paradigm
============================================================
Freiburg Einsilber — quiet presentation, single-word adaptive

Procedure
---------
- One word is played per trial to one ear (left, then right).
- The participant repeats the word aloud.
- The EXAMINER presses 1 (correct) or 0 (incorrect) on the keyboard.
- Amplitude adapts: correct → quieter, incorrect → louder.
- Large steps (±10 dB) before first reversal, fine steps (±2 dB) after.
- Threshold estimated from the last 6 reversals (same as PTA).

Setup
-----
1. Point WAV_DIR to the folder containing your word WAV files.
   Files must be *.wav (mono or stereo, any sample rate).
2. Run:
       python test_srt.py
"""

from pathlib import Path
from python_code.audiology_toolbox.paradigms.paradigm_srt_DEPRECATED import ParadigmSRT
from utils.varspec import VarSpec
from utils.paradigm_setup_dialog import ParadigmSetupDialog

# =============================================================================
# CONFIGURE THIS — path to folder of word WAV files
# =============================================================================
def find_package_dir(start: Path, target_name: str) -> Path:
    for parent in [start.resolve(), *start.resolve().parents]:
        if parent.name == target_name:
            return parent
    raise RuntimeError(f"{target_name} not found in parent hierarchy")

PACKAGE_DIR = find_package_dir(Path(__file__), "audiology_toolbox")

WAV_DIR = PACKAGE_DIR / "wav_files" / "freiburger_einsilber" / "no_noise_floor"

# WAV_DIR = Path(r"D:\PROLACTIN\audiometry\fire_audiometry_battery\python_code\audiology_toolbox\freiburger_einsilber\no_noise_floor")
#              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#              Change to wherever your word WAV files live.
#              Each *.wav file = one word (e.g. "Hut.wav", "Brot.wav", ...)

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print(" SPEECH RECOGNITION THRESHOLD (SRT)")
    print(" Freiburg Einsilber — quiet, diotic (both ears), no word repeats")
    print("=" * 70)
    print()
    print(" NOTE: This test is EXAMINER-RATED.")
    print("       The participant repeats each word aloud.")
    print("       The examiner presses 1 (correct) or 0 (incorrect).")
    print()

    params = {
        "inner": VarSpec(
            name="trial_amp",
            data={
                'start':             0.0005,       # Starting amplitude (~-6 dB FS)
                'step_down_initial': -10,        # Large step before first reversal
                'step_down_final':   -2,         # Fine step after first reversal
                'step_up_initial':    10,
                'step_up_final':      2,
                'min':               0.000001,   # Floor (well below any threshold)
                'max':               1.0,        # Ceiling (0 dB FS)
            }
        ),
        # Diotic: words played to both ears simultaneously (pan stays at 0.0)
    }

    # Show setup dialog (participant ID, optional demo)
    dialog = ParadigmSetupDialog(
        paradigm_name="SRT",
        params=params,
        paradigm=ParadigmSRT(params, wav_dir=WAV_DIR, verbose=True)
    )
    participant_id = dialog.show()

    if participant_id is None:
        print("\nSetup cancelled. Exiting.")
        return

    print(f"\nParticipant : {participant_id}")
    print(f"Word folder : {WAV_DIR}")
    print(f"Presentation: Diotic (both ears simultaneously)")
    print()

    srt = ParadigmSRT(
        params,
        wav_dir=WAV_DIR,
        verbose=True,
        participant_id=participant_id
    )

    try:
        srt.main()
        print(f"\n>>> Results saved: {participant_id}_SRT_*.csv")
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
    except Exception as e:
        print(f"\n!!! Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
