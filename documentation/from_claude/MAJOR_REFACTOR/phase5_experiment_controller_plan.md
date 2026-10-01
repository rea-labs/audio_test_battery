# Phase 5 Refactoring Plan — ExperimentController

*2026-03-29 | PROLACTIN codebase refactoring*

**Depends on:** Phases 1-3 complete and verified. Phase 4 (CalibrationManager) complete or in progress.

---

## Goal

Create an `ExperimentController` class that orchestrates entire test sessions: participant setup, paradigm selection, calibration loading, sequential paradigm execution, and session-level data management. This replaces the current workflow of running individual `test_*.py` scripts manually.

**After Phase 5:**
- Operator launches one script (`run_session.py`) instead of 10+ individual scripts
- Single Tk root window persists across the session — no create/destroy between paradigms
- Operator display becomes the controller's main interface, extended with paradigm selection and session management views
- Calibration loaded once and shared across all paradigms
- `test_*.py` scripts remain functional for single-paradigm development/debugging but are no longer the primary entry point

---

## Current Tk Window Lifecycle (the problem)

Right now, three separate Tk roots are created and destroyed during a single paradigm run:

| Component | Creates | Destroys | Window type |
|---|---|---|---|
| `ParadigmSetupDialog` | `tk.Tk()` in `show()` | `root.destroy()` on accept/cancel | Root |
| `OperatorDisplay` | Hidden `tk.Tk()` + `Toplevel` (singleton) | On program exit | Hidden root + Toplevel |
| `AdaptiveParadigm.main()` | `tk.Tk()` at start of `main()` | At end of paradigm or on abort | Root |

This causes:
- Tk root created/destroyed 2-3 times per paradigm run
- macOS Tk instability (especially with PTB audio active)
- Operator display orphaned if paradigm crashes
- No way to run paradigms in sequence without restarting the process

---

## Target Architecture

```
ExperimentController
  |
  |-- owns tk.Tk() root (single, persists entire session)
  |
  |-- owns OperatorDisplay (Toplevel child of root)
  |     |-- session management view (paradigm list, status)
  |     |-- paradigm monitoring view (existing plots)
  |
  |-- owns CalibrationManager (loaded once)
  |
  |-- creates ParticipantGUI per paradigm (Toplevel child of root)
  |
  |-- creates DataManager per paradigm (shared output directory)
  |
  |-- creates paradigm instances, injects all dependencies, calls main()
```

---

## Design: `ExperimentController` Class

```python
class ExperimentController:
    """
    Top-level orchestrator for audiology test sessions.

    Owns the Tk root window, operator display, calibration, and
    session state. Runs paradigms in sequence, passing shared
    resources via dependency injection.
    """

    def __init__(self, calibration_config: str = None):
        """
        Args:
            calibration_config: path to calibration_config.json.
                               None = uncalibrated mode.
        """
        # Tk root — single instance for entire session
        self.root = tk.Tk()
        self.root.withdraw()  # hidden; children (operator, participant) are Toplevels

        # Calibration (loaded once, shared across paradigms)
        self.calibration = CalibrationManager(calibration_config)

        # Operator display (Toplevel, persists across paradigms)
        self.operator_display = OperatorDisplay(parent=self.root)

        # Session state
        self.participant_id = None
        self.session_dir = None         # output directory for this session
        self.paradigm_queue = []        # list of paradigm configs to run
        self.completed_paradigms = []   # paradigm_codes that finished
        self.current_paradigm = None

    def run_session(self):
        """Main entry point. Shows setup, runs paradigms, exits."""
        # 1. Session setup (participant ID, paradigm selection)
        self.participant_id = self._show_session_setup()
        if self.participant_id is None:
            self.shutdown()
            return

        # 2. Create session output directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.session_dir = (
            Path.cwd() / "test_data" / f"{self.participant_id}_{timestamp}"
        )
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # 3. Run paradigm queue
        for paradigm_config in self.paradigm_queue:
            success = self._run_paradigm(paradigm_config)
            if success:
                self.completed_paradigms.append(paradigm_config['code'])

            # Show between-paradigm screen (unless last)
            if paradigm_config != self.paradigm_queue[-1]:
                action = self._show_between_paradigm_screen()
                if action == 'abort_session':
                    break
                elif action == 'skip_next':
                    continue

        # 4. Session complete
        self._show_session_summary()
        self.shutdown()

    def shutdown(self):
        """Clean exit."""
        if self.operator_display is not None:
            self.operator_display.destroy()
        self.root.destroy()
```

