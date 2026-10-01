# PRD 2026-07-17 — M3/M4: previous-thresholds subplot (panel 39)

_Scope: `varspec.py`, `operator_gui.py`, all 11 `test_*.py` (metadata only).
No base-class adaptive-logic edit, no calibration path. Decisions confirmed by
Eric across the 2026-07-17 GUI session._

---

## Goal

Panel 39 currently plots threshold vs **ordinal config number**, one blue
marker style for everything, with a wheat text box listing every config's outer
vars as free text. For PTA that is an audiogram rendered as a meaningless
integer x-axis; for IFMC it collapses two probe frequencies onto one
indistinguishable series.

Make panel 39 plot threshold vs the **real values of `outer_1`**, with
`outer_2..N` as visually distinct series. M3 and M4 are the same code — M4 is
M3 plus the IFMC/TMC series case, which falls out of the same rule.

Prerequisite (also fixes two TO-DOs on panels 2 and 4): `VarSpec` carries no
display metadata, so no axis anywhere can name its variable properly.

---

## Root cause / current state (verified in code, 2026-07-17)

- `operator_gui._update_threshold_plot` L~540: `config_nums =
  completed_configs['config_num'].values` -> x is the ordinal config index.
  `set_xticks(config_nums)` locks it to integers.
- Single hardcoded style (`marker='o', color='blue'`); no series concept.
- L~580-610: builds `legend_lines` as text, renders via `ax.text()` in a wheat
  box. Not a real legend; unreadable past a few configs.
- `varspec.VarSpec` has **only** `name` + `data`. Nothing records that
  `trial_amp` is dB SPL, `itd_ms` is ms, `fc` is Hz, or that `mod_ind` is
  dimensionless. Panel 2 therefore renders the raw identifier `trial_amp`;
  panel 4 hardcodes `'Stimulus Level'`, which is already wrong for GAP
  (`gap_duration`, s), AM/FM (`mod_ind`), ITD (`itd_ms`).
- Startup placeholders (`_create_plot_panel_placeholder` L161/171/180) read
  `'Adaptive Parameter'` / `'Threshold (dB)'` / `'Stimulus Level (dB)'`. L171 is
  **byte-identical to the non-HL dynamic label**, so "not yet rendered" is
  indistinguishable from "rendered in SPL mode" (cost real debugging time this
  session).

### Outer-var audit (all 11 paradigms, 2026-07-17)

| paradigm | outer_1 | outer_2..N | series |
|---|---|---|---|
| PTA | `fc` (6) | `pan` (2) | 2 |
| LDL | `fc` | `pan` (2) | 2 |
| IFMC | `masker_freq_ratio` (7) | `probe_freq` (runtime ~2) | ~2 |
| TMC | `gap_duration` (4) | `probe_freq` (runtime ~2) | ~2 |
| AM | `fc` (6) | `fm`(1), `tone_level_db`(1) | 1 |
| FM | `fc` (6) | `fm`(1), `tone_level_db`(1) | 1 |
| DLI | `fc` (6) | `ref_level_db`(1) | 1 |
| ILD | `fc` (2) | `ref_level_db`(1) | 1 |
| ITD | `signal_type`(1, **str**) | `fc`(1), `ref_level_db`(1) | 1 |
| GAP | `noise_level_db`(1) | — | 1 |
| SRT | `pan`(1) | — | 1 |

Findings driving the spec:

1. `outer_1` is the correct x-axis for PTA (`fc` -> audiogram) and IFMC
   (`masker_freq_ratio` -> conventional IFMC curve). Convention holds where it
   matters.
2. **ITD `outer_1` is a string** (`signal_type`) -> needs a non-numeric path.
   ITD is also the one paradigm where `outer_1` is arguably NOT the natural
   x-axis (`outer_2 = fc` is). Latent only: singleton today.
3. **GAP / SRT have single-valued `outer_1`** -> single-point plot. Must not
   crash, must not draw a legend.
4. **AM/FM/DLI/ITD/ILD declare constants as outer vars** (`fm=[8]`,
   `tone_level_db=[60.0]`, `ref_level_db=[60.0]`). Crossing these into series
   yields labels like `fm=8, tone_level_db=60.0` on every line — pure noise.

Max series today = **2**. No cap needed (Eric, 2026-07-17).

---

## Decisions (settled, do not re-litigate)

