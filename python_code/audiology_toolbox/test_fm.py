"""
Test script for FM (Frequency Modulation) paradigm.

FM operates in dB SPL via a CalibrationManager (carrier level only;
modulation index remains in percent). Loads the active calibration
profile up front and aborts gracefully if SPL data is unpopulated.
"""

from pathlib import Path

from paradigms.paradigm_fm import ParadigmFM
from utils.varspec import VarSpec
from utils.paradigm_setup_dialog import ParadigmSetupDialog
from utils.calibration import CalibrationManager
from utils.standard_frequencies import AUDIOMETRIC_FREQS

# Path to calibration config (relative to test script working directory).
# TODO: Move calibration_data/ inside audiology_toolbox/ and update this path.
CALIBRATION_CONFIG_PATH = Path(__file__).resolve().parent / "../../calibration_data/calibration_config.json"


def main():
    print("=" * 70)
    print(" FREQUENCY MODULATION (FM) DETECTION")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Calibration pre-flight
    # ------------------------------------------------------------------
    try:
        calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)
    except Exception as e:
        print(f"\n!!! Failed to load calibration from {CALIBRATION_CONFIG_PATH}")
        print(f"!!! {type(e).__name__}: {e}")
        print("!!! FM requires a populated calibration config. Aborting.")
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
    # Paradigm parameters (carrier level in dB SPL; mod_ind in percent)
    # ------------------------------------------------------------------
    params = {
        "inner": VarSpec(
            name="mod_ind",
            label="Modulation Index",
            units="%",
            data={
                'start': 8.0,
                'step_down_initial': 0.5,
                'step_down_final': 0.7,
                'step_up_initial': 2.0,
                'step_up_final': 1.4,
                'min': 0.1,
                'max': 20.0,
                'randomize_factor': 1.2
            }
        ),
        "outer_1": VarSpec(name="fc", data=AUDIOMETRIC_FREQS, label="Frequency", units="Hz"),
        "outer_2": VarSpec(name="fm", data=[4], label="Modulation Rate", units="Hz"),
        # Per-fc carrier level (dB SPL), co-indexed with the fc outer var above
        # (level[i] pairs with fc[i]); NOT an outer var (it zips with fc, it is
        # not crossed). Editable per-freq in the setup dialog; defaults to 60 dB
        # for every fc.
        "target_level": VarSpec(name="tone_level_db",
                                data=[60.0] * len(AUDIOMETRIC_FREQS),
                                label="Tone Level", units="dB SPL"),
    }

    # ------------------------------------------------------------------
    # Setup dialog
    # ------------------------------------------------------------------
    # Set calibration on the dialog's paradigm instance so demo trials
    # don't crash on the CalibrationManager guard in prepare_trial().
    dialog_paradigm = ParadigmFM(params, verbose=True)
    dialog_paradigm.set_calibration(calibration)
    dialog = ParadigmSetupDialog(paradigm_name="FM", params=params,
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

    fm = ParadigmFM(params, verbose=True, participant_id=participant_id)
    fm.set_calibration(calibration)

    try:
        fm.main()
        print(f"\n>>> Results saved: {participant_id}_FM_*.csv")
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
    except Exception as e:
        print(f"\n!!! Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
