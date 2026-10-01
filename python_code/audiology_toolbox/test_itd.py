"""
Test script for ITD (Interaural Time Difference) paradigm.

ITD operates in dB SPL via a CalibrationManager (reference level only;
the adaptive ITD remains in milliseconds). Loads the active calibration
profile up front and aborts gracefully if SPL data is unpopulated.
"""

from pathlib import Path

from paradigms.paradigm_itd import ParadigmITD
from utils.varspec import VarSpec
from utils.paradigm_setup_dialog import ParadigmSetupDialog
from utils.calibration import CalibrationManager

# Path to calibration config (relative to test script working directory).
# TODO: Move calibration_data/ inside audiology_toolbox/ and update this path.
CALIBRATION_CONFIG_PATH = Path(__file__).resolve().parent / "../../calibration_data/calibration_config.json"


def main():
    print("=" * 70)
    print(" INTERAURAL TIME DIFFERENCE (ITD)")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Calibration pre-flight
    # ------------------------------------------------------------------
    try:
        calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)
    except Exception as e:
        print(f"\n!!! Failed to load calibration from {CALIBRATION_CONFIG_PATH}")
        print(f"!!! {type(e).__name__}: {e}")
        print("!!! ITD requires a populated calibration config. Aborting.")
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
    # Paradigm parameters (ref_level in dB SPL; itd_ms in milliseconds)
    # ------------------------------------------------------------------
    params = {
        "inner": VarSpec(
            name="itd_ms",
            label="ITD",
            units="ms",
            data={
                'start': 50.0,
                'step_down_initial': 0.5,
                'step_down_final': 0.7,
                'step_up_initial': 2.0,
                'step_up_final': 1.4,
                'min': 0.01,
                'max': 100.0
            }
        ),
        "outer_1": VarSpec(name="signal_type", data=["sin"], label="Signal Type"),
        "outer_2": VarSpec(name="fc", data=[1000], label="Frequency", units="Hz"),  # Hz; only used for tone trials
        "outer_3": VarSpec(name="ref_level_db", data=[60.0], label="Reference Level", units="dB SPL"),  # dB SPL
    }

    # ------------------------------------------------------------------
    # Setup dialog
    # ------------------------------------------------------------------
    # Set calibration on the dialog's paradigm instance so demo trials
    # don't crash on the CalibrationManager guard in prepare_trial().
    dialog_paradigm = ParadigmITD(params, verbose=True)
    dialog_paradigm.set_calibration(calibration)
    dialog = ParadigmSetupDialog(paradigm_name="ITD", params=params,
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

    itd = ParadigmITD(params, verbose=True, participant_id=participant_id)
    itd.set_calibration(calibration)

    try:
        itd.main()
        print(f"\n>>> Results saved: {participant_id}_ITD_*.csv")
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
    except Exception as e:
        print(f"\n!!! Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
