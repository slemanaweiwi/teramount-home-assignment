"""Pivot: segmentation of its two flat planes, orientation, height difference.

The Pivot is found from its shape, not from a fixed position:

* **Plane 2** (the top plane) is the highest flat plateau that lies fully
  inside the scan. Partial channels cut by the image border are ignored, and
  if two complete channels are visible the one nearest the image centre wins.
* The **ramp** is the gently sloped surface descending from plane 2 to
  plane 1. Its average downhill direction tells which way the channel points,
  which is how upside-down or sideways scans are recognised.
* **Plane 1** is the first large flat plateau reached when walking from
  plane 2 down the ramp, at least ``plane1_min_drop_um`` lower.

Segmentation works on the smoothed canonical surface; the height measurement
(:func:`measure_pivot`) uses the original pixels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from .config import Config
from .errors import ElementNotFoundError
from .fitting import PlaneFit, fit_plane, fit_plane_robust
from .frame import Frame
from .surface import flat_mask

_EIGHT_CONNECTED = np.ones((3, 3), dtype=bool)


@dataclass(frozen=True, eq=False)
class PivotRegions:
    """Masks and anchors of the Pivot in the canonical frame (pixels)."""

    plane1: np.ndarray  # bool mask of the lower plane
    plane2: np.ndarray  # bool mask of the upper plane
    plane2_level_um: float  # median smoothed height of plane 2 (leveled) [µm]
    plane2_centroid_uv: tuple[float, float]  # (u, v) centroid of plane 2 [px]
    axis_u: float  # u of the channel axis (centroid of plane1 | plane2) [px]


def _label_flat(z_seg: np.ndarray, config: Config) -> tuple[np.ndarray, list]:
    labels, _ = ndimage.label(flat_mask(z_seg, config), structure=_EIGHT_CONNECTED)
    return labels, ndimage.find_objects(labels)


def find_plane2(z_seg: np.ndarray, config: Config) -> np.ndarray:
    """Mask of the Pivot's upper plane (plane 2).

    Raises
    ------
    ElementNotFoundError
        If no flat plateau of sufficient area lies fully inside the scan.
    """
    labels, objects = _label_flat(z_seg, config)
    rows, cols = z_seg.shape
    min_px = config.plane2_min_area_um2 / config.pixel_size_um**2
    candidates = []  # (median height, label, centroid row, centroid col)
    for k, sl in enumerate(objects, start=1):
        if sl is None:
            continue
        if sl[0].start == 0 or sl[1].start == 0 or sl[0].stop == rows or sl[1].stop == cols:
            continue  # touches the border: a partial structure
        m = labels[sl] == k
        if m.sum() < min_px:
            continue
        rr, cc = np.nonzero(m)
        candidates.append((float(np.median(z_seg[sl][m])), k,
                           rr.mean() + sl[0].start, cc.mean() + sl[1].start))
    if not candidates:
        raise ElementNotFoundError("plane 2 not found (no complete flat plateau)")
    top = max(c[0] for c in candidates)
    finalists = [c for c in candidates if c[0] >= top - config.plane2_tie_um]
    cy, cx = (rows - 1) / 2, (cols - 1) / 2
    best = min(finalists, key=lambda c: math.hypot(c[2] - cy, c[3] - cx))
    return labels == best[1]


def ramp_direction(z_seg: np.ndarray, plane2: np.ndarray, config: Config
                   ) -> tuple[float, float]:
    """Unit vector ``(du, dv)`` pointing down the ramp, from plane 2 toward plane 1.

    Averages the downhill direction of moderately sloped pixels near plane 2.
    The side walls point in opposite directions and cancel; the cliff on the
    far side is too steep to qualify.

    Raises
    ------
    ElementNotFoundError
        If fewer than 50 ramp pixels are found.
    """
    p = config.pixel_size_um
    pad = int(math.ceil(config.px(config.ramp_search_um))) + 2
    rr, cc = np.nonzero(plane2)
    r0, r1 = max(rr.min() - pad, 0), min(rr.max() + pad + 1, z_seg.shape[0])
    c0, c1 = max(cc.min() - pad, 0), min(cc.max() + pad + 1, z_seg.shape[1])
    z = z_seg[r0:r1, c0:c1]
    p2 = plane2[r0:r1, c0:c1]
    level2 = float(np.median(z[p2]))
    dist = ndimage.distance_transform_edt(~p2) * p
    gy, gx = np.gradient(z)
    slope = np.hypot(gx, gy) / p
    ring = ((dist > 0) & (dist <= config.ramp_search_um) & (slope >= config.ramp_slope_min)
            & (slope <= config.ramp_slope_max) & (z < level2 - 1.0))
    if ring.sum() < 50:
        raise ElementNotFoundError("no ramp found next to plane 2")
    norm = np.hypot(gx[ring], gy[ring])
    d = np.array([np.mean(-gx[ring] / norm), np.mean(-gy[ring] / norm)])
    d /= np.linalg.norm(d)
    return float(d[0]), float(d[1])


def quarter_turns_for(direction: tuple[float, float]) -> int:
    """Counter-clockwise quarter turns (``np.rot90`` k) that make the ramp point up."""
    du, dv = direction
    alpha = math.degrees(math.atan2(-dv, du))  # angle with y pointing up
    return int(round((90.0 - alpha) / 90.0)) % 4


def find_plane1(z_seg: np.ndarray, plane2: np.ndarray, config: Config) -> np.ndarray:
    """Mask of the Pivot's lower plane (plane 1), canonical orientation only.

    Walks from the plane-2 centroid toward -v (up the image, down the ramp)
    and returns the first flat plateau that is at least ``plane1_min_drop_um``
    lower than plane 2 and at least ``plane1_min_area_um2`` large. Smaller
    plateaus (noise specks, the cross floor) are walked past.

    Raises
    ------
    ElementNotFoundError
        If no such plateau is reached within ``walk_max_um``.
    """
    labels, objects = _label_flat(z_seg, config)
    plane2_labels = np.unique(labels[plane2])
    level2 = float(np.median(z_seg[plane2]))
    min_px = config.plane1_min_area_um2 / config.pixel_size_um**2
    cy, cx = ndimage.center_of_mass(plane2)
    col = int(round(cx))
    rejected: set[int] = set()
    for step in range(int(config.px(config.walk_max_um))):
        row = int(round(cy - step))
        if row < 0:
            break
        k = int(labels[row, col])
        if k == 0 or k in plane2_labels or k in rejected:
            continue
        sl = objects[k - 1]
        m = labels[sl] == k
        if m.sum() >= min_px and np.median(z_seg[sl][m]) < level2 - config.plane1_min_drop_um:
            return labels == k
        rejected.add(k)
    raise ElementNotFoundError("plane 1 not found below the ramp")


@dataclass(frozen=True)
class PivotResult:
    """Pivot plane heights (leveled, base = 0) and their difference."""

    height_diff_um: float  # plane 2 - plane 1, crosses excluded [µm]
    height_diff_with_crosses_um: float  # same with cross pixels kept (for comparison) [µm]
    plane1_level_um: float  # plane 1 height at the plane-2 centroid [µm]
    plane2_level_um: float  # plane 2 height at the plane-2 centroid [µm]
    plane1_rms_um: float  # plane-1 fit residual (flatness / noise) [µm]
    plane2_rms_um: float  # plane-2 fit residual [µm]
    parallelism_deg: float  # angle between the two plane normals [deg]


def measure_pivot(z_leveled: np.ndarray, frame: Frame, regions: PivotRegions,
                  cross1_mask: np.ndarray | None, cross2_mask: np.ndarray | None,
                  config: Config) -> PivotResult:
    """Fit both planes on the original pixels and measure their height difference.

    Each plane is fitted (robustly) to its pixels minus a thin edge margin and
    minus the cross: the cross is an etched mark, not part of the surface, and
    including it would pull the plane down. The difference is evaluated at the
    plane-2 centroid, so any residual tilt common to both planes cancels.

    Raises
    ------
    FitError
        If a plane has too few valid pixels.
    """
    p = config.pixel_size_um
    margin = max(int(round(config.px(config.plane_edge_margin_um))), 1)
    u_all, v_all = frame.canonical_coordinates()
    finite = np.isfinite(z_leveled)

    def points(mask_canonical: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        rr, cc = np.nonzero(frame.pull_back(mask_canonical) & finite)
        return u_all[rr, cc] * p, v_all[rr, cc] * p, z_leveled[rr, cc]

    def fits(plane: np.ndarray, cross: np.ndarray | None) -> tuple[PlaneFit, PlaneFit]:
        core = ndimage.binary_erosion(plane, iterations=margin)
        if not core.any():
            core = plane
        cross_zone = (ndimage.binary_dilation(cross, iterations=2) if cross is not None
                      else np.zeros_like(plane))
        robust = fit_plane_robust(*points(core & ~cross_zone))
        naive = fit_plane(*points(core | cross_zone))  # no clipping: the cross stays in
        return robust, naive

    fit1, naive1 = fits(regions.plane1, cross1_mask)
    fit2, naive2 = fits(regions.plane2, cross2_mask)
    uc, vc = (c * p for c in regions.plane2_centroid_uv)
    level1, level2 = float(fit1.evaluate(uc, vc)), float(fit2.evaluate(uc, vc))
    cos_angle = float(np.clip(fit1.normal() @ fit2.normal(), -1.0, 1.0))
    return PivotResult(
        height_diff_um=level2 - level1,
        height_diff_with_crosses_um=float(naive2.evaluate(uc, vc) - naive1.evaluate(uc, vc)),
        plane1_level_um=level1,
        plane2_level_um=level2,
        plane1_rms_um=fit1.rms,
        plane2_rms_um=fit2.rms,
        parallelism_deg=math.degrees(math.acos(cos_angle)),
    )


def segment_pivot(z_seg: np.ndarray, config: Config) -> PivotRegions:
    """Find plane 2, check the orientation, then find plane 1.

    Raises
    ------
    ElementNotFoundError
        If a plane is missing or the ramp does not point up (scan not canonical).
    """
    plane2 = find_plane2(z_seg, config)
    du, dv = ramp_direction(z_seg, plane2, config)
    if dv > -0.7:
        raise ElementNotFoundError(
            f"unexpected orientation: Pivot ramp points ({du:.2f}, {dv:.2f}), not up")
    plane1 = find_plane1(z_seg, plane2, config)
    p2r, p2c = np.nonzero(plane2)
    _, both_c = np.nonzero(plane1 | plane2)
    return PivotRegions(
        plane1=plane1,
        plane2=plane2,
        plane2_level_um=float(np.median(z_seg[plane2])),
        plane2_centroid_uv=(float(p2c.mean()), float(p2r.mean())),
        axis_u=float(both_c.mean()),
    )