| # | Decision |
|---|---|
| D1 | x-axis = `outer_1`, real values. Convention documented in the base-class `params` docstring; NOT enforced by a new schema field. |
| D2 | Series = cross product of `outer_2..N`, **filtered to `len(v.data) > 1`**. |
| D3 | Filtered-out constants shown as a **subtitle annotation**, not dropped. Provisional — revisit after live use. |
| D4 | No series cap. Max is 2; the D2 filter pushes it further out. |
| D5 | x log-scaled iff span >= **1 decade**. NOT 2 decades — PTA `fc` spans 1.51, TMC `gap_duration` 0.90; a 2-decade rule would render the audiogram linear. |
| D6 | Override attr `threshold_plot_x_log = None` on the base class (None = infer, True/False = force). Escape hatch; TMC sits 10% from flipping. |
| D7 | Non-numeric `outer_1` -> minimal ordinal fallback + category tick labels. No crash. |
| D8 | `VarSpec` gains **optional** `label` + `units`. Empty **or missing** -> ignored, fall back to `name`. |
| D9 | Placeholder labels lose their fake units. |
| D10 | Connect-points **on**, hardcoded. Operator toggle deferred (see Deferred). |
| D11 | `units` is a **label only, never a conversion instruction**. `gap_duration` declares `units="s"` (matches storage). No `display_scale` field. |
| D12 | Per-marker value labels **dropped entirely**. Re-add for the single-series case deferred (see Deferred). |
| D13 | `pan` series render as `pan=-1.0` / `pan=1.0`. Left/Right mapping deferred (see Deferred). |
| D14 | x ticks **forced to the actual `outer_1` values** with plain formatting (no matplotlib log-decade ticks). Audiogram convention. |
| D15 | All 11 `test_*.py` in one commit (Eric, 2026-07-17). |

---

## Implementation, per file

### `varspec.py`

```python
@dataclass
class VarSpec:
    name:  str = ""
    data:  list = field(default_factory=list)
    label: str = ""   # human-readable axis label; falls back to name
    units: str = ""   # "dB SPL" | "Hz" | "ms" | "" (dimensionless)
```

Additive; both default `""`. Every existing call site keeps working untouched.

**Access rule (D8):** consumers use `getattr(vs, 'label', '') or vs.name` and
`getattr(vs, 'units', '')` — never bare attribute access. Handles empty AND
missing, so an older/duck-typed VarSpec cannot break the GUI.

Helper (module-level, so GUI and future plotting share one implementation):

```python
def axis_label(vs) -> str:
    """'Frequency (Hz)' / 'Modulation Index' / 'trial_amp'. Never raises."""
```

### `operator_gui.py`

- `_update_threshold_plot()` — rewrite the x/series/legend core:
  - x = real `outer_1` values pulled per completed config from the logged
    columns (already universal since H2).
  - series = D2 cross product; distinct colour + marker per series; real
    `ax.legend()` replaces the wheat `ax.text()` box.
  - log/linear per D5/D6.
  - Non-numeric `outer_1` per D7.
  - Degenerate (single config / single x value): plot the point, no legend.
  - D3 annotation for filtered constants.
  - Value labels next to markers: **removed** (D12). The existing
    `ax.text(config_num + 0.3, threshold, f'{threshold:.1f}')` loop goes.
  - Points connected within a series (D10), hardcoded.
  - `set_xticks(sorted(unique outer_1 values))` + plain scalar formatting (D14),
    so a log axis still reads 250/500/1000/2000/4000/8000 rather than decades.
  - Units via `axis_label()`; y unchanged (existing `hl_mode` logic already
    correct).
- `_update_adaptive_plot()` — y label via `axis_label(inner_var)` instead of
  raw `param_name`. Keeps the M1 `_level_series` unit override when in HL.
- `_update_psychometric_plot()` — x label via `axis_label(inner_var)` instead of
  hardcoded `'Stimulus Level'`. Fixes GAP/AM/FM/ITD mislabelling.
- `_create_plot_panel_placeholder()` / `clear_display()` — D9: `'Adaptive
  Parameter'` -> `'Adaptive Parameter'` (no unit), `'Threshold (dB)'` ->
  `'Threshold'`, `'Stimulus Level (dB)'` -> `'Stimulus Level'`.

### `adaptive_paradigm.py`

- Class attr `threshold_plot_x_log = None` (D6) + docstring.
- `params` docstring: document the `outer_1` = primary/x-axis convention (D1).

### `test_*.py` (all 11)

Metadata only — add `label=` / `units=` to each inner + outer `VarSpec`. One
line per var. **No logic, no values, no config changes.**

Examples: `fc` -> `label="Frequency", units="Hz"`; `trial_amp` ->
`label="Tone Level", units="dB SPL"`; `masker_freq_ratio` ->
`label="Masker/Probe Frequency Ratio"` (dimensionless); `gap_duration` ->
`label="Gap Duration", units="s"` (**D11:** stored in seconds; `units` never
triggers conversion); `itd_ms` -> `label="ITD", units="ms"` (stored in ms —
consistent); `mod_ind` ->
`label="Modulation Index"`; `pan` -> `label="Ear"`.

---

## Key signatures

| file | signature |
|---|---|
| `varspec.py` | `label: str = ""   # human-readable axis label; falls back to name` |
| `varspec.py` | `def axis_label(vs) -> str:` |
| `operator_gui.py` | `_THRESHOLD_PLOT_LOG_DECADES = 1.0` |
| `operator_gui.py` | `def _series_key(self, config_data, series_vars):` |
| `operator_gui.py` | `self.ax_thresholds.set_xscale('log')` |
| `adaptive_paradigm.py` | `threshold_plot_x_log = None   # None = infer (see M3/M4)` |
| `test_pta.py` | `VarSpec(name="fc", data=AUDIOMETRIC_FREQS, label="Frequency", units="Hz")` |
| `test_ifmc.py` | `label="Masker/Probe Frequency Ratio"` |