---

## Session Setup View

New view on the operator display (or a modal dialog). Shows:

1. **Participant ID entry** — same format_participant_id logic as current setup dialog
2. **Paradigm selection** — checkboxes for available paradigms with recommended order
3. **Calibration status** — green/yellow indicator (calibrated/uncalibrated)
4. **Session start button**

```python
def _show_session_setup(self) -> Optional[str]:
    """
    Show session setup dialog. Returns participant_id or None.
    Sets self.paradigm_queue based on operator selections.
    """
    setup = SessionSetupDialog(self.root, self.calibration)
    result = setup.show()  # blocks

    if result is None:
        return None

    self.participant_id = result['participant_id']
    self.paradigm_queue = result['paradigm_queue']
    return self.participant_id
```

### Paradigm Registry

The controller needs to know what paradigms are available and how to instantiate them. Rather than hardcoding, use a registry:

```python
# paradigm_registry.py

PARADIGM_REGISTRY = {
    'PTA': {
        'class': 'paradigms.paradigm_pta.ParadigmPTA',
        'label': 'Pure Tone Audiogram',
        'default_params': {
            'inner': {...},   # same as current test_pta.py
            'outer_1': {...},
        },
        'setup_dialog': 'ParadigmSetupDialog',
        'order': 1,            # recommended run order
        'depends_on': [],      # no prerequisites
    },
    'IFMC': {
        'class': 'paradigms.paradigm_ifmc.ParadigmIFMC',
        'label': 'Iso-Forward Masking Contour',
        'default_params': {...},
        'setup_dialog': 'ThresholdSetupDialog',
        'order': 2,
        'depends_on': ['PTA'],  # needs PTA thresholds
        'setup_kwargs': {
            'db_above_threshold': 10.0,
            'max_amplitude': 0.7,
        },
    },
    # ... etc for all 11 paradigms
}
```

This moves the paradigm configs out of `test_*.py` scripts and into a single declarative registry. The controller reads it; `test_*.py` scripts also read it (for standalone runs).

---

## Running a Single Paradigm

```python
def _run_paradigm(self, paradigm_config: dict) -> bool:
    """
    Run one paradigm. Returns True if completed successfully.

    Steps:
      1. Show paradigm-specific setup dialog (param editing, demo)
      2. Create ParticipantGUI (Toplevel child of self.root)
      3. Create DataManager (session output directory)
      4. Create paradigm instance with all dependencies injected
      5. Call paradigm.main()
      6. Destroy ParticipantGUI
    """
    code = paradigm_config['code']
    cls = paradigm_config['class']       # resolved from registry
    params = paradigm_config['params']    # potentially edited by dialog

    # 1. Paradigm-specific setup dialog
    #    Construct a temporary paradigm for demo playback
    temp_paradigm = cls(params, verbose=False)
    dialog_cls = paradigm_config.get('setup_dialog', ParadigmSetupDialog)

    if dialog_cls == ThresholdSetupDialog:
        dialog = ThresholdSetupDialog(
            paradigm_name=code,
            params=params,
            paradigm=temp_paradigm,
            parent=self.root,          # <-- child of controller's root
            **paradigm_config.get('setup_kwargs', {})
        )
        result = dialog.show()
        if result is None:
            return False
        participant_id, thresholds = result
        # Update params with threshold data (IFMC/TMC specific)
        self._apply_threshold_data(params, thresholds)
    else:
        dialog = ParadigmSetupDialog(
            paradigm_name=code,
            params=params,
            paradigm=temp_paradigm,
            parent=self.root,          # <-- child of controller's root
        )
        participant_id = dialog.show()
        if participant_id is None:
            return False

    # 2. Create GUI (Toplevel child of controller root)
    gui = TkParticipantGUI(
        paradigm_config.get('gui_config', cls.DEFAULT_GUI_CONFIG),
        parent=self.root
    )

    # 3. Create DataManager
    data_manager = DataManager(
        self.participant_id, code,
        output_dir=str(self.session_dir)
    )

    # 4. Create paradigm with injected dependencies
    paradigm = cls(
        params,
        verbose=True,
        participant_id=self.participant_id,
        gui=gui,
        data_manager=data_manager,
        show_operator_display=False,   # controller manages this
    )

    # 5. Attach to operator display
    self.operator_display.attach_paradigm(paradigm)

    # 6. Run
    try:
        paradigm.main()
        return True
    except KeyboardInterrupt:
        print(f"\n{code} aborted by operator.")
        return False
    except Exception as e:
        print(f"\n{code} error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        gui.destroy()
```

