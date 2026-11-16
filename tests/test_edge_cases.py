"""Error paths and rarely taken branches.

Each test describes a situation a real scan or a caller can produce, and the
outcome the code promises: a clear error, or "not found" with a reason, or a
NaN for an unavailable cross-check, never a crash or a silent wrong number.
"""

from __future__ import annotations

import numpy as np
import pytest
from helpers import fake_result, fake_xpander, prepare
from synthetic import add_spikes, make_scan

import teramount_analysis.pipeline as pipeline_module
import teramount_analysis.rotation as rotation_module
import teramount_analysis.xpander as xpander_module
from teramount_analysis import Config, analyse_dataset, analyse_scan
from teramount_analysis.cli import build_parser, config_from_args
from teramount_analysis.crosses import _candidates, find_cross
from teramount_analysis.errors import ElementNotFoundError, FitError, RotationError, ScanLoadError
from teramount_analysis.faults import geometric_flags, nominal_flags
from teramount_analysis.figures import save_scan_figure
from teramount_analysis.fitting import (
    fit_plane,
    fit_profile_circle,
    fit_quadric,
    fit_sphere,
    ransac_plane,
)
from teramount_analysis.frame import Frame
from teramount_analysis.io import load_scan
from teramount_analysis.pivot import (
    PivotRegions,
    PivotResult,
    find_plane1,
    find_plane2,
    measure_pivot,
    ramp_direction,
    segment_pivot,
)
from teramount_analysis.report import _cell
from teramount_analysis.results import ScanResult
from teramount_analysis.rotation import _edge_points, edge_crossing, estimate_rotation
from teramount_analysis.streaks import remove_streaks

# --------------------------------------------------------------------- command line


def test_nominal_radius_option_reaches_the_config():
    args = build_parser().parse_args(["--data", "x", "--nominal-radius", "900"])
    assert config_from_args(args).nominal_radius_um == 900.0


# --------------------------------------------------------------------- loading


def test_npz_archive_with_npy_name_is_refused(tmp_path):
    np.savez(tmp_path / "scan.npz", a=np.zeros((64, 64)))
    (tmp_path / "scan.npz").rename(tmp_path / "scan.npy")
    with pytest.raises(ScanLoadError, match="single array"):
        load_scan(tmp_path / "scan.npy")


# --------------------------------------------------------------------- fitting


def test_fits_refuse_degenerate_input():
    line = np.arange(12.0)
    with pytest.raises(FitError, match="different lengths"):
        fit_plane([0.0, 1.0, 2.0], [0.0, 1.0], [0.0, 1.0, 2.0])
    with pytest.raises(FitError, match="collinear"):
        fit_plane(line, line, line)
    with pytest.raises(FitError, match=">= 3"):
        ransac_plane(line[:2], line[:2], line[:2], 0.1, 10, np.random.default_rng(0))
    with pytest.raises(FitError, match="no valid plane"):  # every sample is collinear
        ransac_plane(line, 2 * line, line, 0.1, 20, np.random.default_rng(0))
    with pytest.raises(FitError, match="2-D area"):
        fit_quadric(line, line, line)
    with pytest.raises(FitError, match=">= 4"):
        fit_sphere(line[:3], line[:3], line[:3], initial=(0.0, 0.0, 0.0, 1.0))
    with pytest.raises(FitError, match=">= 5"):
        fit_profile_circle(line[:4], line[:4])
    with pytest.raises(FitError, match="straight"):
        fit_profile_circle(line, 3.0 + 0.5 * line)


# --------------------------------------------------------------------- rotation


def test_edge_crossing_exactly_on_a_sample():
    h = np.array([0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 2], dtype=float)
    assert edge_crossing(h, np.gradient(h)) == 6.0


def test_edge_crossing_outside_the_search_window_is_rejected():
    h = np.array([0, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2], dtype=float)  # step at 2.5
    g = np.zeros(13)
    g[9] = 1.0  # the gradient points elsewhere
    assert edge_crossing(h, g) is None


@pytest.mark.parametrize("vertical", [True, False])
def test_edge_samples_too_close_to_the_border_are_skipped(vertical):
    z = np.zeros((100, 100))
    seg = ((2, 10), (2, 90)) if vertical else ((10, 2), (90, 2))
    pts, n_real = _edge_points(seg, vertical, z, z, np.ones_like(z, dtype=bool), 6, 0)
    assert pts == [] and n_real == 0


