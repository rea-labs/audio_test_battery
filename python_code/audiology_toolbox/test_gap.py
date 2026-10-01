"""
Test script for GAP (Gap Detection) paradigm.

GAP operates with calibrated dB SPL noise level via a CalibrationManager.
Adaptive parameter (gap_duration) is in seconds (logged in ms).
"""

from pathlib import Path

from paradigms.paradigm_gap import ParadigmGAP
from utils.varspec import VarSpec
from utils.paradigm_setup_dialog import ParadigmSetupDialog
from utils.calibration import CalibrationManager

# Path to calibration config (relative to test script working directory).
# TODO: Move calibration_data/ inside audiology_toolbox/ and update this path.
CALIBRATION_CONFIG_PATH = Path(__file__).resolve().parent / "../../calibration_data/calibration_config.json"


def main():
    print("=" * 70)
    print(" GAP DETECTION - Temporal Resolution")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Calibration pre-flight
    # ------------------------------------------------------------------
    try:
        calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)
    except Exception as e:
        print(f"\n!!! Failed to load calibration from {CALIBRATION_CONFIG_PATH}")
        print(f"!!! {type(e).__name__}: {e}")
        print("!!! GAP requires a populated calibration config. Aborting.")
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
    # Paradigm parameters (noise level in dB SPL)
    # ------------------------------------------------------------------
    params = {
        "inner": VarSpec(
            name="gap_duration",
            label="Gap Duration",
            units="s",
            data={
                'start': 0.010,
                'step_down_initial': -0.005,
                'step_down_final': -0.001,
                'step_up_initial': 0.005,
                'step_up_final': 0.001,
                'min': 0.0001,
                'max': 0.020
            }
        ),
        "outer_1": VarSpec(name="noise_level_db", data=[65.0], label="Noise Level", units="dB SPL"),  # dB SPL
    }

    # ------------------------------------------------------------------
    # Setup dialog
    # ------------------------------------------------------------------
    # Set calibration on the dialog's paradigm instance so demo trials
    # don't crash on the CalibrationManager guard in prepare_trial().
    dialog_paradigm = ParadigmGAP(params, verbose=True)
    dialog_paradigm.set_calibration(calibration)
    dialog = ParadigmSetupDialog(paradigm_name="GAP", params=params,
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

    gap = ParadigmGAP(params, verbose=True, participant_id=participant_id)
    gap.set_calibration(calibration)

    try:
        gap.main()
        print(f"\n>>> Results saved: {participant_id}_GAP_*.csv")
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
    except Exception as e:
        print(f"\n!!! Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
