# Phase 3 Refactoring Plan — DataManager Extraction

*2026-03-29 | PROLACTIN codebase refactoring*

**Depends on:** Phase 1 (boilerplate consolidation) and Phase 2 (ParticipantGUI extraction) complete and verified.

---

## Goal

Extract all data logging, storage, and disk I/O from `AdaptiveParadigm` into a standalone `DataManager` class, injected via constructor. This:

- Gives data handling a single responsible class (currently spread across 7 methods + inline reads in `update_trial_params`)
- Makes the data layer testable independently (log a trial, check the output, no paradigm needed)
- Prepares for ExperimentController (Phase 5), which can hold a session-level DataManager coordinating across paradigms
- Keeps `AdaptiveParadigm` focused on trial logic

---

## Current State (post-Phase 2)

Data-related code in `AdaptiveParadigm`:

| Code | Location | What it does |
|---|---|---|
| `self._data_rows = []` | `__init__` | List accumulator for trial dicts |
| `self.data = pd.DataFrame()` | `__init__` | DataFrame rebuilt each trial |
| `log_data()` | ~line 1062 | Calls `get_log_data()`, appends row, rebuilds DataFrame |
| `write_data_to_disk()` | ~line 1090 | Generates filename, writes CSV to `test_data/` |
| `_temp_data_path()` | ~line 1131 | Returns crash-recovery temp file path |
| `_write_temp_data()` | ~line 1137 | Writes current data to temp CSV |
| `_delete_temp_data()` | ~line 1149 | Deletes temp CSV on clean completion |
| threshold write-back | ~line 878-884 | After psych fit, updates last row of current config in both `_data_rows` and `data` |

**Who reads the data:**

| Consumer | Access pattern | Where |
|---|---|---|
| `update_trial_params()` | `self.data[self.data['config_num'] == ...]` — filters DataFrame to get current config's trials for threshold estimation | adaptive_paradigm.py ~line 845 |
| `operator_gui.py` | `self.paradigm.data` — reads full DataFrame for all four plots (waveform, adaptive track, threshold history, psychometric) | operator_gui.py lines 256, 384, 454, 541 |
| `main()` cleanup | `print(self.data)` — prints final DataFrame | adaptive_paradigm.py ~line 1248 |
| `ResultLoader` | Reads CSVs from disk (not in-memory data) | result_loader.py — separate concern, no change needed |

---

## Design: `DataManager` Class

```python
class DataManager:
    """
    Manages trial-level data logging, CSV output, and crash recovery.

    Owns the data store (_rows list + DataFrame). Paradigm calls
    log_trial() after each trial, DataManager handles everything else.
    """

    def __init__(self, participant_id: str, paradigm_code: str,
                 output_dir: str = None):
        """
        Args:
            participant_id: e.g. "P001"
            paradigm_code: e.g. "PTA", "AM"
            output_dir: directory for CSVs. Default: cwd()/test_data/
        """
        self.participant_id = participant_id
        self.paradigm_code = paradigm_code
        self._output_dir = Path(output_dir) if output_dir else Path.cwd() / "test_data"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._rows = []
        self.data = pd.DataFrame()

    def log_trial(self, row_data: dict):
        """Append one trial's data. Rebuilds DataFrame."""
        self._rows.append(row_data)
        self.data = pd.DataFrame(self._rows)

    def update_last_row(self, config_num: int, updates: dict):
        """
        Update the last row of a given config with new values.
        Used for writing threshold estimates after psychometric fit.

        Args:
            config_num: which config to find the last row of
            updates: dict of column->value to write, e.g.
                     {'threshold_dB': -23.4, 'slope_k': 0.6}
        """
        config_mask = self.data['config_num'] == config_num
        if not config_mask.any():
            return
        last_idx = self.data[config_mask].index[-1]
        for key, val in updates.items():
            self.data.loc[last_idx, key] = val
            self._rows[last_idx][key] = val

    def get_config_data(self, config_num: int,
                        exclude_catch: bool = True) -> pd.DataFrame:
        """
        Get trial data for a specific config.

        Args:
            config_num: config number to filter
            exclude_catch: if True, exclude catch trials

        Returns:
            Filtered DataFrame
        """
        mask = self.data['config_num'] == config_num
        if exclude_catch:
            mask = mask & (self.data['is_catch_trial'] == False)
        return self.data[mask]

    def save(self) -> Path:
        """Write final CSV. Returns path."""
        self._validate()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = self._output_dir / (
            f"{self.participant_id}_{self.paradigm_code}_{timestamp}.csv"
        )
        self.data.to_csv(filename, index=False)
        print(f"\nData saved to: {filename}")
        return filename

    def write_temp(self):
        """Write crash-recovery temp CSV. Overwrites previous."""
        if self.data.empty:
            return
        path = self._temp_path()
        self.data.to_csv(path, index=False)

    def delete_temp(self):
        """Delete temp CSV on clean completion."""
        path = self._temp_path()
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    def _temp_path(self) -> Path:
        return self._output_dir / (
            f"{self.participant_id}_{self.paradigm_code}_temp.csv"
        )

    def _validate(self):
        """Check that paradigm_code is set."""
        if not self.paradigm_code:
            raise ValueError(
                "paradigm_code not set — cannot generate filename"
            )

    @property
    def is_empty(self) -> bool:
        return len(self._rows) == 0
```

