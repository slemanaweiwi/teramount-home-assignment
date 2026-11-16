"""Tests for scan-line streak detection and removal."""

from __future__ import annotations

import numpy as np
import pytest
from synthetic import add_streaks, make_scan

from teramount_analysis.config import Config
from teramount_analysis.streaks import remove_streaks


def _residual_streak_um(corrected: np.ndarray, clean: np.ndarray, axis: int) -> float:
    """Typical line-to-line jump left after correction (the streaks themselves).

    A smooth wave of a few nm over several µm may remain: that is the
    uncertainty of the surface trend, not a streak.
    """
    d = np.nanmedian(corrected - clean, axis=1 - axis)
    jumps = np.diff(d)
    return float(1.4826 * np.median(np.abs(jumps - np.median(jumps))) / np.sqrt(2))


def test_clean_scan_is_left_untouched():
    z, _ = make_scan(slope_x=0.001, slope_y=-0.0015)
    out, s = remove_streaks(z, Config())
    assert not s.corrected and s.level_um < 0.005
    assert np.array_equal(out, z)


@pytest.mark.parametrize("std_um", [0.02, 0.05])
def test_row_streaks_are_measured_and_removed(std_um):
    clean, _ = make_scan(slope_x=0.001)
    out, s = remove_streaks(add_streaks(clean, std_um), Config())
    assert s.corrected and s.axis == "rows"
    assert s.level_um == pytest.approx(std_um, rel=0.25)
    assert _residual_streak_um(out, clean, axis=0) < 0.004


def test_column_streaks_are_removed():
    clean, _ = make_scan()
    streaked = add_streaks(clean.T.copy(), 0.03).T
    out, s = remove_streaks(streaked, Config())
    assert s.corrected and s.axis == "columns"
    assert _residual_streak_um(out, clean, axis=1) < 0.004


def test_streak_correction_can_be_disabled():
    clean, _ = make_scan()
    z = add_streaks(clean, 0.05)
    out, s = remove_streaks(z, Config(correct_streaks=False))
    assert not s.corrected and s.level_um > 0.03 and np.array_equal(out, z)


def test_nan_pixels_stay_nan():
    clean, _ = make_scan(nan_fraction=0.01)
    z = add_streaks(clean, 0.03)
    out, s = remove_streaks(z, Config())
    assert s.corrected and np.array_equal(np.isnan(out), np.isnan(z))
