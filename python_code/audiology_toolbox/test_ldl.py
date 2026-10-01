"""
Test script for LDL (Loudness Discomfort Level) paradigm.

Run order: No prior paradigm results needed.

Frequencies : 500, 1000, 2000, 4000, 8000 Hz (per PROLACTIN plan)
Ears        : Left and Right (pan = -1.0 / +1.0)

LDL operates in dB SPL via a CalibrationManager. The level increases every
trial until the participant reports "Uncomfortable", at which point the run
ends and the LDL is recorded for that frequency / ear combination.

Step size depends on the rating (team decision 2026-07-17, open issue M9/T4):
  - "Comfortable"  -> +5 dB (step_up_initial, coarse)
  - "Loud"         -> +3 dB (step_up_final, fine)

The first "Loud" latches the fine step for the rest of the config; a later
"Comfortable" does not restore +5 dB. See paradigm_ldl.py module docstring.
"""

from pathlib import Path

from paradigms.paradigm_ldl import ParadigmLDL
from utils.varspec import VarSpec
from utils.paradigm_setup_dialog import ParadigmSetupDialog
from utils.calibration import CalibrationManager

# Path to calibration config (relative to test script working directory).
# TODO: Move calibration_data/ inside audiology_toolbox/ and update this path.
CALIBRATION_CONFIG_PATH = Path(__file__).resolve().parent / "../../calibration_data/calibration_config.json"

LDL_FREQUENCIES = [500, 1000, 2000, 4000, 8000]

params = {
    "inner": VarSpec(
        name="trial_amp",
        label="Tone Level",
        units="dB SPL",
        data={
            'start':             60.0,    # dB SPL (comfortable starting point)
                                          # NOTE: LDL selects the step below on the
                                          # first "Loud" rating, not on reversal count
                                          # (its one reversal ends the config).
            'step_up_initial':    5.0,    # dB per trial while "Comfortable" (coarse)
            'step_up_final':      3.0,    # dB per trial from first "Loud" on (fine)
            'step_down_initial': -3.0,    # Never triggered in normal use
            'step_down_final':   -3.0,
            'min':                30.0,   # dB SPL floor
            'max':               105.0,   # dB SPL paradigm soft cap
                                          # (equal to calibration max_spl=105 hard ceiling)
        }
    ),
    "outer_1": VarSpec(name="fc",  data=LDL_FREQUENCIES, label="Frequency", units="Hz"),
    "outer_2": VarSpec(name="pan", data=[-1.0, 1.0], label="Pan"),   # Left then Right
}


def main():
    print("=" * 70)
    print(" LDL - LOUDNESS DISCOMFORT LEVEL")
    print(" Level ascends until 'uncomfortable': +5 dB while 'comfortable',")
    print(" +3 dB from the first 'loud' onwards")
    print(f" Frequencies : {LDL_FREQUENCIES} Hz  |  Ears: L + R")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Calibration pre-flight
    # ------------------------------------------------------------------
    try:
        calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)
    except Exception as e:
        print(f"\n!!! Failed to load calibration from {CALIBRATION_CONFIG_PATH}")
        print(f"!!! {type(e).__name__}: {e}")
        print("!!! LDL requires a populated calibration config. Aborting.")
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
    # Setup dialog
    # ------------------------------------------------------------------
    # Set calibration on the dialog's paradigm instance so demo trials
    # don't crash on the CalibrationManager guard in prepare_trial().
    dialog_paradigm = ParadigmLDL(params, verbose=True)
    dialog_paradigm.set_calibration(calibration)
    dialog = ParadigmSetupDialog(paradigm_name="LDL", params=params,
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
    print(f"Total runs  : {len(LDL_FREQUENCIES) * 2}  "
          f"({len(LDL_FREQUENCIES)} freq x 2 ears)")

    ldl = ParadigmLDL(params, verbose=True, participant_id=participant_id)
    ldl.set_calibration(calibration)

    try:
        ldl.main()
        print(f"\n>>> Results saved: {participant_id}_LDL_*.csv")
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
    except Exception as e:
        print(f"\n!!! Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