### Design notes

**Why `update_last_row()` instead of direct DataFrame access:** The threshold write-back in `update_trial_params()` currently does `self.data.loc[last_idx, 'threshold_dB'] = ...` and `self._data_rows[last_idx]['threshold_dB'] = ...` — it updates both the DataFrame and the backing list. This dual-write is error-prone. `update_last_row()` encapsulates it in one call and keeps the two stores in sync.

**Why `get_config_data()` as a convenience method:** The threshold estimation block filters `self.data` by config_num and catch trial status. This is the only place the paradigm queries the data. Having a named method makes that intent clear and avoids the paradigm needing to know how data is structured internally.

**`data` property stays public:** The operator GUI reads `paradigm.data` (the full DataFrame) in four places. Rather than adding four getter methods, keep `data` as a public attribute on DataManager. The paradigm exposes it as `self.data_manager.data` (or re-export as `self.data` via a property — see below).

---

## Changes to `AdaptiveParadigm`

### Constructor — accept optional `data_manager` parameter:

```python
def __init__(self, params, verbose=False, gui_config=None,
             participant_id=None, show_operator_display=True,
             randomize_config_order=True, gui=None, data_manager=None):
    ...
    # Data management: use provided DataManager or create default
    self._injected_dm = data_manager
    self.data_manager = None  # Created in main() after paradigm_code is known
    ...
```

### Backward-compatible `data` property:

The operator GUI and `main()` currently access `self.data`. Add a property that delegates:

```python
@property
def data(self):
    """Backward-compatible access to trial data DataFrame."""
    if self.data_manager is not None:
        return self.data_manager.data
    return pd.DataFrame()
```

This means `operator_gui.py` code (`self.paradigm.data`) works without any changes.

### `main()` — create DataManager, delegate:

```python
def main(self):
    # Create DataManager (or use injected one)
    if self._injected_dm is not None:
        self.data_manager = self._injected_dm
    else:
        self.data_manager = DataManager(
            self.participant_id, self.paradigm_code
        )

    # ... operator display, GUI setup, trial loop ...

    # Cleanup
    if self._aborted_by_operator:
        print("PARADIGM ABORTED BY OPERATOR — data not saved.")
    else:
        print("PARADIGM COMPLETE")
        print(self.data)
        self.data_manager.save()
        self.data_manager.delete_temp()
```

### `log_data()` — delegate:

```python
def log_data(self):
    """Log current trial data."""
    paradigm_data = self.get_log_data()
    row_data = {
        "unix_time": time.time(),
        "config_num": self.config_num,
        "trial_num": self.trial_num,
        "correct_answer": self.correct_answer,
        "trial_repeats": self.trial_repeats,
        "is_catch_trial": self.is_catch_trial,
        **paradigm_data,
        "threshold_dB": np.nan,
        "slope_k": np.nan,
    }
    self.data_manager.log_trial(row_data)
```

This method stays on `AdaptiveParadigm` because it assembles the trial dict (calling `get_log_data()` which is paradigm-specific). DataManager just receives the assembled dict.

### Threshold estimation in `update_trial_params()` — delegate data access:

```python
# Before:
config_data = self.data[self.data['config_num'] == self.config_num]
non_catch_data = config_data[config_data['is_catch_trial'] == False]
threshold_data = non_catch_data.tail(self.trials_after_reversal)

# After:
non_catch_data = self.data_manager.get_config_data(
    self.config_num, exclude_catch=True
)
threshold_data = non_catch_data.tail(self.trials_after_reversal)
```

```python
# Before (threshold write-back):
config_mask = self.data['config_num'] == self.config_num
last_idx = self.data[config_mask].index[-1]
self.data.loc[last_idx, 'threshold_dB'] = self.threshold_dB
self.data.loc[last_idx, 'slope_k'] = self.slope_k
self._data_rows[last_idx]['threshold_dB'] = self.threshold_dB
self._data_rows[last_idx]['slope_k'] = self.slope_k

# After:
self.data_manager.update_last_row(self.config_num, {
    'threshold_dB': self.threshold_dB,
    'slope_k': self.slope_k
})
```

```python
# Before (temp write after config):
self._write_temp_data()

# After:
self.data_manager.write_temp()
```

### Delete old methods:

