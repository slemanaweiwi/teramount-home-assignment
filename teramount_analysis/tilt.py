"""Tilt estimation and leveling.

The reference for "level" is the base: the large flat surface surrounding the
structures. It is the largest flat region of the scan, but raised structures
cover a big share of the image, so an ordinary plane fit over all flat pixels
would be pulled up by plateaus such as the Pivot planes. RANSAC finds the plane
supported by the most flat pixels; a robust least-squares fit on that plane's
pixels then gives the final, precise tilt.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Config
from .errors import FitError
from .fitting import fit_plane, fit_plane_robust, ransac_plane
from .surface import flat_mask, segmentation_surface


@dataclass(frozen=True)
class TiltResult:
    """Base plane ``z = slope_x*x + slope_y*y + offset`` (x, y in µm)."""

    slope_x: float  # dz/dx [µm/µm]
    slope_y: float  # dz/dy [µm/µm]
    offset_um: float  # plane height at pixel (0, 0) [µm]
    tilt_x_deg: float  # tilt angle along x (rotation about the y axis) [deg]
    tilt_y_deg: float  # tilt angle along y (rotation about the x axis) [deg]
    tilt_total_deg: float  # angle between the base normal and the z axis [deg]
    tilt_azimuth_deg: float  # direction of steepest ascent, from +x toward +y [deg]
    base_rms_um: float  # residual of the base-plane fit [µm]
    base_fraction: float  # share of the scan identified as base


def fit_base_plane(z: np.ndarray, config: Config, flat: np.ndarray | None = None) -> TiltResult:
    """Measure the tilt of the scan from its base plane.

    Parameters
    ----------
    z
        Height map in µm (may contain NaNs).
    config
        Analysis configuration.
    flat
        Flat-pixel mask of ``z`` if already computed (saves a smoothing pass).

    Raises
    ------
    FitError
        If fewer than 1 % of the pixels are flat.
    """
    p = config.pixel_size_um
    valid = np.isfinite(z)
    if flat is None:
        flat = flat_mask(segmentation_surface(z, config), config)
    flat = flat & valid
    if flat.mean() < 0.01:
        raise FitError("too few flat pixels to find the base plane")
    rows, cols = np.nonzero(flat)
    x, y, zz = cols * p, rows * p, z[rows, cols]

    rng = np.random.default_rng(config.random_seed)
    sample = rng.choice(x.size, size=min(x.size, config.ransac_sample_size), replace=False)
    xs, ys, zs = x[sample], y[sample], zz[sample]
    inliers = ransac_plane(xs, ys, zs, config.ransac_inlier_um, config.ransac_iterations, rng)
    coarse = fit_plane(xs[inliers], ys[inliers], zs[inliers])

    near = np.abs(zz - coarse.evaluate(x, y)) < 3 * config.ransac_inlier_um
    fit = fit_plane_robust(x[near], y[near], zz[near])
    sx, sy = fit.a, fit.b
    return TiltResult(
        slope_x=sx,
        slope_y=sy,
        offset_um=fit.c,
        tilt_x_deg=float(np.degrees(np.arctan(sx))),
        tilt_y_deg=float(np.degrees(np.arctan(sy))),
        tilt_total_deg=float(np.degrees(np.arctan(np.hypot(sx, sy)))),
        tilt_azimuth_deg=float(np.degrees(np.arctan2(sy, sx))),
        base_rms_um=fit.rms,
        base_fraction=fit.n_used / z.size,
    )


def remove_tilt(z: np.ndarray, tilt: TiltResult, config: Config) -> np.ndarray:
    """Subtract the base plane so the base sits at height 0.

    With ``config.correct_tilt`` False only a constant is removed (the base
    plane's height at the image centre), so the slope stays in the data.
    NaN pixels stay NaN.
    """
    p = config.pixel_size_um
    rows, cols = np.indices(z.shape, dtype=np.float64)
    if config.correct_tilt:
        plane = tilt.slope_x * cols * p + tilt.slope_y * rows * p + tilt.offset_um
    else:
        cy, cx = (z.shape[0] - 1) / 2, (z.shape[1] - 1) / 2
        plane = tilt.slope_x * cx * p + tilt.slope_y * cy * p + tilt.offset_um
    return z - plane