def test_short_hough_segments_are_ignored(monkeypatch):
    monkeypatch.setattr(rotation_module, "probabilistic_hough_line",
                        lambda *args, **kwargs: [((10, 10), (12, 11))])
    z, _ = make_scan()
    with pytest.raises(RotationError):
        estimate_rotation(z, Config())


# --------------------------------------------------------------------- streaks


def test_streaks_on_a_surface_without_flat_pixels_report_nothing():
    rows, cols = np.indices((200, 200), dtype=float)
    z = 2.0 * (rows + cols)  # steep everywhere: no flat pixel pair
    out, s = remove_streaks(z, Config())
    assert s.level_um == 0.0 and not s.corrected and np.array_equal(out, z)


# --------------------------------------------------------------------- Pivot


def test_small_plateaus_are_not_plane_2():
    z = np.zeros((300, 300))
    z[100:110, 100:110] = 30.0  # 2.5 x 2.5 um: far below the 50 um2 minimum
    with pytest.raises(ElementNotFoundError, match="plane 2"):
        find_plane2(z, Config())


def test_a_plateau_with_only_cliffs_has_no_ramp():
    z = np.zeros((300, 300))
    z[100:200, 100:200] = 30.0  # vertical walls on every side
    with pytest.raises(ElementNotFoundError, match="no ramp"):
        ramp_direction(z, z >= 30.0, Config())


def test_plane_1_not_found_when_nothing_flat_lies_down_the_ramp():
    rows, cols = np.indices((300, 300), dtype=float)
    z = 2.0 * rows * 0.252  # a steep slope, never flat
    z[20:60, 100:200] = 80.0  # plane 2 near the top: the walk leaves the image
    with pytest.raises(ElementNotFoundError, match="plane 1"):
        find_plane1(z, z >= 80.0, Config())


def test_pivot_planes_narrower_than_the_edge_margin_are_still_measured():
    z = np.zeros((120, 120))
    plane1 = np.zeros(z.shape, dtype=bool)
    plane2 = np.zeros(z.shape, dtype=bool)
    plane1[30:32, 10:110] = True  # 2 px wide: the edge margin would erase it
    plane2[80:82, 10:110] = True
    z[plane2] = 18.0
    regions = PivotRegions(plane1, plane2, 18.0, (60.0, 80.5), 60.0)
    r = measure_pivot(z, Frame(z.shape), regions, None, None, Config())
    assert r.height_diff_um == pytest.approx(18.0, abs=1e-9)


# --------------------------------------------------------------------- crosses


def _plus(shape, depth):
    rows, cols = np.indices(shape)
    dx, dy = np.abs(cols - 40), np.abs(rows - 40)
    return np.where(((dx <= 13) & (dy <= 5)) | ((dx <= 5) & (dy <= 13)), depth, 0.0)


def test_raised_crosses_need_raised_polarity():
    residual = _plus((80, 80), +1.5)
    hull = np.ones(residual.shape, dtype=bool)
    assert len(_candidates(residual, hull, Config(cross_polarity="raised"))) == 1
    assert _candidates(residual, hull, Config()) == []


def test_cross_search_on_a_degenerate_plane_returns_not_found():
    z = np.zeros((60, 60))
    line = np.zeros(z.shape, dtype=bool)
    line[30, 10:50] = True  # one pixel wide: nothing left to fit a plane to
    assert not find_cross(z, Frame(z.shape), z, line, 30.0, Config()).found


# --------------------------------------------------------------------- Xpander


def test_apex_walk_stops_where_the_measured_data_ends():
    z, t = make_scan()
    _, _, z_canonical, z_seg = prepare(z, 0.0)
    regions = segment_pivot(z_seg, Config())
    valid = np.ones(z_canonical.shape, dtype=bool)
    valid[:int(t.apex_xy_px[1]) + 80] = False  # no data from just below the apex upward
    zs = xpander_module._detection_surface(z_canonical, Config())
    with pytest.raises(ElementNotFoundError, match="image border"):
        xpander_module._apex_seed(zs, regions, Config(), valid)


