"""Sanity tests for the synthetic scan generator used by the other tests."""

from __future__ import annotations

import numpy as np
import pytest
from synthetic import make_scan

PX = 0.252


def _at(z, x_px, y_px):
    return z[int(round(y_px)), int(round(x_px))]


def test_levels_at_known_points():
    z, t = make_scan(noise_um=0.0)
    xc = 800 * PX / 2

    def at(x_um, y_um):
        return z[int(round(y_um / PX)), int(round(x_um / PX))]

    assert at(xc + 10, 190.0) == pytest.approx(31.0, abs=0.05)  # plane 2
    assert at(xc - 30, 154.0) == pytest.approx(12.9, abs=0.05)  # plane 1
    assert at(xc, 158.5) == pytest.approx(11.1, abs=0.1)  # cross 1 floor
    assert at(xc, 80.0) == pytest.approx(12.4, abs=0.01)  # dome apex
    assert at(xc - 60, 260.0) == pytest.approx(0.0, abs=0.05)  # base (the block is at xc+50)
    assert t.pivot_step_um == pytest.approx(18.1)


def test_rotation_moves_truth_points_like_scipy():
    _, t0 = make_scan(noise_um=0.0)
    _, t1 = make_scan(noise_um=0.0, rotation_deg=1.0)
    c = np.array([(800 - 1) / 2, (1200 - 1) / 2])
    a = np.deg2rad(1.0)
    m = np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
    assert np.allclose(t1.apex_xy_px, c + m @ (np.array(t0.apex_xy_px) - c), atol=1e-9)


def test_tilt_and_nans_and_crop():
    z, _ = make_scan(slope_x=0.001, noise_um=0.0, nan_fraction=0.01, crop_top_um=40.0)
    assert np.isnan(z).mean() == pytest.approx(0.01, abs=0.002)
    assert z.shape[0] == 1200 - int(round(40.0 / 0.252))


@pytest.mark.parametrize("rotation_deg,quarter_turns", [(0.0, 1), (0.0, 2), (0.0, 3), (1.0, 0)])
def test_truth_points_land_on_features(rotation_deg, quarter_turns):
    z, t = make_scan(noise_um=0.0, rotation_deg=rotation_deg, quarter_turns=quarter_turns)
    assert _at(z, *t.apex_xy_px) == pytest.approx(12.4, abs=0.02)
    assert _at(z, *t.cross1_xy_px) == pytest.approx(11.1, abs=0.1)
    assert _at(z, *t.cross2_xy_px) == pytest.approx(29.5, abs=0.1)
    assert t.rotation_deg == pytest.approx(rotation_deg + 90 * quarter_turns)


def test_noise_is_confined_to_its_region():
    clean, t = make_scan(noise_um=0.0)
    noisy, _ = make_scan(noise_um=0.0, xpander_noise_um=0.2)
    diff = noisy - clean
    ax, ay = (int(round(v)) for v in t.apex_xy_px)
    assert diff[ay - 50 : ay + 50, ax - 50 : ax + 50].std() == pytest.approx(0.2, rel=0.1)
    assert np.abs(diff[-200:, :]).max() == 0.0  # base far below the dome is untouched