---

## Out of scope

- `adaptive_paradigm` adaptive logic, staircase, fit, reversal handling.
- Calibration path: `spl_to_amplitude()`, `per_channel_gain`, TrialPlayer,
  calibration guard. Untouched.
- Panels 37/38/40 beyond the two label fixes above.
- `paradigm_setup_dialog.py` (M5/M6 — deferred by Eric this session).
- L14 (paradigm-aware FP warning text) — deferred.
- **`operator_gui.py` L941 `⚠` (U+26A0)** — icon char, violates the
  garbage-char policy. Pre-existing, deliberately not touched. Separate cleanup
  with L7 (`paradigm_ifmc.py` arrows).
- ITD `outer_1` semantic question (`signal_type` vs `fc` as natural x-axis) —
  D7 handles the type; the ordering question is a team call, not this PRD.
- H1/M8 mulligan, H4/T5, H9 — unrelated.

---

## Suggested implementation order

| # | Step | Files | Commit |
|---|---|---|---|
| 1 | `VarSpec.label`/`units` + `axis_label()` | `varspec.py` | 1 |
| 2 | Populate metadata | 11x `test_*.py` | 2 |
| 3 | Panel 2/4 labels + D9 placeholders | `operator_gui.py` | 3 |
| 4 | Panel 39 core (x/series/legend/log/fallbacks) | `operator_gui.py`, `adaptive_paradigm.py` | 4 |

Steps 1-3 are independently shippable and verifiable without touching panel 39.
Step 4 is the real work and consumes 1-3.

---

## Adversarial review — high-severity risks

1. **Stale-base hazard on 11 `test_*.py` files.** Widest blast radius since the
   06-26 incident, which was caused by exactly this. **The Key-Signature check
   does NOT cover this:** signatures only exist for files a previous session
   changed, and only `test_ldl.py` has one (`'step_up_initial':    5.0,`). The
   other ten have no signature, so a stale file passes session-start clean and
   is then edited against the wrong base. **Mitigation:** (a) Eric pushes all 11
   + `varspec.py` before the session starts; (b) before editing, grep all 11 for
   their `"inner"` / `"outer_N"` VarSpec declarations and print as a table for
   Eric to confirm against his local copies — those are the exact lines Step 2
   edits, so a match proves currency where it matters. Non-negotiable.
2. **`test_*.py` are Eric's live config files.** He edits values there between
   runs. A metadata-only diff that silently reformats a `data=` list would
   destroy real configuration. **Mitigation:** additive `label=`/`units=` kwargs
   only; diff must show zero changes to `name=` / `data=`; assert per-file.
3. **D5 threshold is 10% from misfiring.** TMC `gap_duration` = 0.90 decades vs
   a 1.0 rule. Extend gaps to 50 ms -> exactly 1.0 -> silently flips to log.
   **Mitigation:** D6 override exists; set it explicitly on TMC rather than
   relying on inference. Recommend doing so in Step 4.
4. **Series colours must not collide with panel 38's response semantics**
   (green=TP, red=FN, blue=TN, orange=FP). A green/red threshold series next to
   that panel invites misreading. **Mitigation:** distinct qualitative palette
   for panel 39; document the choice.
5. **`units="ms"` vs seconds storage.** `gap_duration` and `TMC_PROLACTIN_GAPS`
   are in **seconds** (0.005-0.040). Declaring `units="ms"` without scaling
   mislabels by 1000x — a data-integrity-grade error on a plot axis.
   **RESOLVED by D11:** `units` is a label only, never a conversion
   instruction; `gap_duration` declares `units="s"`. Any future paradigm whose
   stored unit differs from its display unit must add explicit scaling — it must
   NOT be inferred from this field. Enforce in review.

---

## Resolved (this PRD, 2026-07-17)

All six open questions answered by Eric. Folded into D10-D15 above.

---

## Deferred — flagged for later, deliberately NOT in this PRD

| item | note |
|---|---|
| Connect-points as an operator-facing option | D10 hardcodes on. Revisit if a paradigm wants scatter-only. |
| Per-marker value labels for the single-series case | D12 drops them. Legible at 1 series; re-add behind a series-count check if the operator misses them. |
| `pan` -> `Left` / `Right` display mapping | D13. Needs a per-VarSpec `value_labels` dict; nothing else needs it yet. Scope creep, revisit with M5/M6. |
| `display_scale` on VarSpec | D11 rules it out for now. Only needed if a stored unit must differ from its display unit. |
| ITD `outer_1` = `signal_type` vs `fc` as natural x-axis | Team call. D7 handles the type; the ordering question stands. |
