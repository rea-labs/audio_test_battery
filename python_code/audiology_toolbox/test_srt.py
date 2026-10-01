"""
Test script for SRT (Speech Recognition Threshold) paradigm.

SRT operates in dB SPL via a CalibrationManager. Loads the active
calibration profile up front and aborts gracefully if SPL data is
unpopulated (clinical paradigm -- no meaningful uncalibrated mode).

Procedure
---------
- One word is played per trial (diotic by default; pan=0.0).
- The participant repeats the word aloud.
- The EXAMINER presses 1 (correct) or 0 (incorrect) on the keyboard.
- Level adapts: correct -> quieter, incorrect -> louder.
- Large steps (+/- 10 dB) before first reversal, fine steps (+/- 2 dB) after.
- Threshold estimated from the last reversals (base-class default).

Setup
-----
1. Point WAV_DIR to the folder containing your word WAV files.
2. Run:
       python test_srt.py
"""

from pathlib import Path

from paradigms.paradigm_srt import ParadigmSRT
from utils.varspec import VarSpec
from utils.paradigm_setup_dialog import ParadigmSetupDialog
from utils.calibration import CalibrationManager

# Path to calibration config (relative to test script working directory).
# TODO: replace with proper package-relative resolution once the toolbox
# is structured as a Python package.
CALIBRATION_CONFIG_PATH = Path(__file__).resolve().parent / "../../calibration_data/calibration_config.json"

# Path to folder of word WAV files.
# TODO: replace with proper package-relative resolution.
WAV_DIR = "wav_files/freiburger_einsilber/no_noise_floor"


def main():
    print("=" * 70)
    print(" SPEECH RECOGNITION THRESHOLD (SRT)")
    print("=" * 70)
    print()
    print(" NOTE: This test is EXAMINER-RATED.")
    print("       The participant repeats each word aloud.")
    print("       The examiner presses 1 (correct) or 0 (incorrect).")
    print()

    # ------------------------------------------------------------------
    # Calibration pre-flight
    # ------------------------------------------------------------------
    try:
        calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)
    except Exception as e:
        print(f"\n!!! Failed to load calibration from {CALIBRATION_CONFIG_PATH}")
        print(f"!!! {type(e).__name__}: {e}")
        print("!!! SRT requires a populated calibration config. Aborting.")
        return

    if not calibration.spl_calibrated:
        print(f"\n!!! Calibration profile '{calibration.active_profile}' has no")
        print("!!! SPL data populated. Run the SPL calibration procedure first.")
        print("!!! Aborting.")
        return

    if not calibration.fir_calibrated:
        print(f"\n!!! Warning: profile '{calibration.active_profile}' has no FIR")
        print("!!! inverse filters loaded. Continuing without frequency-response")
        print("!!! correction (SPL conversion still active).")

    print()
    calibration.summary()

    # ------------------------------------------------------------------
    # Paradigm parameters (all levels in dB SPL)
    # ------------------------------------------------------------------
    params = {
        "inner": VarSpec(
            name="trial_amp",
            label="Speech Level",
            units="dB SPL",
            data={
                'start': 50.0,                # dB SPL (well above SRT threshold)
                'step_down_initial': -10,     # large step before first reversal
                'step_down_final': -2,        # fine step after first reversal
                'step_up_initial': 10,
                'step_up_final': 2,
                'min': 0.0,                   # dB SPL floor
                'max': 90.0,                  # dB SPL paradigm soft cap (calibration
                                              # max_spl=105 is the hard ceiling)
            }
        ),
        # Diotic: pan held at 0.0. (Could be expanded to [-1.0, 1.0] for monaural.)
        "outer_1": VarSpec(name="pan", data=[0.0], label="Pan"),
    }

    # ------------------------------------------------------------------
    # Setup dialog
    # ------------------------------------------------------------------
    # Set calibration on the dialog's paradigm instance so demo trials
    # (triggered from the "Play Demo" button) don't crash on the
    # CalibrationManager guard in prepare_trial().
    dialog_paradigm = ParadigmSRT(params, wav_dir=WAV_DIR, verbose=True)
    dialog_paradigm.set_calibration(calibration)
    dialog = ParadigmSetupDialog(paradigm_name="SRT", params=params,
                                 paradigm=dialog_paradigm)
    participant_id = dialog.show()

    if participant_id is None:
        print("\nSetup cancelled. Exiting.")
        return

    # The setup dialog owns the calibration for this run -- the operator may
    # have selected a different headphone profile from its dropdown. Re-read
    # it here so the run uses the chosen profile, not the startup default.
    calibration = dialog.selected_calibration

    print(f"\nParticipant : {participant_id}")
    print(f"Word folder : {WAV_DIR}")
    print(f"Presentation: Diotic (both ears simultaneously)")
    print()

    srt = ParadigmSRT(params, wav_dir=WAV_DIR, verbose=True,
                      participant_id=participant_id)
    srt.set_calibration(calibration)

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
