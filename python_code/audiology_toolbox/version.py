"""
PROLACTIN version.

Bumped manually on releases. Used for CSV provenance headers so that
downstream tooling can validate dataset compatibility.

Versioning convention: SemVer (MAJOR.MINOR.PATCH).
- MAJOR: breaking changes to CSV format, paradigm logic, or calibration math
- MINOR: new paradigms, new optional fields, backward-compatible additions
- PATCH: bug fixes, internal refactors
"""

__version__ = "0.5.0"
