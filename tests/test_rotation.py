"""Tests for the straight-edge rotation estimator."""

from __future__ import annotations

import numpy as np
import pytest
from synthetic import make_scan

from teramount_analysis.config import Config
from teramount_analysis.errors import RotationError
from teramount_analysis.rotation import edge_crossing, estimate_rotation, line_angle


def test_edge_crossing_subpixel():
    x = np.arange(13.0)
    h = 1 / (1 + np.exp(-(x - 6.3) / 0.6))  # step centred at 6.3
    assert edge_crossing(h, np.gradient(h)) == pytest.approx(6.3, abs=0.02)


def test_edge_crossing_falling_step():
    x = np.arange(13.0)
    h = 5.0 - 5.0 / (1 + np.exp(-(x - 5.7) / 0.6))
    assert edge_crossing(h, np.abs(np.gradient(h))) == pytest.approx(5.7, abs=0.02)


def test_edge_crossing_none_without_step():
    flat = np.ones(13)
    assert edge_crossing(flat, np.zeros(13)) is None


def test_line_angle_vertical_and_horizontal():
    y = np.arange(100.0)
    vertical = np.column_stack([10 + np.tan(np.deg2rad(1.0)) * y, y])
    angle, rms = line_angle(vertical, vertical=True)
    assert angle == pytest.approx(1.0) and rms == pytest.approx(0.0, abs=1e-9)
    x = np.arange(100.0)
    horizontal = np.column_stack([x, 5 - np.tan(np.deg2rad(0.5)) * x])
    assert line_angle(horizontal, vertical=False)[0] == pytest.approx(0.5)


@pytest.mark.parametrize("phi", [0.0, 0.5, -1.0, 3.0, -7.5])
def test_rotation_recovered_on_synthetic(phi):
    z, _ = make_scan(rotation_deg=phi)
    r = estimate_rotation(z, Config())
    assert r.angle_deg == pytest.approx(phi, abs=0.03)
    # The synthetic scan has fewer long edges than a real one (real scans give 32-46
    # lines; asserted in test_real_data.py).
    assert r.n_lines >= 5 and r.se_deg < 0.05
    assert len(r.lines) == r.n_lines


def test_rotation_with_nans_and_tilt():
    z, _ = make_scan(rotation_deg=0.75, slope_x=0.001, nan_fraction=0.005)
    assert estimate_rotation(z, Config()).angle_deg == pytest.approx(0.75, abs=0.03)


def test_flat_image_raises():
    with pytest.raises(RotationError):
        estimate_rotation(np.zeros((300, 300)), Config())
