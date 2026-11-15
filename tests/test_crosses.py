"""Tests for cross detection and sub-pixel centres."""

from __future__ import annotations

import numpy as np
import pytest
from helpers import run_crosses
from synthetic import make_scan

from teramount_analysis.frame import Frame


@pytest.mark.parametrize("phi", [0.0, 0.75])
def test_cross_centres_match_truth(phi):
    z, t = make_scan(rotation_deg=phi)
    c1, c2 = run_crosses(z, phi)
    assert c1.found and c2.found
    assert (c1.x_px, c1.y_px) == pytest.approx(t.cross1_xy_px, abs=0.3)
    assert (c2.x_px, c2.y_px) == pytest.approx(t.cross2_xy_px, abs=0.3)
    assert c1.depth_um == pytest.approx(1.8, abs=0.2) and c2.depth_um == pytest.approx(1.5, abs=0.2)


def test_canonical_centre_consistent_with_original():
    z, _ = make_scan(rotation_deg=0.75)
    c1, _ = run_crosses(z, 0.75)
    u, v = Frame(z.shape, 0.75).to_canonical(c1.x_px, c1.y_px)
    assert (c1.u_px, c1.v_px) == pytest.approx((float(u), float(v)), abs=1e-6)


def test_clean_cross_sits_on_the_axis():
    z, _ = make_scan()
    c1, c2 = run_crosses(z, 0.0)
    assert c1.axis_offset_um < 0.3 and c2.axis_offset_um < 0.3
    assert 10 < c1.area_um2 < 40 and 0.75 < c1.solidity < 0.97
    assert c1.mask is not None and c1.mask.dtype == bool


def test_noisy_plane_cross_still_found():
    z, t = make_scan(pivot_noise_um=0.6)
    c1, c2 = run_crosses(z, 0.0)
    assert (c1.x_px, c1.y_px) == pytest.approx(t.cross1_xy_px, abs=0.6)
    assert (c2.x_px, c2.y_px) == pytest.approx(t.cross2_xy_px, abs=0.6)


def test_missing_cross_reported_not_raised():
    z, _ = make_scan(cross2=False)
    c1, c2 = run_crosses(z, 0.0)
    assert c1.found and not c2.found and np.isnan(c2.x_px) and c2.mask is None