def test_failed_cross_checks_give_nan_not_a_failed_measurement(monkeypatch):
    def fail(*args, **kwargs):
        raise FitError("no solution")

    real_quadric = xpander_module.fit_quadric

    def quadric_without_small_apertures(u, v, z):
        if np.size(u) < 100_000:  # the 50 % and 75 % stability fits (32k, 71k points)
            raise FitError("too few points")
        return real_quadric(u, v, z)

    monkeypatch.setattr(xpander_module, "fit_sphere", fail)
    monkeypatch.setattr(xpander_module, "fit_profile_circle", fail)
    monkeypatch.setattr(xpander_module, "fit_quadric", quadric_without_small_apertures)
    z, _ = make_scan()
    _, frame, z_canonical, z_seg = prepare(z, 0.0)
    z_leveled = prepare(z, 0.0)[0]
    x = xpander_module.measure_xpander(z_leveled, frame, z_canonical,
                                       segment_pivot(z_seg, Config()), Config())
    assert x.found and x.rx_um == pytest.approx(820, rel=0.003)
    assert np.isnan(x.r_sphere_um) and np.isnan(x.rx_profile_um) and x.stability_pct == 0.0


# --------------------------------------------------------------------- faults and report


def test_noisy_plane_2_and_ry_out_of_spec_are_flagged():
    r = fake_result(pivot=PivotResult(18.18, 18.0, 12.9, 31.08, 0.045, 0.5, 0.05),
                    xpander=fake_xpander(rx=826.0, ry=900.0))
    assert "plane2_noisy" in geometric_flags(r, Config())
    assert nominal_flags(r, Config()) == ("ry_out_of_spec",)


def test_non_float_cells_are_written_as_text():
    assert _cell(5) == "5" and _cell("ok") == "ok"


# --------------------------------------------------------------------- pipeline


def test_unexpected_error_is_reported_not_raised(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_module, "fit_base_plane", boom)
    r = analyse_scan(make_scan()[0], Config(), "s")
    assert r.status == "failed" and r.error.startswith("unexpected error")


def test_missing_plane_1_is_flagged(monkeypatch):
    def no_plane1(*args, **kwargs):
        raise ElementNotFoundError("plane 1 not found below the ramp")

    monkeypatch.setattr(pipeline_module, "segment_pivot", no_plane1)
    r = analyse_scan(make_scan()[0], Config())
    assert r.status == "failed" and r.faults.geometric == ("plane1_not_found",)


def test_heavy_dust_on_the_dome_gives_a_warning():
    z, _ = make_scan()
    r = analyse_scan(add_spikes(z, 0.03), Config())  # 3 % of the pixels are spikes
    assert r.xpander.found and r.xpander.outlier_pct > 1.0
    assert "xpander_outliers_removed" in r.warnings and r.xpander.rms_um < 0.03


def test_missing_xpander_gives_a_partial_result_and_figure(tmp_path):
    r = analyse_scan(make_scan(crop_top_um=60.0)[0], Config(), "cut")
    assert r.status == "partial" and r.error.startswith("xpander not found")
    save_scan_figure(r, tmp_path / "cut.png", Config())
    assert (tmp_path / "cut.png").stat().st_size > 20_000


def test_failure_figure_without_image(tmp_path):
    r = ScanResult(file="bad.npy", status="failed", error="cannot read")
    save_scan_figure(r, tmp_path / "bad.png", Config())
    assert (tmp_path / "bad.png").stat().st_size > 2_000


def test_a_failing_figure_does_not_lose_the_measurement(tmp_path, caplog):
    np.save(tmp_path / "0.npy", make_scan()[0])

    def broken(result):
        raise RuntimeError("figure failed")

    res = analyse_dataset([tmp_path / "0.npy"], Config(), on_scan=broken)
    assert res[0].status == "ok" and "callback failed" in caplog.text


def test_dome_fit_with_too_few_pixels_left_is_refused():
    from teramount_analysis.xpander import _Aperture, _fit

    du, dv = (a.ravel() for a in np.meshgrid(np.linspace(-40, 40, 9), np.linspace(-40, 40, 9)))
    z = 12.0 - (du * 0.252) ** 2 / 1640 - (dv * 0.252) ** 2 / 1680
    z = z + np.random.default_rng(0).normal(0, 0.01, z.size)
    ap = _Aperture(np.arange(du.size), np.zeros(du.size, int), du, dv, z)
    strict = Config(outlier_clip_sigma=0.0, outlier_clip_min_um=1e-12)  # drops everything
    with pytest.raises(FitError, match="too few"):
        _fit(ap, strict)
