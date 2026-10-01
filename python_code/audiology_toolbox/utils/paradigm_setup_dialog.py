"""
Paradigm Setup Dialogs

Provides pre-paradigm GUI dialogs for operator configuration.

Two classes:
  ParadigmSetupDialog  -- base class, used by all paradigms
                          Shows participant ID entry + parameter summary
  ThresholdSetupDialog -- extends base, used by IFMC and TMC
                          Adds frequency set selection, PTA threshold
                          loading, editable threshold/probe table

Intended call site: test_*.py scripts, before constructing the paradigm.

Future: will be called from ExperimentController instead.

Usage (IFMC / TMC):
    from utils.paradigm_setup_dialog import ThresholdSetupDialog
    dialog = ThresholdSetupDialog(
        paradigm_name="IFMC",
        params=params,
        default_freq_set_key="IFMC — Lecluyse 2013",
        db_above_threshold=24.0,
        max_amplitude=0.7,
    )
    participant_id, thresholds = dialog.show()
    # thresholds: {freq: {"threshold_dB": x, "probe_amp": y}} or None

Usage (all other paradigms):
    from utils.paradigm_setup_dialog import ParadigmSetupDialog
    dialog = ParadigmSetupDialog(paradigm_name="PTA", params=params)
    participant_id = dialog.show()
    # returns formatted ID string e.g. "P0018", or None if cancelled

Note on db_above_threshold default (24.0 dB SL):
    Lecluyse 2013 / MultiThreshold convention is 10 dB SL above the probe's
    OWN threshold (i.e. a 16 ms threshold from `abs_threshold_16`). PROLACTIN
    currently uses a long-tone PTA (500 ms) for threshold setup, which gives
    thresholds ~10-15 dB lower than 16 ms thresholds for the same listener
    (temporal integration). Using +10 dB SL on a long-tone threshold lands
    the 16 ms probe at or below detection threshold -- inaudible.
    Compensating offset: +24 dB SL produces a clearly-audible probe across
    typical listeners. TODO: implement abs_threshold_16 paradigm; once
    available, revert default to 10.0 dB SL.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, Dict, Tuple, Any

from utils.standard_frequencies import FREQUENCY_SETS
from utils.result_loader import ResultLoader
from utils.calibration import CalibrationManager
from audio_devices import get_current_device
from trial_player import TrialPlayer


# ---------------------------------------------------------------------------
# Calibration advisory thresholds
# ---------------------------------------------------------------------------

# Minimum SPL ceiling (dB) for LDL to be meaningful. A profile whose ceiling
# sits below this cannot drive levels high enough to reach loudness
# discomfort, so LDL is out of scope on that transducer (currently the ER-2
# insert earphones at 87 dB -- see open issue L23). Advisory only, never
# blocking: the operator may still start the run.
#
# NOTE: the ER-2 ceiling is a consequence of its 10 ohm impedance
# current-limiting the RME line outputs. Once the ER-2 is moved onto the same
# headphone output as the other transducers (via an impedance-appropriate
# splitter), that ceiling rises and this advisory should stop firing on its
# own -- no code change needed.
LDL_MIN_CEILING_DB = 100.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_participant_id(raw: str) -> Optional[str]:
    """
    Convert numeric or already-formatted input to canonical form.

    Format: <LETTER><####>, a single capital letter + 4 digits.

    Rules:
      "18"    -> "P0018"   (digit-only input defaults to letter "P")
      "p18"   -> "P0018"
      "P0018" -> "P0018"
      "A18"   -> "A0018"
      "a0018" -> "A0018"
      ""      -> None

    Returns None if input cannot be parsed (e.g. multiple letters,
    non-digit number part, or more than 4 digits).
    """
    raw = raw.strip().upper()
    if not raw:
        return None
    if raw[0].isascii() and raw[0].isalpha():
        letter = raw[0]
        num_part = raw[1:]
    else:
        # Digit-only input: default to "P" for load-field back-compat.
        letter = "P"
        num_part = raw
    if not (num_part.isascii() and num_part.isdecimal()):
        return None
    if len(num_part) > 4:
        return None
    return letter + num_part.zfill(4)


def _center_window(root: tk.Tk) -> None:
    """Center a Tk window on the screen."""
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


class _Tooltip:
    """
    Minimal hover tooltip for a Tk widget.

    Usage:
        _Tooltip(some_label, "Helpful text shown on hover")
    """

    def __init__(self, widget: tk.Widget, text: str,
                 delay_ms: int = 400, wraplength: int = 360):
        self._widget = widget
        self._text = text
        self._delay = delay_ms
        self._wraplength = wraplength
        self._tip: Optional[tk.Toplevel] = None
        self._after_id: Optional[str] = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, _event=None) -> None:
        self._cancel_pending()
        self._after_id = self._widget.after(self._delay, self._show)

    def _on_leave(self, _event=None) -> None:
        self._cancel_pending()
        self._hide()

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self) -> None:
        if self._tip is not None:
            return
        x = self._widget.winfo_rootx() + 20
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tip = tk.Toplevel(self._widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._tip, text=self._text,
            font=("Arial", 9), justify="left",
            bg="#ffffe0", fg="black",
            relief="solid", borderwidth=1,
            wraplength=self._wraplength, padx=6, pady=4,
        ).pack()

    def _hide(self) -> None:
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


# ---------------------------------------------------------------------------
# ParadigmSetupDialog  (base — all paradigms)
# ---------------------------------------------------------------------------

class ParadigmSetupDialog:
    """
    Pre-paradigm setup dialog shown before every paradigm run.

    Collects participant ID and provides editable fields for all paradigm
    parameters (inner var data dict + outer var value lists).

    On Accept, the params dict is mutated in-place before the dialog closes,
    so the calling test script sees the updated values immediately.

    Returns participant_id string on Accept, None on Cancel.

    Optional: pass default_freq_set_key to pre-select a named frequency set
    in the dropdown for any outer var named 'fc'.
    """

    # Colours
    _C_BG        = "#f5f5f5"
    _C_HEADER    = "#2c3e50"
    _C_ACCENT    = "#2980b9"
    _C_OK        = "#27ae60"
    _C_WARN      = "#e67e22"
    _C_ERR       = "#c0392b"
    _C_ROW_ALT   = "#eaf0fb"
    _C_ROW_NORM  = "#ffffff"

    def __init__(self,
                 paradigm_name: str,
                 params: Dict[str, Any],
                 paradigm,
                 window_title: str = None,
                 default_freq_set_key: str = "Audiometric — ISO 389"):
        self.paradigm_name = paradigm_name
        self.params = params
        self.paradigm = paradigm
        self.window_title = window_title or f"{paradigm_name} — Paradigm Setup"
        self._default_freq_set_key = default_freq_set_key

        self._result_pid: Optional[str] = None
        self._root: Optional[tk.Tk] = None

        # Calibration profile picker. The dialog is the single source of truth
        # for which calibration this run uses: selected_calibration starts as
        # the paradigm's and is rebuilt whenever the operator picks a different
        # profile. Test scripts read it back after show(). The selection is
        # transient -- it never rewrites the default in config/DEFAULTS.py.
        self.selected_calibration = getattr(paradigm, "calibration", None)
        self._profile_var: Optional[tk.StringVar] = None
        self._profile_combo = None
        self._profile_status_lbl: Optional[tk.Label] = None
        self._profile_advisory_lbl: Optional[tk.Label] = None
        self._last_good_profile: Optional[str] = None

        # Start button handle, so the calibration gate can enable/disable it.
        self._start_btn: Optional[tk.Button] = None

        # dB HL warning, rebuilt live on profile change (a new profile may or
        # may not carry a RETSPL table).
        self._hl_warn_frame: Optional[tk.Frame] = None
        self._hl_warn_lbl: Optional[tk.Label] = None

        # Populated in _build_inner_var_editor / _build_outer_var_editors
        self._inner_entries: Dict[str, tk.StringVar] = {}
        self._outer_entries: Dict[str, tk.StringVar] = {}  # keyed by "outer_N"
        self._outer_fc_set_vars: Dict[str, tk.StringVar] = {}  # keyed by "outer_N"

        # Populated in _build_demo_section
        self._demo_entries: Dict[str, tk.StringVar] = {}  # keyed by var name

        # Populated in _build_target_level_editor (AM/FM only; present iff
        # params carries a "target_level" array). Per-fc carrier level fields,
        # keyed by fc value; rebuilt live when the fc set changes so the editor
        # and the fc outer var stay co-indexed.
        self._target_entries: Dict[Any, tk.StringVar] = {}   # keyed by fc value
        self._target_values_by_freq: Dict[Any, str] = {}     # edits preserved across rebuild
        self._target_defaults: Dict[Any, float] = {}         # seed from params["target_level"]
        self._target_rows: Optional[tk.Frame] = None         # container rebuilt in place

        # Scrollable-layout handles (populated in _build_ui). Header and button
        # bar are pinned; variable sections live in a scrollable middle so the
        # window never overflows the screen.
        self._header_frame: Optional[tk.Frame] = None
        self._btn_bar: Optional[tk.Frame] = None
        self._scroll_canvas: Optional[tk.Canvas] = None
        self._scroll_inner: Optional[tk.Frame] = None
        self._scroll_hint: Optional[tk.Label] = None       # "scroll for more" strip

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def show(self) -> Optional[str]:
        """Show dialog (blocking). Returns formatted participant ID or None."""
        self._root = tk.Tk()
        self._root.title(self.window_title)
        self._root.configure(bg=self._C_BG)
        # Width fixed; height resizable so the user can enlarge if desired. The
        # scrollable middle keeps everything reachable even on short screens.
        self._root.resizable(False, True)

        self._build_ui(self._root)

        self._fit_to_screen()
        self._root.mainloop()
        return self._result_pid

    def _fit_to_screen(self) -> None:
        """Size the window to its content but cap the height to the screen, and
        centre it. With the scrollable middle, capping never hides the pinned
        Start/Cancel bar -- content scrolls instead. Falls back to plain
        centring if the scroll layout is not present (e.g. a subclass)."""
        root = self._root
        root.update_idletasks()

        if self._scroll_inner is None or self._header_frame is None or self._btn_bar is None:
            _center_window(root)
            return

        content_h = self._scroll_inner.winfo_reqheight()
        header_h = self._header_frame.winfo_reqheight()
        btn_h = self._btn_bar.winfo_reqheight()
        content_w = self._scroll_inner.winfo_reqwidth()

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()

        # Leave headroom for the OS menu bar / dock / window chrome.
        margin = 120
        desired_h = header_h + content_h + btn_h + 4
        win_h = min(desired_h, sh - margin)
        win_w = content_w + 24  # scrollbar + padding

        x = max(0, (sw - win_w) // 2)
        y = max(0, (sh - win_h) // 2)
        root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        root.update_idletasks()
        self._update_scroll_hint()

    def _update_scroll_hint(self, *_args) -> None:
        """Show the 'scroll down for more' strip only while content extends past
        the visible bottom; hide it at the bottom or when nothing overflows."""
        canvas = self._scroll_canvas
        hint = self._scroll_hint
        if canvas is None or hint is None:
            return
        try:
            _top, bottom = canvas.yview()
        except Exception:
            return
        more_below = bottom < 0.999
        mapped = bool(hint.winfo_ismapped())
        if more_below and not mapped:
            # Sit just above the pinned button bar (before the canvas in the
            # packing order keeps it between the canvas and that bar).
            hint.pack(side=tk.BOTTOM, fill=tk.X, before=canvas)
        elif not more_below and mapped:
            hint.pack_forget()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, root: tk.Tk) -> None:
        # Header pinned to the top.
        self._build_header(root)

        # Start/Cancel pinned to a fixed bottom bar so they stay reachable no
        # matter how tall the variable sections grow (per-fc target rows can
        # push the content past the screen height).
        btn_bar = tk.Frame(root, bg=self._C_BG)
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._btn_bar = btn_bar

        # Scrollable middle: a canvas + vertical scrollbar hosting an inner
        # frame. Every variable/config section builds into the inner frame, so
        # the dialog scrolls instead of overflowing the screen.
        canvas = tk.Canvas(root, bg=self._C_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # "More below" affordance: a thin strip just above the button bar,
        # shown only while content extends past the visible area (hidden once
        # scrolled to the bottom or when nothing overflows). Created here,
        # packed/unpacked by _update_scroll_hint.
        self._scroll_hint = tk.Label(
            root,
            text="\u25bc  Scroll down for more options  \u25bc",
            font=("Arial", 9, "bold"),
            fg=self._C_ACCENT, bg=self._C_ROW_ALT, pady=3)

        # Wrap the scrollbar callback so the hint re-evaluates on every scroll.
        def _on_yscroll(*args):
            vsb.set(*args)
            self._update_scroll_hint()
        canvas.configure(yscrollcommand=_on_yscroll)

        inner = tk.Frame(canvas, bg=self._C_BG)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        self._scroll_canvas = canvas
        self._scroll_inner = inner

        def _sync_scrollregion(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            self._update_scroll_hint()
        inner.bind("<Configure>", _sync_scrollregion)

        def _match_inner_width(e):
            canvas.itemconfigure(inner_id, width=e.width)
            self._update_scroll_hint()
        canvas.bind("<Configure>", _match_inner_width)

        # Cross-platform mousewheel scroll while the pointer is over the canvas
        # (Mac/Windows use <MouseWheel>; Linux uses Button-4/5). Bound on enter,
        # released on leave, so it does not hijack the wheel elsewhere.
        def _on_wheel(event):
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

        def _bind_wheel(_e=None):
            canvas.bind_all("<MouseWheel>", _on_wheel)
            canvas.bind_all("<Button-4>", _on_wheel)
            canvas.bind_all("<Button-5>", _on_wheel)

        def _unbind_wheel(_e=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        # Variable/config sections -> scrollable inner frame.
        self._build_audio_device_section(inner)
        self._build_calibration_section(inner)
        self._build_participant_section(inner)
        self._build_inner_var_editor(inner)
        self._build_outer_var_editors(inner)
        self._build_target_level_editor(inner)
        self._build_demo_section(inner)

        # Buttons -> fixed bottom bar.
        self._build_buttons(btn_bar)

        # Start button exists only now, so apply the calibration gate here.
        self._refresh_start_gate()

    def _build_header(self, parent: tk.Widget) -> None:
        hdr = tk.Frame(parent, bg=self._C_HEADER, pady=12)
        hdr.pack(fill=tk.X)
        self._header_frame = hdr
        tk.Label(hdr,
                 text=f"  {self.paradigm_name}  —  Pre-Test Setup",
                 font=("Arial", 16, "bold"),
                 fg="white", bg=self._C_HEADER
                 ).pack(side=tk.LEFT, padx=16)

    def _build_audio_device_section(self, parent: tk.Widget) -> None:
        device = get_current_device()
        if device:
            device_text = device
            tooltip_text = (
                "Selected automatically by substring match against the "
                "device list at startup.\n\n"
                "To change the audio device:\n"
                "  1. Click Cancel\n"
                "  2. Edit config/DEFAULTS.py -> "
                "'audio_device_substrings'\n"
                "  3. Re-run the test script\n\n"
                "(Note: on Windows the device name may be prefixed with a "
                "number, e.g. '(2- ...)' -- that number can change when "
                "devices are added/removed, so prefer brand/model substrings "
                "like 'Fireface', 'UCX'.)"
            )
            value_color = self._C_ACCENT
        else:
            device_text = "(system default \u2014 no substring match)"
            tooltip_text = (
                "No device matched the configured substrings, so PsychoPy "
                "will fall back to the system default output.\n\n"
                "To select a specific device:\n"
                "  1. Click Cancel\n"
                "  2. Edit config/DEFAULTS.py -> "
                "'audio_device_substrings'\n"
                "  3. Re-run the test script"
            )
            value_color = self._C_WARN

        frame = tk.Frame(parent, bg=self._C_BG, pady=4)
        frame.pack(fill=tk.X, padx=16, pady=(8, 0))

        row = tk.Frame(frame, bg=self._C_BG)
        row.pack(fill=tk.X)

        tk.Label(row, text="Audio output device:",
                 font=("Arial", 10, "bold"), fg="black", bg=self._C_BG,
                 anchor="w").pack(side=tk.LEFT)

        value_lbl = tk.Label(row, text=device_text,
                             font=("Arial", 10), fg=value_color,
                             bg=self._C_BG, anchor="w")
        value_lbl.pack(side=tk.LEFT, padx=(6, 4))

        info_lbl = tk.Label(row, text="\u24d8",  # circled "i"
                            font=("Arial", 11, "bold"),
                            fg=self._C_ACCENT, bg=self._C_BG,
                            cursor="question_arrow")
        info_lbl.pack(side=tk.LEFT)

        _Tooltip(info_lbl, tooltip_text)
        _Tooltip(value_lbl, tooltip_text)

    def _build_calibration_section(self, parent: tk.Widget) -> None:
        """Calibration profile row: dropdown picker + live status/advisory.

        The operator picks the profile matching the headphones physically
        connected. The selection applies to THIS run only -- it never rewrites
        'default_headphone_calibration_profile' in config/DEFAULTS.py.

        Degrades to a read-only value label (mirroring the audio-device row)
        when a picker is not possible: no calibration object, an unreadable
        config path, or a config carrying only one profile.
        """
        cal = self.selected_calibration

        frame = tk.Frame(parent, bg=self._C_BG, pady=4)
        frame.pack(fill=tk.X, padx=16, pady=(6, 0))

        row = tk.Frame(frame, bg=self._C_BG)
        row.pack(fill=tk.X)

        tk.Label(row, text="Calibration profile:",
                 font=("Arial", 10, "bold"), fg="black", bg=self._C_BG,
                 anchor="w").pack(side=tk.LEFT)

        tooltip_text = (
            "Headphone calibration profile used for THIS run.\n\n"
            "Pick the profile matching the headphones physically connected "
            "to the interface.\n\n"
            "The selection is transient: it does NOT change the default in\n"
            "config/DEFAULTS.py -> 'default_headphone_calibration_profile'."
        )

        profiles = []
        if cal is not None:
            try:
                profiles = list(cal.available_profiles)
            except Exception:
                profiles = []

        can_pick = False
        if cal is not None and len(profiles) > 1:
            try:
                can_pick = Path(cal.config_path).is_file()
            except Exception:
                can_pick = False

        if can_pick:
            self._last_good_profile = cal.active_profile
            self._profile_var = tk.StringVar(value=cal.active_profile)
            combo = ttk.Combobox(row, textvariable=self._profile_var,
                                 values=profiles, state="readonly",
                                 font=("Arial", 10), width=34)
            combo.pack(side=tk.LEFT, padx=(6, 4))
            combo.bind("<<ComboboxSelected>>", self._on_profile_change)
            self._profile_combo = combo
            anchor_widget = combo
        else:
            if cal is not None:
                value_text = cal.active_profile
                value_color = self._C_ACCENT
            else:
                value_text = "(no calibration loaded)"
                value_color = self._C_WARN
            anchor_widget = tk.Label(row, text=value_text,
                                     font=("Arial", 10), fg=value_color,
                                     bg=self._C_BG, anchor="w")
            anchor_widget.pack(side=tk.LEFT, padx=(6, 4))

        info_lbl = tk.Label(row, text="\u24d8",  # circled "i"
                            font=("Arial", 11, "bold"),
                            fg=self._C_ACCENT, bg=self._C_BG,
                            cursor="question_arrow")
        info_lbl.pack(side=tk.LEFT)

        _Tooltip(info_lbl, tooltip_text)
        _Tooltip(anchor_widget, tooltip_text)

        # Live calibration-state line (green / orange / red).
        self._profile_status_lbl = tk.Label(
            frame, text="", font=("Arial", 9, "bold"),
            bg=self._C_BG, anchor="w", justify="left")
        self._profile_status_lbl.pack(fill=tk.X, padx=(2, 0))

        # Non-blocking paradigm/profile advisory (see _profile_advisory).
        self._profile_advisory_lbl = tk.Label(
            frame, text="", font=("Arial", 9), fg=self._C_WARN,
            bg=self._C_BG, anchor="w", justify="left", wraplength=620)
        self._profile_advisory_lbl.pack(fill=tk.X, padx=(2, 0))

        self._refresh_profile_status()

    def _refresh_hl_warning(self) -> None:
        """Show/hide the 'dB HL but no RETSPL table' warning for the selection.

        Re-evaluated on profile change: RETSPL availability is per-profile.
        No-op for paradigms whose inner-var editor was built without the
        warning container (i.e. before it exists).
        """
        if self._hl_warn_lbl is None or self._hl_warn_frame is None:
            return
        units = getattr(self.paradigm, "operator_units", "dB SPL")
        cal = self.selected_calibration
        needs_warning = (units == "dB HL"
                         and (cal is None
                              or not getattr(cal, "hl_calibrated", False)))
        if needs_warning:
            if not self._hl_warn_lbl.winfo_ismapped():
                self._hl_warn_lbl.pack(fill=tk.X, pady=(0, 4))
        else:
            self._hl_warn_lbl.pack_forget()

    def _profile_advisory(self, paradigm_name: str, calibration) -> Optional[str]:
        """Advisory string for known-problematic paradigm/profile pairs, else None.

        Deliberately a small seeded ruleset rather than a general per-paradigm
        compatibility engine (that would need profile-allowlist metadata).
        Advisories are informational only and never block the run.
        """
        if calibration is None:
            return None
        try:
            ceiling = float(calibration.max_spl)
        except Exception:
            return None

        if ((paradigm_name or "").strip().upper() == "LDL"
                and ceiling < LDL_MIN_CEILING_DB):
            return (
                f"Advisory: this profile's SPL ceiling is {ceiling:g} dB, below "
                f"the {LDL_MIN_CEILING_DB:g} dB LDL needs to reach loudness "
                f"discomfort. LDL is out of scope for this transducer."
            )
        return None

    def _refresh_profile_status(self) -> None:
        """Repaint the calibration status + advisory lines from the selection."""
        cal = self.selected_calibration

        if self._profile_status_lbl is not None:
            if cal is None:
                text, colour = "No calibration loaded.", self._C_ERR
            elif not cal.spl_calibrated:
                text = ("No SPL calibration data for this profile "
                        "- cannot start.")
                colour = self._C_ERR
            elif not cal.fir_calibrated:
                text = ("SPL calibrated; no FIR inverse filter "
                        "- no headphone frequency correction.")
                colour = self._C_WARN
            else:
                text, colour = "SPL + FIR calibrated.", self._C_OK
            self._profile_status_lbl.config(text=text, fg=colour)

        if self._profile_advisory_lbl is not None:
            advisory = self._profile_advisory(self.paradigm_name, cal)
            self._profile_advisory_lbl.config(text=advisory or "")

    def _on_profile_change(self, event=None) -> None:
        """Rebuild the CalibrationManager for the newly picked profile.

        On failure the previous profile is kept and the dropdown reverts, so
        the dialog always holds a loadable calibration.
        """
        if self._profile_var is None:
            return
        chosen = self._profile_var.get()
        cal = self.selected_calibration
        if cal is None or chosen == getattr(cal, "active_profile", None):
            return

        try:
            new_cal = CalibrationManager(cal.config_path, profile=chosen)
        except Exception as exc:
            messagebox.showwarning(
                "Calibration Profile",
                f"Could not load profile '{chosen}':\n\n{exc}\n\n"
                f"Keeping '{self._last_good_profile}'.",
                parent=self._root
            )
            if self._last_good_profile is not None:
                self._profile_var.set(self._last_good_profile)
            return

        self.selected_calibration = new_cal
        self._last_good_profile = new_cal.active_profile
        # Echo back the canonical spelling resolved by CalibrationManager.
        self._profile_var.set(new_cal.active_profile)

        # Re-wire the demo paradigm so demo playback uses the new profile.
        setter = getattr(self.paradigm, "set_calibration", None)
        if callable(setter):
            setter(new_cal)

        self._refresh_profile_status()
        self._refresh_hl_warning()
        self._refresh_start_gate()
        self._on_calibration_changed()

    def _on_calibration_changed(self) -> None:
        """Hook for subclasses to refresh anything derived from calibration.

        No-op in the base dialog (nothing here is calibration-derived).
        Overridden by ThresholdSetupDialog, whose probe amplitudes come from
        spl_to_amplitude and so go stale when the profile changes.
        """
        pass

    def _refresh_start_gate(self) -> None:
        """Enable/disable Start according to the selected profile's SPL data.

        A missing FIR filter warns but does not gate (SPL math still works).
        Missing SPL data does gate: level conversion would fail at the first
        trial. Dialogs opened without any calibration are left enabled
        (unchanged legacy behaviour).
        """
        if self._start_btn is None:
            return
        cal = self.selected_calibration
        if cal is None:
            self._start_btn.config(state=tk.NORMAL)
            return
        self._start_btn.config(
            state=(tk.NORMAL if cal.spl_calibrated else tk.DISABLED))

    def _calibration_gate_ok(self) -> bool:
        """True if the run may start.

        Mirrors _refresh_start_gate, and is also checked in _on_accept because
        the <Return> key binding reaches _on_accept without going through the
        (possibly disabled) Start button.
        """
        cal = self.selected_calibration
        if cal is None or cal.spl_calibrated:
            return True
        messagebox.showerror(
            "Calibration Required",
            f"Profile '{cal.active_profile}' has no SPL calibration data.\n\n"
            "Select a calibrated profile before starting.",
            parent=self._root
        )
        return False

    def _build_participant_section(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(parent, text="Participant",
                              font=("Arial", 11, "bold"),
                              fg="black", bg=self._C_BG, pady=8, padx=12)
        frame.pack(fill=tk.X, padx=16, pady=(12, 6))

        row = tk.Frame(frame, bg=self._C_BG)
        row.pack(fill=tk.X)

        tk.Label(row, text="Participant number:",
                 font=("Arial", 11), fg="black", bg=self._C_BG,
                 width=20, anchor="w").pack(side=tk.LEFT)

        self._letter_var = tk.StringVar(value="P")
        self._number_var = tk.StringVar()

        vc_letter = (frame.register(self._vc_letter), "%P")
        vc_number = (frame.register(self._vc_number), "%P")

        letter_entry = tk.Entry(row, textvariable=self._letter_var,
                                font=("Arial", 13, "bold"), width=3,
                                justify="center",
                                validate="key", validatecommand=vc_letter)
        letter_entry.pack(side=tk.LEFT, padx=(6, 0))

        number_entry = tk.Entry(row, textvariable=self._number_var,
                                font=("Arial", 13, "bold"), width=7,
                                validate="key", validatecommand=vc_number)
        number_entry.pack(side=tk.LEFT, padx=(2, 6))
        number_entry.bind("<FocusOut>", self._on_number_blur)
        number_entry.focus()

        self._pid_preview = tk.Label(row, text="",
                                     font=("Arial", 11), fg=self._C_ACCENT,
                                     bg=self._C_BG)
        self._pid_preview.pack(side=tk.LEFT, padx=8)

        tk.Label(frame,
                 text="Letter + number (e.g. P 18 \u2192 P0018). Letter is forced "
                      "uppercase; number is zero-padded to 4 digits.",
                 font=("Arial", 9), fg="gray", bg=self._C_BG
                 ).pack(anchor="w", pady=(4, 0))

        self._letter_var.trace_add("write", self._on_letter_change)
        self._number_var.trace_add("write", self._on_pid_change)

    @staticmethod
    def _vc_letter(proposed: str) -> bool:
        """Allow only an empty field or a single ASCII letter."""
        return proposed == "" or (
            len(proposed) == 1 and proposed.isascii() and proposed.isalpha()
        )

    @staticmethod
    def _vc_number(proposed: str) -> bool:
        """Allow only an empty field or up to 4 ASCII decimal digits."""
        return proposed == "" or (
            proposed.isascii() and proposed.isdecimal() and len(proposed) <= 4
        )

    def _raw_pid(self) -> str:
        """Combined letter + number as a single raw string for parsing."""
        return self._letter_var.get() + self._number_var.get()

    def _on_letter_change(self, *_) -> None:
        cur = self._letter_var.get()
        up = cur.upper()
        if cur != up:
            self._letter_var.set(up)  # re-triggers trace; up == up so no loop
            return
        self._on_pid_change()

    def _on_number_blur(self, _event=None) -> None:
        cur = self._number_var.get().strip()
        if cur:
            self._number_var.set(cur.zfill(4))

    def _on_pid_change(self, *_) -> None:
        fmt = format_participant_id(self._raw_pid())
        if fmt:
            self._pid_preview.config(text=f"\u2192 {fmt}", fg=self._C_ACCENT)
            # Subclass hook: sync load field when participant field changes
            self._on_pid_synced(fmt)
        else:
            self._pid_preview.config(text="", fg=self._C_ACCENT)

    def _on_pid_synced(self, formatted_pid: str) -> None:
        """Override in subclasses to react to participant ID changes."""
        pass

    def _build_inner_var_editor(self, parent: tk.Widget) -> None:
        """Editable grid for the inner variable's data dict."""
        inner_vs = self.params.get("inner")
        if inner_vs is None or not isinstance(inner_vs.data, dict):
            return

        # Operator-facing level unit for this run (fixed by paradigm config).
        # Absolute levels (start/min/max) are entered/interpreted in this unit;
        # step sizes are dB increments and are unit-agnostic.
        units = getattr(self.paradigm, "operator_units", "dB SPL")
        level_keys = ("start", "min", "max")

        frame = tk.LabelFrame(parent,
                              text=f"Inner Variable — {inner_vs.name}",
                              font=("Arial", 11, "bold"),
                              fg="black", bg=self._C_BG, pady=8, padx=12)
        frame.pack(fill=tk.X, padx=16, pady=(6, 2))

        # Mode note: make the active unit explicit (it cannot be changed here).
        tk.Label(frame,
                 text=f"Levels (start / min / max) entered in: {units}  "
                      f"(set in paradigm config)",
                 font=("Arial", 9, "italic"), fg="#333333", bg=self._C_BG,
                 anchor="w").pack(fill=tk.X, pady=(0, 4))

        # dB HL warning lives in an always-packed container so it can be shown
        # or hidden in place when the operator switches calibration profile
        # (a different profile may or may not carry a RETSPL table). An empty
        # container collapses to zero height.
        self._hl_warn_frame = tk.Frame(frame, bg=self._C_BG)
        self._hl_warn_frame.pack(fill=tk.X)
        self._hl_warn_lbl = tk.Label(
            self._hl_warn_frame,
            text="WARNING: dB HL selected but the active profile has "
                 "no RETSPL table - the run will fail to start.",
            font=("Arial", 9, "bold"), fg="#922b21", bg=self._C_BG,
            anchor="w")
        self._refresh_hl_warning()

        grid = tk.Frame(frame, bg=self._C_BG)
        grid.pack(fill=tk.X)

        for row_idx, (key, val) in enumerate(inner_vs.data.items()):
            label_txt = f"{key} ({units}):" if key in level_keys else f"{key}:"
            tk.Label(grid, text=label_txt,
                     font=("Arial", 10), fg="black", bg=self._C_BG,
                     anchor="e", width=22
                     ).grid(row=row_idx, column=0, sticky="e", pady=2, padx=(0, 6))

            var = tk.StringVar(value=str(val))
            self._inner_entries[key] = var
            tk.Entry(grid, textvariable=var,
                     font=("Arial", 10), width=14
                     ).grid(row=row_idx, column=1, sticky="w", pady=2)

    def _build_outer_var_editors(self, parent: tk.Widget) -> None:
        """One editable section per outer_N variable."""
        outer_keys = [k for k in self.params if k.startswith("outer_")]
        if not outer_keys:
            return

        freq_set_keys = list(FREQUENCY_SETS.keys())

        for key in sorted(outer_keys):
            vs = self.params[key]
            frame = tk.LabelFrame(parent,
                                  text=f"Outer Variable — {vs.name}",
                                  font=("Arial", 11, "bold"),
                                  fg="black", bg=self._C_BG, pady=8, padx=12)
            frame.pack(fill=tk.X, padx=16, pady=2)

            is_fc = (vs.name == "fc")

            if is_fc:
                # Frequency-set dropdown
                row_top = tk.Frame(frame, bg=self._C_BG)
                row_top.pack(fill=tk.X, pady=(0, 4))
                tk.Label(row_top, text="Frequency set:",
                         font=("Arial", 10), fg="black", bg=self._C_BG,
                         width=16, anchor="w"
                         ).pack(side=tk.LEFT)

                set_var = tk.StringVar(value=self._default_freq_set_key)
                self._outer_fc_set_vars[key] = set_var

                cb = ttk.Combobox(row_top, textvariable=set_var,
                                  values=freq_set_keys, state="readonly", width=30)
                cb.pack(side=tk.LEFT, padx=4)

            # Comma-separated values field
            row_vals = tk.Frame(frame, bg=self._C_BG)
            row_vals.pack(fill=tk.X)
            tk.Label(row_vals, text="Values:",
                     font=("Arial", 10), fg="black", bg=self._C_BG,
                     width=16, anchor="w"
                     ).pack(side=tk.LEFT)

            if is_fc:
                # Initialise from the named set so dropdown and values field agree
                init_vals = FREQUENCY_SETS.get(self._default_freq_set_key, vs.data)
            else:
                init_vals = vs.data
            csv_str = ", ".join(str(v) for v in init_vals) if isinstance(init_vals, list) else str(init_vals)
            val_var = tk.StringVar(value=csv_str)
            self._outer_entries[key] = val_var

            tk.Entry(row_vals, textvariable=val_var,
                     font=("Arial", 10), width=50
                     ).pack(side=tk.LEFT, padx=4)

            if is_fc:
                # Wire dropdown → populate values field
                def _on_set_change(event=None, _key=key, _val_var=val_var, _set_var=set_var):
                    freqs = FREQUENCY_SETS.get(_set_var.get(), [])
                    _val_var.set(", ".join(str(f) for f in freqs))
                cb.bind("<<ComboboxSelected>>", _on_set_change)

    # ------------------------------------------------------------------
    # Per-fc target level editor (AM/FM)
    # ------------------------------------------------------------------

    @staticmethod
    def _fc_key(f):
        """Normalise an fc value to a stable dict key (float where possible)."""
        try:
            return float(f)
        except (TypeError, ValueError):
            return f

    def _current_fc_list(self, fc_key):
        """Current fc values, read from the live fc entry (source of truth the
        user sees) and falling back to params. Numeric where parseable."""
        if fc_key is not None and fc_key in self._outer_entries:
            raw = self._outer_entries[fc_key].get()
            out = []
            for tok in raw.split(","):
                tok = tok.strip()
                if not tok:
                    continue
                try:
                    out.append(float(tok))
                except ValueError:
                    out.append(tok)
            return out
        vs = self.params.get(fc_key) if fc_key else None
        return list(vs.data) if vs is not None else []

    def _build_target_level_editor(self, parent: tk.Widget) -> None:
        """One dB SPL field per carrier frequency (AM/FM only).

        Rendered ONLY when params carries a "target_level" array, so every other
        paradigm using this dialog is untouched. The level list is co-indexed
        with the fc outer var (level[i] pairs with fc[i]); the rows are rebuilt
        live whenever the fc set/values change, which IS the mechanism that keeps
        the two in lockstep. Every field must be filled on accept.
        """
        target_vs = self.params.get("target_level")
        if target_vs is None:
            return

        fc_key = next((k for k in self.params
                       if k.startswith("outer_")
                       and getattr(self.params[k], "name", None) == "fc"), None)

        label = getattr(target_vs, "label", "") or getattr(target_vs, "name", "Target Level")
        units = getattr(target_vs, "units", "") or "dB SPL"

        frame = tk.LabelFrame(parent,
                              text=f"Per-Frequency Target Level \u2014 {label} ({units})",
                              font=("Arial", 11, "bold"),
                              fg="black", bg=self._C_BG, pady=8, padx=12)
        frame.pack(fill=tk.X, padx=16, pady=2)

        tk.Label(frame,
                 text="One level per carrier frequency (co-indexed with fc). "
                      "Adapts automatically when you change the frequency set.",
                 font=("Arial", 9), fg="#555555", bg=self._C_BG,
                 anchor="w", justify=tk.LEFT
                 ).pack(fill=tk.X, pady=(0, 4))

        self._target_rows = tk.Frame(frame, bg=self._C_BG)
        self._target_rows.pack(fill=tk.X)

        # Seed defaults from the supplied target_level array (fallback 60),
        # co-indexed with the initial fc list.
        self._target_defaults = {}
        existing = list(getattr(target_vs, "data", []) or [])
        for i, f in enumerate(self._current_fc_list(fc_key)):
            self._target_defaults[self._fc_key(f)] = (
                existing[i] if i < len(existing) else 60.0)

        self._rebuild_target_rows(fc_key)

        # Live rebuild when fc changes (dropdown .set() or manual typing both
        # write the fc StringVar). Focus stays in the fc entry, so re-rendering
        # the rows below does not disturb the user.
        if fc_key is not None and fc_key in self._outer_entries:
            self._outer_entries[fc_key].trace_add(
                "write", lambda *_: self._rebuild_target_rows(fc_key))

    def _rebuild_target_rows(self, fc_key) -> None:
        """(Re)build one dB field per current fc, preserving prior edits by
        frequency. New freqs seed to their default (60); removed freqs drop."""
        if self._target_rows is None:
            return

        # Snapshot current field contents so edits survive the rebuild.
        for fk, var in self._target_entries.items():
            self._target_values_by_freq[fk] = var.get()

        for child in self._target_rows.winfo_children():
            child.destroy()
        self._target_entries = {}

        for f in self._current_fc_list(fc_key):
            fk = self._fc_key(f)
            val = self._target_values_by_freq.get(fk)
            if val is None:
                val = f"{self._target_defaults.get(fk, 60.0):g}"

            row = tk.Frame(self._target_rows, bg=self._C_BG)
            row.pack(fill=tk.X, pady=1)
            freq_lbl = f"{f:g}" if isinstance(f, (int, float)) else str(f)
            tk.Label(row, text=f"{freq_lbl} Hz:",
                     font=("Arial", 10), fg="black", bg=self._C_BG,
                     width=12, anchor="w").pack(side=tk.LEFT)
            v = tk.StringVar(value=val)
            tk.Entry(row, textvariable=v, font=("Arial", 10), width=10
                     ).pack(side=tk.LEFT, padx=4)
            self._target_entries[fk] = v

    def _build_demo_section(self, parent: tk.Widget) -> None:
        """Editable demo trial fields + Play Demo button."""
        frame = tk.LabelFrame(parent, text="Demo Trial",
                              font=("Arial", 11, "bold"),
                              fg="black", bg=self._C_BG, pady=8, padx=12)
        frame.pack(fill=tk.X, padx=16, pady=(6, 2))

        grid = tk.Frame(frame, bg=self._C_BG)
        grid.pack(side=tk.LEFT, fill=tk.X, expand=True)

        row_idx = 0

        # Inner var — default to 'start' value
        inner_vs = self.params.get("inner")
        if inner_vs is not None and isinstance(inner_vs.data, dict):
            default_val = inner_vs.data.get('start', 0.0)
            tk.Label(grid, text=f"{inner_vs.name}  (inner):",
                     font=("Arial", 10), fg="black", bg=self._C_BG,
                     anchor="e", width=24
                     ).grid(row=row_idx, column=0, sticky="e", pady=2, padx=(0, 6))
            var = tk.StringVar(value=str(default_val))
            self._demo_entries[inner_vs.name] = var
            tk.Entry(grid, textvariable=var,
                     font=("Arial", 10), width=14
                     ).grid(row=row_idx, column=1, sticky="w", pady=2)
            row_idx += 1

        # Outer vars — default to first value in each list
        outer_keys = sorted(k for k in self.params if k.startswith("outer_"))
        for key in outer_keys:
            vs = self.params[key]
            first_val = vs.data[0] if isinstance(vs.data, list) and vs.data else ""
            tk.Label(grid, text=f"{vs.name}  (outer):",
                     font=("Arial", 10), fg="black", bg=self._C_BG,
                     anchor="e", width=24
                     ).grid(row=row_idx, column=0, sticky="e", pady=2, padx=(0, 6))
            var = tk.StringVar(value=str(first_val))
            self._demo_entries[vs.name] = var
            tk.Entry(grid, textvariable=var,
                     font=("Arial", 10), width=14
                     ).grid(row=row_idx, column=1, sticky="w", pady=2)
            row_idx += 1

        # Duration (s) -- driven by the paradigm's demo_duration_attr, if set.
        # Restores the demo trial-length field. Skipped when the attr is None
        # (GAP, IFMC, TMC) or already shown above as an outer var (dedup).
        dur_attr = getattr(self.paradigm, "demo_duration_attr", None)
        if dur_attr and dur_attr not in self._demo_entries:
            dur_default = getattr(self.paradigm, dur_attr, "")
            tk.Label(grid, text="Duration (s):",
                     font=("Arial", 10), fg="black", bg=self._C_BG,
                     anchor="e", width=24
                     ).grid(row=row_idx, column=0, sticky="e", pady=2, padx=(0, 6))
            var = tk.StringVar(value=str(dur_default))
            self._demo_entries[dur_attr] = var
            tk.Entry(grid, textvariable=var,
                     font=("Arial", 10), width=14
                     ).grid(row=row_idx, column=1, sticky="w", pady=2)
            row_idx += 1

        # Restore a demo carrier-level field for AM/FM. tone_level_db is no
        # longer an outer var (it is the per-fc target-level map), so it would
        # not otherwise appear here. DEMO-ONLY override: written under
        # "_demo_tone_level", which play_demo_trial applies and
        # _derive_dependent_params honours in place of the per-fc map, so the
        # operator can preview at a chosen level. Does not affect the real run.
        if (self.params.get("target_level") is not None
                and "_demo_tone_level" not in self._demo_entries):
            tl_vs = self.params["target_level"]
            tl_data = getattr(tl_vs, "data", None)
            default_level = tl_data[0] if isinstance(tl_data, list) and tl_data else 60.0
            tk.Label(grid, text="tone_level_db  (level):",
                     font=("Arial", 10), fg="black", bg=self._C_BG,
                     anchor="e", width=24
                     ).grid(row=row_idx, column=0, sticky="e", pady=2, padx=(0, 6))
            var = tk.StringVar(value=str(default_level))
            self._demo_entries["_demo_tone_level"] = var
            tk.Entry(grid, textvariable=var,
                     font=("Arial", 10), width=14
                     ).grid(row=row_idx, column=1, sticky="w", pady=2)
            row_idx += 1

        # Expose the demo grid + next free row so subclasses can append demo
        # fields (e.g. ThresholdSetupDialog's demo probe-level entry).
        self._demo_grid = grid
        self._demo_grid_row = row_idx

        # Play Demo button — right side of the frame
        btn_frame = tk.Frame(frame, bg=self._C_BG)
        btn_frame.pack(side=tk.RIGHT, padx=(12, 0))
        tk.Button(btn_frame,
                  text="\u25b6  Play Demo",
                  font=("Arial", 11, "bold"), width=14,
                  command=self._on_play_demo
                  ).pack(expand=True)

    def _on_play_demo(self) -> None:
        """Parse demo fields and call paradigm.play_demo_trial()."""
        demo_vals = {}
        for name, var in self._demo_entries.items():
            raw = var.get().strip()
            # Try float first, fall back to string (e.g. signal_type='sin')
            try:
                demo_vals[name] = float(raw)
            except ValueError:
                demo_vals[name] = raw

        # Subclass hook: inject/override derived demo values (e.g. a probe_level
        # computed from the threshold table) before the trial plays. No-op base.
        self._augment_demo_vals(demo_vals)

        try:
            self.paradigm.play_demo_trial(demo_vals)
        except Exception as ex:
            messagebox.showerror("Demo Error",
                                 f"Demo trial failed:\n{ex}",
                                 parent=self._root)

    def _augment_demo_vals(self, demo_vals: dict) -> None:
        """Hook: subclasses may add/override demo values before play. No-op base."""
        pass

    def _build_buttons(self, parent: tk.Widget) -> None:
        frame = tk.Frame(parent, bg=self._C_BG, pady=14)
        frame.pack(fill=tk.X, padx=16)

        tk.Button(frame, text="Cancel",
                  font=("Arial", 11), width=12, fg="black",
                  command=self._on_cancel
                  ).pack(side=tk.RIGHT, padx=6)

        # Kept as a handle: _refresh_start_gate enables/disables it according
        # to the selected calibration profile's SPL state.
        self._start_btn = tk.Button(frame, text="\u25b6  Start",
                                    font=("Arial", 12, "bold"), width=14,
                                    command=self._on_accept)
        self._start_btn.pack(side=tk.RIGHT, padx=6)

        self._root.bind("<Escape>", lambda _: self._on_cancel())
        self._root.bind("<Return>", lambda _: self._on_accept())

    # ------------------------------------------------------------------
    # Accept / cancel
    # ------------------------------------------------------------------

    def _validate_pid(self) -> Optional[str]:
        pid = format_participant_id(self._raw_pid())
        if not pid:
            messagebox.showerror(
                "Invalid Participant ID",
                "Enter a single letter and a participant number "
                "(e.g. P 18 \u2192 P0018).",
                parent=self._root
            )
        return pid

    def _on_accept(self) -> None:
        # Checked here as well as via the Start button state: the <Return>
        # binding reaches this method even when Start is disabled.
        if not self._calibration_gate_ok():
            return

        pid = self._validate_pid()
        if pid is None:
            return

        # --- Write inner var edits back to params ---
        inner_vs = self.params.get("inner")
        if inner_vs is not None and isinstance(inner_vs.data, dict):
            for key, var in self._inner_entries.items():
                raw = var.get().strip()
                try:
                    inner_vs.data[key] = float(raw)
                except ValueError:
                    messagebox.showerror(
                        "Invalid Parameter",
                        f"Inner var '{key}': '{raw}' is not a valid number.",
                        parent=self._root
                    )
                    return

        # --- Write outer var edits back to params ---
        for outer_key, var in self._outer_entries.items():
            raw = var.get().strip()
            tokens = [x.strip() for x in raw.split(",") if x.strip()]
            if not tokens:
                vs_name = self.params[outer_key].name
                messagebox.showerror(
                    "Invalid Parameter",
                    f"Outer var '{vs_name}': list is empty.",
                    parent=self._root
                )
                return
            # Try numeric first; fall back to strings
            try:
                values = [float(t) for t in tokens]
            except ValueError:
                values = tokens  # keep as strings
            self.params[outer_key].data = values

        # --- Write per-fc target level array back to params (AM/FM only) ---
        if self.params.get("target_level") is not None:
            fc_key = next((k for k in self.params
                           if k.startswith("outer_")
                           and getattr(self.params[k], "name", None) == "fc"), None)
            fc_list = self._current_fc_list(fc_key)
            # Force a final rebuild so the rows are co-indexed with the final fc
            # list even if a manual fc edit did not trigger the live trace.
            self._rebuild_target_rows(fc_key)
            arr = []
            for f in fc_list:
                freq_lbl = f"{f:g}" if isinstance(f, (int, float)) else str(f)
                var = self._target_entries.get(self._fc_key(f))
                raw = var.get().strip() if var is not None else ""
                if not raw:
                    messagebox.showerror(
                        "Invalid Parameter",
                        f"Target level for {freq_lbl} Hz is empty.",
                        parent=self._root
                    )
                    return
                try:
                    arr.append(float(raw))
                except ValueError:
                    messagebox.showerror(
                        "Invalid Parameter",
                        f"Target level for {freq_lbl} Hz: '{raw}' is not a number.",
                        parent=self._root
                    )
                    return
            self.params["target_level"].data = arr

        self._result_pid = pid
        self._root.destroy()

    def _on_cancel(self) -> None:
        self._result_pid = None
        self._root.destroy()


