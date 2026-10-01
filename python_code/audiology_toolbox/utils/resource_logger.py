"""
resource_logger.py

Per-trial resource logger for PROLACTIN crash / memory-leak debugging
("Test 2": is RSS climbing across a long run, and if so, what is growing?).

Drop-in, zero-coupling: construct once, call log() once per trial, close() at
end. Writes a sidecar CSV next to the normal output. Designed so that:
  * A crash mid-run leaves a complete row-by-row RSS trace on disk
    (file is line-buffered, so every row is flushed as it is written).
  * The logger itself NEVER raises into the trial loop (all work is wrapped).
  * The always-on metrics are O(1) so the RSS curve is not perturbed by the
    act of measuring it. The heavy gc object scan is opt-in (object_scan_every).

Cross-platform (Mac + Windows). Requires psutil for memory/handle metrics; if
psutil is not installed the logger still runs but leaves those columns blank
and prints a one-time notice (add `psutil` to environment.yml to enable).
"""

import csv
import gc
import os
import time
from pathlib import Path

try:
    import psutil
    _HAVE_PSUTIL = True
except ImportError:
    psutil = None
    _HAVE_PSUTIL = False


# Columns always written (cheap, O(1) per trial).
_BASE_FIELDS = [
    "elapsed_s",
    "unix_time",
    "config_num",
    "trial_num",
    "rss_mb",
    "vms_mb",
    "num_threads",
    "num_handles_or_fds",
]

# Columns written only on scan trials (heavy, O(number of live objects)).
_SCAN_FIELDS = [
    "gc_objects",
    "sound_objs",
    "figure_objs",
    "ndarray_objs",
]


class ResourceLogger:
    """
    Logs process resource usage per trial to a sidecar CSV.

    Parameters
    ----------
    output_dir : str | Path
        Directory the CSV is written into (same dir as the normal results).
    participant_id : str
        Used only for the filename.
    paradigm_code : str
        Used only for the filename.
    enabled : bool
        Master off-switch. When False, all methods are no-ops.
    object_scan_every : int
        0  -> never scan live objects (default; keeps overhead O(1)/trial).
        N  -> also count gc objects + Sound/Figure/ndarray instances every
              Nth trial. Use for a dedicated "what is leaking" run only.
    """

    def __init__(self, output_dir, participant_id, paradigm_code,
                 enabled=True, object_scan_every=0):
        self.enabled = bool(enabled)
        self.object_scan_every = int(object_scan_every)
        self._proc = None
        self._fh = None
        self._writer = None
        self._t0 = time.time()
        self._fieldnames = list(_BASE_FIELDS)
        if self.object_scan_every > 0:
            self._fieldnames += _SCAN_FIELDS

        if not self.enabled:
            return

        try:
            if _HAVE_PSUTIL:
                self._proc = psutil.Process(os.getpid())
            else:
                print("[resource_logger] psutil not installed -- memory/handle "
                      "columns will be blank. Add 'psutil' to environment.yml "
                      "to enable Test 2 memory tracing.")

            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            path = out / f"{participant_id}_{paradigm_code}_resource.csv"
            # buffering=1 -> line buffered -> each row flushed as written, so a
            # crash preserves the full trace up to the last completed trial.
            self._fh = open(path, "w", newline="", buffering=1)
            self._writer = csv.DictWriter(self._fh, fieldnames=self._fieldnames)
            self._writer.writeheader()
            print(f"[resource_logger] logging to {path} "
                  f"(object_scan_every={self.object_scan_every})")
        except Exception as exc:  # never let setup kill the run
            print(f"[resource_logger] disabled (setup failed: {exc})")
            self.enabled = False

    def log(self, config_num, trial_num):
        """Write one row for the current trial. Safe to call unconditionally."""
        if not self.enabled or self._writer is None:
            return
        try:
            row = {
                "elapsed_s": round(time.time() - self._t0, 3),
                "unix_time": round(time.time(), 3),
                "config_num": config_num,
                "trial_num": trial_num,
                "rss_mb": "",
                "vms_mb": "",
                "num_threads": "",
                "num_handles_or_fds": "",
            }

            if self._proc is not None:
                mem = self._proc.memory_info()
                row["rss_mb"] = round(mem.rss / (1024.0 * 1024.0), 2)
                row["vms_mb"] = round(mem.vms / (1024.0 * 1024.0), 2)
                row["num_threads"] = self._proc.num_threads()
                row["num_handles_or_fds"] = self._handle_count()

            if self.object_scan_every > 0 and (trial_num % self.object_scan_every == 0):
                row.update(self._object_counts())

            self._writer.writerow(row)
        except Exception as exc:  # logging must never break the trial loop
            print(f"[resource_logger] log() error (ignored): {exc}")

    def close(self):
        """Flush and close the sidecar file. Safe to call multiple times."""
        try:
            if self._fh is not None:
                self._fh.flush()
                self._fh.close()
        except Exception:
            pass
        finally:
            self._fh = None
            self._writer = None

    # ---- internals -------------------------------------------------------

    def _handle_count(self):
        """Windows handle count, else POSIX fd count, else blank."""
        try:
            if hasattr(self._proc, "num_handles"):   # Windows
                return self._proc.num_handles()
            if hasattr(self._proc, "num_fds"):        # Mac / Linux
                return self._proc.num_fds()
        except Exception:
            pass
        return ""

    def _object_counts(self):
        """
        Heavy: iterate all gc-tracked objects once and tally the leak-prone
        types. Only called on scan trials. Counts by class name (no psychopy /
        matplotlib import needed, so no dependency and no false negatives if the
        Sound class is backend-specific, e.g. SoundPTB).
        """
        counts = {"gc_objects": 0, "sound_objs": 0, "figure_objs": 0, "ndarray_objs": 0}
        try:
            objs = gc.get_objects()
            counts["gc_objects"] = len(objs)
            for o in objs:
                name = type(o).__name__
                if name.startswith("Sound"):
                    counts["sound_objs"] += 1
                elif name == "Figure":
                    counts["figure_objs"] += 1
                elif name == "ndarray":
                    counts["ndarray_objs"] += 1
        except Exception as exc:
            print(f"[resource_logger] object scan error (ignored): {exc}")
        return counts
