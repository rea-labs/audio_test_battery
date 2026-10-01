"""
Utilities for loading and accessing previous test results.

Includes GUI for file selection when multiple results exist.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict
import tkinter as tk
from tkinter import messagebox, filedialog
from trial_player import TrialPlayer
import numpy as np


class ResultLoader:
    """Load and access previous paradigm results."""

    def __init__(self, data_dir: str = None):
        """
        Args:
            data_dir: Directory containing CSV results.
                     Default: test_data/ relative to cwd(),
                     matching write_data_to_disk() in adaptive_paradigm.py.
        """
        if data_dir is None:
            self.data_dir = Path.cwd() / "test_data"
        else:
            self.data_dir = Path(data_dir)

    def find_results(self,
                     participant_id: str,
                     paradigm: str = None) -> List[Path]:
        """Find result CSVs for participant, newest first."""
        if paradigm:
            pattern = participant_id + "_" + paradigm + "_*.csv"
        else:
            pattern = participant_id + "_*_*.csv"
        matches = list(self.data_dir.glob(pattern))
        matches.sort(reverse=True)
        return matches

    def select_file_gui(self,
                        participant_id: str,
                        paradigm: str,
                        auto_select_recent: bool = True) -> "Optional[Path]":
        """Show GUI for file selection. Returns selected path or None."""
        files = self.find_results(participant_id, paradigm)

        if not files:
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(
                "No Results Found",
                "No " + paradigm + " results found for participant " + participant_id
            )
            root.destroy()
            return None

        most_recent = files[0]
        root = tk.Tk()
        root.title("Select " + paradigm + " Results File")
        root.geometry("600x300")
        selected_file = [None]

        info_frame = tk.Frame(root, padx=20, pady=20)
        info_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            info_frame,
            text="Loading " + paradigm + " results for " + participant_id,
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        tk.Label(info_frame, text="Most recent file found:", font=("Arial", 10)).pack()
        tk.Label(info_frame, text=most_recent.name, font=("Arial", 12, "bold"), fg="blue").pack(pady=5)

        if len(files) > 1:
            tk.Label(info_frame,
                     text=str(len(files)-1) + " other file(s) also available:",
                     font=("Arial", 9), fg="gray").pack()
            for f in files[1:4]:
                tk.Label(info_frame, text="  * " + f.name,
                         font=("Arial", 8), fg="gray").pack()
            if len(files) > 4:
                tk.Label(info_frame, text="  ... and " + str(len(files)-4) + " more",
                         font=("Arial", 8), fg="gray").pack()

        button_frame = tk.Frame(root, padx=20, pady=20)
        button_frame.pack()

        def accept():
            selected_file[0] = most_recent
            root.destroy()

        def select_other():
            filepath = filedialog.askopenfilename(
                title="Select " + paradigm + " file for " + participant_id,
                initialdir=self.data_dir,
                filetypes=[("CSV files", "*.csv"), ("All Files", "*.*")]
            )
            if filepath:
                selected_file[0] = Path(filepath)
            root.destroy()

        def cancel():
            selected_file[0] = None
            root.destroy()

        tk.Button(button_frame, text="Accept (Most Recent)", command=accept,
                  font=("Arial", 12), bg="lightgreen", width=25, height=2
                  ).pack(side=tk.LEFT, padx=10)

        if len(files) > 1:
            tk.Button(button_frame, text="Browse Other Files...", command=select_other,
                      font=("Arial", 12), width=20, height=2).pack(side=tk.LEFT, padx=10)

        tk.Button(button_frame, text="Cancel", command=cancel,
                  font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=10)

        root.bind("<Return>", lambda e: accept())
        root.bind("<Escape>", lambda e: cancel())
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry("+" + str(x) + "+" + str(y))
        root.mainloop()
        return selected_file[0]

    def load_results(self,
                     participant_id: str,
                     paradigm: str,
                     show_gui: bool = True) -> "Optional[pd.DataFrame]":
        """Load results CSV. Returns DataFrame or None."""
        if show_gui:
            filepath = self.select_file_gui(participant_id, paradigm)
        else:
            files = self.find_results(participant_id, paradigm)
            filepath = files[0] if files else None
        if filepath is None:
            return None
        print("Loading: " + filepath.name)
        # comment="#" skips metadata header lines (PROLACTIN >= 0.5.0).
        # Legacy CSVs have no `#` lines and parse identically.
        return pd.read_csv(filepath, comment="#")

    def get_metadata(self, filepath) -> dict:
        """
        Read the `#`-prefixed metadata header from a PROLACTIN CSV.

        Returns a dict of `{key: value_str}` (all values as strings;
        callers are responsible for parsing). Returns an empty dict for
        legacy CSVs without a header. Stops scanning at the first
        non-`#` line.
        """
        from pathlib import Path
        path = Path(filepath)
        md = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\r\n")
                    if not line.startswith("#"):
                        break
                    body = line.lstrip("#").strip()
                    if ":" not in body:
                        continue
                    key, value = body.split(":", 1)
                    md[key.strip()] = value.strip()
        except OSError:
            pass
        return md

    def get_pta_thresholds(self,
                           participant_id: str,
                           frequencies: List[int] = None,
                           show_gui: bool = True,
                           allow_manual_entry: bool = True) -> "Optional[Dict[int, float]]":
        """
        Extract PTA thresholds in dB for specified frequencies.
        If no file found and allow_manual_entry=True, shows manual entry dialog.
        Returns dict {freq: threshold_dB} or None.
        """
        if frequencies is None:
            frequencies = [250, 500, 1000, 2000, 4000, 8000]

        pta_data = self.load_results(participant_id, "PTA", show_gui=show_gui)

        if pta_data is None:
            if allow_manual_entry:
                return self._manual_threshold_entry(participant_id, frequencies)
            return None

        thresholds = {}
        for freq in frequencies:
            freq_data = pta_data[pta_data["fc"] == freq]
            if len(freq_data) == 0:
                continue
            if "threshold_dB" in freq_data.columns:
                threshold_db = freq_data["threshold_dB"].iloc[-1]
                if -20 <= threshold_db <= 100:
                    thresholds[freq] = threshold_db
                else:
                    print("WARNING: Unusual threshold at " + str(freq) + " Hz: " + str(round(threshold_db, 1)) + " dB")
        return thresholds

    def _manual_threshold_entry(self,
                                participant_id: str,
                                frequencies: List[int]) -> "Optional[Dict[int, float]]":
        """Ask user whether to enter thresholds manually, then show dialog."""
        root = tk.Tk()
        root.withdraw()
        freq_str = ", ".join(str(f) for f in frequencies)
        msg = ("No PTA results found for participant " + participant_id + ".\n\n"
               "Would you like to enter thresholds manually?\n\n"
               "Frequencies: " + freq_str + " Hz")
        response = messagebox.askyesno("No PTA Results Found", msg)
        root.destroy()
        if not response:
            return None
        return self._threshold_entry_dialog(participant_id, frequencies)

    def _threshold_entry_dialog(self,
                                participant_id: str,
                                frequencies: List[int]) -> "Optional[Dict[int, float]]":
        """GUI form for manually entering one threshold per frequency."""
        root = tk.Tk()
        root.title("Enter PTA Thresholds - " + participant_id)
        root.geometry("500x450")
        threshold_entries = {}
        thresholds = {}
        cancelled = [False]

        tk.Label(root, text="Enter PTA Thresholds for " + participant_id,
                 font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(root, text="Enter threshold in dB for each frequency:",
                 font=("Arial", 10)).pack(pady=5)
        tk.Label(root, text="(Typical range: 0-80 dB)",
                 font=("Arial", 9), fg="gray").pack()

        frame = tk.Frame(root)
        frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        for i, freq in enumerate(frequencies):
            row = tk.Frame(frame)
            row.pack(fill=tk.X, pady=5)
            tk.Label(row, text=str(freq) + " Hz:", font=("Arial", 12),
                     width=10, anchor="e").pack(side=tk.LEFT, padx=5)
            entry = tk.Entry(row, font=("Arial", 12), width=15)
            entry.pack(side=tk.LEFT, padx=5)
            tk.Label(row, text="dB", font=("Arial", 10)).pack(side=tk.LEFT)
            threshold_entries[freq] = entry
            if i == 0:
                entry.focus()

        def validate_and_submit():
            for freq, entry in threshold_entries.items():
                value = entry.get().strip()
                if not value:
                    messagebox.showerror("Missing Value",
                        "Please enter a threshold for " + str(freq) + " Hz")
                    entry.focus()
                    return
                try:
                    db = float(value)
                    if db < -20 or db > 120:
                        msg = ("Threshold at " + str(freq) + " Hz = " + str(db)
                               + " dB seems unusual.\nTypical range: 0-80 dB\n\nAccept anyway?")
                        if not messagebox.askyesno("Unusual Value", msg):
                            entry.focus()
                            return
                    thresholds[freq] = db
                except ValueError:
                    messagebox.showerror("Invalid Input",
                        " + " + value + " + " + " is not a valid number")
                    entry.focus()
                    return
            root.destroy()

        def cancel():
            cancelled[0] = True
            root.destroy()

        btn = tk.Frame(root)
        btn.pack(pady=20)
        tk.Button(btn, text="Submit", command=validate_and_submit,
                  font=("Arial", 12), bg="lightgreen", width=15, height=2
                  ).pack(side=tk.LEFT, padx=10)
        tk.Button(btn, text="Cancel", command=cancel,
                  font=("Arial", 12), width=15, height=2).pack(side=tk.LEFT, padx=10)

        def on_return(event):
            if root.focus_get() == threshold_entries[frequencies[-1]]:
                validate_and_submit()

        root.bind("<Return>", on_return)
        root.bind("<Escape>", lambda e: cancel())
        root.update_idletasks()
        x = (root.winfo_screenwidth() - root.winfo_width()) // 2
        y = (root.winfo_screenheight() - root.winfo_height()) // 2
        root.geometry("+" + str(x) + "+" + str(y))
        root.mainloop()

        if cancelled[0]:
            return None
        for freq, thresh in sorted(thresholds.items()):
            print("  " + str(freq) + " Hz: " + str(round(thresh, 1)) + " dB")
        return thresholds

    def get_ifmc_probe_level(self,
                             participant_id: str,
                             probe_freq: int,
                             db_above_threshold: float = 10.0,
                             show_gui: bool = True,
                             max_amplitude: float = 0.7,
                             calibration=None) -> "Optional[float]":
        """
        Calculate safe IFMC probe amplitude from PTA threshold.
        Adds db_above_threshold to PTA threshold, converts to amplitude,
        and enforces max_amplitude safety ceiling.

        When `calibration` (CalibrationManager) is provided, treats the PTA
        threshold as dB SPL and uses cm.spl_to_amplitude (diotic average)
        for the conversion. When None, uses legacy db2amp (treats threshold
        as dB FS) and emits a DeprecationWarning. Pass calibration whenever
        the source PTA CSV was recorded with calibration active.
        """
        thresholds = self.get_pta_thresholds(
            participant_id, [probe_freq], show_gui=show_gui
        )
        if thresholds is None or probe_freq not in thresholds:
            return None
        threshold_db = thresholds[probe_freq]
        probe_db = threshold_db + db_above_threshold
        if calibration is not None:
            amp_L, amp_R = calibration.spl_to_amplitude(probe_db)
            probe_amp = (amp_L + amp_R) / 2.0
            unit_label = "dB SPL"
        else:
            import warnings
            warnings.warn(
                "get_ifmc_probe_level called without a CalibrationManager; "
                "treating threshold as dB FS via legacy db2amp. Pass "
                "calibration=cm to use dB SPL math.",
                DeprecationWarning, stacklevel=2,
            )
            probe_amp = TrialPlayer.db2amp(probe_db)
            unit_label = "dB"
        if probe_amp > max_amplitude:
            print("WARNING: Clamping probe amplitude from " + str(round(probe_amp, 3))
                  + " to " + str(max_amplitude))
            probe_amp = max_amplitude
        if probe_amp > 1.0:
            print("CRITICAL: probe_amp > 1.0, clamping to " + str(max_amplitude))
            probe_amp = max_amplitude
        print("  " + str(probe_freq) + " Hz: " + str(round(threshold_db, 1))
              + " " + unit_label + " threshold -> " + str(round(probe_db, 1))
              + " " + unit_label + " probe = " + str(round(probe_amp, 4)) + " amplitude")
        return probe_amp

    def get_tmc_probe_level(self,
                            participant_id: str,
                            probe_freq: int,
                            db_above_threshold: float = 10.0,
                            show_gui: bool = True,
                            max_amplitude: float = 0.7,
                            calibration=None) -> "Optional[float]":
        """
        Calculate safe TMC probe amplitude from standard PTA threshold.

        TMC probes are set at 10 dB SL above the (standard) PTA threshold
        at the same frequency. This uses the same PTA CSV as IFMC - there
        is no separate 16 ms threshold measurement in our battery.

        Args:
            participant_id:     Participant ID string
            probe_freq:         Probe frequency in Hz
            db_above_threshold: dB SL above PTA threshold (default 10)
            show_gui:           Show file-selection GUI
            max_amplitude:      Safety ceiling (default 0.7)
            calibration:        Optional CalibrationManager. When provided,
                                threshold is treated as dB SPL and converted
                                via spl_to_amplitude (diotic average). When
                                None, falls back to legacy db2amp with a
                                DeprecationWarning.

        Returns:
            Probe amplitude (0-1), or None if threshold unavailable
        """
        # Re-use get_pta_thresholds - same PTA file, same column
        thresholds = self.get_pta_thresholds(
            participant_id, [probe_freq], show_gui=show_gui
        )
        if thresholds is None or probe_freq not in thresholds:
            return None

        threshold_db = thresholds[probe_freq]
        probe_db     = threshold_db + db_above_threshold
        if calibration is not None:
            amp_L, amp_R = calibration.spl_to_amplitude(probe_db)
            probe_amp = (amp_L + amp_R) / 2.0
            unit_label = "dB SPL"
        else:
            import warnings
            warnings.warn(
                "get_tmc_probe_level called without a CalibrationManager; "
                "treating threshold as dB FS via legacy db2amp. Pass "
                "calibration=cm to use dB SPL math.",
                DeprecationWarning, stacklevel=2,
            )
            probe_amp = TrialPlayer.db2amp(probe_db)
            unit_label = "dB"

        if probe_amp > max_amplitude:
            print("WARNING: Clamping TMC probe amplitude from "
                  + str(round(probe_amp, 3)) + " to " + str(max_amplitude))
            probe_amp = max_amplitude

        if probe_amp > 1.0:
            print("CRITICAL: TMC probe_amp > 1.0, clamping to " + str(max_amplitude))
            probe_amp = max_amplitude

        print("  TMC " + str(probe_freq) + " Hz: " + str(round(threshold_db, 1))
              + " " + unit_label + " PTA -> " + str(round(probe_db, 1))
              + " " + unit_label + " probe = " + str(round(probe_amp, 4)) + " amplitude")
        return probe_amp


def get_tmc_probe_level(participant_id: str,
                        probe_freq: int,
                        db_above_threshold: float = 10.0,
                        show_gui: bool = True,
                        max_amplitude: float = 0.7,
                        calibration=None) -> "Optional[float]":
    """
    Convenience wrapper: calculate a safe TMC probe amplitude for one frequency.
    Identical to get_ifmc_probe_level - both derive probe level from the standard
    PTA (threshold_dB column, fc column) and add db_above_threshold dB SL.
    """
    loader = ResultLoader()
    return loader.get_tmc_probe_level(participant_id, probe_freq,
                                      db_above_threshold=db_above_threshold,
                                      show_gui=show_gui,
                                      max_amplitude=max_amplitude,
                                      calibration=calibration)


def get_pta_threshold(participant_id: str,
                      frequency: int,
                      show_gui: bool = True,
                      data_dir: str = None) -> "Optional[float]":
    """Quick access to a single PTA threshold in dB."""
    loader = ResultLoader(data_dir)
    thresholds = loader.get_pta_thresholds(
        participant_id, [frequency], show_gui=show_gui
    )
    if thresholds and frequency in thresholds:
        return thresholds[frequency]
    return None