Remove from `AdaptiveParadigm`:
- `write_data_to_disk()` → `data_manager.save()`
- `_temp_data_path()` → `data_manager._temp_path()`
- `_write_temp_data()` → `data_manager.write_temp()`
- `_delete_temp_data()` → `data_manager.delete_temp()`

Remove state:
- `self._data_rows` → lives in DataManager
- `self.data` → replaced by property delegating to DataManager

`log_data()` stays on AdaptiveParadigm (it assembles the row dict), but the storage call delegates to `data_manager.log_trial()`.

---

## Changes to `operator_gui.py`

**None.** The backward-compatible `self.data` property means all four read sites (`self.paradigm.data`) work unchanged.

---

## Changes to Other Files

**`result_loader.py`** — no changes. It reads CSVs from disk, completely independent of in-memory DataManager.

**`paradigm_setup_dialog.py`** — no changes. Doesn't touch data.

**All `paradigm_*.py`** — no changes. Subclasses only override `get_log_data()`, which stays on AdaptiveParadigm.

**All `test_*.py`** — no changes. Default path (`data_manager=None` → created in `main()`) preserves behavior.

---

## File Summary

| File | Change | Risk |
|---|---|---|
| `utils/data_manager.py` | **NEW** — DataManager class | Low (new file) |
| `adaptive_paradigm.py` | Accept `data_manager=` param, delegate data calls, add `data` property, delete 4 methods + 2 state vars | Medium |
| `operator_gui.py` | No changes (backward-compatible property) | None |
| All `paradigm_*.py` | No changes | None |
| All `test_*.py` | No changes | None |

---

## Implementation Order

| # | Task | Effort |
|---|------|--------|
| 1 | Create `utils/data_manager.py` | 1 hr |
| 2 | Wire into `AdaptiveParadigm`: add `data_manager=` param, `data` property, delegate `log_data()` storage call, delegate threshold write-back and temp write/delete | 1.5 hr |
| 3 | Delete old methods and state from `AdaptiveParadigm` | 30 min |
| 4 | **Verify:** Run PTA + AM. Compare CSV output column-for-column with pre-Phase 3 run. Check threshold values populated. Check temp file created during run and deleted on clean exit. | 30 min |
| 5 | **Verify:** Run IFMC or TMC to confirm ResultLoader still picks up PTA data correctly (not affected, but sanity check). | 15 min |
| 6 | **Verify:** Confirm operator GUI plots still work (they read `paradigm.data` which now goes through the property). | 15 min |

**Total estimate:** ~4 hours, single session.

---

## Verification Strategy

This is a low-risk extraction — the data code is already well-isolated.

- **CSV output:** Run PTA, compare CSV filename format, column order, and values. Should be byte-identical except timestamp.
- **Threshold estimation:** Run PTA for a few configs. Check that `threshold_dB` and `slope_k` appear in the correct row of the CSV.
- **Crash recovery:** Start a run, kill it mid-config. Verify temp CSV exists in `test_data/`. Restart clean run, verify temp file deleted on completion.
- **Operator GUI:** Run any paradigm with operator display enabled. All four plots should render as before.

---

## Open Questions

1. **Should `log_data()` move to DataManager entirely?** Currently it stays on AdaptiveParadigm because it calls `get_log_data()` (paradigm-specific) and assembles the full row dict (with `config_num`, `trial_num`, etc.). An alternative is to have the paradigm pass a pre-assembled dict and DataManager just stores it. That's already what happens — `log_data()` is essentially a dict builder that calls `data_manager.log_trial(row_data)`. Keeping it on AdaptiveParadigm is fine. The dict assembly is trial logic, not data management.

2. **DataFrame rebuild on every trial:** `log_trial()` calls `pd.DataFrame(self._rows)` after every row append. This is the O(n) replacement for the old O(n²) `pd.concat`, but it still rebuilds the whole DataFrame each trial. For typical runs (~100-200 trials), this is sub-millisecond and irrelevant. If runs ever get much longer, we could switch to deferred rebuild (only build DataFrame when accessed). Not worth doing now.

3. **ExperimentController integration (Phase 5):** The controller could hold a session-level DataManager that coordinates across paradigms — e.g., session metadata, cross-paradigm data directory, session-level temp recovery. For now, each paradigm creates its own DataManager in `main()`. The controller will override this by injecting a pre-configured DataManager.

---

## Interaction with Later Phases

**Phase 5 (ExperimentController):** Controller creates `DataManager(participant_id, paradigm_code, output_dir=session_dir)` and injects it into each paradigm. Session-level output directory, session log, and cross-paradigm data coordination live on the controller, not the DataManager.

**Phase 6 (Testing):** Automated tests can inject a DataManager with a temporary output directory. After the test run, assert on `data_manager.data` contents without touching the filesystem. Or use the default DataManager and check the CSV file.
