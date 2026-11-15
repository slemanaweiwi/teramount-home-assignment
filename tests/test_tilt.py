"""Tests for base-plane tilt estimation and leveling."""

from __future__ import annotations

import numpy as np
import pytest
from synthetic import make_scan

from teramount_analysis.config import Config
from teramount_analysis.errors import FitError
from teramount_analysis.tilt import fit_base_plane, remove_tilt


def test_tilt_recovered_on_synthetic():
    z, _ = make_scan(slope_x=0.0015, slope_y=-0.0010, rotation_deg=0.5)
    r = fit_base_plane(z, Config())
    assert r.slope_x == pytest.approx(0.0015, abs=2e-5)
    assert r.slope_y == pytest.approx(-0.0010, abs=2e-5)
    assert r.tilt_x_deg == pytest.approx(np.degrees(np.arctan(0.0015)), abs=0.002)
    assert r.tilt_total_deg == pytest.approx(np.degrees(np.arctan(np.hypot(0.0015, 0.001))),
                                             abs=0.002)
    assert r.tilt_azimuth_deg == pytest.approx(np.degrees(np.arctan2(-0.001, 0.0015)), abs=1.0)
    assert r.base_rms_um < 0.02
    assert 0.3 < r.base_fraction < 0.9


def test_tilt_ignores_nan_pixels():
    z, _ = make_scan(slope_x=0.001, nan_fraction=0.02)
    assert fit_base_plane(z, Config()).slope_x == pytest.approx(0.001, abs=2e-5)


def test_remove_tilt_levels_base():
    z, _ = make_scan(slope_x=0.001, slope_y=0.002)
    lev = remove_tilt(z, fit_base_plane(z, Config()), Config())
    assert abs(np.nanmedian(lev[-100:, :])) < 0.01  # bottom rows are base
    assert abs(np.nanmedian(lev[-100:, :100]) - np.nanmedian(lev[-100:, -100:])) < 0.01


def test_remove_tilt_keeps_nans():
    z, _ = make_scan(nan_fraction=0.01)
    lev = remove_tilt(z, fit_base_plane(z, Config()), Config())
    assert np.array_equal(np.isnan(lev), np.isnan(z))


def test_tilt_correction_disabled_subtracts_only_a_constant():
    z, _ = make_scan(slope_x=0.002)
    cfg = Config(correct_tilt=False)
    lev = remove_tilt(z, fit_base_plane(z, cfg), cfg)
    rise = np.nanmedian(lev[-100:, -50:]) - np.nanmedian(lev[-100:, :50])
    assert rise == pytest.approx(0.002 * (800 - 50) * 0.252, rel=0.05)  # slope still present


def test_nothing_flat_raises():
    x = np.arange(200.0) * 0.252
    steep = np.tile(1.0 * x, (200, 1))  # 1 µm/µm everywhere
    with pytest.raises(FitError):
        fit_base_plane(steep, Config())
