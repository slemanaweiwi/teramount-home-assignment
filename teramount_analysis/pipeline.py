"""End-to-end analysis of one scan and of a whole dataset.

Steps for one scan:

0. **Streaks** — remove scan-line streaks when clearly present.
1. **Tilt** — fit the base plane and subtract it (heights become relative to
   the base, which also removes any absolute height offset).
2. **Rotation** — measure the in-plane rotation from straight edges.
3. **Orientation** — find plane 2 in the rotation-corrected image; the
   direction of the Pivot ramp decides the quarter turns that bring the
   channel into the canonical orientation (ramp up, Xpander above).
4. **Pivot** — segment plane 1 and plane 2, find both crosses, measure the
   plane heights and their difference.
5. **Xpander** — locate the dome, choose the aperture, fit the surface.
6. **Faults** — geometric and nominal checks per scan; statistical checks
   across the dataset in :func:`analyse_dataset`.

Expected problems in the data (a missing element, an unreadable file) never
stop a run: they are recorded in the result's ``status`` and ``error``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np

from .config import Config
from .crosses import find_cross
from .errors import AnalysisError, ElementNotFoundError, RotationError
from .faults import geometric_flags, nominal_flags, statistical_flags
from .frame import Frame
from .io import check_height_map, load_scan
from .pivot import find_plane2, measure_pivot, quarter_turns_for, ramp_direction, segment_pivot
from .results import FaultReport, ScanDebug, ScanResult
from .rotation import estimate_rotation
from .streaks import remove_streaks
from .surface import flat_mask, segmentation_surface
from .tilt import fit_base_plane, remove_tilt
from .xpander import measure_xpander

log = logging.getLogger(__name__)


def analyse_scan(z: np.ndarray, config: Config, name: str = "") -> ScanResult:
    """Analyse one height map (µm). Never raises for problems in the data.

    An input that is not a usable height map (wrong shape, too small, not
    numeric, no finite value) gives a ``failed`` result with the reason.
    """
    result = ScanResult(file=name)
    try:
        _run(z, config, result)
    except AnalysisError as exc:
        result.status = "partial" if result.pivot is not None else "failed"
        result.error = str(exc)
        log.warning("%s: %s", name or "scan", exc)
    except Exception as exc:  # any other failure must not stop a batch run
        result.status = "partial" if result.pivot is not None else "failed"
        result.error = f"unexpected error: {exc!r}"
        log.error("%s: unexpected error: %r", name or "scan", exc)
        log.debug("traceback", exc_info=True)
    result.faults = FaultReport(geometric_flags(result, config), nominal_flags(result, config))
    return result


def _run(z: np.ndarray, config: Config, result: ScanResult) -> None:
    """Fill ``result`` step by step; raises AnalysisError on a blocking problem."""
    z = check_height_map(z, result.file or "scan")
    flat = flat_mask(segmentation_surface(z, config), config)  # shared: one smoothing pass
    z, result.streaks = remove_streaks(z, config, flat)
    if result.streaks.corrected:
        result.warnings = (*result.warnings, "scan_line_streaks_removed")
    result.tilt = fit_base_plane(z, config, flat)
    z_leveled = remove_tilt(z, result.tilt, config)
    result.debug = ScanDebug(z_leveled)

    phi = 0.0
    if config.correct_rotation:
        try:
            result.rotation = estimate_rotation(z_leveled, config)
            phi = result.rotation.angle_deg
        except RotationError as exc:  # a limit of the analysis, not a chip defect
            log.warning("%s: rotation not measured (%s); assuming 0 deg", result.file, exc)
            result.warnings = (*result.warnings, "rotation_not_measured")
    result.frame = Frame(z.shape, phi, 0)

    z_seg = segmentation_surface(result.frame.canonical_image(z_leveled), config)
    try:
        plane2 = find_plane2(z_seg, config)
    except ElementNotFoundError:
        result.missing = ("plane2",)
        raise
    try:
        k = quarter_turns_for(ramp_direction(z_seg, plane2, config))
    except ElementNotFoundError:
        result.missing = ("ramp",)
        raise
    result.frame = Frame(z.shape, phi, k)
    z_seg = np.ascontiguousarray(np.rot90(z_seg, k))
    try:
        regions = segment_pivot(z_seg, config)
    except ElementNotFoundError:
        result.missing = ("plane1",)
        raise
    frame = result.frame
    z_canonical = frame.canonical_image(z_leveled)
    result.debug = ScanDebug(z_leveled, z_canonical, regions)

    result.cross1 = find_cross(z_leveled, frame, z_canonical, regions.plane1, regions.axis_u,
                               config)
    result.cross2 = find_cross(z_leveled, frame, z_canonical, regions.plane2, regions.axis_u,
                               config)
    result.pivot = measure_pivot(z_leveled, frame, regions, result.cross1.mask,
                                 result.cross2.mask, config)
    result.xpander = measure_xpander(z_leveled, frame, z_canonical, regions, config)

    problems = [f"cross {n} not found"
                for n, c in ((1, result.cross1), (2, result.cross2)) if not c.found]
    if not result.xpander.found:
        problems.append(f"xpander not found: {result.xpander.reason}")
    elif result.xpander.outlier_pct > config.xpander_max_outlier_pct:
        result.warnings = (*result.warnings, "xpander_outliers_removed")
    glitches = result.pivot.glitch_lines + (result.xpander.glitch_lines
                                            if result.xpander.found else 0.0)
    if glitches > 0:  # outliers shaped like a scan line recorded at the wrong height
        result.warnings = (*result.warnings, "scan_line_glitch")
    result.status = "partial" if problems else "ok"
    result.error = "; ".join(problems)


def analyse_file(path: Path | str, config: Config) -> ScanResult:
    """Load and analyse one ``.npy`` scan; an unreadable file gives a failed result."""
    path = Path(path)
    try:
        z = load_scan(path, config.z_scale)
    except AnalysisError as exc:
        log.warning("%s: %s", path.name, exc)
        return ScanResult(file=path.name, status="failed", error=str(exc), faults=FaultReport())
    return analyse_scan(z, config, path.name)


def analyse_dataset(paths: Sequence[Path], config: Config,
                    on_scan: Callable[[ScanResult], None] | None = None) -> list[ScanResult]:
    """Analyse every scan, then add the statistical flags across the run.

    Parameters
    ----------
    paths
        Scans to analyse, in report order.
    on_scan
        Called with each result while its debug arrays are still attached
        (used to draw figures); the arrays are released right after.
    """
    results: list[ScanResult] = []
    for i, path in enumerate(paths, start=1):
        log.info("[%d/%d] %s", i, len(paths), Path(path).name)
        result = analyse_file(path, config)
        if on_scan is not None:
            try:
                on_scan(result)
            except Exception:  # a failing figure must not lose the measurement
                log.exception("%s: per-scan callback failed", result.file)
        result.debug = None
        results.append(result)
    stats = statistical_flags([r.metrics(config) for r in results], config)
    for result, flags in zip(results, stats, strict=True):
        base = result.faults or FaultReport()
        result.faults = FaultReport(base.geometric, base.nominal, flags)
    return results
