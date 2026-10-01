# Phase 2 Refactoring Plan — ParticipantGUI Extraction

*2026-03-29 | PROLACTIN codebase refactoring*

**Depends on:** Phase 1 (boilerplate consolidation) complete and verified.

---

## Goal

Extract all participant-facing GUI code from `AdaptiveParadigm` into a standalone `ParticipantGUI` class, injected via constructor. This enables:

- **NiceGUI migration** — swap `TkParticipantGUI` for `WebParticipantGUI` without touching paradigm code
- **Headless mode** — inject `MockParticipantGUI` for automated testing (Phase 6)
- **ExperimentController integration** (Phase 5) — controller creates the GUI once, passes it to paradigms

---

## Current State (post-Phase 1)

Three methods on `AdaptiveParadigm` contain all participant GUI code:

| Method | Lines | What it does |
|---|---|---|
| `get_response()` | ~110 | Creates Tk buttons/labels, binds keyboard, blocks on `mainloop()`, returns int or None |
| `update_gui_state()` | ~50 | Shows "Playing stimulus..." or disabled buttons during playback |
| `show_false_positive_warning()` | ~25 | Replaces window content with FP warning, pauses 2s |

Additionally, `self.root` (the `tk.Tk()` window) is:
- Created in `main()` (line 1176)
- Destroyed in `check_paradigm_end_conds()` (line 960) and `notify_wrv_limit()` (line 799)
- Accessed by `operator_gui.py` (line 295) to lift/refocus the participant window after plot updates

`play_demo_trial()` does **not** interact with the GUI — it only plays audio.

---

## Design: `ParticipantGUI` Interface

```python
class ParticipantGUI:
    """
    Abstract interface for participant response collection.
    Concrete implementations: TkParticipantGUI, MockParticipantGUI,
    (future) WebParticipantGUI.
    """

    def get_response(self) -> int | None:
        """Block until participant responds. Return option index or None (repeat)."""
        raise NotImplementedError

    def show_playing(self):
        """Show 'Playing stimulus...' state. Disable response buttons."""
        raise NotImplementedError

    def show_waiting(self):
        """Show response buttons. Called after playback finishes, before get_response()."""
        raise NotImplementedError

    def show_fp_warning(self):
        """Show false positive warning. Block briefly (~2s), then return."""
        raise NotImplementedError

    def show_message(self, text: str):
        """Display arbitrary message (e.g. '...' between trials)."""
        raise NotImplementedError

    def lift(self):
        """Bring window to front. Used by operator display to refocus."""
        raise NotImplementedError

    def destroy(self):
        """Destroy the GUI. Called on paradigm end or abort."""
        raise NotImplementedError
```

### Why `show_playing()` + `show_waiting()` instead of `update_gui_state(trial_playing)`

The current `update_gui_state(trial_playing=True/False)` is a flag-driven method that rebuilds the entire window contents on every call. Splitting into `show_playing()` and `show_waiting()` is cleaner — each method has one job, and the caller doesn't pass a boolean to switch behavior. This also maps better to web GUI implementations where "show playing" and "show buttons" are different page states.

---

## Concrete Implementation: `TkParticipantGUI`

```python
class TkParticipantGUI(ParticipantGUI):
    """Tkinter implementation — current behavior, extracted."""

    def __init__(self, gui_config: dict, parent=None):
        """
        Args:
            gui_config: dict with 'question', 'options', 'keys',
                       'allow_repeat', 'window_title', 'font_size',
                       'window_geometry'
            parent: Optional Tk parent widget. If None, creates tk.Tk().
                    If provided (e.g. by ExperimentController), creates
                    a Frame or Toplevel as child.
        """
        self.config = gui_config

        if parent is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(parent)

        self.root.title(gui_config.get('window_title', 'Audiology Test'))
        self.root.geometry(gui_config.get('window_geometry', '400x200'))
        self.root.lift()
        self.root.focus_force()

    def get_response(self) -> int | None:
        # ... existing get_response() code from AdaptiveParadigm,
        #     using self.root and self.config instead of
        #     self.root and self.gui_config
        ...

    def show_playing(self):
        # ... "Playing stimulus..." label, no buttons
        ...

    def show_waiting(self):
        # ... question label + disabled buttons (visual only,
        #     actual response handled by get_response)
        ...

    def show_fp_warning(self):
        # ... existing show_false_positive_warning() code
        ...

    def show_message(self, text: str):
        # ... clear window, show text label
        ...

    def lift(self):
        if self.root is not None:
            try:
                self.root.lift()
                self.root.focus_force()
            except tk.TclError:
                pass

    def destroy(self):
        if self.root is not None:
            self.root.destroy()
            self.root = None
```

### The `parent` parameter

This is the hook for Phase 5 (ExperimentController). Currently `parent=None` and the GUI creates its own `tk.Tk()`. When the controller exists, it passes its root window as `parent`, and the GUI creates a `Toplevel` child instead. This means:

