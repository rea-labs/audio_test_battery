"""
Test script for PTA (Pure Tone Audiogram) paradigm.

PTA now operates in dB SPL via a CalibrationManager. Loads the active
calibration profile up front and aborts gracefully if SPL data is
unpopulated.
"""

from pathlib import Path

from paradigms.paradigm_pta import ParadigmPTA
from utils.varspec import VarSpec
from utils.paradigm_setup_dialog import ParadigmSetupDialog
from utils.calibration import CalibrationManager
from utils.standard_frequencies import AUDIOMETRIC_FREQS

# Path to calibration config (relative to test script working directory).
# TODO: Move calibration_data/ inside audiology_toolbox/ and update this path.
CALIBRATION_CONFIG_PATH = Path(__file__).resolve().parent / "../../calibration_data/calibration_config.json"


def main():
    print("=" * 70)
    print(" PURE TONE AUDIOGRAM (PTA)")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Calibration pre-flight
    # ------------------------------------------------------------------
    try:
        calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)
    except Exception as e:
        print(f"\n!!! Failed to load calibration from {CALIBRATION_CONFIG_PATH}")
        print(f"!!! {type(e).__name__}: {e}")
        print("!!! PTA requires a populated calibration config. Aborting.")
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
            label="Tone Level",
            units="dB SPL",
            data={
                'start': 60.0,           # dB SPL (comfortable conversational)
                'step_down_initial': -10,
                'step_down_final': -2,
                'step_up_initial': 10,
                'step_up_final': 2,
                'min': -10.0,            # dB SPL floor (negative is physical;
                                         # 0 dB SPL is normal-hearing threshold)
                'max': 90.0,             # dB SPL paradigm soft cap (calibration
                                         # max_spl=105 is the hard ceiling)
            }
        ),
        "outer_1": VarSpec(name="fc", data=AUDIOMETRIC_FREQS, label="Frequency", units="Hz"),
        "outer_2": VarSpec(name="pan", data=[-1.0, 1.0], label="Pan"),
        # "outer_2": VarSpec(name="trial_dur", data=[0.5]),
        # "outer_3": VarSpec(name="pan", data=[-1.0, 1.0])
    }

    # ------------------------------------------------------------------
    # Setup dialog
    # ------------------------------------------------------------------
    # Set calibration on the dialog's paradigm instance so demo trials
    # (triggered from the "Play Demo" button) don't crash on the
    # CalibrationManager guard in prepare_trial().
    dialog_paradigm = ParadigmPTA(params, verbose=True)
    dialog_paradigm.set_calibration(calibration)
    dialog = ParadigmSetupDialog(paradigm_name="PTA", params=params,
                                 paradigm=dialog_paradigm)
    participant_id = dialog.show()

    if participant_id is None:
        print("\nSetup cancelled. Exiting.")
        return

    # The setup dialog owns the calibration for this run -- the operator may
    # have selected a different headphone profile from its dropdown. Re-read
    # it here so the run uses the chosen profile, not the startup default.
    calibration = dialog.selected_calibration

    print(f"\nParticipant: {participant_id}")
    print(f"Frequencies: {AUDIOMETRIC_FREQS} Hz")

    pta = ParadigmPTA(params, verbose=True, participant_id=participant_id)
    pta.set_calibration(calibration)

    try:
        pta.main()
        print(f"\n>>> Results saved: {participant_id}_PTA_*.csv")
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
    except Exception as e:
        print(f"\n!!! Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
