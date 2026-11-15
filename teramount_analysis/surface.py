"""Surface helpers: invalid-pixel filling, smoothing, slope and flatness.

Segmentation (finding *where* things are) runs on a smoothed copy of the
surface so that noise cannot break up flat regions; measurements always use
the original heights.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from .config import Config


def fill_invalid(z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Replace non-finite pixels with the value of the nearest valid pixel.

    Returns
    -------
    (filled, valid)
        A filled float copy and the boolean mask of originally valid pixels.

    Raises
    ------
    ValueError
        If no pixel is finite.
    """
    z = np.asarray(z, dtype=np.float64)
    valid = np.isfinite(z)
    if valid.all():
        return z.copy(), valid
    if not valid.any():
        raise ValueError("surface has no finite values")
    nearest = ndimage.distance_transform_edt(~valid, return_distances=False,
                                             return_indices=True)
    return z[tuple(nearest)], valid


def smooth(z: np.ndarray, sigma_px: float, median_px: int = 0) -> np.ndarray:
    """Optional median pre-filter (removes spikes), then Gaussian smoothing."""
    out = np.asarray(z, dtype=np.float64)
    if median_px and median_px > 1:
        out = ndimage.median_filter(out, size=median_px, mode="nearest")
    if sigma_px > 0:
        out = ndimage.gaussian_filter(out, sigma_px, mode="nearest")
    return out


def slope(z: np.ndarray, pixel_size_um: float) -> np.ndarray:
    """Magnitude of the surface gradient in µm per µm (heights in µm)."""
    gy, gx = np.gradient(z)
    return np.hypot(gx, gy) / pixel_size_um


def segmentation_surface(z: np.ndarray, config: Config) -> np.ndarray:
    """NaN-free, median- and Gaussian-smoothed copy used to find regions."""
    return smooth(fill_invalid(z)[0], config.px(config.seg_sigma_um), config.seg_median_px)


def flat_mask(z_seg: np.ndarray, config: Config) -> np.ndarray:
    """Pixels whose slope is below ``config.flat_slope_max`` (plateaus)."""
    return slope(z_seg, config.pixel_size_um) < config.flat_slope_max