- No `tk.Tk()` create/destroy between paradigms (the controller's root persists)
- The operator display and participant GUI share the same Tk event loop
- `get_response()` must use `self.root.wait_variable()` instead of `self.root.mainloop()` — because the controller owns the mainloop

This `wait_variable()` change is the trickiest part of Phase 2. Currently `get_response()` calls `self.root.mainloop()` to block, then `self.root.quit()` to unblock. This only works when the paradigm owns the Tk root. With a parent, we need:

```python
def get_response(self) -> int | None:
    self._response_var = tk.IntVar(value=-1)

    def respond(value):
        ...
        self._response_var.set(value)

    # ... build buttons with respond() callbacks ...
    self.root.wait_variable(self._response_var)

    val = self._response_var.get()
    return None if val == -999 else val  # -999 = repeat
```

`wait_variable()` blocks the calling thread until the variable changes, but doesn't start a nested mainloop. This works whether the GUI owns Tk or not. **Recommend switching to `wait_variable()` now** even though the controller doesn't exist yet — it's the same user-visible behavior, and avoids a second Tk refactor in Phase 5.

---

## Concrete Implementation: `MockParticipantGUI`

For Phase 6 (automated testing). Minimal implementation:

```python
class MockParticipantGUI(ParticipantGUI):
    """Returns pre-programmed responses for headless testing."""

    def __init__(self, response_fn):
        """
        Args:
            response_fn: callable(paradigm_state) -> int
                         Called each time get_response() is invoked.
                         Receives paradigm state dict so MockParticipant
                         can make threshold-aware decisions.
        """
        self._response_fn = response_fn
        self._state = {}

    def set_state(self, state: dict):
        """Called by paradigm before get_response() to pass current state."""
        self._state = state

    def get_response(self) -> int:
        return self._response_fn(self._state)

    def show_playing(self): pass
    def show_waiting(self): pass
    def show_fp_warning(self): pass
    def show_message(self, text): pass
    def lift(self): pass
    def destroy(self): pass
```

The actual `MockParticipant` logic (simulating a listener with a known threshold) is Phase 6 work. This class just provides the interface hook.

---

## Changes to `AdaptiveParadigm`

### Constructor — accept optional `gui` parameter:

```python
def __init__(self, params, verbose=False, gui_config=None,
             participant_id=None, show_operator_display=True,
             randomize_config_order=True, gui=None):
    ...
    # Store gui_config for reference (e.g. paradigm_setup_dialog uses it)
    self.gui_config = gui_config or self._default_gui_config()

    # GUI injection: use provided GUI or create default Tkinter GUI
    # GUI is created lazily in main() if gui=None, because the setup
    # dialog needs to run first (and it creates its own Tk root).
    self._injected_gui = gui
    self.gui = None  # Set in main()
    ...
```

### `main()` — create GUI at start, delegate:

```python
def main(self):
    # Attach operator display
    if self.show_operator_display:
        self.operator_display = get_operator_display()
        self.operator_display.attach_paradigm(self)
        self.operator_display.show()

    # Create participant GUI (or use injected one)
    if self._injected_gui is not None:
        self.gui = self._injected_gui
    else:
        self.gui = TkParticipantGUI(self.gui_config)

    # Run trial loop
    self.run_trial_loop()  # or current inline loop

    # Cleanup
    if self._aborted_by_operator:
        print("PARADIGM ABORTED BY OPERATOR — data not saved.")
    else:
        print("PARADIGM COMPLETE")
        self.write_data_to_disk()
        self._delete_temp_data()

    self.gui.destroy()
    self.gui = None
```

### Trial loop — replace direct GUI calls:

```python
# Before (current):
self.update_gui_state(trial_playing=True)
self.execute_trial()
core.wait(0.5)
self.user_input = self.get_response(trial_playing=False)

# After:
self.gui.show_playing()
self.execute_trial()
core.wait(0.5)
self.user_input = self.gui.get_response()
```

### FP warning — delegate:

```python
# In update_counters(), the FP branch:
# Before:
self.show_false_positive_warning()

# After:
self.gui.show_fp_warning()
```

### Abort/end — delegate destroy:

```python
# In notify_wrv_limit():
if choice == 'abort_paradigm':
    self._aborted_by_operator = True
    self.end_paradigm = True
    if self.gui is not None:
        self.gui.destroy()
        self.gui = None

# In check_paradigm_end_conds():
if self.config_num > self.total_num_configs:
    self.end_paradigm = True
    # Don't destroy GUI here — main() handles cleanup
```

### Delete old methods:

After extraction, remove from `AdaptiveParadigm`:
- `get_response()` — now on `TkParticipantGUI`
- `update_gui_state()` — replaced by `gui.show_playing()` / `gui.show_waiting()`
- `show_false_positive_warning()` — now `gui.show_fp_warning()`

`self.root` is gone from AdaptiveParadigm entirely.

---

## Changes to `operator_gui.py`

One coupling point to fix:

```python
# Before (line 295):
if hasattr(self.paradigm, 'root') and self.paradigm.root is not None:
    self.paradigm.root.lift()
    self.paradigm.root.focus_force()

# After:
if hasattr(self.paradigm, 'gui') and self.paradigm.gui is not None:
    self.paradigm.gui.lift()
```

---

## Changes to `paradigm_setup_dialog.py`

The setup dialog currently creates its own `tk.Tk()` root and runs independently before the paradigm's `main()`. It accesses `paradigm.gui_config` for demo section labels, but does **not** use the paradigm's GUI window. No changes needed — `gui_config` stays on AdaptiveParadigm as a data attribute.

---

## Changes to `test_*.py` Scripts

No changes required. The default path (`gui=None` → TkParticipantGUI created in `main()`) preserves current behavior. Future automated tests will pass `gui=MockParticipantGUI(...)`.

---

## File Summary

| File | Change | Risk |
|---|---|---|
| `utils/participant_gui.py` | **NEW** — `ParticipantGUI` interface, `TkParticipantGUI`, `MockParticipantGUI` stub | Low (new file) |
| `adaptive_paradigm.py` | Accept `gui=` param, delegate GUI calls, delete 3 methods, remove `self.root` | Medium |
| `operator_gui.py` | Change `paradigm.root` → `paradigm.gui.lift()` (one location) | Very low |
| `paradigm_setup_dialog.py` | No changes | None |
| All `test_*.py` | No changes | None |
| All `paradigm_*.py` | No changes (they don't touch GUI directly) | None |

---

## Implementation Order

| # | Task | Effort |
|---|------|--------|
| 1 | Create `utils/participant_gui.py` with `ParticipantGUI` interface + `TkParticipantGUI` (copy existing code from AdaptiveParadigm, adapt to class structure) | 2 hr |
| 2 | Switch `get_response()` from `mainloop()`/`quit()` to `wait_variable()` pattern | 1 hr |
| 2v | **Verify:** Run PTA with standalone `TkParticipantGUI` to confirm `wait_variable()` works correctly (response timing, keyboard shortcuts, repeat button) | 30 min |
| 3 | Wire into `AdaptiveParadigm`: add `gui=` param, delegate all GUI calls, delete old methods, remove `self.root` | 2 hr |
| 4 | Fix `operator_gui.py` coupling (`paradigm.root` → `paradigm.gui.lift()`) | 15 min |
| 5 | Add `MockParticipantGUI` stub (no-op methods, response callback) | 30 min |
| 6 | **Verify:** Run all 11 paradigms (short runs). Confirm GUI behavior identical to pre-Phase 2. | 1-2 hr |

**Total estimate:** ~7-8 hours, single focused session.

---

## Verification Strategy

- **Step 2v (wait_variable):** This is the highest-risk change. Test thoroughly with PTA: confirm keyboard shortcuts work, repeat button works, response timing is unchanged, no double-response bugs. Test on macOS specifically (Tk quirks).
- **Step 6 (full regression):** Run all 11 paradigms, short runs. Check: GUI appears, buttons work, keyboard works, FP warning shows, operator display refocuses participant window after plot update, demo mode in setup dialog still works.

---

## Open Questions

1. **`wait_variable()` on macOS/Apple Silicon:** Tk's `wait_variable()` should work the same as `mainloop()` for blocking, but Tk on macOS has quirks (especially with PTB audio). If `wait_variable()` causes issues, we can fall back to `mainloop()`/`quit()` for now and switch to `wait_variable()` in Phase 5 when the controller forces the change. Low risk but worth flagging.

2. **GUI config ownership:** `gui_config` stays on AdaptiveParadigm as a data dict. `TkParticipantGUI` receives it at construction. If the setup dialog edits `gui_config` (e.g., changes question text), this happens before `main()` creates the GUI, so the edited config is picked up automatically. No issue.

3. **Between-trial message ("..."):** Currently `get_response()` shows "..." after a response is registered (line 509-515). This brief holding message prevents double-clicks. This moves into `TkParticipantGUI.get_response()` — it's GUI-internal behavior, not paradigm logic.

4. **`show_waiting()` vs relying on `get_response()` to build UI:** Currently `get_response()` both builds the UI (buttons, labels) and blocks for input. We could keep that pattern (get_response does everything) and drop `show_waiting()` from the interface. Simpler, but less flexible for web GUIs where showing buttons and waiting for response are asynchronous. **Recommend keeping `show_waiting()` in the interface but having `TkParticipantGUI.get_response()` call it internally** — so callers only need to call `get_response()`, but web implementations can separate the two.

---

## Interaction with Later Phases

**Phase 5 (ExperimentController):** The controller creates `TkParticipantGUI(gui_config, parent=controller.root)` and passes it to each paradigm. Between paradigms, the controller can update the GUI window (show "Next paradigm" screen) without destroying it. The `wait_variable()` pattern is essential for this — `mainloop()` won't work with a shared root.

**Phase 6 (Testing):** Test scripts pass `gui=MockParticipantGUI(response_fn)`. The paradigm runs headless. `MockParticipant` logic (simulating a listener) lives in a separate class that provides the `response_fn` callback.