---

## Between-Paradigm Screen

After each paradigm completes, the controller shows a summary + options:

```python
def _show_between_paradigm_screen(self) -> str:
    """
    Show between-paradigm screen on operator display.

    Returns:
        'continue' - proceed to next paradigm
        'skip_next' - skip the next paradigm
        'abort_session' - end session
    """
    # Show on operator display: completed paradigm results,
    # next paradigm info, three buttons
    ...
```

This replaces the current workflow of the operator manually running the next `test_*.py` script.

---

## Changes to Existing Code

### `operator_gui.py`

**Accept `parent` parameter:**

```python
class OperatorDisplay:
    def __init__(self, title="Operator Display", parent=None):
        if parent is not None:
            self.root = tk.Toplevel(parent)
        else:
            # Standalone mode (backward compat for test_*.py scripts)
            global _tk_hidden_root
            if _tk_hidden_root is None:
                _tk_hidden_root = tk.Tk()
                _tk_hidden_root.withdraw()
            self.root = tk.Toplevel(_tk_hidden_root)
```

**Add session management view:** A new panel/tab that shows the paradigm queue, completion status, and between-paradigm controls. This is an extension to the existing operator display, not a replacement — the four monitoring plots stay as-is.

**Add `clear_display()` improvements:** Already exists (line 653), but verify it fully resets between paradigms.

### `paradigm_setup_dialog.py`

**Accept `parent` parameter:**

```python
class ParadigmSetupDialog:
    def __init__(self, paradigm_name, params, paradigm=None,
                 default_freq_set_key=..., parent=None):
        ...
        # Use parent if provided, otherwise create own root
        if parent is not None:
            self._root = tk.Toplevel(parent)
        else:
            self._root = tk.Tk()
```

Currently the dialog creates `tk.Tk()` and calls `mainloop()`. With a parent, it should use `wait_window()` instead (blocks until the Toplevel is destroyed, without starting a nested mainloop):

```python
def show(self):
    ...
    if self._parent is not None:
        self._root.wait_window()  # block without nested mainloop
    else:
        self._root.mainloop()     # standalone mode
    return self._result
```

### `adaptive_paradigm.py`

**`main()` no longer creates Tk root or operator display when dependencies are injected:**

After Phases 2-3, `main()` already accepts `gui=` and `data_manager=`. The controller passes both, plus sets `show_operator_display=False` (the controller manages the operator display externally). The paradigm's `main()` just runs the trial loop:

```python
def main(self):
    # GUI already injected (or create default)
    if self._injected_gui is not None:
        self.gui = self._injected_gui
    else:
        self.gui = TkParticipantGUI(self.gui_config)

    # DataManager already injected (or create default)
    if self._injected_dm is not None:
        self.data_manager = self._injected_dm
    else:
        self.data_manager = DataManager(self.participant_id, self.paradigm_code)

    # Operator display — only create if not externally managed
    if self.show_operator_display and self.operator_display is None:
        self.operator_display = get_operator_display()
        self.operator_display.attach_paradigm(self)
        self.operator_display.show()

    # Run
    self.run_trial_loop()

    # Cleanup
    ...
```

