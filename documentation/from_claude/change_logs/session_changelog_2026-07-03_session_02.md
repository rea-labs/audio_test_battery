# Session Changelog -- 2026-07-03 (session 02)

## Session start protocol (NEXT session)
1. Push local working copies into the project FIRST.
2. Verify the Key Signatures below against the uploaded files.
3. Review Open Issues / Next Steps.

## High-level summary
Debug instrumentation for the lab-PC lag/crash investigation (thermal vs
memory). Two capabilities, both in the base so all 11 paradigms inherit them:
(1) an always-on crash handler that, on an uncaught exception mid-run, saves
partial temp data + a timestamped traceback to `debug_logs/`, then re-raises;
(2) an opt-in per-trial resource logger (RSS/VMS/threads/handles, optional gc
object counts) for "Test 2" -- is process memory climbing across a long run.
Toggle centralized in `config/DEFAULTS.py`. A prior source review found NO
Python-side leak (DataFrame is rebuilt-not-appended and freed each trial; GUI
axes cleared every redraw; Sound objects are per-trial locals). The only risk
not provable from source is native PTB audio-track release; the logger will
surface that as rising RSS. Verified end-to-end on Mac via a forced-crash smoke
test (crash file + temp both written, re-raise clean).

## Work completed
- adaptive_paradigm.py: `import traceback` + `from config.DEFAULTS import DEFAULTS`;
  resource flags now read from DEFAULTS (`.get()` fallbacks, off if absent);
  ResourceLogger built in `main()` (lazy import, guarded); per-trial `.log()`
  after `update_display`; trial loop wrapped in try/except/finally (temp save +
  crash file + re-raise; logger `close()` in finally); new `_debug_log_dir()`
  returning `cwd/debug_logs`.
- utils/resource_logger.py (NEW): `ResourceLogger`. Cheap psutil metrics every
  trial (RSS/VMS/threads/handles, O(1)); optional gc-typed scan
  (Sound/Figure/ndarray) gated by `object_scan_every`. Line-buffered CSV
  (crash-safe), never raises into the loop, degrades gracefully if psutil absent.
- config/DEFAULTS.py: ADD `"resource_logging": True` + `"resource_scan_every": 0`
  (MANUAL -- Eric adds; project copy was stale [External-Headphones active, no
  DEFAULTS_local block] so it was deliberately NOT regenerated).
- environment.yml: ADD `psutil` (conda-forge). [done Eric-side]
- PROLACTIN_resource_logging_handoff.md (NEW): team setup/run guide.
- test_ifmc.py: per-file toggle added then removed -> net unchanged vs original.

## Files modified
| File | Change |
|---|---|
| paradigms/adaptive_paradigm.py | traceback+DEFAULTS import; DEFAULTS-driven resource flags; crash handler around trial loop; per-trial resource log; _debug_log_dir() |
| utils/resource_logger.py | NEW -- per-trial RSS/handle/gc logger |
| config/DEFAULTS.py | ADD 2 keys (MANUAL, Eric) |
| environment.yml | ADD psutil (done) |
| PROLACTIN_resource_logging_handoff.md | NEW -- team handoff doc |

Files NOT modified: test_ifmc.py (net unchanged), test_pta.py (inherits central
flag, no wiring), all paradigm_*.py, operator_gui.py, trial_player.py,
event_gen.py, calibration.py, result_loader.py.

## Key Signatures (grep to confirm the new versions)
- adaptive_paradigm.py:
  - `from config.DEFAULTS import DEFAULTS`
  - `self.resource_logging = DEFAULTS.get("resource_logging", False)`
  - `def _debug_log_dir(self) -> Path:`
  - `print(f"[crash handler] traceback written to {_crash_path}")`
- utils/resource_logger.py:
  - `class ResourceLogger:`
  - `def _handle_count(self):`
- config/DEFAULTS.py (after Eric's edit):
  - `"resource_logging": True,`
- environment.yml:
  - `- psutil`

## Open Issues / Next Steps
- LAB-PC LAG/CRASH (thermal vs memory) -- instrumentation shipped, handed to
  team. Awaiting from a long IFMC/PTA run: resource CSV (flat vs rising rss_mb),
  any `*_crash_*.txt` (traceback present = software bug; absent + temp CSV left =
  external kill / OOM / thermal, since SIGKILL skips the handler), and
  num_handles trend (Windows handle leak = separate failure mode). If RSS rises
  -> 2nd run with `resource_scan_every=10` to identify the growing type (PTB
  Sound tracks are the prime suspect). If RSS flat -> drop memory, return to
  thermal (Test 3: core temp via HWiNFO/Core Temp) + redraw load (4x
  canvas.draw/trial) + O(n^2) DataFrame-rebuild CPU.
- Prior thermal evidence still stands (flat per-trial machine overhead across
  268 trials), BUT Mac was never long-run-tested, so a cross-platform PTB track
  leak is not excluded -- the RSS curve settles it.
- After the campaign: set `resource_logging` False in DEFAULTS.
- Carried forward (untouched this session): H4 (PTA trial_dur / 16 ms), H5 (IFMC
  silent catch audibility, Tier-2 verbose run), H8 (IFMC high-config crash
  re-check), Mulligan config-rerun (unbounded curve_fit guard), SPL
  re-measurement (dB(Z), N>=5 reseat), PEQ calibration path.

## Re-upload into project (so next start-check passes)
- paradigms/adaptive_paradigm.py
- utils/resource_logger.py (new)
- config/DEFAULTS.py (after adding the 2 keys)
- environment.yml
- PROLACTIN_resource_logging_handoff.md (new)
- this changelog (session_changelog_2026-07-03_session_02.md)
