# Implementation Plan — 5 Major Priorities

Comprehensive plan for completing the audiology test battery based on codebase analysis and documentation review.

---

## Priority 1: Operator GUI (Real-Time Monitoring)

### **Current State**
- No operator display exists; only verbose terminal output
- `AdaptiveParadigm.main()` runs headlessly except for participant GUI
- Paradigm state tracked internally (`trial_num`, `current_streak`, `total_num_reversals`, `threshold_dB`, etc.) but not visualized

### **Reference Material**
- **MultiThreshold manual section 3.4 (Graphics)**: Shows 3 panels in operator GUI:
  - **Panel 37**: Stimulus waveform display (half-wave rectified, log scale)
  - **Panel 38**: Within-run variable track (adaptive level over trials + running threshold estimate)
  - **Panel 39**: Previous thresholds (all completed runs in current session)
  - **Panel 40**: Psychometric function (prob correct vs level)
- **Lecluyse 2013**: Describes threshold estimation via psychometric function fitting (Boltzmann sigmoid)

### **Design Approach**

#### Architecture
```
┌─────────────────────┐
│  AdaptiveParadigm   │
│   (existing code)   │
└──────────┬──────────┘
           │
           │ calls after each trial
           ▼
  ┌────────────────────┐
  │   OperatorDisplay  │ ← new class
  │   (in Tkinter)     │
  └────────────────────┘
           │
      ┌────┴────┐
      ▼         ▼
   Matplotlib   Tkinter
   (plots)      (text/tables)
```

**Separation of concerns:**
- `AdaptiveParadigm` → runs trial logic, stores data
- `OperatorDisplay` → subscribes to paradigm events, updates plots

#### Implementation Steps

**Step 1.1: Create OperatorDisplay class (Tkinter + Matplotlib)**

Location: `operator_gui.py`

```python
class OperatorDisplay:
    def __init__(self, paradigm):
        self.paradigm = paradigm
        self.root = tk.Toplevel()  # separate window from participant GUI
        self.root.title("Operator — " + paradigm.paradigm_code)
        
        # Layout: left panel = text, right panel = plots
        #  ┌──────────┬──────────────┐
        #  │  Info    │   Plots      │
        #  │  Text    │              │
        #  └──────────┴──────────────┘
        
        self.info_frame = tk.Frame(self.root)  # text stats
        self.plot_frame = tk.Frame(self.root)  # matplotlib canvases
        
    def update_trial(self):
        """Called by paradigm after each trial."""
        # Update text (current config, trial, streak, reversals)
        # Update plots (adaptive track, threshold history)
        
    def update_config(self):
        """Called when paradigm moves to next config."""
        # Log completed threshold
        # Update threshold history plot
```

**Where to integrate:** Modify `AdaptiveParadigm.main()`:

```python
def main(self):
    # ...
    if self.show_operator_display:
        from operator_gui import OperatorDisplay
        self.operator_display = OperatorDisplay(self)
    
    # In trial loop, after check_answer():
    if hasattr(self, 'operator_display'):
        self.operator_display.update_trial()
```

**Step 1.2: Implement plots**

**Plot 1: Adaptive track (panel 38 equivalent)**
- X-axis: trial number (within current config)
- Y-axis: adaptive parameter value (dB for PTA, masker level for IFMC/TMC, gap for GAP, etc.)
- Plot: scatter points for each trial, color-coded by response (TP=green, FN=red, TN/FP=gray)
- Overlay: running threshold estimate (psychometric function mean — see below)

**Plot 2: Threshold history (panel 39 equivalent)**
- X-axis: config number
- Y-axis: threshold estimate (dB)
- Bar chart or scatter: one point per completed config

**Plot 3: Psychometric function (panel 40 equivalent, optional)**
- X-axis: stimulus level (dB)
- Y-axis: p(detect)
- Fit: Boltzmann sigmoid to trial data
- Note: This requires adding `fit_psychometric_function()` (see Step 1.3)

**Step 1.3: Add threshold estimation via psychometric fitting**

Currently `AdaptiveParadigm` computes `threshold_dB` as midpoint of last two levels — this is a placeholder. MultiThreshold fits a psychometric function. Add to `adaptive_paradigm.py`:

