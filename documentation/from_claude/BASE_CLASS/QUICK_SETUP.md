# Quick Setup Checklist ✅

## 1. Create Directories
```bash
mkdir -p audiology_toolbox/paradigms
mkdir -p audiology_toolbox/utils
mkdir -p audiology_toolbox/config
```

## 2. Create __init__.py Files
```bash
touch audiology_toolbox/paradigms/__init__.py
touch audiology_toolbox/utils/__init__.py
touch audiology_toolbox/config/__init__.py
```

## 3. Copy Files

### From your existing project:
- ✅ `trial_player.py` → `audiology_toolbox/`
- ✅ `event_gen.py` → `audiology_toolbox/`
- ✅ `varspec.py` → `audiology_toolbox/utils/`
- ✅ `DEFAULTS.py` → `audiology_toolbox/config/`

### From outputs (new files):
- ✅ `adaptive_paradigm.py` → `audiology_toolbox/paradigms/`
- ✅ `paradigm_pta.py` → `audiology_toolbox/paradigms/`
- ✅ `test_pta.py` → `audiology_toolbox/`

## 4. Run Test
```bash
cd audiology_toolbox
python test_pta.py
```

## 5. What Should Happen

✅ Prints configuration
✅ Press ENTER to start
✅ GUI window opens
✅ Trial 1: Hear loud tone (press 1)
✅ Trial 2: Silence (press 0)
✅ More trials adaptively adjust
✅ Saves CSV to `test_data/`

## If Problems...

**Import errors?** → Check you're in `audiology_toolbox/` directory
**No sound?** → Verify psychopy/PTB audio works with existing code first
**No GUI?** → Try `pythonw test_pta.py` on Mac

## File Tree Should Look Like:
```
audiology_toolbox/
├── paradigms/
│   ├── __init__.py
│   ├── adaptive_paradigm.py    ✅ NEW
│   └── paradigm_pta.py          ✅ NEW
├── utils/
│   ├── __init__.py
│   └── varspec.py              (existing)
├── config/
│   ├── __init__.py
│   └── DEFAULTS.py             (existing)
├── trial_player.py             (existing)
├── event_gen.py                (existing)
└── test_pta.py                  ✅ NEW
```
