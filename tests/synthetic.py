"""Synthetic topography scans with known ground truth (test infrastructure).

The geometry imitates the real Teramount channel (heights in µm, leveled base
at 0): a supporting band, a row of Xpander domes with a 126 µm pitch that meet
at gentle valleys, the Pivot (plane 1, ramp, plane 2, two recessed crosses,
raised pads) on a tooth, and an isolated block with a cross that the analysis
must ignore. Scans can be rotated, quarter-turned, cropped, tilted, made noisy
and given NaN dropouts; :class:`SyntheticTruth` reports where every feature
ends up in the final image.

This module deliberately does not import ``teramount_analysis``: the truth must
be computed independently of the code under test.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

PITCH_UM = 126.0  # distance between neighbouring channels
APEX_Y_UM = 80.0  # dome apex row
APEX_HEIGHT_UM = 12.4
TOOTH_UM = 11.0
PLANE1_UM = 12.9
PLANE2_UM = 31.0
PLANE2_Y_UM = (182.6, 194.2)
CROSS1_Y_UM = 158.5
CROSS2_Y_UM = 188.4
CROSS1_DEPTH_UM = 1.8
CROSS2_DEPTH_UM = 1.5


@dataclass(frozen=True)
class SyntheticTruth:
    """Ground truth of a synthetic scan, in the final (output) pixel frame."""

    rotation_deg: float
    slope_x: float
    slope_y: float
    pivot_step_um: float
    cross1_xy_px: tuple[float, float]
    cross2_xy_px: tuple[float, float]
    apex_xy_px: tuple[float, float]
    rx_um: float
    ry_um: float
    plane2_center_xy_px: tuple[float, float]


def _plus(x: np.ndarray, y: np.ndarray, cx: float, cy: float) -> np.ndarray:
    """Plus-shaped mask: two 6.5 x 2.5 µm arms crossing at (cx, cy)."""
    dx, dy = np.abs(x - cx), np.abs(y - cy)
    return ((dx <= 3.25) & (dy <= 1.25)) | ((dx <= 1.25) & (dy <= 3.25))


def _render(
    shape: tuple[int, int],
    p: float,
    xc: float,
    rx: float,
    ry: float,
    dome: str,
    second_channel: bool,
    cross1: bool,
    cross2: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Draw the canonical (unrotated) scan; return heights and two noise masks."""
    rows, cols = np.indices(shape, dtype=float)
    x, y = cols * p, rows * p
    z = np.zeros(shape)

    z[y < 12.0] = 13.0  # supporting band
    domes = np.full(shape, -np.inf)
    for k in (-1, 0, 1):
        dx, dy = x - xc - PITCH_UM * k, y - APEX_Y_UM
        if dome == "sphere":
            h = APEX_HEIGHT_UM - (rx - np.sqrt(np.maximum(rx**2 - dx**2 - dy**2, 0.0)))
        else:
            h = APEX_HEIGHT_UM - dx**2 / (2 * rx) - dy**2 / (2 * ry)
        domes = np.maximum(domes, h)
    dome_row = (y >= 12.0) & (y < 145.0)
    z[dome_row] = domes[dome_row]

    centres = [xc] + ([xc + PITCH_UM] if second_channel else [])
    for cx in centres:
        dx = x - cx
        z[(np.abs(dx) <= 43) & (y >= 145) & (y < 200)] = TOOTH_UM
        z[(np.abs(dx) <= 38) & (y >= 152) & (y < 199)] = PLANE1_UM
        for sx in (-34.0, 34.0):
            for sy in (160.0, 170.0, 180.0, 190.0):
                z[(np.abs(dx - sx) <= 2) & (np.abs(y - sy) <= 2)] = PLANE1_UM + 2.0
        ramp = (np.abs(dx) <= 16) & (y >= 165) & (y < PLANE2_Y_UM[0])
        z[ramp] = PLANE1_UM + (y[ramp] - 165.0) * (PLANE2_UM - PLANE1_UM) / (PLANE2_Y_UM[0] - 165.0)
        z[(np.abs(dx) <= 16) & (y >= PLANE2_Y_UM[0]) & (y < PLANE2_Y_UM[1])] = PLANE2_UM
        if cross1:
            z[_plus(x, y, cx, CROSS1_Y_UM)] = PLANE1_UM - CROSS1_DEPTH_UM
        if cross2:
            z[_plus(x, y, cx, CROSS2_Y_UM)] = PLANE2_UM - CROSS2_DEPTH_UM

    block = (np.abs(x - (xc + 50)) <= 30) & (np.abs(y - 250) <= 30)
    z[block] = 23.5
    z[_plus(x, y, xc + 50, 250.0)] = 22.0

    pivot_mask = (np.abs(x - xc) <= 38) & (y >= 152) & (y < 199)
    dome_mask = (np.abs(x - xc) <= 63) & dome_row
    return z, pivot_mask, dome_mask