```python
def fit_psychometric_function(self):
    """
    Fit Boltzmann sigmoid to response data (Lecluyse & Meddis 2009).
    
    Returns: (threshold, slope_k)
      threshold = 50% point on psychometric curve
      slope_k   = steepness parameter
    """
    # Gather (level, response) pairs for current config
    levels = [row['adaptive_param_value'] for row in self.current_config_trials]
    responses = [1 if row['correct_answer'] in ['TP', 'TN'] else 0 for row in self.current_config_trials]
    
    # Fit: p(detect) = 1 / (1 + exp(-(level - threshold)/slope_k))
    from scipy.optimize import curve_fit
    def boltzmann(x, threshold, slope_k):
        return 1 / (1 + np.exp(-(x - threshold) / slope_k))
    
    (threshold, slope_k), _ = curve_fit(boltzmann, levels, responses, 
                                        p0=[np.mean(levels), 2.0])
    return threshold, slope_k
```

Call this at the end of each config (when `end_config=True`) and log to CSV.

**Step 1.4: Text info panel**

Display in left panel:
```
Paradigm: PTA
Participant: P001
Config: 3 / 15
  - Frequency: 1000 Hz
  - Duration: 0.5 s

Current Trial: 14
Streak: +2 (2 correct in a row)
Reversals: 2
Trials Remaining: 6

False Alarm Rate: 3.2%

Current Level: 42.3 dB
Threshold Estimate: 38.7 dB (running)
```

Update this after every trial via `update_trial()`.

**Step 1.5: Stimulus waveform display (optional, panel 37)**

This is less critical — MultiThreshold shows it for debugging, but it's not essential for operation. Defer to later or skip entirely.

---

### **Questions / Uncertainties**
- Do you want a **single operator window across all paradigms**, or a new window per paradigm?
  - Recommendation: Single persistent window, cleared/reset between paradigms.
  
- **Matplotlib vs Plotly/Bokeh?**
  - Tkinter + Matplotlib is simplest and already compatible with existing Tk participant GUI.
  - Later refactor to NiceGUI can use Plotly.

- **Psychometric fitting: always enabled?**
  - Recommendation: Add as optional feature (default ON), since it's the "proper" threshold estimate per Lecluyse.

---

### **Implementation Timeline**
- **Week 1**: Create `OperatorDisplay` shell, integrate into `AdaptiveParadigm`, show text panel only
- **Week 2**: Add Plot 1 (adaptive track) with real-time updates
- **Week 3**: Add Plot 2 (threshold history), implement psychometric fitting
- **Week 4**: Polish, test across all paradigms (PTA, GAP, IFMC, TMC, etc.)

---

## Priority 2: Headphone Calibration

### **Current State**
- **No calibration implemented**: `TrialPlayer.db2amp()` is a placeholder (linear `10^(dB/20)`)
- **No SPL mapping**: dB values are "relative" (0 dB = 0 amplitude, 100 dB = 1.0 amplitude)
- **No frequency response correction**: headphone colorations not compensated

### **Reference Material**
- **UZH MultiThreshold doc**: Describes calibration file loading (frequency-specific correction values in dB attenuation)
- **Miro diagram**: Shows calibration workflow:
  1. Measure frequency response (pink noise or swept sine → mic/dummy head)
  2. Compute inverse filter (FIR or minimum-phase)
  3. Measure level (SPL at fixed amplitude → compute gain offset)
  4. Apply corrections in signal chain

### **Design Approach**

#### Two-Part Calibration

**Part A: Frequency Response Correction (Inverse Filter)**

Goal: Flatten headphone frequency response so that all frequencies are reproduced at equal SPL for equal digital amplitude.

