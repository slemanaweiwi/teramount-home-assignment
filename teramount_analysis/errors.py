"""Exception hierarchy for expected analysis failures.

Every failure that is a property of the *data* (an element that is missing, a
scan that cannot be read, a fit that does not converge) raises a subclass of
:class:`AnalysisError`. The pipeline catches these per scan and reports them in
the results table, so one bad scan never stops a whole run.
"""

from __future__ import annotations


class AnalysisError(Exception):
    """Base class for expected, per-scan analysis failures."""


class ScanLoadError(AnalysisError):
    """The scan file is missing, unreadable, or not a usable 2-D height map."""


class ElementNotFoundError(AnalysisError):
    """A structure (plane, cross, Xpander) could not be located in the scan."""


class RotationError(AnalysisError):
    """The in-plane rotation could not be measured (no straight edges found)."""


class FitError(AnalysisError):
    """A model fit failed (too few points, singular system, non-convex dome)."""
