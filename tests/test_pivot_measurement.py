"""Tests for the Pivot plane fits and height difference."""

from __future__ import annotations

import pytest
from helpers import run_pivot
from synthetic import make_scan


@pytest.mark.parametrize("phi,slopes", [(0.0, (0, 0)), (-1.0, (0.0015, -0.001))])
def test_height_difference(phi, slopes):
    z, _ = make_scan(rotation_deg=phi, slope_x=slopes[0], slope_y=slopes[1])
    p = run_pivot(z, phi)
    assert p.height_diff_um == pytest.approx(18.1, abs=0.02)
    assert p.parallelism_deg < 0.05


def test_plane_levels_relative_to_base():
    z, _ = make_scan()
    p = run_pivot(z, 0.0)
    assert p.plane1_level_um == pytest.approx(12.9, abs=0.05)
    assert p.plane2_level_um == pytest.approx(31.0, abs=0.05)
    assert p.plane1_rms_um < 0.03 and p.plane2_rms_um < 0.03


def test_height_difference_with_pivot_noise():
    z, _ = make_scan(pivot_noise_um=0.6)
    p = run_pivot(z, 0.0)
    assert p.height_diff_um == pytest.approx(18.1, abs=0.05)
    assert p.plane1_rms_um > 0.4


def test_crosses_bias_naive_estimate():
    z, _ = make_scan(noise_um=0.0)
    p = run_pivot(z, 0.0)
    assert 0.005 < abs(p.height_diff_with_crosses_um - p.height_diff_um) < 1.0


def test_works_without_cross_masks():
    z, _ = make_scan()
    p = run_pivot(z, 0.0, use_cross_masks=False)
    assert p.height_diff_um == pytest.approx(18.1, abs=0.03)  # robust clipping drops the crosses
