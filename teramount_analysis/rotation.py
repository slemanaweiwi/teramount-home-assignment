"""In-plane rotation from the scan's long straight edges.

Lithographic structures are bounded by straight edges parallel to the chip
axes (channel walls, slot edges, band edges). Their angle relative to the
image axes is the rotation of the chip in the scan.

1. Canny finds edge pixels; a probabilistic Hough transform groups them into
   candidate straight segments within ``rotation_search_deg`` of horizontal
   or vertical.
2. Each segment is re-measured with sub-pixel precision: on every row (for a
   near-vertical edge) or column (near-horizontal edge) the edge position is
   the point where the height profile crosses half-way up the step. (Taking
   the peak of the gradient instead suffers from "pixel locking", which pulls
   small angles toward zero.)
3. A straight line is fitted to each edge; edges that are not straight are
   rejected.
4. The rotation is the median of the per-edge angles weighted by edge length,
   which ignores the occasional wall that is not exactly parallel to the axes.

Sign convention: positive = counter-clockwise as displayed (origin top-left),
the same as the angle passed to ``scipy.ndimage.rotate``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from skimage.feature import canny
from skimage.transform import probabilistic_hough_line

from .config import Config
from .errors import RotationError
from .surface import fill_invalid, smooth


@dataclass(frozen=True)
class EdgeLine:
    """One straight edge used for the rotation estimate (pixel coordinates)."""

    x0: float
    y0: float
    x1: float
    y1: float
    vertical: bool  # True for a near-vertical edge
    angle_deg: float  # chip rotation implied by this edge [deg]
    rms_px: float  # residual of the straight-line fit [px]
    n_points: int  # number of sub-pixel edge points used


@dataclass(frozen=True)
class RotationResult:
    """Estimated rotation and the evidence behind it."""

    angle_deg: float  # weighted median of the edge angles [deg]
    se_deg: float  # standard error of that median [deg]
    n_lines: int  # number of edges used
    lines: tuple[EdgeLine, ...]


def edge_crossing(heights: np.ndarray, gradients: np.ndarray) -> float | None:
    """Sub-pixel position where a step profile crosses its mid-level.

    Parameters
    ----------
    heights
        Height profile across the edge.
    gradients
        Gradient magnitude along the same profile (locates the step).

    Returns
    -------
    float or None
        Index (fractional) of the mid-level crossing, or None when the profile
        holds no usable step.
    """
    h = np.asarray(heights, dtype=np.float64)
    g = np.asarray(gradients, dtype=np.float64)
    n = h.size
    i = int(np.argmax(g))
    if not 1 < i < n - 2:
        return None
    left = h[max(i - 6, 0):max(i - 3, 1)]
    right = h[i + 4:i + 7]
    if left.size == 0 or right.size == 0:
        return None
    mid = 0.5 * (np.median(left) + np.median(right))
    d = h - mid
    for k in range(max(i - 3, 0), min(i + 3, n - 1)):
        if d[k] == 0:
            return float(k)
        if d[k] * d[k + 1] < 0:
            return k + (mid - h[k]) / (h[k + 1] - h[k])
    return None


def line_angle(points: np.ndarray, vertical: bool) -> tuple[float, float]:
    """Rotation angle implied by a straight edge, and its fit residual.

    A near-vertical edge is fitted as ``x = a + b*y`` (angle = atan b); a
    near-horizontal one as ``y = a + b*x`` (angle = -atan b), so that both give
    the counter-clockwise rotation of the chip.

    Returns
    -------
    (angle_deg, rms_px)
    """
    p = np.asarray(points, dtype=np.float64)
    if vertical:
        b, a = np.polyfit(p[:, 1], p[:, 0], 1)
        res = p[:, 0] - (a + b * p[:, 1])
        angle = math.degrees(math.atan(b))
    else:
        b, a = np.polyfit(p[:, 0], p[:, 1], 1)
        res = p[:, 1] - (a + b * p[:, 0])
        angle = -math.degrees(math.atan(b))
    return angle, float(np.sqrt(np.mean(res**2)))


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cum = np.cumsum(w)
    return float(v[np.searchsorted(cum, 0.5 * cum[-1])])


def _edge_points(seg: tuple, vertical: bool, zs: np.ndarray, g: np.ndarray, half: int,
                 margin: int) -> tuple[list[tuple[float, float]], int]:
    """Sub-pixel edge points along one Hough segment and the number of samples.

    Samples closer than ``margin`` px to the image border are skipped: there
    the smoothing used by Canny is affected by the border.
    """
    (x0, y0), (x1, y1) = seg
    rows, cols = zs.shape
    pts: list[tuple[float, float]] = []
    if vertical:
        lo, hi = sorted((y0, y1))
        samples = range(max(lo + 2, margin), min(hi - 1, rows - margin))
        for r in samples:
            c0 = int(round(x0 + (r - y0) * (x1 - x0) / (y1 - y0)))
            if c0 - half < 0 or c0 + half >= cols:
                continue
            p = edge_crossing(zs[r, c0 - half:c0 + half + 1], g[r, c0 - half:c0 + half + 1])
            if p is not None:
                pts.append((c0 - half + p, float(r)))
    else:
        lo, hi = sorted((x0, x1))
        samples = range(max(lo + 2, margin), min(hi - 1, cols - margin))
        for c in samples:
            r0 = int(round(y0 + (c - x0) * (y1 - y0) / (x1 - x0)))
            if r0 - half < 0 or r0 + half >= rows:
                continue
            p = edge_crossing(zs[r0 - half:r0 + half + 1, c], g[r0 - half:r0 + half + 1, c])
            if p is not None:
                pts.append((float(c), r0 - half + p))
    return pts, len(samples)


def _runs_along_border(x0: int, y0: int, x1: int, y1: int, vertical: bool, rows: int,
                       cols: int, margin: int) -> bool:
    """True for a segment lying in the border band, parallel to the border."""
    if vertical:
        return min(x0, x1) < margin or max(x0, x1) > cols - 1 - margin
    return min(y0, y1) < margin or max(y0, y1) > rows - 1 - margin


def estimate_rotation(z_leveled: np.ndarray, config: Config) -> RotationResult:
    """Measure the in-plane rotation of a (leveled) scan.

    Raises
    ------
    RotationError
        If no straight edge survives the checks (e.g. a featureless scan).
    """
    zf = fill_invalid(z_leveled)[0]
    sigma_px = config.px(config.rotation_canny_sigma_um)
    edges = canny(zf, sigma=sigma_px, low_threshold=config.rotation_canny_low,
                  high_threshold=config.rotation_canny_high, mode="nearest")
    span = config.rotation_search_deg
    steps = np.linspace(-span, span, int(round(8 * span)) + 1)
    theta = np.deg2rad(np.r_[steps, 90.0 + steps])
    theta = (theta + np.pi / 2) % np.pi - np.pi / 2
    segments = probabilistic_hough_line(
        edges, threshold=10,
        line_length=max(int(round(config.px(config.rotation_min_line_um))), 5),
        line_gap=max(int(round(config.px(config.rotation_line_gap_um))), 1),
        theta=theta, rng=config.random_seed,
    )

    zs = smooth(zf, 1.0)
    g = np.hypot(ndimage.sobel(zs, axis=0), ndimage.sobel(zs, axis=1))
    half = config.rotation_profile_half_px
    margin = math.ceil(3 * sigma_px) + half
    rows, cols = zf.shape
    lines: list[EdgeLine] = []
    for (x0, y0), (x1, y1) in segments:
        if max(abs(x1 - x0), abs(y1 - y0)) < 5:
            continue
        vertical = abs(y1 - y0) > abs(x1 - x0)
        if _runs_along_border(x0, y0, x1, y1, vertical, rows, cols, margin):
            continue  # border artefact, not a structure edge
        pts, n_samples = _edge_points(((x0, y0), (x1, y1)), vertical, zs, g, half, margin)
        if n_samples < 3 or len(pts) < max(3, config.rotation_min_valid_fraction * n_samples):
            continue
        angle, rms = line_angle(np.array(pts), vertical)
        if rms > config.rotation_max_line_rms_px:
            continue
        lines.append(EdgeLine(float(x0), float(y0), float(x1), float(y1), vertical, angle, rms,
                              len(pts)))
    if not lines:
        raise RotationError("no straight edges found to measure the rotation")

    angles = np.array([ln.angle_deg for ln in lines])
    weights = np.array([ln.n_points for ln in lines], dtype=np.float64)
    angle = _weighted_median(angles, weights)
    mad = float(np.median(np.abs(angles - angle)))
    se = 1.2533 * 1.4826 * mad / math.sqrt(len(lines))
    return RotationResult(angle, se, len(lines), tuple(lines))
