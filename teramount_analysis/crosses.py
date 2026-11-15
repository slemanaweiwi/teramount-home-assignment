"""Cross (alignment mark) detection and sub-pixel centres.

Each Pivot plane carries one cross etched into it. A plane is fitted to the
plane's pixels, and the cross is the plus-shaped region lying more than
``cross_min_depth_um`` below that plane. Candidates must have a plausible
area, a cross-like solidity (a plus sign does not fill its convex hull, unlike
a square pad or a round pit) and a roughly square bounding box; the one
nearest the channel axis wins.

The centre is the depth-weighted centroid of the original (non-interpolated)
pixels, so it is accurate to a fraction of a pixel even though the cross
outline is pixelated.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from skimage.measure import regionprops
from skimage.morphology import convex_hull_image

from .config import Config
from .errors import FitError
from .fitting import PlaneFit, fit_plane_robust
from .frame import Frame

_EIGHT_CONNECTED = np.ones((3, 3), dtype=bool)


@dataclass(frozen=True, eq=False)
class CrossResult:
    """A detected cross. When ``found`` is False every number is NaN."""

    found: bool
    x_px: float  # centre, original frame (column)
    y_px: float  # centre, original frame (row)
    u_px: float  # centre, canonical frame
    v_px: float
    depth_um: float  # median depth below the plane [µm]
    area_um2: float  # area of the detected region [µm²]
    solidity: float  # area / convex-hull area
    axis_offset_um: float  # |u - channel axis| [µm]
    mask: np.ndarray | None  # canonical-frame mask (full image size)


NOT_FOUND = CrossResult(False, *([float("nan")] * 8), None)


def _candidates(residual: np.ndarray, hull: np.ndarray, config: Config) -> list:
    """Cross-shaped components of the thresholded residual (crop coordinates).

    The residual is de-noised with physical-size filters: in pixels, a fixed
    window would round the plus sign into a blob on coarser scans.
    """
    smoothed = np.where(hull, residual, 0.0)
    median = config.odd_px(config.cross_median_um)
    if median > 1:
        smoothed = ndimage.median_filter(smoothed, median)
    smoothed = ndimage.gaussian_filter(smoothed, config.px(config.cross_sigma_um))
    if config.cross_polarity == "recessed":
        cand = hull & (smoothed < -config.cross_min_depth_um)
    else:
        cand = hull & (smoothed > config.cross_min_depth_um)
    labels, _ = ndimage.label(cand, structure=_EIGHT_CONNECTED)
    area_px = config.pixel_size_um**2
    keep = []
    for rp in regionprops(labels):
        r0, c0, r1, c1 = rp.bbox
        aspect = (c1 - c0) / (r1 - r0)
        if (config.cross_area_min_um2 <= rp.area * area_px <= config.cross_area_max_um2
                and config.cross_solidity_min <= rp.solidity <= config.cross_solidity_max
                and config.cross_aspect_min <= aspect <= config.cross_aspect_max):
            keep.append(rp)
    return keep


def find_cross(z_leveled: np.ndarray, frame: Frame, z_canonical: np.ndarray,
               plane_mask: np.ndarray, axis_u: float, config: Config) -> CrossResult:
    """Locate the cross on one Pivot plane.

    Parameters
    ----------
    z_leveled
        Leveled heights in the original frame (measurement source).
    frame
        Original <-> canonical mapping.
    z_canonical
        Leveled heights resampled into the canonical frame (detection only).
    plane_mask
        Canonical mask of the plane carrying the cross.
    axis_u
        Canonical column of the channel axis (crosses lie on it).

    Returns
    -------
    CrossResult
        ``found=False`` when no cross-shaped region is present (never raises).
    """
    hull_full = convex_hull_image(plane_mask)
    rows, cols = np.nonzero(hull_full)
    r0, r1 = max(rows.min() - 3, 0), min(rows.max() + 4, plane_mask.shape[0])
    c0, c1 = max(cols.min() - 3, 0), min(cols.max() + 4, plane_mask.shape[1])
    crop = (slice(r0, r1), slice(c0, c1))
    z = z_canonical[crop]
    fit_px = ndimage.binary_erosion(plane_mask[crop],
                                    iterations=config.whole_px(config.plane_edge_margin_um))
    vv, uu = np.nonzero(fit_px)
    try:
        plane = fit_plane_robust(uu + c0, vv + r0, z[vv, uu])
    except FitError:
        return NOT_FOUND
    vg, ug = np.indices(z.shape)
    residual = z - plane.evaluate(ug + c0, vg + r0)
    found = _candidates(residual, hull_full[crop], config)
    if not found:
        return NOT_FOUND
    best = min(found, key=lambda rp: abs(rp.centroid[1] + c0 - axis_u))

    mask = np.zeros(plane_mask.shape, dtype=bool)
    mask[crop][best.coords[:, 0], best.coords[:, 1]] = True
    return _measure(z_leveled, frame, plane, mask, best, axis_u, config)


def _measure(z_leveled: np.ndarray, frame: Frame, plane: PlaneFit, mask: np.ndarray, rp,
             axis_u: float, config: Config) -> CrossResult:
    """Depth-weighted centre and depth of a cross from the original pixels."""
    sign = -1.0 if config.cross_polarity == "recessed" else 1.0
    u_all, v_all = frame.canonical_coordinates()

    def raw_residual(canonical_mask: np.ndarray) -> tuple[np.ndarray, ...]:
        pix = frame.pull_back(canonical_mask) & np.isfinite(z_leveled)
        rr, cc = np.nonzero(pix)
        u, v = u_all[rr, cc], v_all[rr, cc]
        return rr, cc, u, v, z_leveled[rr, cc] - plane.evaluate(u, v)

    rr, cc, u, v, res = raw_residual(ndimage.binary_dilation(mask))
    w = np.clip(sign * res, 0.0, None)
    if w.sum() <= 0:
        return NOT_FOUND
    core = ndimage.binary_erosion(mask)
    *_, res_core = raw_residual(core if core.any() else mask)
    u_c = float(np.average(u, weights=w))
    return CrossResult(
        found=True,
        x_px=float(np.average(cc, weights=w)),
        y_px=float(np.average(rr, weights=w)),
        u_px=u_c,
        v_px=float(np.average(v, weights=w)),
        depth_um=float(np.median(np.abs(res_core))),
        area_um2=float(rp.area * config.pixel_size_um**2),
        solidity=float(rp.solidity),
        axis_offset_um=abs(u_c - axis_u) * config.pixel_size_um,
        mask=mask,
    )
