"""Tests for the surface helpers (NaN filling, smoothing, slope, flatness)."""

from __future__ import annotations

import numpy as np
import pytest

from teramount_analysis.config import Config
from teramount_analysis.surface import (
    fill_invalid,
    flat_mask,
    segmentation_surface,
    slope,
    smooth,
)


def test_fill_invalid_uses_nearest():
    z = np.full((5, 5), 5.0)
    z[2, 2] = np.nan
    filled, valid = fill_invalid(z)
    assert filled[2, 2] == 5.0
    assert not valid[2, 2] and valid.sum() == 24
    assert np.isnan(z[2, 2])  # input untouched


def test_fill_invalid_takes_a_neighbour_value():
    z = np.arange(25.0).reshape(5, 5)
    z[0, 0] = np.inf
    filled, _ = fill_invalid(z)
    assert filled[0, 0] in (z[0, 1], z[1, 0])


def test_fill_invalid_without_nans_returns_copy():
    z = np.ones((4, 4))
    filled, valid = fill_invalid(z)
    assert filled is not z and valid.all()


def test_smooth_median_removes_spike():
    z = np.zeros((30, 30))
    z[15, 15] = 100.0
    assert smooth(z, 1.0, median_px=3).max() < 1e-12
    assert smooth(z, 1.0).max() > 1.0  # Gaussian alone only spreads it


def test_slope_units():
    x = np.arange(100.0) * 0.252
    z = np.tile(0.5 * x, (50, 1))  # 0.5 µm per µm
    assert np.allclose(slope(z, 0.252)[5:-5, 5:-5], 0.5)


def test_flat_mask_threshold():
    x = np.arange(100.0) * 0.252
    gentle = np.tile(0.1 * x, (60, 1))
    steep = np.tile(0.5 * x, (60, 1))
    assert flat_mask(gentle, Config())[10:-10, 10:-10].all()
    assert not flat_mask(steep, Config())[10:-10, 10:-10].any()


def test_segmentation_surface_is_finite_with_nans():
    z = np.zeros((80, 80))
    z[::7, ::5] = np.nan
    out = segmentation_surface(z, Config())
    assert np.isfinite(out).all() and np.allclose(out, 0.0)


@pytest.mark.parametrize("bad", [np.full((5, 5), np.nan)])
def test_fill_invalid_rejects_all_invalid(bad):
    with pytest.raises(ValueError):
        fill_invalid(bad)