# ---------------------------------------------------------------------------
# ThresholdSetupDialog  (IFMC / TMC)
# ---------------------------------------------------------------------------

class ThresholdSetupDialog(ParadigmSetupDialog):
    """
    Extended setup dialog for paradigms requiring PTA thresholds (IFMC, TMC).

    Adds:
      - Frequency set dropdown
      - db_above_threshold and max_amplitude editable fields
      - Editable threshold table with include checkboxes, live probe columns
      - Load Most Recent / Load from CSV buttons
      - Add frequency row button
      - Frequency mismatch handled by showing all freqs with checkboxes

    show() returns (participant_id, thresholds_dict) or (None, None).
    thresholds_dict: {freq: {"threshold_dB": float, "probe_amp": float}}
    Only rows with the include checkbox ticked are returned.
    """

    def __init__(self,
                 paradigm_name: str,
                 params: Dict[str, Any],
                 paradigm,
                 default_freq_set_key: str,
                 db_above_threshold: float = 24.0,
                 max_amplitude: float = 0.7,
                 data_dir: str = None,
                 calibration=None):
        super().__init__(paradigm_name, params, paradigm)
        self._default_freq_key = default_freq_set_key
        self._db_above_var  = None   # created in _build_ui after Tk root exists
        self._max_amp_var   = None
        self._init_db_above = db_above_threshold
        self._init_max_amp  = max_amplitude
        self._data_dir = data_dir
        # The dialog owns the run's calibration (see base __init__). The
        # explicit calibration= argument wins over whatever the paradigm was
        # constructed with; _calibration below is a read-only view of it, so
        # every probe-math and profile-check read follows the operator's
        # dropdown selection automatically.
        if calibration is not None:
            self.selected_calibration = calibration
        # When set, probe arithmetic uses dB SPL math via cm.spl_to_amplitude.
        # When None, falls back to legacy db2amp (treats threshold_dB as dB FS).

        # Ordered list of frequencies currently in the table
        self._table_freqs = []

        # Per-row Tk variables keyed by freq
        # {freq: {"thresh", "probe_db", "probe_amp", "status",
        #         "status_lbl", "entry", "include", "in_set"}}
        self._row_vars: Dict[int, Dict] = {}

        self._source_label_var: Optional[tk.StringVar] = None
        self._result_thresholds: Optional[Dict] = None

        # Public-after-show: surface the setup parameters used (db_above,
        # max_amp, source CSV path) for downstream consumers (paradigm
        # CSV header generation).
        self.setup_summary: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @property
    def _calibration(self):
        """The calibration for this run (CalibrationManager or None).

        Read-only view of selected_calibration so existing probe-math and
        profile-mismatch reads track the operator's dropdown selection
        without needing to be re-pointed individually.
        """
        return self.selected_calibration

    def show(self) -> Tuple[Optional[str], Optional[Dict]]:
        pid = super().show()
        return pid, self._result_thresholds

    # ------------------------------------------------------------------
    # Sync participant field -> load field
    # ------------------------------------------------------------------

    def _on_pid_synced(self, formatted_pid: str) -> None:
        """When operator types in participant field, mirror to load field."""
        if hasattr(self, '_load_pid_var'):
            self._load_pid_var.set(formatted_pid)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, root: tk.Tk) -> None:
        self._db_above_var = tk.DoubleVar(value=self._init_db_above)
        self._max_amp_var  = tk.DoubleVar(value=self._init_max_amp)

        self._build_header(root)
        self._build_audio_device_section(root)
        self._build_calibration_section(root)
        self._build_participant_section(root)
        self._build_freq_and_probe_section(root)
        self._build_threshold_table(root)
        self._build_extra_outer_var_editors(root)
        self._build_demo_section(root)
        self._build_demo_probe_level_field()
        self._build_buttons(root)

        # Start button exists only now, so apply the calibration gate here.
        self._refresh_start_gate()

        # Populate table with default frequency set immediately
        self._on_freq_set_change()

    def _build_freq_and_probe_section(self, parent: tk.Widget) -> None:
        outer = tk.Frame(parent, bg=self._C_BG)
        outer.pack(fill=tk.X, padx=16, pady=6)

        # ---- Left: frequency set + load controls ----
        left = tk.LabelFrame(outer, text="Frequency Set & Data Source",
                             font=("Arial", 11, "bold"),
                             fg="black", bg=self._C_BG, pady=8, padx=12)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # Frequency set dropdown
        row1 = tk.Frame(left, bg=self._C_BG)
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="Frequency set:", font=("Arial", 11),
                 fg="black", bg=self._C_BG, width=16, anchor="w"
                 ).pack(side=tk.LEFT)
        self._freq_set_var = tk.StringVar(value=self._default_freq_key)
        freq_keys = list(FREQUENCY_SETS.keys())
        cb = ttk.Combobox(row1, textvariable=self._freq_set_var,
                          values=freq_keys, state="readonly", width=30)
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _: self._on_freq_set_change())

        # Load controls
        row2 = tk.Frame(left, bg=self._C_BG)
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="Load from participant:",
                 font=("Arial", 11), fg="black", bg=self._C_BG,
                 width=16, anchor="w").pack(side=tk.LEFT)
        self._load_pid_var = tk.StringVar()
        load_entry = tk.Entry(row2, textvariable=self._load_pid_var,
                              font=("Arial", 11), width=10)
        load_entry.pack(side=tk.LEFT, padx=4)
        load_entry.bind("<Return>", lambda _: self._load_most_recent())
        tk.Button(row2, text="Load Most Recent",
                  font=("Arial", 10), fg="black",
                  command=self._load_most_recent
                  ).pack(side=tk.LEFT, padx=4)
        tk.Button(row2, text="Load from CSV\u2026",
                  font=("Arial", 10), fg="black",
                  command=self._load_from_csv
                  ).pack(side=tk.LEFT, padx=4)

        # Source label
        self._source_label_var = tk.StringVar(value="No file loaded")
        tk.Label(left, textvariable=self._source_label_var,
                 font=("Arial", 9), fg="gray", bg=self._C_BG
                 ).pack(anchor="w", pady=(4, 0))

        # ---- Right: probe parameters ----
        right = tk.LabelFrame(outer, text="Probe Parameters",
                              font=("Arial", 11, "bold"),
                              fg="black", bg=self._C_BG, pady=8, padx=12)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0))

        def _labelled_entry(frame, label, var):
            r = tk.Frame(frame, bg=self._C_BG)
            r.pack(fill=tk.X, pady=4)
            tk.Label(r, text=label, font=("Arial", 10),
                     fg="black", bg=self._C_BG, width=20, anchor="w"
                     ).pack(side=tk.LEFT)
            e = tk.Entry(r, textvariable=var, font=("Arial", 11), width=8)
            e.pack(side=tk.LEFT, padx=4)
            e.bind("<FocusOut>", lambda _: self._refresh_probe_columns())
            e.bind("<Return>",   lambda _: self._refresh_probe_columns())

        _labelled_entry(right, "dB above threshold:", self._db_above_var)
        _labelled_entry(right, "Max amplitude:",       self._max_amp_var)

    def _build_extra_outer_var_editors(self, parent: tk.Widget) -> None:
        """Editors for outer vars the threshold table does NOT own.

        The threshold table already owns probe_freq (its frequency rows) and,
        post-demotion, probe_level (derived amplitude). The remaining outer var
        -- masker_freq_ratio (IFMC) / gap_duration (TMC) -- had no editor and
        was only settable in test_*.py; expose it here. Filter by NAME (not key)
        so it survives outer_N renumbering. Values are read back in _on_accept.
        """
        outer_keys = [
            k for k in self.params
            if k.startswith("outer_")
            and self.params[k].name not in ("probe_freq", "probe_level")
        ]
        if not outer_keys:
            return

        for key in sorted(outer_keys):
            vs = self.params[key]
            frame = tk.LabelFrame(parent,
                                  text=f"Outer Variable \u2014 {vs.name}",
                                  font=("Arial", 11, "bold"),
                                  fg="black", bg=self._C_BG, pady=8, padx=12)
            frame.pack(fill=tk.X, padx=16, pady=2)

            row_vals = tk.Frame(frame, bg=self._C_BG)
            row_vals.pack(fill=tk.X)
            tk.Label(row_vals, text="Values:",
                     font=("Arial", 10), fg="black", bg=self._C_BG,
                     width=16, anchor="w"
                     ).pack(side=tk.LEFT)

            init_vals = vs.data
            csv_str = (", ".join(str(v) for v in init_vals)
                       if isinstance(init_vals, list) else str(init_vals))
            val_var = tk.StringVar(value=csv_str)
            self._outer_entries[key] = val_var

            tk.Entry(row_vals, textvariable=val_var,
                     font=("Arial", 10), width=50
                     ).pack(side=tk.LEFT, padx=4)

    def _build_threshold_table(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(parent,
                              text="Threshold Preview  (click threshold cell to edit)",
                              font=("Arial", 11, "bold"),
                              fg="black", bg=self._C_BG, pady=8, padx=12)
        frame.pack(fill=tk.X, padx=16, pady=6)
        self._table_frame = frame

        # Column headers: Include | Freq | Threshold | Probe dB | Probe Amp | Status
        # Header text reflects calibration mode: dB SPL when calibrated,
        # dB (unitless / dB FS legacy) otherwise.
        self._col_widths = [6, 10, 14, 12, 10, 12]
        if self._calibration is not None:
            thresh_label = "Threshold (dB SPL)"
            probe_db_label = "Probe (dB SPL)"
        else:
            thresh_label = "Threshold (dB)"
            probe_db_label = "Probe dB SL"
        headers = ["Incl.", "Freq (Hz)", thresh_label, probe_db_label,
                   "Probe Amp", "Status"]
        hdr_row = tk.Frame(frame, bg=self._C_HEADER)
        hdr_row.pack(fill=tk.X)
        for h, w in zip(headers, self._col_widths):
            tk.Label(hdr_row, text=h, font=("Arial", 10, "bold"),
                     fg="white", bg=self._C_HEADER,
                     width=w, relief=tk.FLAT, pady=4
                     ).pack(side=tk.LEFT)

        self._rows_frame = tk.Frame(frame, bg=self._C_BG)
        self._rows_frame.pack(fill=tk.X)

        # "Add frequency" button below table
        add_frame = tk.Frame(frame, bg=self._C_BG)
        add_frame.pack(fill=tk.X, pady=(6, 0))
        tk.Button(add_frame, text="+ Add Frequency",
                  font=("Arial", 10), fg="black",
                  command=self._add_freq_row
                  ).pack(side=tk.LEFT)

    def _add_table_row(self, freq: int, in_set: bool,
                       threshold_str: str = "") -> None:
        """Add one row to the table for the given frequency."""
        i = len(self._table_freqs)
        bg = self._C_ROW_ALT if i % 2 == 0 else self._C_ROW_NORM

        row = tk.Frame(self._rows_frame, bg=bg)
        row.pack(fill=tk.X)

        # Include checkbox — default ON if freq is in the selected set
        include_var = tk.BooleanVar(value=in_set)
        cb = tk.Checkbutton(row, variable=include_var, bg=bg,
                            activebackground=bg)
        cb.pack(side=tk.LEFT, padx=4)

        # Freq label (fixed)
        tk.Label(row, text=str(freq), font=("Arial", 11),
                 fg="black", width=self._col_widths[1], bg=bg, pady=3
                 ).pack(side=tk.LEFT)

        # Threshold entry
        thresh_var = tk.StringVar(value=threshold_str)
        thresh_entry = tk.Entry(row, textvariable=thresh_var,
                                font=("Arial", 11), width=self._col_widths[2],
                                relief=tk.SUNKEN)
        thresh_entry.pack(side=tk.LEFT, padx=2, pady=2)
        thresh_entry.bind("<FocusOut>", lambda e, f=freq: self._on_thresh_edit(f))
        thresh_entry.bind("<Return>",   lambda e, f=freq: self._on_thresh_edit(f))

        # Probe dB SL (computed)
        probe_db_var = tk.StringVar(value="\u2014")
        tk.Label(row, textvariable=probe_db_var, font=("Arial", 11),
                 fg="black", width=self._col_widths[3], bg=bg
                 ).pack(side=tk.LEFT)

        # Probe amp (computed)
        probe_amp_var = tk.StringVar(value="\u2014")
        tk.Label(row, textvariable=probe_amp_var, font=("Arial", 11),
                 fg="black", width=self._col_widths[4], bg=bg
                 ).pack(side=tk.LEFT)

        # Status
        status_var = tk.StringVar(value="no data" if not threshold_str else "")
        status_lbl = tk.Label(row, textvariable=status_var,
                              font=("Arial", 9), width=self._col_widths[5],
                              fg="gray", bg=bg)
        status_lbl.pack(side=tk.LEFT)

        self._row_vars[freq] = {
            "thresh":     thresh_var,
            "probe_db":   probe_db_var,
            "probe_amp":  probe_amp_var,
            "status":     status_var,
            "status_lbl": status_lbl,
            "entry":      thresh_entry,
            "include":    include_var,
            "in_set":     in_set,
            "bg":         bg,
        }
        self._table_freqs.append(freq)

        # If threshold was pre-filled, compute derived columns immediately
        if threshold_str:
            try:
                self._update_row_computed(freq, float(threshold_str))
            except ValueError:
                pass

    def _populate_table_rows(self, frequencies,
                             loaded: Dict[int, float] = None) -> None:
        """
        Rebuild table rows.

        Shows all freqs in `frequencies` (in_set=True) plus any extra freqs
        in `loaded` that are not in `frequencies` (in_set=False, unchecked).
        """
        for w in self._rows_frame.winfo_children():
            w.destroy()
        self._row_vars.clear()
        self._table_freqs.clear()

        loaded = loaded or {}
        set_freqs   = list(frequencies)
        extra_freqs = sorted(f for f in loaded if f not in set_freqs)
        all_freqs   = sorted(set_freqs + extra_freqs)

        for freq in all_freqs:
            in_set = freq in set_freqs
            thresh_str = f"{loaded[freq]:.1f}" if freq in loaded else ""
            self._add_table_row(freq, in_set=in_set, threshold_str=thresh_str)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_freq_set_change(self) -> None:
        key = self._freq_set_var.get()
        freqs = FREQUENCY_SETS.get(key, [])
        self._populate_table_rows(freqs)
        self._source_label_var.set("No file loaded")

    def _add_freq_row(self) -> None:
        """Prompt for a new frequency and add it to the table."""
        dialog = tk.Toplevel(self._root)
        dialog.title("Add Frequency")
        dialog.configure(bg=self._C_BG)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text="Frequency (Hz):",
                 font=("Arial", 11), fg="black", bg=self._C_BG
                 ).grid(row=0, column=0, padx=12, pady=12, sticky="w")
        freq_var = tk.StringVar()
        freq_entry = tk.Entry(dialog, textvariable=freq_var,
                              font=("Arial", 11), width=10)
        freq_entry.grid(row=0, column=1, padx=6, pady=12)
        freq_entry.focus()

        def _ok():
            raw = freq_var.get().strip()
            try:
                freq = int(float(raw))
            except ValueError:
                messagebox.showerror("Invalid", f"'{raw}' is not a valid frequency.",
                                     parent=dialog)
                return
            if freq in self._row_vars:
                messagebox.showwarning("Duplicate",
                                       f"{freq} Hz is already in the table.",
                                       parent=dialog)
                return
            dialog.destroy()
            self._add_table_row(freq, in_set=True, threshold_str="")

        def _cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=self._C_BG)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame, text="Add", font=("Arial", 11), fg="black",
                  command=_ok).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text="Cancel", font=("Arial", 11), fg="black",
                  command=_cancel).pack(side=tk.LEFT, padx=8)
        dialog.bind("<Return>", lambda _: _ok())
        dialog.bind("<Escape>", lambda _: _cancel())
        _center_window(dialog)

    def _load_most_recent(self) -> None:
        raw = self._load_pid_var.get().strip()
        if not raw:
            raw = self._raw_pid().strip()
        pid = format_participant_id(raw)
        if not pid:
            messagebox.showerror("Invalid ID",
                                 "Enter a participant number in the load field "
                                 "(or in the Participant field above).",
                                 parent=self._root)
            return

        loader = ResultLoader(self._data_dir)

        # Try 4-digit form first, then 3-digit for backward compatibility.
        # Preserve the participant's letter prefix (was hardcoded "P").
        letter = pid[0]
        num = int(pid[1:])
        candidates = list(dict.fromkeys([
            letter + str(num).zfill(4),
            letter + str(num).zfill(3),
        ]))
        files = []
        matched_pid = pid
        for candidate in candidates:
            files = loader.find_results(candidate, "PTA")
            if files:
                matched_pid = candidate
                break

        if not files:
            messagebox.showwarning("No PTA File Found",
                                   f"No PTA results found for {pid}.",
                                   parent=self._root)
            return

        self._load_from_path(files[0], matched_pid)

    def _load_from_csv(self) -> None:
        data_dir = self._data_dir or str(Path.cwd() / "test_data")
        path = filedialog.askopenfilename(
            title="Select PTA CSV file",
            initialdir=data_dir,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            parent=self._root
        )
        if not path:
            return
        self._load_from_path(Path(path))

    @staticmethod
    def _read_csv_metadata(path) -> dict:
        """
        Parse `#`-prefixed metadata header from a PROLACTIN CSV.
        Returns dict of {key: value_str}; empty dict for legacy CSVs.
        Mirrors ResultLoader.get_metadata to avoid a circular import.
        """
        md: Dict[str, str] = {}
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

    def _load_from_path(self, path: Path, pid: str = None) -> None:
        """Load a PTA CSV and rebuild the table showing all freqs."""
        import pandas as pd

        # ---- Read metadata header (PROLACTIN >= 0.5.0) ------------------
        metadata = self._read_csv_metadata(path)
        csv_units = metadata.get("level_units")
        csv_profile = metadata.get("calibration_profile")

        # ---- Calibration / units compatibility checks -------------------
        if self._calibration is not None:
            # Calibration is active: dataset MUST be in dB SPL.
            if csv_units != "dB SPL":
                messagebox.showerror(
                    "Incompatible Dataset",
                    f"This CSV is in legacy units ({csv_units or 'unspecified'}).\n\n"
                    f"With calibration active, only dB SPL datasets are\n"
                    f"supported. Re-run PTA to generate a calibrated dataset.",
                    parent=self._root
                )
                return
            # Cross-profile check: warn if profile differs.
            active_profile = self._calibration.active_profile
            if csv_profile and csv_profile != "none" and csv_profile != active_profile:
                if not messagebox.askyesno(
                    "Calibration Profile Mismatch",
                    f"PTA CSV was recorded with profile:\n  {csv_profile}\n\n"
                    f"Active calibration profile:\n  {active_profile}\n\n"
                    f"Calibration aims to make profiles interchangeable, but\n"
                    f"residual differences (coupler vs real-ear coupling, drift\n"
                    f"between sessions, frequency-band coverage) can introduce\n"
                    f"sub-dB errors.\n\n"
                    f"Load anyway?",
                    parent=self._root
                ):
                    return
        else:
            # No calibration: warn if dataset IS in dB SPL (probe pipeline
            # will compute wrong levels using legacy db2amp).
            if csv_units == "dB SPL":
                messagebox.showwarning(
                    "Calibration Not Active",
                    "This CSV is in dB SPL but no calibration is configured.\n"
                    "Probe levels will be computed using legacy dB-FS math\n"
                    "and will NOT match the requested dB SPL values.",
                    parent=self._root
                )
                # Allow loading; user has been warned.

        # ---- Load CSV body ---------------------------------------------
        try:
            # comment="#" skips PROLACTIN metadata header (>= 0.5.0).
            # Legacy CSVs have no `#` lines and parse identically.
            df = pd.read_csv(path, comment="#")
        except Exception as ex:
            messagebox.showerror("Load Error",
                                 f"Could not read file:\n{ex}",
                                 parent=self._root)
            return

        if "fc" not in df.columns or "threshold_dB" not in df.columns:
            messagebox.showerror("Format Error",
                                 "CSV must contain 'fc' and 'threshold_dB' columns.",
                                 parent=self._root)
            return

        # Build {freq: threshold_dB} from file
        loaded: Dict[int, float] = {}
        for freq in df["fc"].unique():
            rows = df[df["fc"] == freq]
            if len(rows) > 0:
                loaded[int(freq)] = float(rows["threshold_dB"].iloc[-1])

        # Rebuild table: set freqs + any extras from file
        key = self._freq_set_var.get()
        set_freqs = FREQUENCY_SETS.get(key, [])
        self._populate_table_rows(set_freqs, loaded=loaded)

        self._source_label_var.set(f"Loaded: {path.name}")

    def _on_thresh_edit(self, freq: int) -> None:
        raw = self._row_vars[freq]["thresh"].get().strip()
        if not raw:
            self._row_vars[freq]["probe_db"].set("\u2014")
            self._row_vars[freq]["probe_amp"].set("\u2014")
            self._row_vars[freq]["status"].set("no data")
            self._row_vars[freq]["status_lbl"].config(fg="gray")
            return
        try:
            val = float(raw)
        except ValueError:
            self._row_vars[freq]["status"].set("invalid")
            self._row_vars[freq]["status_lbl"].config(fg=self._C_ERR)
            return
        self._update_row_computed(freq, val)

    def _on_calibration_changed(self) -> None:
        """Recompute probe columns after a profile switch.

        Probe amplitudes are derived from the calibration via
        spl_to_amplitude, so they are stale the moment the profile changes.
        """
        self._refresh_probe_columns()

    def _refresh_probe_columns(self) -> None:
        for freq in self._row_vars:
            raw = self._row_vars[freq]["thresh"].get().strip()
            if raw:
                try:
                    self._update_row_computed(freq, float(raw))
                except ValueError:
                    pass

    def _update_row_computed(self, freq: int, threshold_db: float) -> None:
        try:
            db_above = float(self._db_above_var.get())
            max_amp  = float(self._max_amp_var.get())
        except (tk.TclError, ValueError):
            return

        probe_db = threshold_db + db_above
        # Branch on calibration: SPL math when calibrated, legacy db2amp
        # otherwise. spl_to_amplitude returns (amp_L, amp_R); diotic average
        # is the transitional shortcut (option (a) in the migration plan)
        # until probe handling is migrated to per-channel SPL.
        if self._calibration is not None:
            try:
                amp_L, amp_R = self._calibration.spl_to_amplitude(probe_db)
                probe_amp = (amp_L + amp_R) / 2.0
            except Exception:
                # SPL math failed (e.g. uncalibrated profile slipped through);
                # fall back to legacy path silently for live preview.
                probe_amp = TrialPlayer.db2amp(probe_db)
        else:
            probe_amp = TrialPlayer.db2amp(probe_db)
        clamped   = probe_amp > max_amp
        if clamped:
            probe_amp = max_amp

        self._row_vars[freq]["probe_db"].set(f"{probe_db:.1f}")
        self._row_vars[freq]["probe_amp"].set(f"{probe_amp:.4f}")

        unusual = threshold_db < -20 or threshold_db > 120
        if unusual:
            status, colour = "unusual \u26a0", self._C_WARN
        elif clamped:
            status, colour = "clamped \u26a0", self._C_WARN
        else:
            status, colour = "ok", self._C_OK
        self._row_vars[freq]["status"].set(status)
        self._row_vars[freq]["status_lbl"].config(fg=colour)

        # Keep the demo probe-level field in sync with loaded/edited thresholds
        # (overwrite-on-change). No-op until the demo field has been built.
        self._sync_demo_probe_level()

    # Easy fallback demo probe level (dB SPL) used when no threshold is loaded
    # for the demo frequency. Deliberately modest so the demo does not give a
    # false impression of the test's difficulty; the team can adjust it.
    _EASY_DEMO_PROBE_DB = 60.0

    # ------------------------------------------------------------------
    # Demo
    # ------------------------------------------------------------------

    def _build_demo_probe_level_field(self) -> None:
        """Append a 'Probe level (dB SPL)' entry to the demo grid.

        Value derives from the loaded threshold for the current demo probe_freq
        (threshold + dB SL, i.e. the table's Probe dB column); falls back to an
        easy default when no data is available. Recomputed -- overwriting manual
        edits -- when the demo probe_freq or the threshold table changes.
        """
        grid = getattr(self, "_demo_grid", None)
        if grid is None:
            return
        row_idx = self._demo_grid_row
        tk.Label(grid, text="Probe level (dB SPL):",
                 font=("Arial", 10), fg="black", bg=self._C_BG,
                 anchor="e", width=24
                 ).grid(row=row_idx, column=0, sticky="e", pady=2, padx=(0, 6))
        self._demo_probe_level_var = tk.StringVar(
            value=f"{self._current_demo_probe_level_db():.1f}")
        tk.Entry(grid, textvariable=self._demo_probe_level_var,
                 font=("Arial", 10), width=14
                 ).grid(row=row_idx, column=1, sticky="w", pady=2)
        self._demo_grid_row = row_idx + 1

        # Overwrite-on-change: recompute when the demo probe_freq is edited.
        pf_var = self._demo_entries.get("probe_freq")
        if pf_var is not None:
            pf_var.trace_add("write", lambda *_: self._sync_demo_probe_level())

    def _sync_demo_probe_level(self) -> None:
        """Recompute the demo probe-level field from current freq/threshold state.

        Guarded so it is safe to call before the field exists (the threshold
        table populates during _build_ui before the demo field is built).
        """
        var = getattr(self, "_demo_probe_level_var", None)
        if var is not None:
            var.set(f"{self._current_demo_probe_level_db():.1f}")

    def _current_demo_probe_level_db(self) -> float:
        """dB SPL probe level for the current demo probe_freq.

        Reads the table's computed Probe dB (threshold + dB SL) for that freq;
        returns the easy default if the freq has no row or no valid threshold.
        """
        pf_var = self._demo_entries.get("probe_freq")
        if pf_var is not None:
            try:
                freq = float(pf_var.get().strip())
            except ValueError:
                freq = None
            if freq is not None:
                row = self._row_vars.get(freq)  # int/float keys compare equal
                if row is not None:
                    try:
                        return float(row["probe_db"].get().strip())
                    except ValueError:
                        pass
        return self._EASY_DEMO_PROBE_DB

    def _spl_to_amp(self, probe_db: float) -> float:
        """dB SPL -> linear amplitude, calibration-aware, capped at max_amplitude.

        Mirrors _update_row_computed: diotic average of spl_to_amplitude when
        calibrated, legacy db2amp otherwise (and as a fallback if SPL math
        raises).
        """
        try:
            max_amp = float(self._max_amp_var.get())
        except (tk.TclError, ValueError):
            max_amp = 1.0
        if self._calibration is not None:
            try:
                amp_L, amp_R = self._calibration.spl_to_amplitude(probe_db)
                amp = (amp_L + amp_R) / 2.0
            except Exception:
                amp = TrialPlayer.db2amp(probe_db)
        else:
            amp = TrialPlayer.db2amp(probe_db)
        return min(amp, max_amp)

    def _augment_demo_vals(self, demo_vals: dict) -> None:
        """Inject a demo probe_level (linear amp) from the dB-SPL demo field.

        The dialog's paradigm instance never gets set_probe_levels() (that runs
        post-dialog on a separate instance), so the paradigm's own derivation
        finds an empty map and skips; supply probe_level directly instead.
        """
        var = getattr(self, "_demo_probe_level_var", None)
        if var is None:
            return
        try:
            probe_db = float(var.get().strip())
        except ValueError:
            probe_db = self._EASY_DEMO_PROBE_DB
        demo_vals["probe_level"] = self._spl_to_amp(probe_db)

    # ------------------------------------------------------------------
    # Accept / cancel
    # ------------------------------------------------------------------

    def _on_accept(self) -> None:
        # Checked here as well as via the Start button state: the <Return>
        # binding reaches this method even when Start is disabled.
        if not self._calibration_gate_ok():
            return

        pid = self._validate_pid()
        if pid is None:
            return

        try:
            db_above = float(self._db_above_var.get())
            max_amp  = float(self._max_amp_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Invalid Parameters",
                                 "db_above_threshold and max_amplitude must be numbers.",
                                 parent=self._root)
            return

        # --- Write extra outer-var edits back to params ---
        # Only the outer vars rendered by _build_extra_outer_var_editors are in
        # _outer_entries (i.e. masker_freq_ratio / gap_duration; probe_freq and
        # probe_level are owned by the threshold table). Mirrors the base
        # ParadigmSetupDialog read-back: numeric-parse, str fallback, empty guard.
        for outer_key, var in self._outer_entries.items():
            raw = var.get().strip()
            tokens = [x.strip() for x in raw.split(",") if x.strip()]
            if not tokens:
                vs_name = self.params[outer_key].name
                messagebox.showerror(
                    "Invalid Parameter",
                    f"Outer var '{vs_name}': list is empty.",
                    parent=self._root
                )
                return
            try:
                values = [float(t) for t in tokens]
            except ValueError:
                values = tokens  # keep as strings
            self.params[outer_key].data = values

        thresholds = {}
        problems   = []

        for freq, vars_ in self._row_vars.items():
            # Skip unchecked rows
            if not vars_["include"].get():
                continue
            raw = vars_["thresh"].get().strip()
            if not raw:
                # Checked but no threshold entered — block Accept
                problems.append(f"{freq} Hz: checked but no threshold entered")
                continue
            try:
                thresh_db = float(raw)
            except ValueError:
                problems.append(f"{freq} Hz: '{raw}' is not a valid number")
                continue

            probe_db = thresh_db + db_above
            # Calibration-aware probe amplitude (mirrors _update_row_computed).
            if self._calibration is not None:
                amp_L, amp_R = self._calibration.spl_to_amplitude(probe_db)
                probe_amp = (amp_L + amp_R) / 2.0
            else:
                probe_amp = TrialPlayer.db2amp(probe_db)
            if probe_amp > max_amp:
                probe_amp = max_amp

            thresholds[freq] = {
                "threshold_dB": thresh_db,
                "probe_amp":    probe_amp,
            }

        if problems:
            messagebox.showerror("Invalid Threshold Values",
                                 "Fix the following before proceeding:\n\n"
                                 + "\n".join(problems),
                                 parent=self._root)
            return

        if not thresholds:
            if not messagebox.askyesno(
                "No Thresholds",
                "No checked rows with threshold values.\n\n"
                "Proceeding will test zero frequencies.\n\nContinue anyway?",
                parent=self._root
            ):
                return

        self._result_pid        = pid
        self._result_thresholds = thresholds
        # Populate public setup_summary for downstream consumers (e.g. the
        # paradigm's CSV header generator).
        source_label = self._source_label_var.get() if self._source_label_var else ""
        # source_label is something like "Loaded: P001_PTA_2026-04-30_..." or "" / "manual"
        if source_label.startswith("Loaded: "):
            csv_source = source_label[len("Loaded: "):]
        else:
            csv_source = "manual"
        self.setup_summary = {
            "db_above_threshold": db_above,
            "max_amplitude": max_amp,
            "threshold_source_csv": csv_source,
            "threshold_units": "dB SPL" if self._calibration is not None else "dB",
        }
        self._root.destroy()

    def _on_cancel(self) -> None:
        self._result_pid        = None
        self._result_thresholds = None
        self._root.destroy()
