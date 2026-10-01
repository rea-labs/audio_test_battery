# PRD - Per-trial reaction time logging (2026-06-30, final)

## Goal
Record participant reaction time on every logged trial, all 11 paradigms, into
the CSV. ONE column:
- `reaction_time_s` = t_response - end of last audible interval (R1)

Defined for ALL trials incl. catch (catch = target amp 0.0 but same
new_trial/play_trial path -> end_times still computed). No NaN special-case.

## Known caveat (accepted)
R1 includes a fixed dead interval before the participant can respond: ringout
(85.3 ms calibrated / 0 ms uncalibrated, 4096-tap FIR @ 48 kHz) + 0.1 s PTB
margin + 0.5 s anti-click + GUI-build. The ringout part is calibration-dependent,
so reaction_time_s is offset ~85 ms higher on calibrated vs uncalibrated runs.
Accepted by Eric; documented in a code comment. (rt_from_enabled_s / R3 was the
confound-free alternative; dropped per decision to keep a single column.)

## Clock
Single clock = ptb (psychtoolbox), same clock the audio is scheduled on. Base
class gains `import psychtoolbox as ptb` (mirrors trial_player.py line 8).

## Implementation, per file

### trial_player.py  (1 edit, in play_trial)
After `now = ptb.GetSecs()` and the schedule is built, store the audible end of
the last interval on the ptb clock:
    self.stim_end_time = now + max(self.end_times)
Re-stamped every play_trial call -> repeats reference the most recent playback
automatically. (`now` and `self.end_times` already exist at L227/L248.)

### adaptive_paradigm.py  (4 edits)
1. Import (top, near other imports):
       import psychtoolbox as ptb
2. __init__: init attrs so a row can never carry a stale value:
       self.reaction_time_s = np.nan
       self._resp_time      = None
3. get_response():
   - At top, reset: `self._resp_time = None`.
   - Inside the first ACCEPTED response (top of respond(), after the
     response_registered flag is set true): `self._resp_time = ptb.GetSecs()`.
     Covers both button click and key (on_key calls respond()); sub-ms overhead.
   - After mainloop returns, compute (guard for None / missing stim_end):
         _se = getattr(self.tp, "stim_end_time", None)
         self.reaction_time_s = (self._resp_time - _se) if (self._resp_time is not None and _se is not None) else np.nan
     On a "repeat" (returns None) this is recomputed on the next call ->
     final value references the last playback. Correct.
   - Add the caveat comment here (dead-interval / ringout note).
4. log_data(): add ONE universal column right after the `pan` line, before
   `**paradigm_data` (H2 pattern -> all 11 paradigms inherit it, zero subclass
   edits):
       "reaction_time_s": getattr(self, "reaction_time_s", np.nan),

## Key signatures (for session-cleanup changelog)
- trial_player.py:
    `self.stim_end_time = now + max(self.end_times)`
- adaptive_paradigm.py:
    `import psychtoolbox as ptb`
    `self.reaction_time_s = np.nan`
    `"reaction_time_s": getattr(self, "reaction_time_s", np.nan),`

## Out of scope
- All paradigm_*.py (inherit the column for free).
- calibration.py, operator_gui.py, paradigm_setup_dialog.py, DEFAULTS.py, varspec.
- Demo trials (play_demo_trial) - not logged, no RT.
- test_*.py - inherit new column automatically; no edits (confirmed none assert
  exact column sets).
- No change to anti-click 0.5 s wait, ringout, or any timing behavior.
- R3 / rt_from_enabled_s - dropped.

## Suggested order
| # | Step | Verify |
|---|------|--------|
| 1 | trial_player.py stim_end_time | grep + ast.parse |
| 2 | adaptive_paradigm.py import + __init__ attrs | grep + ast.parse |
| 3 | adaptive_paradigm.py get_response stamp + compute | grep + ast.parse |
| 4 | adaptive_paradigm.py log_data column (after pan) | grep + ast.parse |
| 5 | non-ASCII / mojibake sweep both files | clean |

## Open questions
None - spec finalized. Awaiting go-ahead to implement.