**Workflow:**
1. **Measurement** (you're doing this in REW):
   - Play pink noise or log swept sine through headphones
   - Measure with calibrated mic or HATS (Head-And-Torso Simulator)
   - Export impulse response (IR) or frequency response
   
2. **Inverse filter generation** (also in REW or offline):
   - REW can generate minimum-phase FIR inverse filters
   - Export as WAV impulse response (e.g., `headphone_left_inverse.wav`, `headphone_right_inverse.wav`)
   
3. **Convolution** (in Python):
   - Load IR once at startup
   - Convolve every output signal with IR before playback

**Part B: SPL Level Mapping (Gain Calibration)**

Goal: Map dB SPL to digital amplitude so that `30 dB SPL` actually produces 30 dB SPL at the headphone.

**Workflow:**
1. **Measurement**:
   - Play 1 kHz tone at known digital amplitude (e.g., amp=0.5)
   - Measure SPL at headphone with calibrated mic
   - Record: `amp=0.5 → 65 dB SPL` (example)
   
2. **Compute calibration**:
   - `reference_amp = 0.5`
   - `reference_spl = 65.0`  # measured
   - Any desired SPL: `amp = reference_amp * 10^((desired_spl - reference_spl)/20)`
   
3. **Store in config file**:
   ```json
   {
     "left": {
       "reference_amp": 0.5,
       "reference_spl_1kHz": 65.0,
       "inverse_filter_path": "calibration/left_inverse.wav"
     },
     "right": { ... }
   }
   ```

#### Implementation Steps

**Step 2.1: Create CalibrationManager class**

Location: `utils/calibration.py`

```python
class CalibrationManager:
    def __init__(self, config_path="calibration/calibration.json"):
        self.config = self.load_config(config_path)
        self.inverse_filters = self.load_inverse_filters()
        
    def spl_to_amplitude(self, spl_dB, ear="diotic"):
        """Convert SPL (dB) to digital amplitude (0-1)."""
        ref_amp = self.config[ear]["reference_amp"]
        ref_spl = self.config[ear]["reference_spl_1kHz"]
        return ref_amp * 10**((spl_dB - ref_spl) / 20)
    
    def apply_correction(self, signal, ear="diotic"):
        """Convolve signal with inverse filter."""
        ir = self.inverse_filters[ear]
        return scipy.signal.fftconvolve(signal, ir, mode='same')
```

**Step 2.2: Integrate into TrialPlayer**

Modify `TrialPlayer.__init__()`:

```python
def __init__(self, ...):
    # ...
    self.calibration = CalibrationManager()  # singleton, load once
    
def db2amp(db_spl):
    """DEPRECATED: Use calibration.spl_to_amplitude() instead."""
    # Keep for backward compatibility, but warn
    return self.calibration.spl_to_amplitude(db_spl)
```

Modify `play_trial()`:

```python
def play_trial(self):
    # After generating self.sound (stereo numpy array):
    # Apply inverse filter
    self.sound[:, 0] = self.calibration.apply_correction(self.sound[:, 0], ear="left")
    self.sound[:, 1] = self.calibration.apply_correction(self.sound[:, 1], ear="right")
    
    # Then play as usual
    ptbsound = ptb.audio.Sound(self.sound, sampleRate=self.fs)
    ptbsound.play()
```

**Step 2.3: Update all paradigms to use real SPL**

Currently paradigms use arbitrary units (amplitude 0-1). Change to dB SPL:

**Example — PTA:**
```python
# OLD (adaptive_paradigm.py inner variable):
VarSpec(name="trial_amp", data={'start': 0.5, ...})  # amplitude

# NEW:
VarSpec(name="trial_spl", data={'start': 30.0, 'step_down': -10, ...})  # dB SPL
```

Then in `prepare_trial()`:
```python
amp = self.calibration.spl_to_amplitude(self.trial_spl)
self.tp.new_trial(fc=self.fc, amp=amp, ...)
```

**Step 2.4: Calibration procedure GUI**

Create `calibration_tool.py` to help generate calibration files:

1. Play 1 kHz tone at various amplitudes
2. Operator enters measured SPL
3. Tool computes reference values
4. Saves to `calibration.json`

---

### **Questions / Uncertainties**

- **REW workflow confirmation needed:**
  - You mentioned starting REW calibration — do you have:
    1. Measurement mic calibration file?
    2. HATS or in-ear mic?
    3. REW exporting inverse filters as WAV?
  - I can help verify the REW setup if needed.

- **Per-frequency calibration?**
  - UZH doc mentions frequency-specific correction values. This is handled by the inverse filter (FIR) — no need for per-tone lookup tables if using convolution.

- **Latency from convolution?**
  - FIR convolution adds latency (~IR length / 2). Use minimum-phase IRs (REW option) to minimize.
  - Psychopy PTB audio handles this, but test to confirm no audible artifacts.

---

### **Implementation Timeline**
- **Week 1**: Complete REW measurements, generate inverse filters
- **Week 2**: Create `CalibrationManager`, integrate SPL→amp conversion into `TrialPlayer`
- **Week 3**: Add inverse filter convolution, test with PTA
- **Week 4**: Update all paradigms to use SPL, validate with acoustic measurements

---

## Priority 3: Paradigm Testing & Tuning

### **Current State**
- All paradigms implemented and syntactically correct
- Not yet validated against MultiThreshold behavior or team requirements
- Parameters (start levels, step sizes, trial counts) use defaults from literature but not tuned for PROLACTIN

### **Testing Plan**

#### Phase 1: Functional Verification (Week 1-2)
For each paradigm, verify:
1. **Adaptive logic**: Does level/difficulty track correctly?
   - Run with synthetic responses (mock participant)
   - Check reversal detection, midpoint reset, trial countdown
2. **CSV output**: All expected columns present and correct?
3. **Catch trials**: FP detection working?
4. **Multi-config looping**: Outer variables iterate properly?

**Tool to build:** `mock_participant.py`
```python
class MockParticipant:
    """Simulates participant with known threshold."""
    def __init__(self, true_threshold=40.0, lapse_rate=0.05):
        self.threshold = true_threshold
        self.lapse_rate = lapse_rate
    
    def respond(self, stimulus_level):
        """Return 1 (heard) or 0 (not heard) based on psychometric function."""
        p_detect = 1 / (1 + np.exp(-(stimulus_level - self.threshold) / 2))
        if np.random.rand() < self.lapse_rate:
            p_detect = 1 - p_detect  # lapse
        return 1 if np.random.rand() < p_detect else 0
```

Run each paradigm with mock participant, compare estimated threshold to `true_threshold`.

#### Phase 2: Parameter Tuning (Week 3-4)

**What to tune:**
- **Start levels**: Too low → lots of trials before reversal. Too high → unsafe (especially LDL)
- **Step sizes**: Too large → imprecise threshold. Too small → slow convergence
- **Trial count after reversal**: More trials → better precision, longer session

**Method:**
1. Run 100 simulations per paradigm with mock participant
2. Measure:
   - Threshold estimation error (bias & variance)
   - Session duration (number of trials)
   - False alarm rate (if catch trials)
3. Adjust parameters to optimize precision/duration tradeoff

**Example findings (from Lecluyse 2009):**
- 10 dB → 2 dB steps optimal for PTA
- 10 trials after reversal gives ~1 dB accuracy for normal hearing

#### Phase 3: UX Testing (Week 5-6)

**Participant UX:**
- Run paradigms with naive participants (lab members)
- Collect feedback:
  - Are instructions clear?
  - Is task difficulty appropriate?
  - Any confusing elements?
- Common issues to watch:
  - Forward masking tasks (IFMC/TMC) harder than PTA — need good training
  - LDL: participants may hesitate to report "uncomfortable" — emphasize safety

**Operator UX:**
- Can operator monitor progress?
- Are alerts for false alarms visible?
- Can operator abort/restart runs easily?

#### Phase 4: Validation Against Literature (Week 7)

Compare your results to published norms:
- **PTA**: Thresholds should be <20 dB HL for normal hearing
- **IFMC depth**: ~20-30 dB for normal hearing (Lecluyse 2013)
- **TMC slope**: 30-40 dB/100ms for normal hearing (Lecluyse 2013)
- **GAP**: <5 ms threshold for normal hearing

---

### **Implementation Timeline**
- **Week 1-2**: Build mock participant, run automated tests
- **Week 3-4**: Parameter optimization via simulation
- **Week 5-6**: UX testing with humans
- **Week 7**: Validation against literature norms

---

## Priority 4: HID Input (Tablet / MIDI Controller)

### **Current State**
- Participant GUI uses tkinter buttons + keyboard
- No external HID support

### **Design Approach**

#### Option A: NiceGUI Web Interface (Tablet)

**Advantages:**
- Cross-platform (any device with browser)
- Touch-friendly UI
- Modern, polished appearance

**Architecture:**
```
┌──────────────────┐         ┌─────────────────┐
│  Paradigm        │ ◄──────►│  NiceGUI Server │
│  (Python)        │  HTTP   │  (localhost)    │
└──────────────────┘         └────────┬────────┘
                                      │
                                      ▼
                              ┌───────────────┐
                              │  Tablet/Phone │
                              │  (Browser)    │
                              └───────────────┘
```

**Implementation:**
1. Install NiceGUI: `pip install nicegui`
2. Create `participant_gui_web.py`:
```python
from nicegui import ui

class ParticipantGUIWeb:
    def __init__(self, paradigm):
        self.paradigm = paradigm
        
    @ui.page('/')
    def main_page():
        ui.label('Did you hear the tone?').classes('text-2xl')
        ui.button('No', on_click=lambda: self.respond(0))
        ui.button('Yes', on_click=lambda: self.respond(1))
        
    def respond(self, value):
        self.paradigm.user_input = value
        # Signal paradigm to continue
```

3. Integrate into `AdaptiveParadigm`:
```python
def main(self):
    if self.use_web_gui:
        self.web_gui = ParticipantGUIWeb(self)
        self.web_gui.start(port=8080)
```

4. On tablet: Navigate to `http://[computer-ip]:8080`

**Challenges:**
- Threading: NiceGUI server runs in separate thread from paradigm loop
- Synchronization: Need event-based signaling (use `threading.Event()` or async)

#### Option B: MIDI Controller

**Advantages:**
- Hardware buttons (tactile feedback)
- Low latency
- No screen required

**Implementation:**
1. Install `python-rtmidi`: `pip install python-rtmidi`
2. Create `midi_input.py`:
```python
import rtmidi

class MIDIInput:
    def __init__(self):
        self.midiin = rtmidi.MidiIn()
        ports = self.midiin.get_ports()
        self.midiin.open_port(0)  # Open first MIDI device
        self.midiin.set_callback(self.on_midi_message)
    
    def on_midi_message(self, message, data):
        # MIDI note-on: message[0][0] == 144
        # Note number: message[0][1]
        # Map buttons: 60 = "No", 61 = "Yes"
        if message[0][0] == 144:  # Note on
            note = message[0][1]
            if note == 60:
                self.response = 0
            elif note == 61:
                self.response = 1
```

3. Integrate into `AdaptiveParadigm.get_response()`:
```python
def get_response(self):
    if self.use_midi:
        while self.midi_input.response is None:
            time.sleep(0.01)
        return self.midi_input.response
    else:
        # Standard Tk GUI
```

#### Option C: TouchOSC

Similar to MIDI but uses OSC (Open Sound Control) protocol over network. Good for wireless tablets.

---

### **Recommendation**
Start with **Option A (NiceGUI)** — it's most flexible and allows building custom UIs per paradigm. MIDI/OSC can be added later as alternative input methods.

---

### **Implementation Timeline**
- **Week 1**: NiceGUI prototype for single paradigm (PTA)
- **Week 2**: Integrate event-based communication with AdaptiveParadigm
- **Week 3**: Deploy to tablet, test latency/reliability
- **Week 4**: Extend to all paradigms, polish UI

---

## Priority 5: Refactoring & OOP Structure

### **Current State**
- `AdaptiveParadigm` is monolithic (945 lines)
- GUI code mixed with trial logic
- No clear separation: Paradigm / TrialPlayer / EventGen / GUI / DataManager

### **Target Architecture (from Miro diagram)**

```
┌─────────────────────────────────────┐
│   ExperimentalController            │
│   (orchestrates everything)         │
└──────┬──────────────────────────────┘
       │
   ┌───┴────┬──────────┬─────────┐
   ▼        ▼          ▼         ▼
Paradigm   GUI    DataManager  I/O
  Base    (Participant  (logs,   (HID,
 (logic)  + Operator)  results) calib)
```

### **Refactoring Plan**

#### Step 5.1: Extract GUI from AdaptiveParadigm

**Current:** `AdaptiveParadigm` contains Tkinter code inline (`get_response()`, `update_gui_state()`)

**Target:** Separate GUI class

```python
class ParticipantGUI:
    """Handles participant response collection."""
    def __init__(self, config):
        self.config = config
        self.root = tk.Tk()
        
    def get_response(self):
        """Block until response, return int (0, 1, 2, etc.)."""
        # All Tk code here
        
    def show_message(self, text):
        """Display message to participant."""

class OperatorGUI:
    """Handles operator display (real-time plots)."""
    def __init__(self, paradigm):
        # All Matplotlib + Tkinter code here
```

Then `AdaptiveParadigm`:
```python
def __init__(self, params, gui=None):
    if gui is None:
        self.gui = ParticipantGUI(self.gui_config)
    else:
        self.gui = gui  # injectable (for web GUI, etc.)
        
def main(self):
    # ...
    self.user_input = self.gui.get_response()  # delegate
```

#### Step 5.2: Create DataManager class

**Current:** `AdaptiveParadigm` manages `self.data` DataFrame and `write_data_to_disk()`

**Target:**
```python
class DataManager:
    """Handles all data logging and I/O."""
    def __init__(self, participant_id, paradigm_code):
        self.participant_id = participant_id
        self.paradigm_code = paradigm_code
        self.data = []  # list of dicts, one per trial
        
    def log_trial(self, trial_dict):
        """Add trial to data store."""
        self.data.append(trial_dict)
        
    def save(self, directory="test_data"):
        """Write to CSV."""
        df = pd.DataFrame(self.data)
        # ... timestamp, filename, etc.
```

#### Step 5.3: Create I/O class (calibration + HID)

```python
class IOManager:
    """Handles audio calibration and input devices."""
    def __init__(self):
        self.calibration = CalibrationManager()
        self.hid = self.detect_hid()  # MIDI, OSC, keyboard
        
    def get_input(self):
        """Blocking read from HID."""
        if self.hid.type == "midi":
            return self.hid.read_midi()
        elif self.hid.type == "web":
            return self.hid.read_web()
        else:
            return self.hid.read_keyboard()
```

#### Step 5.4: Refactor AdaptiveParadigm → cleaner separation

**Final structure:**
```python
class AdaptiveParadigm:
    def __init__(self, params, participant_id, io=None, data_manager=None):
        self.params = params
        self.io = io or IOManager()
        self.data_manager = data_manager or DataManager(participant_id, self.paradigm_code)
        self.participant_gui = ParticipantGUI(self.gui_config)
        self.operator_gui = OperatorGUI(self) if SHOW_OPERATOR else None
        
    def main(self):
        # Pure trial logic — no GUI/data code
        for config in self.configs:
            for trial in self.trials:
                self.prepare_trial()
                self.tp.play_trial()
                response = self.io.get_input()  # abstracted
                self.check_answer(response)
                self.data_manager.log_trial(self.get_log_data())
                if self.operator_gui:
                    self.operator_gui.update()
        self.data_manager.save()
```

**Benefits:**
- Each class has single responsibility
- GUIs are swappable (Tkinter → NiceGUI is just changing `ParticipantGUI` class)
- Testing easier (mock `IOManager` for unit tests)
- Calibration changes don't touch paradigm code

---

### **Implementation Timeline**
- **Week 1**: Extract GUI classes (Participant + Operator)
- **Week 2**: Create DataManager, refactor logging
- **Week 3**: Create IOManager, integrate calibration
- **Week 4**: Clean up AdaptiveParadigm, update all paradigms to use new structure

---

## Cross-Priority Dependencies

```
Priority 2 (Calibration) ──> Must complete before Priority 3 (Testing)
                              (can't validate thresholds without SPL calibration)

Priority 1 (Operator GUI) ──> Helps with Priority 3 (Testing)
                              (easier to monitor during UX tests)

Priority 5 (Refactor) ────> Should happen AFTER Priorities 1-3
                              (don't refactor unstable code)
                              
Priority 4 (HID) ─────────> Can happen in parallel with Priorities 1-2
```

**Recommended order:**
1. **Calibration (Priority 2)** — foundational
2. **Operator GUI (Priority 1)** — enables better monitoring
3. **Testing & Tuning (Priority 3)** — validate everything works
4. **HID Input (Priority 4)** — improve UX
5. **Refactoring (Priority 5)** — solidify architecture

---

## Open Questions for Discussion

1. **Operator GUI**: Single window for all paradigms, or per-paradigm windows?
2. **REW workflow**: Do you need help verifying the calibration measurements?
3. **NiceGUI**: Worth migrating participant GUI now, or wait until after Priority 3?
4. **Psychometric fitting**: Always compute, or only when explicitly requested?
5. **Session management**: Do you need a "session controller" to run multiple paradigms in sequence (e.g., PTA → IFMC → TMC) automatically?

---

## Estimated Total Timeline

Assuming one person working full-time:

- **Priority 2 (Calibration)**: 4 weeks
- **Priority 1 (Operator GUI)**: 4 weeks
- **Priority 3 (Testing)**: 7 weeks
- **Priority 4 (HID)**: 4 weeks
- **Priority 5 (Refactor)**: 4 weeks

**Total: ~23 weeks (5-6 months)**

If priorities run in parallel (e.g., HID while testing), could compress to **~16 weeks (4 months)**.

