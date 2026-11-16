"""Scan-line streaks: whole lines of a scan shifted by their own height.

An optical profilometer builds the height map line by line, and drift
between lines shows as streaks: every row (or column) offset by a small
constant. The offsets are measured from the height steps between
neighbouring lines, using only pixels that are flat in both lines (an edge
would look like a step); the median over each line ignores the structures.
Summing the steps gives the height of every line; a running mean (Gaussian)
over a few µm of lines is the surface trend (tilt, curvature), so what is
left is the streak offset of each line. A mean, not a median: the slow part
of random line offsets cannot be told apart from the surface and is left as
it was, and a median would amplify it.

A scan is corrected only when the streaks are clearly present
(``Config.streak_min_um``). On a clean scan the measured level is the
method's own uncertainty, a few nm at most, and the scan is returned
unchanged.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from .config import Config
from .surface import flat_mask, segmentation_surface

_MIN_FLAT_PER_LINE = 20  # fewer flat pixel pairs: the line's step is unknown
_MAD_TO_SIGMA = 1.4826


@dataclass(frozen=True)
class StreakResult:
    """Streaks found in a scan and whether they were removed."""

    level_um: float  # robust spread of the line offsets, larger direction [µm]
    noise_floor_um: float  # spread the estimate shows from pixel noise alone [µm]
    axis: str  # direction of the larger streaks: "rows" or "columns"
    corrected: bool  # True when the offsets were subtracted


def _line_offsets(z: np.ndarray, flat: np.ndarray, sigma: float) -> tuple[np.ndarray, float]:
    """Streak offset of every row of ``z``, and the spread pixel noise alone gives it.

    Each line's step is a median of ``n`` noisy differences, so it carries an
    error of about 1.25 x their spread / sqrt(n); the typical value over the
    lines is the floor below which a "streak" is just noise.
    """
    d = z[1:] - z[:-1]
    ok = flat[1:] & flat[:-1] & np.isfinite(d)
    counts = ok.sum(axis=1)
    with warnings.catch_warnings():  # lines with no flat pixel: handled just below
        warnings.simplefilter("ignore", RuntimeWarning)
        diffs = np.where(ok, d, np.nan)
        steps = np.nanmedian(diffs, axis=1) if d.size else np.zeros(0)
        spread = _MAD_TO_SIGMA * np.nanmedian(np.abs(diffs - steps[:, None]), axis=1)
    known = counts >= _MIN_FLAT_PER_LINE
    if not known.any():
        return np.zeros(z.shape[0]), 0.0
    floor = float(np.median(1.2533 * spread[known] / np.sqrt(counts[known])))
    steps = np.where(known, steps, np.median(steps[known]))  # unknown: the typical step
    heights = np.concatenate([[0.0], np.cumsum(steps)])
    trend = ndimage.gaussian_filter1d(heights, sigma, mode="nearest")
    return heights - trend, floor


def _level(offsets: np.ndarray) -> float:
    return float(_MAD_TO_SIGMA * np.median(np.abs(offsets - np.median(offsets))))


def remove_streaks(z: np.ndarray, config: Config, flat: np.ndarray | None = None
                   ) -> tuple[np.ndarray, StreakResult]:
    """Measure scan-line streaks and subtract them when clearly present.

    ``flat`` is the flat-pixel mask of ``z`` if already computed.

    Returns
    -------
    (heights, result)
        ``z`` itself when nothing was corrected, otherwise a corrected copy
        (NaN pixels stay NaN), and what was found.
    """
    if flat is None:
        flat = flat_mask(segmentation_surface(z, config), config)
    flat = flat & np.isfinite(z)
    sigma = config.px(config.streak_trend_um)
    rows, row_floor = _line_offsets(z, flat, sigma)
    cols, col_floor = _line_offsets(z.T, flat.T, sigma)
    row_level, col_level = _level(rows), _level(cols)
    axis = "rows" if row_level >= col_level else "columns"
    level = max(row_level, col_level)
    floor = max(row_floor, col_floor)

    def clear(lvl: float, flr: float) -> bool:  # well above the method's own noise
        return lvl > max(config.streak_min_um, config.streak_noise_factor * flr)

    if not config.correct_streaks or not (clear(row_level, row_floor)
                                          or clear(col_level, col_floor)):
        return z, StreakResult(level, floor, axis, False)
    out = z.copy()
    if clear(row_level, row_floor):
        out = out - rows[:, None]
    if clear(col_level, col_floor):
        out = out - cols[None, :]
    return out, StreakResult(level, floor, axis, True)
