"""
Utilities package for audiology test battery.

Includes:
- result_loader: Load and access previous test results
- standard_frequencies: Standard audiometric frequency definitions
- varspec: Variable specification for paradigm configuration
"""

from .result_loader import ResultLoader, get_pta_threshold
from .standard_frequencies import *

__all__ = [
    'ResultLoader',
    'get_pta_threshold',
    'AUDIOMETRIC_FREQS',
    'EXTENDED_FREQS',
    'QUICK_TEST_FREQS',
    'IFMC_PROBE_FREQS',
    'IFMC_MASKER_RATIOS',
    'TMC_GAPS',
    'TMC_PROLACTIN_GAPS',
    'TMC_PROLACTIN_FREQS'
]