def _transform(img: np.ndarray, rotation_deg: float, quarter_turns: int, crop_rows: int,
               order: int) -> np.ndarray:
    """Rotate about the array centre, quarter-turn, then crop rows from the top."""
    if rotation_deg:
        img = ndimage.rotate(img, rotation_deg, reshape=False, order=order,
                             mode="constant", cval=0.0)
    img = np.rot90(img, quarter_turns)
    return np.ascontiguousarray(img[crop_rows:])


def _map_point(x: float, y: float, shape: tuple[int, int], rotation_deg: float,
               quarter_turns: int, crop_rows: int) -> tuple[float, float]:
    """Where a canonical pixel position ends up after :func:`_transform`."""
    h, w = shape
    if rotation_deg:
        c = np.array([(w - 1) / 2, (h - 1) / 2])
        a = np.deg2rad(rotation_deg)
        m = np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
        x, y = c + m @ (np.array([x, y]) - c)
    for _ in range(quarter_turns % 4):  # np.rot90(., 1): (x, y) -> (y, w - 1 - x)
        x, y = y, w - 1 - x
        h, w = w, h
    return float(x), float(y - crop_rows)


def make_scan(
    *,
    shape: tuple[int, int] = (1200, 800),
    pixel_size_um: float = 0.252,
    rotation_deg: float = 0.0,
    quarter_turns: int = 0,
    slope_x: float = 0.0,
    slope_y: float = 0.0,
    noise_um: float = 0.012,
    pivot_noise_um: float = 0.0,
    xpander_noise_um: float = 0.0,
    rx_um: float = 820.0,
    ry_um: float = 840.0,
    dome: str = "paraboloid",
    channel_offset_um: float = 0.0,
    second_channel: bool = False,
    cross1: bool = True,
    cross2: bool = True,
    crop_top_um: float = 0.0,
    nan_fraction: float = 0.0,
    seed: int = 0,
) -> tuple[np.ndarray, SyntheticTruth]:
    """Generate a synthetic scan and its ground truth.

    ``dome="sphere"`` draws a spherical cap of radius ``rx_um`` (``ry_um`` is
    then ignored and reported equal to ``rx_um``). Rotation follows the
    ``scipy.ndimage.rotate`` convention (positive = counter-clockwise on screen).
    """
    p = pixel_size_um
    xc = shape[1] * p / 2 + channel_offset_um
    crop_rows = int(round(crop_top_um / p))
    rng = np.random.default_rng(seed)

    z, pivot_mask, dome_mask = _render(shape, p, xc, rx_um, ry_um, dome, second_channel,
                                       cross1, cross2)
    z = ndimage.gaussian_filter(z, 0.7)
    z = _transform(z, rotation_deg, quarter_turns, crop_rows, order=1)
    pivot_mask = _transform(pivot_mask.astype(float), rotation_deg, quarter_turns, crop_rows,
                            order=0) > 0.5
    dome_mask = _transform(dome_mask.astype(float), rotation_deg, quarter_turns, crop_rows,
                           order=0) > 0.5

    rows, cols = np.indices(z.shape, dtype=float)
    z = z + slope_x * cols * p + slope_y * rows * p
    if noise_um:
        z = z + rng.normal(0.0, noise_um, z.shape)
    if pivot_noise_um:
        z = z + np.where(pivot_mask, rng.normal(0.0, pivot_noise_um, z.shape), 0.0)
    if xpander_noise_um:
        z = z + np.where(dome_mask, rng.normal(0.0, xpander_noise_um, z.shape), 0.0)
    if nan_fraction:
        idx = rng.choice(z.size, size=int(round(nan_fraction * z.size)), replace=False)
        z.flat[idx] = np.nan

    def where(x_um: float, y_um: float) -> tuple[float, float]:
        return _map_point(x_um / p, y_um / p, shape, rotation_deg, quarter_turns, crop_rows)

    truth = SyntheticTruth(
        rotation_deg=rotation_deg + 90.0 * quarter_turns,
        slope_x=slope_x,
        slope_y=slope_y,
        pivot_step_um=PLANE2_UM - PLANE1_UM,
        cross1_xy_px=where(xc, CROSS1_Y_UM),
        cross2_xy_px=where(xc, CROSS2_Y_UM),
        apex_xy_px=where(xc, APEX_Y_UM),
        rx_um=rx_um,
        ry_um=rx_um if dome == "sphere" else ry_um,
        plane2_center_xy_px=where(xc, sum(PLANE2_Y_UM) / 2),
    )
    return z, truth