No structural changes needed beyond what Phases 2-3 already set up. The controller just passes pre-built dependencies.

### `test_*.py` Scripts

**Stay functional** for standalone development. They continue to work exactly as today — creating their own paradigm, dialog, and calling `paradigm.main()`. The only difference is that post-Phase 5, they're the "dev/debug" entry point, not the primary workflow.

Optionally, they can be simplified to read from the paradigm registry:

```python
# test_pta.py (simplified, post-Phase 5)
from experiment_controller import PARADIGM_REGISTRY

def main():
    config = PARADIGM_REGISTRY['PTA']
    # ... create paradigm from config, show dialog, run ...
```

But this is optional — the existing test scripts work fine as-is.

---

## Paradigm Dependencies (run order)

Some paradigms need results from earlier paradigms:

| Paradigm | Depends on | Reason |
|---|---|---|
| PTA | — | Runs first, no dependencies |
| IFMC | PTA | Needs PTA thresholds to set probe levels |
| TMC | PTA | Same as IFMC |
| All others | — | Independent |

The controller enforces this: if IFMC is queued but PTA hasn't run (or its data isn't available), show a warning and offer to run PTA first, enter thresholds manually, or load from a previous session.

This is already handled by `ResultLoader` + `ThresholdSetupDialog` — the controller just needs to call them in the right order.

---

## Session Output Structure

```
test_data/
  P0018_2026-03-29_14-30-00/        # session directory
    P0018_PTA_2026-03-29_14-30-45.csv
    P0018_AM_2026-03-29_14-42-12.csv
    P0018_IFMC_2026-03-29_14-55-33.csv
    session_log.json                  # session metadata
```

`session_log.json`:
```json
{
    "participant_id": "P0018",
    "session_start": "2026-03-29T14:30:00",
    "calibration": {
        "profile": "DT250_RME_UFX",
        "is_calibrated": true
    },
    "paradigms_run": [
        {"code": "PTA",  "status": "complete", "csv": "P0018_PTA_...csv"},
        {"code": "AM",   "status": "complete", "csv": "P0018_AM_...csv"},
        {"code": "IFMC", "status": "aborted",  "csv": null}
    ]
}
```

---

## File Summary

| File | Change | Risk |
|---|---|---|
| `experiment_controller.py` | **NEW** — ExperimentController class | Medium (new file, complex integration) |
| `paradigm_registry.py` | **NEW** — declarative paradigm configs | Low (data only) |
| `session_setup_dialog.py` | **NEW** — session-level setup GUI | Low-medium (Tk dialog) |
| `run_session.py` | **NEW** — entry point script | Very low |
| `operator_gui.py` | Accept `parent=` param, add session management view | Medium |
| `paradigm_setup_dialog.py` | Accept `parent=` param, support `wait_window()` | Low-medium |
| `adaptive_paradigm.py` | No structural changes (Phases 2-3 already set up injection) | Very low |
| All `paradigm_*.py` | No changes | None |
| All `test_*.py` | No changes (still work standalone) | None |

---

## Implementation Order

| # | Task | Effort |
|---|------|--------|
| 1 | Create `paradigm_registry.py` — extract paradigm configs from `test_*.py` into declarative registry | 2 hr |
| 2 | Update `operator_gui.py` — accept `parent=` param, backward-compatible | 30 min |
| 3 | Update `paradigm_setup_dialog.py` — accept `parent=` param, add `wait_window()` path | 1 hr |
| 3v | **Verify:** Run PTA via `test_pta.py` to confirm standalone mode still works with updated dialog | 15 min |
| 4 | Create `session_setup_dialog.py` — participant ID + paradigm selection UI | 2-3 hr |
| 5 | Create `experiment_controller.py` — core orchestration, paradigm instantiation, dependency injection | 3-4 hr |
| 6 | Add between-paradigm screen to operator display | 1-2 hr |
| 7 | Add session log output (`session_log.json`) | 30 min |
| 8 | Create `run_session.py` entry point | 30 min |
| 9 | **Verify:** Run full 3-paradigm session (PTA → AM → GAP). Check session directory, CSV output, session log, paradigm transitions. | 1 hr |
| 10 | **Verify:** Run IFMC session (PTA → IFMC). Confirm threshold loading works through controller. | 30 min |
| 11 | **Verify:** Run `test_pta.py` standalone — confirm it still works independently. | 15 min |

