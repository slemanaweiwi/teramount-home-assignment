"""Tests for Xpander localisation, aperture selection and curvature."""

from __future__ import annotations

import numpy as np
import pytest
from helpers import prepare, run_xpander
from synthetic import make_scan

from teramount_analysis.config import Config
from teramount_analysis.frame import Frame
from teramount_analysis.surface import smooth
from teramount_analysis.xpander import boundary_distances


@pytest.mark.parametrize("phi", [0.0, -1.0])
def test_paraboloid_radii_recovered(phi):
    z, t = make_scan(rotation_deg=phi, rx_um=820, ry_um=840)
    x = run_xpander(z, phi)
    assert x.found, x.reason
    assert x.rx_um == pytest.approx(820, rel=0.003) and x.ry_um == pytest.approx(840, rel=0.003)
    assert (x.apex_x_px, x.apex_y_px) == pytest.approx(t.apex_xy_px, abs=1.0)
    assert x.aperture_radius_um == pytest.approx(0.8 * 63, rel=0.1)
    assert x.nrms_pct < 1.0 and x.r_squared > 0.999


def test_principal_radii_and_stability_of_a_paraboloid():
    z, _ = make_scan(rx_um=820, ry_um=840)
    x = run_xpander(z, 0.0)
    assert x.r1_um == pytest.approx(820, rel=0.003) and x.r2_um == pytest.approx(840, rel=0.003)
    assert abs(x.principal_angle_deg) < 2.0  # R1 lies along +u
    assert x.stability_pct < 0.5
    assert x.axis_offset_um < 0.5
    assert x.residual_map is not None and np.isfinite(x.residual_map).sum() > 0.9 * x.n_points


@pytest.mark.parametrize("angle", [20.0, -35.0])
def test_principal_angle_is_counter_clockwise(angle):
    # Same sign convention as the rotation: positive = counter-clockwise as displayed.
    z, _ = make_scan(rx_um=800, ry_um=860, dome_angle_deg=angle)
    x = run_xpander(z, 0.0)
    assert x.r1_um == pytest.approx(800, rel=0.005) and x.r2_um == pytest.approx(860, rel=0.005)
    assert x.principal_angle_deg == pytest.approx(angle, abs=1.0)


def test_boundary_stops_at_the_valley_to_the_neighbour():
    z, t = make_scan()
    zs = smooth(prepare(z, 0.0)[2], Config().px(2.0))
    d = boundary_distances(zs, t.apex_xy_px, Config())
    assert d.min() * 0.252 == pytest.approx(63.0, rel=0.05)


@pytest.mark.parametrize("phi, offset", [(9.0, -62.0), (-9.0, 62.0)])
def test_aperture_stays_inside_the_measured_data(phi, offset):
    # Near a corner of a rotated scan the canonical image is extrapolated: the
    # rays that size the aperture must stop where the measured data ends.
    z, _ = make_scan(rotation_deg=phi, channel_offset_um=offset)
    x = run_xpander(z, phi)
    assert x.found, x.reason
    a = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    rad = x.aperture_radius_um / 0.252
    xs, ys = Frame(z.shape, phi, 0).to_original(x.apex_u_px + rad * np.cos(a),
                                                x.apex_v_px + rad * np.sin(a))
    h, w = z.shape
    assert xs.min() >= 0 and ys.min() >= 0 and xs.max() <= w - 1 and ys.max() <= h - 1
    assert x.rx_um == pytest.approx(820, rel=0.005) and x.ry_um == pytest.approx(840, rel=0.005)


def test_sphere_cap_cross_checks():
    z, _ = make_scan(dome="sphere", rx_um=830, ry_um=830)
    x = run_xpander(z, 0.0)
    assert x.r_sphere_um == pytest.approx(830, rel=0.003)
    assert x.rx_um == pytest.approx(830, rel=0.005)
    assert x.rx_profile_um == pytest.approx(830, rel=0.01)
    assert x.ry_profile_um == pytest.approx(830, rel=0.01)


def test_noisy_dome_radius_unbiased_but_flagged_by_nrms():
    z, _ = make_scan(xpander_noise_um=0.2, rx_um=820, ry_um=840)
    x = run_xpander(z, 0.0)
    assert x.rx_um == pytest.approx(820, rel=0.01) and x.nrms_pct > 2.0
    assert abs(x.rx_um - 820) < 3 * x.rx_ci95_um + 1.0


def test_fit_failure_in_summary_is_reported_not_raised(monkeypatch):
    import teramount_analysis.xpander as xpander_module
    from teramount_analysis.errors import FitError

    def singular(*args, **kwargs):
        raise FitError("quadric has no unique vertex (singular Hessian)")

    monkeypatch.setattr(xpander_module, "_summarise", singular)
    z, _ = make_scan()
    x = run_xpander(z, 0.0)
    assert not x.found and "vertex" in x.reason


def test_dome_cut_by_border_reason_names_the_border():
    # Apex 32 µm below the top edge: prominent, but the border limits the aperture.
    z, _ = make_scan(crop_top_um=48.0)
    x = run_xpander(z, 0.0, Config(xpander_min_aperture_um=30.0))
    assert not x.found and "border" in x.reason and "neighbour" not in x.reason


def test_neighbour_too_close_reason_names_the_neighbour():
    z, _ = make_scan()  # the valley to the next dome is 63 µm away: aperture 50 µm
    x = run_xpander(z, 0.0, Config(xpander_min_aperture_um=60.0))
    assert not x.found and "neighbour" in x.reason and "border" not in x.reason


def test_dome_cut_by_border_is_not_found():
    z, _ = make_scan(crop_top_um=60.0)  # top 60 µm removed: dome apex 20 µm from the border
    x = run_xpander(z, 0.0)
    assert not x.found and x.reason  # rejected by prominence or by aperture size, never fitted
    assert np.isnan(x.rx_um)
