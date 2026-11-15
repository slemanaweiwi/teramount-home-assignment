"""Fault checks in three independent layers.

* **Geometric** — the structure violates properties that hold for any good
  element, with no reference needed: an element is missing, a surface that
  should be smooth is noisy, a cross or the Xpander apex is off the channel
  axis, the two Pivot planes are not parallel, the dome is strongly
  astigmatic. Works on a single scan.
* **Nominal** — a measurement is outside the nominal spec (``Config``
  ``nominal_*`` +/- ``tol_*``, estimated from the clean provided files and
  overridable from the command line).
* **Statistical** — a measurement is an outlier relative to the other scans
  of the same run (robust z-score from median and MAD). Reported separately:
  unusual is not the same as defective.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from .config import Config
from .results import ScanResult

STAT_METRICS: tuple[str, ...] = (
    "pivot_height_diff_um", "xpander_rx_um", "xpander_ry_um", "xpander_nrms_pct",
    "plane1_rms_um", "plane2_rms_um", "cross1_axis_offset_um", "cross2_axis_offset_um",
    "xpander_apex_axis_offset_um",
)


def geometric_flags(result: ScanResult, config: Config) -> tuple[str, ...]:
    """Structural checks that need no reference values."""
    flags = [f"{el}_not_found" for el in ("plane2", "plane1") if el in result.missing]
    for n, cross in ((1, result.cross1), (2, result.cross2)):
        if cross is not None and not cross.found:
            flags.append(f"cross{n}_not_found")
    x = result.xpander
    xpander_missing = x is not None and not x.found
    if xpander_missing or (x is None and result.pivot is not None):
        flags.append("xpander_not_found")  # None after a Pivot = measurement aborted
    pv = result.pivot
    if pv is not None:
        if pv.plane1_rms_um > config.max_plane_rms_um:
            flags.append("plane1_noisy")
        if pv.plane2_rms_um > config.max_plane_rms_um:
            flags.append("plane2_noisy")
    if x is not None and x.found and x.rms_um > config.max_xpander_rms_um:
        flags.append("xpander_surface_noisy")
    for n, cross in ((1, result.cross1), (2, result.cross2)):
        off_axis = cross is not None and cross.axis_offset_um > config.max_cross_axis_offset_um
        if off_axis and cross.found:
            flags.append(f"cross{n}_off_axis")
    if x is not None and x.found:
        if x.axis_offset_um > config.max_apex_axis_offset_um:
            flags.append("apex_off_axis")
    if pv is not None and pv.parallelism_deg > config.max_plane_parallelism_deg:
        flags.append("planes_not_parallel")
    if x is not None and x.found:
        asymmetry = 100.0 * abs(x.rx_um - x.ry_um) / (0.5 * (x.rx_um + x.ry_um))
        if asymmetry > config.max_radius_asymmetry_pct:
            flags.append("xpander_astigmatic")
    return tuple(flags)


def nominal_flags(result: ScanResult, config: Config) -> tuple[str, ...]:
    """Comparison with the nominal spec values in the configuration."""
    flags: list[str] = []
    pv = result.pivot
    if pv is not None:
        if abs(pv.height_diff_um - config.nominal_pivot_step_um) > config.tol_pivot_step_um:
            flags.append("pivot_step_out_of_spec")
    x = result.xpander
    if x is not None and x.found:
        if abs(x.rx_um - config.nominal_radius_um) > config.tol_radius_um:
            flags.append("rx_out_of_spec")
        if abs(x.ry_um - config.nominal_radius_um) > config.tol_radius_um:
            flags.append("ry_out_of_spec")
    return tuple(flags)


def statistical_flags(metrics_list: Sequence[Mapping[str, float]], config: Config
                      ) -> list[tuple[str, ...]]:
    """Robust outliers of each metric in :data:`STAT_METRICS` across a run.

    The robust z-score is ``0.6745 * (x - median) / MAD``. A metric is skipped
    when fewer than ``min_files_for_statistics`` scans have a value for it, or
    when its MAD is zero.
    """
    flags: list[list[str]] = [[] for _ in metrics_list]
    for metric in STAT_METRICS:
        values = np.array([float(m.get(metric, np.nan)) for m in metrics_list])
        finite = np.isfinite(values)
        if finite.sum() < config.min_files_for_statistics:
            continue
        median = float(np.median(values[finite]))
        mad = float(np.median(np.abs(values[finite] - median)))
        if mad == 0:
            continue
        z = 0.6745 * (values - median) / mad
        for i in np.nonzero(finite & (np.abs(z) > config.outlier_z))[0]:
            flags[i].append(f"{metric}_outlier")
    return [tuple(f) for f in flags]