**Total estimate:** ~12-15 hours across 2-3 sessions.

---

## Verification Strategy

- **Step 3v (dialog parent):** Most critical compatibility check. The dialog must still work when called from `test_*.py` (no parent) and from the controller (with parent). Both paths must handle accept, cancel, and demo mode.
- **Step 9 (multi-paradigm session):** Core test. Run PTA → AM → GAP in sequence. Check: single Tk root persists, operator display updates per paradigm, CSV files land in session directory, between-paradigm screen appears, session log is written.
- **Step 10 (threshold dependency):** IFMC depends on PTA. Run PTA, then IFMC in same session. Confirm ResultLoader finds the PTA CSV in the session directory and loads thresholds correctly.
- **Step 11 (standalone regression):** `test_*.py` scripts must still work for development. Run `test_pta.py` by itself, confirm full functionality.

---

## Open Questions

1. **Paradigm registry vs. test scripts as source of truth.** The registry duplicates param configs that currently live in `test_*.py`. Two options: (a) registry is authoritative, test scripts read from it; (b) test scripts stay authoritative, registry is auto-generated from them. Leaning toward **(a)** — the registry is cleaner and test scripts can import from it. But this means param changes happen in the registry, not the test scripts. Worth discussing which feels more natural for your workflow.

2. **Session setup: modal dialog vs. view in operator display.** The setup could be a standalone modal dialog (like current ParadigmSetupDialog) or a view/panel within the operator display window. Modal dialog is simpler and consistent with existing patterns. Operator display view is more integrated but requires reworking the operator display layout. **Recommend modal dialog for now**, migrate to integrated view later if desired.

3. **Per-paradigm setup dialogs within a session.** Currently each paradigm has its own setup dialog (param editing, demo mode). Should the controller show these between paradigms, or should the session setup collect all params upfront? **Recommend per-paradigm dialogs** — they're already built, they allow demo mode right before each paradigm, and operators may want to adjust params based on how earlier paradigms went.

4. **Calibration spot-check.** The Phase B plan mentions a pre-session calibration verification ("play 1 kHz at 60 dB SPL, confirm ±2 dB"). Should the controller offer this at session start? **Recommend adding a "Verify Calibration" button** to the session setup dialog that triggers a quick spot-check. Implementation is simple once CalibrationManager exists. Defer to after Phase 4.

5. **`ParadigmSetupDialog` and `wait_window()` on macOS.** `wait_window()` should work correctly as a blocking call on Toplevel windows, but Tk on macOS has quirks. Same risk as the `wait_variable()` change in Phase 2 — needs macOS testing. If problematic, fall back to a nested `mainloop()` / `quit()` pair within the dialog (messier but functional).

6. **Saving params to disk.** When the operator edits params in the setup dialog, should the edited values be persisted? Currently they're ephemeral — only apply to that run. For research reproducibility, it might be worth writing the final param set to `session_log.json`. **Recommend yes** — log the actual params used (after any operator edits) alongside each paradigm entry in the session log. Low effort, high value.

---

## Interaction with Other Phases

**Phase 2 (ParticipantGUI):** The controller creates `TkParticipantGUI(gui_config, parent=self.root)` and injects it. The `wait_variable()` pattern from Phase 2 is essential — it allows blocking for responses without owning the Tk mainloop.

**Phase 3 (DataManager):** The controller creates `DataManager(participant_id, paradigm_code, output_dir=session_dir)` and injects it. All CSVs land in the session directory.

**Phase 4 (CalibrationManager):** The controller creates `CalibrationManager(config_path)` once at session start and passes it to each paradigm. Each paradigm's TrialPlayer uses it for the `prepare_sound()` gateway.

**Phase 6 (Testing):** Automated tests can create an ExperimentController with `MockParticipantGUI` and a temp session directory, then run paradigms headlessly. This is the full integration test path.
