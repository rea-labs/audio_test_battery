"""
Operator GUI — Real-time monitoring display for paradigm execution.

Provides live updates during paradigm runs showing:
  - Current paradigm/participant/config info
  - Trial-by-trial statistics (streak, reversals, etc.)
  - Four stacked plot panels:
    * Panel 37: Stimulus timing diagram (event blocks, dB rel FS)
    * Panel 38: Within-run variable track (adaptive parameter vs trial)
    * Panel 39: Previous thresholds (completed configs)
    * Panel 40: Psychometric function fit

Based on MultiThreshold operator GUI (sections 3.1 and 3.4 of manual).

Refresh model (two-phase, one figure render per phase):
  - update_stimulus() — called by the paradigm right after prepare_trial(),
    when tp holds the UPCOMING trial. Redraws panel 37 only, so the operator
    sees what the participant is about to hear.
  - update_display() — called after the response is processed. Redraws the
    text panel and panels 38/39/40. Also called once per config from
    update_trial_params(), after the psychometric fit and before the config
    rolls over, which is the only point at which the fitted curve is
    reachable (see open issue M2).

The individual _update_*_plot() helpers mutate their own axes and never call
canvas.draw() themselves; each phase issues a single canvas.draw_idle().

Units: value panels follow paradigm.operator_units ('dB SPL' or 'dB HL'),
resolved per-run via _operator_in_hl() / _hl_value(). See open issue M1.

Axis naming: variable axes are named from the VarSpec display metadata
(label/units) via utils.varspec.axis_label(), so panels read 'Tone Level
(dB SPL)' / 'Gap Duration (s)' rather than the raw identifier or a hardcoded
guess (M3/M4). Both fields are optional and fall back to the identifier.
A VarSpec's `units` describes the unit its values are STORED in; the only
display unit that may override it is 'dB HL', and only where _level_series()
reports it, because that is the one case where the plotted numbers have
actually been converted.

Placeholder axis labels (startup, and clear_display() at paradigm end) are
deliberately unitless: a placeholder that reads 'Threshold (dB)' is
indistinguishable from a real SPL-mode render, which has cost debugging time
before (open issue L29). Panel 39's placeholder x label is 'Outer Variable'
for the same reason: the panel plots outer_1, so a placeholder reading
'Configuration Number' would name a variable it never draws. That string is
still used as the LIVE x label in the no-outer-vars fallback, where it is
accurate.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for embedding in tkinter
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from trial_player import TrialPlayer
from utils.varspec import axis_label


# ---------------------------------------------------------------------------
# Panel 39 (previous thresholds) display constants
# ---------------------------------------------------------------------------

# Infer a log x-axis once the outer_1 values span at least this many decades.
# NOT 2: PTA's fc spans 1.51 decades and must render as an audiogram, while
# TMC's gap_duration spans 0.90. That leaves a (0.90, 1.51] window and 1.0 is
# the round number inside it -- a deliberately narrow margin, which is why
# AdaptiveParadigm.threshold_plot_x_log exists as an explicit override. (D5/D6)
_THRESHOLD_PLOT_LOG_DECADES = 1.0

# Qualitative palette for panel 39 series. Deliberately disjoint from panel
# 38's response semantics (green=TP, red=FN, blue=TN, orange=FP): panel 38 sits
# directly above, and a green or red threshold series next to it would invite
# reading the colour as a response type.
_THRESHOLD_SERIES_COLORS = ['#7570b3', '#a6761d', '#e7298a',
                            '#00868b', '#54278f', '#4d4d4d']
_THRESHOLD_SERIES_MARKERS = ['o', 's', '^', 'D', 'v', 'P']


class OperatorDisplay:
    """
    Single persistent window that monitors paradigm execution.
    
    Shows text info on left, four stacked plot panels on right.
    Window persists across multiple paradigms if run in sequence.

    Refreshed by the paradigm in two phases per trial - update_stimulus()
    after prepare_trial(), update_display() after the response. See the
    module docstring for the full refresh model.
    """
    
    def __init__(self, title="Operator Display"):
        """
        Create operator window.
        
        Args:
            title: Window title (can be updated per paradigm)
        """
        self.root = None
        self.paradigm = None  # Will be set when paradigm starts
        
        # Create window
        self._create_window(title)
        
        # Initialize text display elements
        self._create_text_panel()
        
        # Placeholder for plot panel (Step 1.2)
        self._create_plot_panel_placeholder()
        
    def _create_window(self, title):
        """Create the main operator window."""
        # Ensure a hidden Tk root exists so Toplevel has a parent.
        # Without this, Tkinter silently creates a visible blank "tk #2" window.
        global _tk_hidden_root
        if _tk_hidden_root is None:
            _tk_hidden_root = tk.Tk()
            _tk_hidden_root.withdraw()
        self.root = tk.Toplevel(_tk_hidden_root)  # Separate from participant GUI
        self.root.title(title)
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Don't steal focus from participant GUI
        self.root.focus_set()  # Set focus once to acknowledge creation
        
        # Main layout: left panel (text) + right panel (plots)
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel: text info (300px wide)
        self.text_frame = tk.Frame(self.main_frame, width=300, bg="#f0f0f0")
        self.text_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        self.text_frame.pack_propagate(False)  # Fixed width
        
        # Right panel: plots (remainder of space)
        self.plot_frame = tk.Frame(self.main_frame, bg="white")
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _create_text_panel(self):
        """Create text info display on left side."""
        # Title
        title_label = tk.Label(
            self.text_frame,
            text="Paradigm Monitor",
            font=("Arial", 16, "bold"),
            bg="#f0f0f0",
            fg="black"  # Black text
        )
        title_label.pack(pady=(10, 20))

        # Read-only indicator of the operator-facing level unit for this run.
        # The unit is fixed by the paradigm config (operator_units) and is NOT
        # changeable from the GUI, by design, to avoid ambiguity. Text is set
        # in _sync_units_indicator().
        self.units_indicator = tk.Label(
            self.text_frame,
            text="",
            font=("Arial", 11, "italic"),
            bg="#f0f0f0",
            fg="#444444",
        )
        self.units_indicator.pack(pady=(0, 8))

        # Status text (will be updated dynamically)
        self.status_text = tk.Text(
            self.text_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            bg="#f0f0f0",
            fg="black",  # Black text on gray background
            relief=tk.FLAT,
            state=tk.DISABLED,  # Read-only
            width=35,
            height=50
        )
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_plot_panel_placeholder(self):
        """
        Create matplotlib figure with 4 subplots.

        Axis labels set here are PLACEHOLDERS shown before any trial has been
        rendered; the _update_*_plot() helpers replace them with names derived
        from the VarSpec metadata. They carry no units on purpose (L29): a
        placeholder reading 'Threshold (dB)' was byte-identical to the real
        non-HL label, making "not yet rendered" indistinguishable from
        "rendered in SPL mode".
        """
        # Create matplotlib figure with 4 vertically stacked subplots
        self.fig = Figure(figsize=(10, 12), facecolor='white')
        
        # Panel 37: Stimulus waveform (half-wave rectified) - TOP
        self.ax_waveform = self.fig.add_subplot(4, 1, 1)
        self.ax_waveform.set_xlabel('Time (s)', fontsize=10, color='black')
        self.ax_waveform.set_ylabel('Amplitude (dB)', fontsize=10, color='black')
        self.ax_waveform.set_title('Stimulus Waveform (Half-Wave Rectified)', fontsize=11, color='black', fontweight='bold')
        self.ax_waveform.grid(True, alpha=0.3)
        self.ax_waveform.tick_params(colors='black', labelsize=9)
        for spine in self.ax_waveform.spines.values():
            spine.set_edgecolor('black')
        
        # Panel 38: Within-run variable track (adaptive parameter vs trial)
        self.ax_adaptive = self.fig.add_subplot(4, 1, 2)
        self.ax_adaptive.set_xlabel('Trial Number', fontsize=10, color='black')
        self.ax_adaptive.set_ylabel('Adaptive Parameter', fontsize=10, color='black')
        self.ax_adaptive.set_title('Within-Run Variable Track', fontsize=11, color='black', fontweight='bold')
        self.ax_adaptive.grid(True, alpha=0.3)
        self.ax_adaptive.tick_params(colors='black', labelsize=9)
        for spine in self.ax_adaptive.spines.values():
            spine.set_edgecolor('black')
        
        # Panel 39: Previous thresholds (completed configs)
        self.ax_thresholds = self.fig.add_subplot(4, 1, 3)
        self.ax_thresholds.set_xlabel('Outer Variable', fontsize=10, color='black')
        self.ax_thresholds.set_ylabel('Threshold', fontsize=10, color='black')
        self.ax_thresholds.set_title('Previous Thresholds', fontsize=11, color='black', fontweight='bold')
        self.ax_thresholds.grid(True, alpha=0.3)
        self.ax_thresholds.tick_params(colors='black', labelsize=9)
        for spine in self.ax_thresholds.spines.values():
            spine.set_edgecolor('black')
        
        # Panel 40: Psychometric function - BOTTOM
        self.ax_psychometric = self.fig.add_subplot(4, 1, 4)
        self.ax_psychometric.set_xlabel('Stimulus Level', fontsize=10, color='black')
        self.ax_psychometric.set_ylabel('P(Yes)', fontsize=10, color='black')
        self.ax_psychometric.set_title('Psychometric Function', fontsize=11, color='black', fontweight='bold')
        self.ax_psychometric.grid(True, alpha=0.3)
        self.ax_psychometric.tick_params(colors='black', labelsize=9)
        self.ax_psychometric.set_ylim(-0.05, 1.05)
        for spine in self.ax_psychometric.spines.values():
            spine.set_edgecolor('black')
        
        # Adjust spacing between subplots
        self.fig.tight_layout(pad=1.5)
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Store completed thresholds across configs
        self.threshold_history = []  # List of (config_num, threshold_dB) tuples
    
    def attach_paradigm(self, paradigm):
        """
        Attach to a paradigm instance to monitor.
        
        Args:
            paradigm: AdaptiveParadigm instance
        """
        self.paradigm = paradigm
        self.root.title(f"Operator Display --> {paradigm.paradigm_code}")
        self._sync_units_indicator()
        self.update_display()
    
    def _operator_in_hl(self):
        """
        True when every precondition for displaying dB HL is met:

        1. paradigm.operator_units == 'dB HL' (fixed per run in the paradigm
           config; not toggled here), AND
        2. an HL-calibrated CalibrationManager is attached, AND
        3. the paradigm is flagged hl_reportable.

        Condition 3 mirrors the gate in _threshold_to_hl(), which decides
        whether threshold_dB_HL is written to the CSV. Both must agree: HL is
        only meaningful for an absolute single-ear dB SPL level at one
        pure-tone fc, which per the 2026-06-11 team decision is PTA only.
        Without this check the display would happily show dB HL for a paradigm
        whose CSV correctly refuses to (e.g. LDL, SRT), and for inner
        variables that are not SPL levels at all (gap_duration, mod_ind,
        level_diff_dB, itd_ms). See open issue M1.
        """
        p = self.paradigm
        if p is None:
            return False
        if getattr(p, 'operator_units', 'dB SPL') != 'dB HL':
            return False
        cal = getattr(p, 'calibration', None)
        if cal is None or not getattr(cal, 'hl_calibrated', False):
            return False
        try:
            return p._get_paradigm_metadata().get('hl_reportable') is True
        except Exception:
            return False

    def _hl_value(self, spl_value):
        """
        Convert a dB SPL value to dB HL for the current config frequency, or
        return None when not in dB HL mode / not convertible (e.g. fc not yet
        set). Pure display helper - never raises.
        """
        if not self._operator_in_hl():
            return None
        p = self.paradigm
        fc = getattr(p, 'fc', None)
        if fc is None:
            return None
        try:
            return p.calibration.spl_to_hl(float(spl_value), float(fc))
        except Exception:
            return None

    def _level_series(self, spl_values):
        """
        Convert a sequence of dB SPL levels into the operator's display units.

        Returns (values, unit_label) where unit_label is 'dB HL' if the
        conversion was applied and 'dB SPL' otherwise. Falls back to the
        unconverted values on any failure - pure display helper, never raises.

        Only ever converts when _operator_in_hl() is True, which requires the
        paradigm to be hl_reportable; that guarantees the values really are
        absolute SPL levels at self.fc and not some other inner variable
        (gap_duration, mod_ind, itd_ms, ...). See open issue M1.
        """
        values = np.asarray(spl_values, dtype=float)
        if not self._operator_in_hl():
            return values, 'dB SPL'
        p = self.paradigm
        fc = getattr(p, 'fc', None)
        if fc is None:
            return values, 'dB SPL'
        try:
            converted = np.array(
                [p.calibration.spl_to_hl(float(v), float(fc)) for v in values],
                dtype=float
            )
        except Exception:
            return values, 'dB SPL'
        return converted, 'dB HL'

    def _sync_units_indicator(self):
        """Update the read-only operator-units indicator label."""
        if not hasattr(self, 'units_indicator'):
            return
        p = self.paradigm
        units = getattr(p, 'operator_units', 'dB SPL') if p is not None else 'dB SPL'
        if units == 'dB HL' and not self._operator_in_hl():
            # Configured for HL but HL is not displayable - either no
            # HL-calibrated profile is attached or the paradigm is not
            # hl_reportable. Display falls back to dB SPL; make that explicit
            # rather than silently lying.
            text = "Operator units: dB HL (set in config) - HL unavailable, showing dB SPL"
        else:
            text = f"Operator units: {units} (set in config)"
        self.units_indicator.config(text=text)

    def update_stimulus(self):
        """
        Redraw the stimulus timing panel only.

        Called by the paradigm immediately after prepare_trial(), when
        paradigm.tp holds the UPCOMING trial. The panel therefore shows what
        the participant is about to hear; previously the whole display was
        refreshed only after the response, leaving this panel one trial behind.

        Deliberately does not touch the text panel or the data panels: those
        describe the response, which does not exist yet at this point in the
        trial. They are refreshed by update_display() instead.
        """
        if self.paradigm is None:
            return

        self._update_waveform_plot()
        self.canvas.draw_idle()

    def update_display(self):
        """
        Update the text panel and the three data panels (adaptive track,
        previous thresholds, psychometric function) from the current paradigm
        state.

        Called after each trial by the paradigm, once the response has been
        processed, and once more at the end of each config (from
        update_trial_params(), before the config rolls over) so the fitted
        psychometric curve is drawn while it is still reachable - see M2.

        Does NOT redraw the stimulus panel; that is update_stimulus()'s job
        and it has already run for this trial.
        """
        if self.paradigm is None:
            return
        
        # Keep the read-only operator-units indicator current.
        self._sync_units_indicator()

        # Build status text
        lines = []
        lines.append("=" * 35)
        lines.append(f"PARADIGM: {self.paradigm.paradigm_code}")
        lines.append(f"PARTICIPANT: {self.paradigm.participant_id}")
        lines.append("=" * 35)
        lines.append("")
        
        # Current config info
        lines.append("CURRENT CONFIGURATION:")
        lines.append(f"  Config: {self.paradigm.config_num} / {self.paradigm.total_num_configs}")
        
        # Show outer variable values for current config
        if hasattr(self.paradigm, 'outer_vars') and len(self.paradigm.outer_vars) > 0:
            for var_spec in self.paradigm.outer_vars:
                if hasattr(self.paradigm, var_spec.name):
                    value = getattr(self.paradigm, var_spec.name)
                    lines.append(f"  {var_spec.name}: {value}")
        
        lines.append("")
        
        # Current trial info
        lines.append("CURRENT TRIAL:")
        lines.append(f"  Trial: {self.paradigm.trial_num}")
        lines.append(f"  Streak: {self.paradigm.current_streak:+d}")
        lines.append(f"  Reversals: {self.paradigm.total_num_reversals}")
        
        if self.paradigm.trials_remaining is not None:
            lines.append(f"  Remaining: {self.paradigm.trials_remaining}")
        else:
            lines.append(f"  Remaining: (counting to first reversal)")
        
        lines.append("")
        
        # Adaptive parameter (inner variable)
        lines.append("ADAPTIVE PARAMETER:")
        if hasattr(self.paradigm, 'inner_var') and self.paradigm.inner_var:
            param_name = self.paradigm.inner_var.name
            if hasattr(self.paradigm, param_name):
                param_value = getattr(self.paradigm, param_name)
                
                # Format depending on type
                if isinstance(param_value, float):
                    hl = self._hl_value(param_value)
                    if hl is not None:
                        lines.append(f"  {param_name}: {hl:.3f} dB HL ({param_value:.3f} dB SPL)")
                    else:
                        lines.append(f"  {param_name}: {param_value:.3f}")
                else:
                    lines.append(f"  {param_name}: {param_value}")
        
        lines.append("")
        
        # Threshold estimate (if available)
        lines.append("THRESHOLD ESTIMATE:")
        if hasattr(self.paradigm, 'threshold_dB') and self.paradigm.threshold_dB is not None:
            if not np.isnan(self.paradigm.threshold_dB):
                hl = self._hl_value(self.paradigm.threshold_dB)
                if hl is not None:
                    lines.append(f"  Threshold: {hl:.2f} dB HL ({self.paradigm.threshold_dB:.2f} dB SPL)")
                else:
                    lines.append(f"  Threshold: {self.paradigm.threshold_dB:.2f} dB")
                if hasattr(self.paradigm, 'slope_k') and self.paradigm.slope_k is not None:
                    if not np.isnan(self.paradigm.slope_k):
                        lines.append(f"  Slope (k): {self.paradigm.slope_k:.3f}")
            else:
                lines.append(f"  (not yet estimated)")
        else:
            lines.append(f"  (not yet estimated)")
        
        lines.append("")
        
        # Catch trial stats
        if hasattr(self.paradigm, 'data') and len(self.paradigm.data) > 0:
            df = self.paradigm.data
            n_trials = len(df)
            n_catch = (df['is_catch_trial'] == True).sum()
            n_fp = (df['correct_answer'] == 'FP').sum()
            
            if n_catch > 0:
                fp_rate = 100.0 * n_fp / n_catch
            else:
                fp_rate = 0.0
            
            catch_rate = 100.0 * self.paradigm._current_catch_trial_rate
            lines.append("CATCH TRIAL STATS:")
            lines.append(f"  Current catch trial rate: {catch_rate:.1f}%")
            lines.append(f"  Total trials: {n_trials}")
            lines.append(f"  Catch trials: {n_catch}")
            lines.append(f"  False alarms: {n_fp}")
            lines.append(f"  FP rate: {fp_rate:.1f}%")
        
        lines.append("")
        lines.append("=" * 35)
        
        # Update text widget
        status_str = "\n".join(lines)
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(1.0, status_str)
        self.status_text.config(state=tk.DISABLED)
        
        # Force GUI update
        self.root.update_idletasks()
        
        # Update the data plots. The stimulus panel is excluded - it was drawn
        # by update_stimulus() after prepare_trial().
        #
        # These helpers only mutate their own axes; the single draw_idle()
        # below renders the figure once. Each helper used to end with its own
        # canvas.draw(), which re-rendered the whole 4-panel figure on every
        # call - four full redraws per trial where one suffices.
        self._update_adaptive_plot()
        self._update_threshold_plot()
        self._update_psychometric_plot()
        self.canvas.draw_idle()
        
        # Return focus to participant GUI if it exists
        if hasattr(self.paradigm, 'root') and self.paradigm.root is not None:
            try:
                self.paradigm.root.lift()
                self.paradigm.root.focus_force()
            except:
                pass  # Ignore if participant GUI not ready
    
    def _update_waveform_plot(self):
        """
        Update stimulus timing plot (panel 37) - show timing diagram.

        Since we don't store the actual waveform, we show a timing diagram
        with rectangular blocks representing each stimulus event, read live
        from paradigm.tp.

        Called via update_stimulus() straight after prepare_trial(), so tp
        describes the trial that is about to play. Does not draw; the caller
        issues one canvas.draw_idle().
        """
        # Clear plot first
        self.ax_waveform.clear()
        
        if self.paradigm is None:
            self._draw_empty_waveform("No paradigm attached")
            return
        
        if not hasattr(self.paradigm, 'tp'):
            self._draw_empty_waveform("TrialPlayer not initialized")
            return
        
        tp = self.paradigm.tp
        
        # Check if trial has been configured
        if not hasattr(tp, 'start_times') or not hasattr(tp, 'end_times'):
            self._draw_empty_waveform("Waiting for first trial...")
            return
        
        # Draw rectangular blocks for each event
        for i in range(len(tp.start_times)):
            start = tp.start_times[i]
            end = tp.end_times[i]
            amp = tp.amp[i]
            
            # Convert amplitude to dB
            amp_db = TrialPlayer.amp2db(amp) if amp > 0 else -100
            
            # Draw rectangle
            self.ax_waveform.add_patch(
                plt.Rectangle((start, -100), end - start, amp_db + 100,
                             facecolor='blue', edgecolor='black', alpha=0.7)
            )
            
            # Add frequency label
            if hasattr(tp, 'fc') and i < len(tp.fc):
                mid_time = (start + end) / 2
                self.ax_waveform.text(mid_time, amp_db + 2, f'{tp.fc[i]:.0f} Hz',
                                     ha='center', va='bottom', fontsize=7, color='black')
        
        # Set axis limits
        if len(tp.start_times) > 0:
            self.ax_waveform.set_xlim(0, max(tp.end_times) * 1.1)
            self.ax_waveform.set_ylim(-100, 5)
        
        self.ax_waveform.set_xlabel('Time (s)', fontsize=10, color='black')
        self.ax_waveform.set_ylabel('Amplitude (dB rel FS)', fontsize=10, color='black')
        self.ax_waveform.set_title('Stimulus Timing Diagram', fontsize=11, color='black', fontweight='bold')
        self.ax_waveform.grid(True, alpha=0.3)
        self.ax_waveform.tick_params(colors='black', labelsize=9)
        for spine in self.ax_waveform.spines.values():
            spine.set_edgecolor('black')
    
    def _draw_empty_waveform(self, message):
        """Draw empty waveform plot with message."""
        self.ax_waveform.text(0.5, 0.5, message, 
                             ha='center', va='center', 
                             fontsize=10, color='gray',
                             transform=self.ax_waveform.transAxes)
        self.ax_waveform.set_xlabel('Time (s)', fontsize=10, color='black')
        self.ax_waveform.set_ylabel('Amplitude (dB)', fontsize=10, color='black')
        self.ax_waveform.set_title('Stimulus Waveform (Half-Wave Rectified)', fontsize=11, color='black', fontweight='bold')
        self.ax_waveform.grid(True, alpha=0.3)
        self.ax_waveform.tick_params(colors='black', labelsize=9)
        for spine in self.ax_waveform.spines.values():
            spine.set_edgecolor('black')
    
    def _update_adaptive_plot(self):
        """
        Update the adaptive track plot (panel 38): inner variable vs trial
        number for the current config, marker-coded by response type.

        The y axis follows the operator's units (M1) - converted to dB HL only
        when _operator_in_hl() allows it, dB SPL / raw inner-variable units
        otherwise. It is named from the inner VarSpec's display metadata via
        axis_label() (M3/M4), falling back to the raw identifier when the
        paradigm declares none. Does not draw; the caller issues one
        canvas.draw_idle().
        """
        if self.paradigm is None or not hasattr(self.paradigm, 'data'):
            return
        
        # Get data for current config only
        df = self.paradigm.data
        if len(df) == 0:
            return
        
        current_config_data = df[df['config_num'] == self.paradigm.config_num]
        if len(current_config_data) == 0:
            return
        
        # Extract trial numbers (relative to current config)
        trial_nums = current_config_data['trial_num'].values
        
        # Get adaptive parameter name and values
        if hasattr(self.paradigm, 'inner_var') and self.paradigm.inner_var:
            param_name = self.paradigm.inner_var.name
            if param_name in current_config_data.columns:
                param_values = current_config_data[param_name].values
            else:
                return  # Adaptive parameter not in data yet
        else:
            return

        # Follow the operator's units (M1). No-op unless the run is in dB HL
        # and the paradigm is hl_reportable, in which case param_values is an
        # absolute SPL level at self.fc and unit_label becomes 'dB HL'. The
        # whole panel is one config, so fc is constant across these points.
        param_values, level_unit = self._level_series(param_values)

        # Name the axis from the VarSpec's display metadata, falling back to
        # the raw identifier when a paradigm declares none (M3/M4).
        # _level_series() returns 'dB SPL' as its no-op unit for EVERY inner
        # variable, including ones that are not levels at all (gap_duration,
        # mod_ind, itd_ms). So it may only override the declared unit when it
        # actually converted, i.e. when it reports 'dB HL'; otherwise the
        # VarSpec's own units are the truth.
        units_override = 'dB HL' if level_unit == 'dB HL' else None
        y_label = axis_label(self.paradigm.inner_var, units_override=units_override)
        
        # Get response classifications
        responses = current_config_data['correct_answer'].values
        
        # Clear previous plot
        self.ax_adaptive.clear()
        
        # Plot each response type with specific color/marker
        response_styles = {
            'TP': {'color': 'green',  'marker': 'o', 'label': 'Detected (TP)'},
            'FN': {'color': 'red',    'marker': 'o', 'label': 'Missed (FN)'},
            'TN': {'color': 'blue',   'marker': 'x', 'label': 'Correct Rejection (TN)'},
            'FP': {'color': 'orange', 'marker': 'x', 'label': 'False Alarm (FP)'}
        }
        
        for response_type, style in response_styles.items():
            mask = responses == response_type
            if np.any(mask):
                self.ax_adaptive.plot(
                    trial_nums[mask],
                    param_values[mask],
                    marker=style['marker'],
                    color=style['color'],
                    linestyle='none',
                    markersize=8,
                    label=style['label'],
                    markeredgewidth=1.5,
                    markeredgecolor='black' if style['marker'] == 'o' else style['color']
                )
        
        # Set labels and title
        self.ax_adaptive.set_xlabel('Trial Number', fontsize=10, color='black')
        self.ax_adaptive.set_ylabel(y_label, fontsize=10, color='black')
        self.ax_adaptive.set_title('Within-Run Variable Track', fontsize=12, color='black', fontweight='bold')
        self.ax_adaptive.grid(True, alpha=0.3)
        self.ax_adaptive.legend(loc='best', fontsize=8, framealpha=0.9)
        
        # Set text colors to black
        self.ax_adaptive.tick_params(colors='black', labelsize=9)
        for spine in self.ax_adaptive.spines.values():
            spine.set_edgecolor('black')
    
    def _format_var_value(self, value):
        """
        Format an outer-variable value for a tick or legend entry.

        Uses %g, which suits both ends of this project's range without a
        per-variable rule: fc 250.0 -> '250' (audiogram convention, no stray
        decimal point), gap_duration 0.005 -> '0.005', masker_freq_ratio 0.5 ->
        '0.5' and 1.0 -> '1'. A fixed-precision rule cannot do all three - 3 dp
        is needed for the gaps but renders the ratios as '0.500'.

        Note this drops trailing zeros, so pan reads 'Pan=-1' rather than
        'Pan=-1.0'. Non-numeric values pass through as str (D7). Never raises.
        """
        try:
            if isinstance(value, (bool, str)) or value is None:
                return str(value)
            fval = float(value)
            if not np.isfinite(fval):
                return str(value)
            return f'{fval:g}'
        except Exception:
            return str(value)

    def _series_key(self, config_data, series_vars):
        """
        Build the legend label for one config's series membership (D2).

        config_data is a single logged row (all outer values are present on
        every row since H2). series_vars is the already-filtered list of
        outer_2..N VarSpecs that actually vary. Returns '' when there are no
        series vars, which the caller uses to mean "one unlabelled series, no
        legend" -- the GAP/SRT single-config case. Never raises.
        """
        parts = []
        for var_spec in series_vars:
            try:
                name = getattr(var_spec, 'label', '') or var_spec.name
                value = config_data[var_spec.name]
            except Exception:
                continue
            parts.append(f'{name}={self._format_var_value(value)}')
        return ', '.join(parts)

    def _threshold_x_is_log(self, x_values):
        """
        Decide the panel 39 x scale: paradigm override if set, else infer (D5/D6).

        Inference needs at least two positive finite values spanning
        _THRESHOLD_PLOT_LOG_DECADES decades. A non-positive value makes log
        impossible regardless of span, so it forces linear rather than being
        quietly dropped -- silently plotting a subset of the configs would be
        worse than a linear axis. Never raises.
        """
        try:
            override = getattr(self.paradigm, 'threshold_plot_x_log', None)
            if override is not None:
                return bool(override)
            vals = np.asarray(x_values, dtype=float)
            vals = vals[np.isfinite(vals)]
            if len(vals) < 2 or np.any(vals <= 0):
                return False
            lo, hi = float(np.min(vals)), float(np.max(vals))
            if lo <= 0 or hi <= 0:
                return False
            return bool(np.log10(hi / lo) >= _THRESHOLD_PLOT_LOG_DECADES)
        except Exception:
            return False

    def _update_threshold_plot(self):
        """
        Update previous thresholds plot (panel 39): one point per completed
        config, plotted against the REAL values of outer_1 (M3/M4).

        x is outer_1 by convention (documented on AdaptiveParadigm.params, not
        schema-enforced): the paradigm author orders the outer vars so the
        first is the natural x-axis -- PTA fc gives an audiogram, IFMC
        masker_freq_ratio the conventional IFMC curve. It used to be the
        ordinal config number, which made the audiogram unreadable and
        collapsed IFMC's two probe frequencies onto one indistinguishable
        series.

        outer_2..N become visually distinct series, but only where they
        actually vary (D2). Five paradigms declare constants as outer vars
        (AM/FM fm=[8], tone_level_db=[60.0]; DLI/ILD/ITD ref_level_db=[60.0]),
        and crossing those in would tag every line with pure noise; they are
        surfaced as an annotation instead (D3).

        Degenerate shapes are normal here, not edge cases: GAP and SRT have a
        single-valued outer_1 and plot exactly one point with no legend, and
        ITD's outer_1 is a string, which takes the categorical path (D7).

        Values follow the operator's units (M1) via the threshold_dB_HL column
        when the run is in dB HL, else threshold_dB. Does not draw; the caller
        issues one canvas.draw_idle().
        """
        if self.paradigm is None or not hasattr(self.paradigm, 'data'):
            return
        
        df = self.paradigm.data
        if len(df) == 0:
            return
        
        # Display in dB HL when the run is configured for HL (operator_units)
        # and an HL value column exists; otherwise the inner variable's own
        # declared unit. The threshold is a value of the inner variable, so it
        # carries the inner variable's unit -- 'Threshold (dB)' was wrong for
        # GAP (seconds), AM/FM (percent) and ITD (ms) in exactly the way the
        # panel 40 x-label was (L30).
        hl_mode = (self._operator_in_hl()
                   and 'threshold_dB_HL' in df.columns)
        if hl_mode:
            value_col = 'threshold_dB_HL'
            y_unit = 'dB HL'
        else:
            value_col = 'threshold_dB'
            y_unit = str(getattr(getattr(self.paradigm, 'inner_var', None),
                                 'units', '') or '')
        y_label = f'Threshold ({y_unit})' if y_unit else 'Threshold'

        # Get thresholds from completed configs
        # Find rows where the threshold is not NaN (last row of each config)
        completed_configs = df[df[value_col].notna()]
        
        if len(completed_configs) == 0:
            return

        thresholds = completed_configs[value_col].values

        # Split outer vars into x (outer_1) and series candidates (outer_2..N).
        # outer_vars preserves params insertion order, so index 0 IS outer_1.
        outer_vars = list(getattr(self.paradigm, 'outer_vars', None) or [])
        x_var = outer_vars[0] if outer_vars else None
        if x_var is not None and x_var.name not in completed_configs.columns:
            x_var = None   # not logged (should not happen since H2) -> fall back

        series_vars = [v for v in outer_vars[1:]
                       if len(getattr(v, 'data', None) or []) > 1
                       and v.name in completed_configs.columns]
        const_vars = [v for v in outer_vars[1:]
                      if len(getattr(v, 'data', None) or []) <= 1
                      and v.name in completed_configs.columns]

        # Clear and plot
        self.ax_thresholds.clear()

        if x_var is None:
            # No usable outer_1: keep the legacy ordinal x rather than refusing
            # to draw. Only reachable for a paradigm with no outer vars at all.
            x_raw = completed_configs['config_num'].values
            x_label = 'Configuration Number'
        else:
            x_raw = completed_configs[x_var.name].values
            x_label = axis_label(x_var)

        # Numeric or categorical? ITD's outer_1 is signal_type=["sin"] (D7).
        categories = None
        try:
            x_vals = np.asarray(x_raw, dtype=float)
            if not np.all(np.isfinite(x_vals)):
                raise ValueError('non-finite outer_1 values')
        except (TypeError, ValueError):
            # Ordinal fallback: map each distinct value to an index, in order
            # of first appearance, and label the ticks with the values.
            categories = list(dict.fromkeys([str(v) for v in x_raw]))
            index_of = {c: i for i, c in enumerate(categories)}
            x_vals = np.asarray([index_of[str(v)] for v in x_raw], dtype=float)

        x_log = (not categories) and self._threshold_x_is_log(x_vals)

        # Group configs into series. No series vars -> one unlabelled series.
        series = {}   # insertion-ordered; first-seen series keeps colour slot 0
        for row_idx in range(len(completed_configs)):
            row = completed_configs.iloc[row_idx]
            key = self._series_key(row, series_vars)
            series.setdefault(key, ([], []))
            series[key][0].append(x_vals[row_idx])
            series[key][1].append(thresholds[row_idx])

        for series_idx, (key, (xs, ys)) in enumerate(series.items()):
            # Sort within the series so the connecting line follows the x axis
            # rather than config presentation order, which is shuffled.
            order = np.argsort(np.asarray(xs, dtype=float))
            xs_sorted = np.asarray(xs, dtype=float)[order]
            ys_sorted = np.asarray(ys, dtype=float)[order]
            color = _THRESHOLD_SERIES_COLORS[series_idx % len(_THRESHOLD_SERIES_COLORS)]
            marker = _THRESHOLD_SERIES_MARKERS[series_idx % len(_THRESHOLD_SERIES_MARKERS)]
            self.ax_thresholds.plot(
                xs_sorted, ys_sorted,
                marker=marker,
                color=color,
                markersize=8,
                linestyle='-',          # points connected (D10)
                linewidth=1.5,
                markeredgewidth=1.2,
                markeredgecolor='black',
                label=key if key else None
            )

        if x_log:
            self.ax_thresholds.set_xscale('log')

        # Ticks at the actual outer_1 values, plainly formatted (D14): a log
        # axis must still read 250/500/1000/... rather than matplotlib's
        # decade ticks, which would leave the audiogram almost unlabelled.
        if categories:
            self.ax_thresholds.set_xticks(range(len(categories)))
            self.ax_thresholds.set_xticklabels(categories)
        else:
            ticks = sorted(set(float(v) for v in x_vals))
            self.ax_thresholds.set_xticks(ticks)
            self.ax_thresholds.set_xticklabels(
                [self._format_var_value(t) for t in ticks])
            if x_log:
                self.ax_thresholds.minorticks_off()

        # x padding: multiplicative on a log axis, additive otherwise. A single
        # x value (GAP, SRT) still needs a non-zero span or the axis collapses.
        try:
            lo, hi = float(np.min(x_vals)), float(np.max(x_vals))
            if x_log:
                if lo == hi:
                    self.ax_thresholds.set_xlim(lo / 1.2, hi * 1.2)
                else:
                    self.ax_thresholds.set_xlim(lo / 1.1, hi * 1.1)
            else:
                pad = (hi - lo) * 0.08 if hi > lo else max(abs(hi) * 0.1, 0.5)
                self.ax_thresholds.set_xlim(lo - pad, hi + pad)
        except Exception:
            pass

        self.ax_thresholds.set_xlabel(x_label, fontsize=10, color='black')
        self.ax_thresholds.set_ylabel(y_label, fontsize=10, color='black')
        self.ax_thresholds.set_title('Previous Thresholds', fontsize=11, color='black', fontweight='bold')
        self.ax_thresholds.grid(True, alpha=0.3)
        self.ax_thresholds.tick_params(colors='black', labelsize=9)
        for spine in self.ax_thresholds.spines.values():
            spine.set_edgecolor('black')

        # Real legend, replacing the free-text wheat box. Only when there is
        # something to disambiguate: one series needs no key, and GAP/SRT would
        # otherwise get an empty box.
        if len(series) > 1:
            self.ax_thresholds.legend(loc='best', fontsize=8, framealpha=0.9)

        # Constants filtered out of the series (D3): shown rather than dropped,
        # so the operator can still see the fm / tone_level_db / ref_level_db a
        # run was performed at. Provisional placement -- revisit after live use.
        if const_vars:
            const_txt = self._series_key(completed_configs.iloc[0], const_vars)
            if const_txt:
                self.ax_thresholds.text(
                    0.99, 1.01, const_txt,
                    transform=self.ax_thresholds.transAxes,
                    ha='right', va='bottom',
                    fontsize=7, color='#555555', style='italic')
        
    def _update_psychometric_plot(self):
        """
        Update psychometric function plot (panel 40) for the current config:
        per-trial responses, 1 dB binned proportions, and the fitted sigmoid.

        The fitted curve is only drawable at end of config, while
        paradigm.threshold_dB / slope_k are still set - update_trial_params()
        calls update_display() at exactly that point before resetting them
        (M2). On all other trials the curve is absent by design.

        The level axis follows the operator's units (M1) and is named from the
        inner VarSpec's display metadata via axis_label() (M3/M4). It was
        previously hardcoded to 'Stimulus Level (dB ...)', which was wrong for
        every paradigm whose inner variable is not a level - GAP
        (gap_duration, s), AM/FM (mod_ind, %), ITD (itd_ms) - in both the axis
        label and the fit legend (open issue L30). Does not draw; the caller
        issues one canvas.draw_idle().
        """
        if self.paradigm is None or not hasattr(self.paradigm, 'data'):
            return
        
        df = self.paradigm.data
        if len(df) == 0:
            return
        
        # Get data for current config only
        current_config_data = df[df['config_num'] == self.paradigm.config_num]
        if len(current_config_data) == 0:
            return
        
        # Get adaptive parameter name and values
        if not hasattr(self.paradigm, 'inner_var') or not self.paradigm.inner_var:
            return
        
        param_name = self.paradigm.inner_var.name
        if param_name not in current_config_data.columns:
            return
        
        # Extract levels and responses (exclude catch trials)
        non_catch = current_config_data[current_config_data['is_catch_trial'] == False]
        if len(non_catch) == 0:
            return
        
        levels = non_catch[param_name].values
        responses = (non_catch['correct_answer'] == 'TP').astype(int).values

        # Follow the operator's units (M1). No-op unless the run is in dB HL
        # and the paradigm is hl_reportable. Applied to the raw levels before
        # binning so the bins, the fitted curve and the axis all share one
        # scale. Since HL = SPL - RETSPL(fc) and fc is constant within a
        # config, this is a rigid shift: bin widths and the fitted slope k are
        # unchanged, and theta shifts with the data.
        levels, level_unit = self._level_series(levels)

        # Effective display unit for this panel (M3/M4). _level_series()
        # reports 'dB SPL' as its no-op unit for every inner variable, which
        # is wrong for the ones that are not levels (gap_duration is seconds,
        # mod_ind is percent, itd_ms is ms). Trust it only when it actually
        # converted, i.e. reports 'dB HL'; otherwise the VarSpec's declared
        # unit is the truth. Used for the x label AND the fit legend, which
        # previously inherited the same wrong unit.
        if level_unit == 'dB HL':
            unit_txt = 'dB HL'
        else:
            unit_txt = str(getattr(self.paradigm.inner_var, 'units', '') or '')
        x_label = axis_label(self.paradigm.inner_var,
                             units_override=unit_txt)
        
        # Clear plot
        self.ax_psychometric.clear()
        
        # Plot individual responses as small dots (top = yes, bottom = no)
        yes_levels = levels[responses == 1]
        no_levels = levels[responses == 0]
        self.ax_psychometric.plot(yes_levels, np.ones(len(yes_levels)) * 1.0, 
                                 'o', color='black', markersize=3, alpha=0.5, label='Yes')
        self.ax_psychometric.plot(no_levels, np.zeros(len(no_levels)), 
                                 'o', color='black', markersize=3, alpha=0.5, label='No')
        
        # Compute binned proportions (1 dB bins as per MultiThreshold)
        min_level = np.floor(np.min(levels)) if len(levels) > 0 else 0
        max_level = np.ceil(np.max(levels)) if len(levels) > 0 else 100
        
        if len(levels) > 0:
            bins = np.arange(min_level, max_level + 1, 1.0)  # 1 dB bins
            
            bin_centers = []
            bin_proportions = []
            bin_counts = []
            
            for i in range(len(bins) - 1):
                mask = (levels >= bins[i]) & (levels < bins[i+1])
                if np.any(mask):
                    bin_responses = responses[mask]
                    proportion = np.mean(bin_responses)
                    count = len(bin_responses)
                    bin_centers.append((bins[i] + bins[i+1]) / 2)
                    bin_proportions.append(proportion)
                    bin_counts.append(count)
            
            if bin_centers:
                # Plot proportions as circles (size = number of responses in bin)
                max_count = max(bin_counts)
                sizes = [100 * (c / max_count) for c in bin_counts]
                self.ax_psychometric.scatter(bin_centers, bin_proportions, 
                                            s=sizes, color='blue', alpha=0.6, 
                                            edgecolors='black', linewidths=1.5,
                                            zorder=5)
        
        # Plot fitted psychometric function if available
        curve_plotted = False
        if hasattr(self.paradigm, 'threshold_dB') and self.paradigm.threshold_dB is not None:
            if not np.isnan(self.paradigm.threshold_dB):
                if hasattr(self.paradigm, 'slope_k') and self.paradigm.slope_k is not None:
                    if not np.isnan(self.paradigm.slope_k):
                        # Generate smooth sigmoid curve.
                        # theta is fitted in dB SPL, so it must be shifted onto
                        # the same axis as the (possibly HL-converted) levels
                        # above (M1). k needs no conversion: the SPL->HL map is
                        # a constant offset at fixed fc, so the slope in dB is
                        # identical in both scales.
                        threshold = self._hl_value(self.paradigm.threshold_dB)
                        if threshold is None:
                            threshold = self.paradigm.threshold_dB
                        k = self.paradigm.slope_k
                        
                        # Extend range a bit beyond data for better visualization
                        x_min = min_level - 5
                        x_max = max_level + 5
                        x_range = np.linspace(x_min, x_max, 300)
                        
                        # Logistic psychometric function
                        y_curve = 1.0 / (1.0 + np.exp(-k * (x_range - threshold)))
                        
                        # Legend/console unit: unit_txt, not level_unit -
                        # see the derivation above. .strip() keeps the text
                        # tidy for dimensionless inner variables, whose
                        # unit_txt is ''.
                        theta_txt = f'{threshold:.1f} {unit_txt}'.strip()

                        # Plot fitted sigmoid curve in red
                        self.ax_psychometric.plot(x_range, y_curve, 
                                                 'r-', linewidth=3, 
                                                 label=f'Fit: θ={theta_txt}, k={k:.2f}',
                                                 zorder=10, alpha=0.9)
                        curve_plotted = True
                        
                        if self.paradigm.verbose:
                            print(f"  Psychometric curve plotted: θ={theta_txt}, k={k:.2f}")
                            print(f"  X range: {x_min:.1f} to {x_max:.1f}")
                            print(f"  Data range: {min_level:.1f} to {max_level:.1f}")
        
        if not curve_plotted and self.paradigm.verbose:
            print("  Psychometric curve NOT plotted - threshold not available yet")
        
        # Labels and formatting
        self.ax_psychometric.set_xlabel(x_label, fontsize=10, color='black')
        self.ax_psychometric.set_ylabel('P(Yes)', fontsize=10, color='black')
        self.ax_psychometric.set_title('Psychometric Function', fontsize=11, color='black', fontweight='bold')
        self.ax_psychometric.set_ylim(-0.05, 1.05)
        self.ax_psychometric.grid(True, alpha=0.3)
        self.ax_psychometric.tick_params(colors='black', labelsize=9)
        self.ax_psychometric.legend(loc='best', fontsize=8, framealpha=0.9)
        for spine in self.ax_psychometric.spines.values():
            spine.set_edgecolor('black')
        
    
    def clear_display(self):
        """Clear display (called when paradigm ends or config changes)."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(1.0, "Paradigm complete.\nWaiting for next paradigm...")
        self.status_text.config(state=tk.DISABLED)
        
        # Clear all plots
        if hasattr(self, 'ax_waveform'):
            self.ax_waveform.clear()
            self.ax_waveform.set_xlabel('Time (s)', fontsize=10, color='black')
            self.ax_waveform.set_ylabel('Amplitude (dB)', fontsize=10, color='black')
            self.ax_waveform.set_title('Stimulus Waveform (Half-Wave Rectified)', fontsize=11, color='black', fontweight='bold')
            self.ax_waveform.grid(True, alpha=0.3)
        
        if hasattr(self, 'ax_adaptive'):
            self.ax_adaptive.clear()
            self.ax_adaptive.set_xlabel('Trial Number', fontsize=10, color='black')
            self.ax_adaptive.set_ylabel('Adaptive Parameter', fontsize=10, color='black')
            self.ax_adaptive.set_title('Within-Run Variable Track', fontsize=11, color='black', fontweight='bold')
            self.ax_adaptive.grid(True, alpha=0.3)
        
        if hasattr(self, 'ax_thresholds'):
            self.ax_thresholds.clear()
            self.ax_thresholds.set_xlabel('Outer Variable', fontsize=10, color='black')
            self.ax_thresholds.set_ylabel('Threshold', fontsize=10, color='black')
            self.ax_thresholds.set_title('Previous Thresholds', fontsize=11, color='black', fontweight='bold')
            self.ax_thresholds.grid(True, alpha=0.3)
        
        if hasattr(self, 'ax_psychometric'):
            self.ax_psychometric.clear()
            self.ax_psychometric.set_xlabel('Stimulus Level', fontsize=10, color='black')
            self.ax_psychometric.set_ylabel('P(Yes)', fontsize=10, color='black')
            self.ax_psychometric.set_title('Psychometric Function', fontsize=11, color='black', fontweight='bold')
            self.ax_psychometric.set_ylim(-0.05, 1.05)
            self.ax_psychometric.grid(True, alpha=0.3)
        
        if hasattr(self, 'canvas'):
            self.canvas.draw()
        
        self.root.update_idletasks()
    
    def show_wrv_warning(self, msg: str) -> str:
        """
        Display a blocking WRV limit warning overlaid on the plot area.

        Blocks all paradigm operation until the operator chooses an option.
        'Abort paradigm' is the default (highlighted, triggered by Return/Space).

        Returns:
            'abort_paradigm' → stop everything, do not write data
            'abort_config'   → end current config, write partial data, continue
            'continue'       → do nothing, let paradigm proceed
        """
        if self.root is None:
            return 'abort_paradigm'

        result = {'choice': 'abort_paradigm'}

        # Overlay frame covering the plot area
        overlay = tk.Frame(self.plot_frame, bg="#922b21")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Warning header. ASCII-only per the garbage-char policy: icon
        # characters mojibake on the Windows lab PC, which is exactly where
        # this banner has to be readable.
        tk.Label(
            overlay,
            text="!!  WRV LIMIT HIT",
            font=("Arial", 18, "bold"),
            fg="white", bg="#922b21",
            pady=20
        ).pack()

        # Message
        tk.Label(
            overlay,
            text=msg,
            font=("Arial", 13),
            fg="white", bg="#922b21",
            wraplength=600, justify="center",
            pady=4
        ).pack()

        tk.Label(
            overlay,
            text="The adaptive track is at its boundary. Choose how to proceed:",
            font=("Arial", 11, "italic"),
            fg="#f5b7b1", bg="#922b21",
            pady=8
        ).pack()

        # Button frame
        btn_frame = tk.Frame(overlay, bg="#922b21", pady=20)
        btn_frame.pack()

        def _abort_paradigm():
            result['choice'] = 'abort_paradigm'
            overlay.destroy()

        def _abort_config():
            result['choice'] = 'abort_config'
            overlay.destroy()

        def _continue():
            result['choice'] = 'continue'
            overlay.destroy()

        # Abort paradigm — default (highlighted)
        abort_paradigm_btn = tk.Button(
            btn_frame,
            text="Abort paradigm\n[Enter / Space]",
            font=("Arial", 12, "bold"),
            fg="black", bg="#6e2a2a",
            activeforeground="black", activebackground="#5a2020",
            relief=tk.RAISED, bd=3,
            padx=18, pady=10,
            default=tk.ACTIVE,
            command=_abort_paradigm
        )
        abort_paradigm_btn.pack(side=tk.LEFT, padx=(0, 12))

        # Abort config
        tk.Button(
            btn_frame,
            text="Abort config\n[write partial data]",
            font=("Arial", 12),
            fg="black", bg="#7f8c8d",
            activeforeground="black", activebackground="#626566",
            relief=tk.RAISED, bd=2,
            padx=18, pady=10,
            command=_abort_config
        ).pack(side=tk.LEFT, padx=(0, 12))

        # Continue
        tk.Button(
            btn_frame,
            text="Continue",
            font=("Arial", 12),
            fg="black", bg="#5d6d7e",
            activeforeground="black", activebackground="#4a5568",
            relief=tk.RAISED, bd=2,
            padx=18, pady=10,
            command=_continue
        ).pack(side=tk.LEFT)

        # Keyboard shortcuts
        overlay.bind("<Return>", lambda _: _abort_paradigm())
        overlay.bind("<space>", lambda _: _abort_paradigm())
        overlay.bind("<Escape>", lambda _: _continue())

        overlay.focus_set()
        abort_paradigm_btn.focus_set()
        self.root.update()

        # Block until dismissed
        self.root.wait_window(overlay)

        return result['choice']

    def _on_close(self):
        """Handle window close button."""
        # Don't destroy — just hide
        self.root.withdraw()
    
    def show(self):
        """Show window if hidden."""
        self.root.deiconify()
    
    def hide(self):
        """Hide window."""
        self.root.withdraw()
    
    def destroy(self):
        """Destroy window (called on program exit)."""
        if self.root is not None:
            self.root.destroy()
            self.root = None


# Module-level singleton instance (persists across paradigms)
_operator_display_instance = None

# Hidden Tk root used to parent the Toplevel operator window.
# Prevents Tkinter auto-creating a visible blank window.
_tk_hidden_root = None


def get_operator_display():
    """
    Get singleton operator display instance.
    
    Creates window on first call, returns existing instance thereafter.
    This allows the same window to persist across multiple paradigm runs.
    
    Returns:
        OperatorDisplay instance
    """
    global _operator_display_instance
    
    if _operator_display_instance is None:
        _operator_display_instance = OperatorDisplay()
    
    return _operator_display_instance


def close_operator_display():
    """Close and destroy operator display (called on program exit)."""
    global _operator_display_instance
    
    if _operator_display_instance is not None:
        _operator_display_instance.destroy()
        _operator_display_instance = None
