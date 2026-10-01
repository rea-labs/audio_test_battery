# PROLACTIN - Resource / Crash Logging: Team Setup + Run Guide

Purpose: instrument long IFMC runs on the lab PC to settle whether the
lag/crash is a **memory leak** (RSS climbing until the machine's RAM ceiling)
or something else (thermal / CPU load / external kill). This adds a per-trial
resource logger plus an always-on crash handler that saves partial data and a
traceback when a run dies mid-way.

Nothing here changes test behavior or results. The logger is off by default and
only enabled for IFMC right now.

---

## 1. Files to sync (pull the updated versions)

- `paradigms/adaptive_paradigm.py`   (base: crash handler + logger hooks + central toggle)
- `config/DEFAULTS.py`               (adds `resource_logging` / `resource_scan_every` keys)
- `utils/resource_logger.py`         (NEW file - must land in `utils/`)
- `environment.yml`                  (adds `psutil`)

Note: `utils/resource_logger.py` is a new module. Confirm it is present in
`utils/` after syncing, or the run prints a one-line notice and continues
without resource logging.

## 2. Update the conda env (adds psutil)

`psutil` is what reads process memory / handle counts. It is on conda-forge
(already a channel). Pick ONE:

**Fast - install into the existing env:**
```
conda activate psychopy
conda install -c conda-forge psutil
```

**Or update from the yml:**
```
conda env update -n psychopy -f environment.yml
```

Then restart the env / relaunch the terminal so it picks up the change:
```
conda deactivate
conda activate psychopy
```

Verify:
```
python -c "import psutil; print(psutil.__version__)"
```

If `psutil` is missing, the run still works - the memory columns are just left
blank. So a missing install is not fatal, but the test needs psutil to produce
useful data.

## 3. Output location

Both files are written to a `debug_logs/` folder, created automatically at
runtime as a sibling of `test_data/` (under whatever directory you launch the
test from - launch from the usual project root so it lands beside `test_data/`).

No manual folder creation needed. Add `debug_logs/` to `.gitignore` _(manually transfer any logs via slack OR move them to the /data_4_review folder)_.

## 4. Run

Run any paradigm exactly as normal, e.g.:
```
python test_ifmc.py
python test_pta.py
```

Resource logging is enabled centrally in `config/DEFAULTS.py`
(`resource_logging: True`), so it is ON for every paradigm with no per-test
action needed. It writes one row per trial to:
```
debug_logs/<participant>_<PARADIGM>_resource.csv
```

The crash handler is always on (no toggle). If a run dies with a Python error,
it saves partial data and a traceback (see section 6).

## 5. What to collect and send back

After each long run (finished OR crashed), send:

- `debug_logs/<participant>_IFMC_resource.csv`   (always produced)
- `debug_logs/<participant>_IFMC_crash_<timestamp>.txt`   (only if it crashed with an error)
- `test_data/<participant>_IFMC_temp.csv`   (only present if the run did not finish cleanly)

Also note by hand:
- Did the run finish, or die? If it died, did Python print a traceback, or did
  the process / machine just disappear with no message?
- Roughly which trial / config it died at (and whether that varies run to run).

## 6. How we read it (for context - no action needed)

Resource CSV columns of interest:
- `rss_mb`  = real RAM used by the process. **Flat across trials = not a memory
  leak. Steadily rising = leak** (the weak PC hits its RAM ceiling and dies).
- `num_handles_or_fds` = OS handle count (Windows) / file descriptors (Mac). A
  steady rise here is a separate Windows failure mode (handle leak).
- `gc_objects`, `sound_objs`, `ndarray_objs` are blank unless deep scanning is
  turned on (see section 7); they tell us WHAT is growing if RSS rises.

Crash artifacts:
- **Crash `.txt` present** (with a traceback at a specific line) = a software
  bug; the failing line is in the file.
- **No crash `.txt`, but a `_temp.csv` is left behind** = the process was killed
  from outside (OS out-of-memory, or thermal shutdown) - Python never got to
  run the handler. This is itself a strong signal it is NOT a plain code bug.

## 7. Optional: deep object scan (only if asked)

By default only the cheap, zero-overhead metrics are logged every trial. To also
count live Sound / ndarray / Figure objects (heavier - walks all Python objects,
adds CPU per scan), set in `config/DEFAULTS.py`:

```
"resource_scan_every": 10,   # 0 = off (default); N = scan every Nth trial
```

Leave this at `0` for the first run (clean RSS curve). Only switch it on for a
follow-up run if RSS is found to be rising and we need to know what is growing.

## 8. Disable / scope notes

- To turn the resource logger off entirely: set `"resource_logging": False`
  in `config/DEFAULTS.py` (one switch, all paradigms).
- The crash handler is battery-wide (all paradigms, since it lives in the base)
  and cannot be toggled off - it only acts when a run actually crashes.
- The resource logger is now active for all paradigms via the central toggle
  (PTA included, which also crashes on the lab PC). No per-test wiring.
