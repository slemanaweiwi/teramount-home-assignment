"""Tests for the Pivot plane fits and height difference."""

from __future__ import annotations

import pytest
from helpers import run_pivot
from synthetic import add_particle, make_scan


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


def test_steep_dust_on_plane_1_is_left_out_and_does_not_change_the_step():
    # A 1 um particle breaks the flatness, so the segmentation leaves it out of the
    # plane (like the chip's own raised pads): it cannot bias the step.
    z, t = make_scan()
    cx, cy = t.cross1_xy_px
    pv = run_pivot(add_particle(z, (cx - 20 / 0.252, cy + 4 / 0.252), 2.0, 1.0), 0.0)
    assert pv.height_diff_um == pytest.approx(18.1, abs=0.02)


def test_shallow_bump_on_plane_1_is_reported_and_does_not_change_the_step():
    # A low, broad bump stays inside the flat plane: it is dropped from the fit
    # with a rim around it, and reported as a local feature.
    z, t = make_scan()
    cx, cy = t.cross1_xy_px
    # Middle of the free strip between the pads (x = -34 um) and the ramp (x = -16 um).
    pv = run_pivot(add_particle(z, (cx - 24 / 0.252, cy + 16 / 0.252), 4.0, 0.3), 0.0)
    assert pv.plane1_feature_um2 > 1.0 and pv.plane2_feature_um2 == 0.0
    assert pv.height_diff_um == pytest.approx(18.1, abs=0.02)


def test_pit_on_plane_2_is_reported():
    z, t = make_scan()
    cx, cy = t.cross2_xy_px
    pv = run_pivot(add_particle(z, (cx + 9 / 0.252, cy), 1.5, -0.6), 0.0)
    assert pv.plane2_feature_um2 > 1.0


def test_bad_scan_line_across_plane_1_is_a_line_not_a_feature():
    z, t = make_scan()
    z[int(t.cross1_xy_px[1]) + 30] += 0.5  # 7.6 um below cross 1, inside plane 1
    pv = run_pivot(z, 0.0)
    assert pv.glitch_lines >= 1 and pv.plane1_feature_um2 == 0.0
    assert pv.height_diff_um == pytest.approx(18.1, abs=0.02)


def test_clean_planes_have_no_features():
    pv = run_pivot(make_scan()[0], 0.0)
    assert pv.plane1_feature_um2 == 0.0 and pv.plane2_feature_um2 == 0.0 and pv.glitch_lines == 0
