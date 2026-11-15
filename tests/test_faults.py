"""Tests for the result container and the three layers of fault checks."""

from __future__ import annotations

import dataclasses
import math

import pytest

from teramount_analysis.config import Config
from teramount_analysis.crosses import NOT_FOUND, CrossResult
from teramount_analysis.faults import geometric_flags, nominal_flags, statistical_flags
from teramount_analysis.frame import Frame
from teramount_analysis.pivot import PivotResult
from teramount_analysis.results import METRIC_COLUMNS, FaultReport, ScanResult
from teramount_analysis.rotation import RotationResult
from teramount_analysis.tilt import TiltResult
from teramount_analysis.xpander import XpanderResult


def _cross(offset_um=0.2):
    return CrossResult(True, 500.0, 770.0, 500.5, 770.2, 1.75, 19.0, 0.9, offset_um, None)


def _xpander(rx=826.0, ry=824.0, nrms=0.6, offset=0.5):
    base = XpanderResult.not_found("unused")
    return dataclasses.replace(
        base, found=True, reason="", apex_x_px=512.0, apex_y_px=385.0, apex_u_px=512.0,
        apex_v_px=385.0, axis_offset_um=offset, aperture_radius_um=49.0, rx_um=rx, ry_um=ry,
        rx_ci95_um=0.1, ry_ci95_um=0.1, r1_um=min(rx, ry), r2_um=max(rx, ry),
        principal_angle_deg=0.0, rms_um=nrms / 100 * 1.45, nrms_pct=nrms, r_squared=0.9996,
        sag_um=1.45, r_sphere_um=0.5 * (rx + ry), rx_profile_um=rx, ry_profile_um=ry,
        stability_pct=1.0, n_points=120_000)


def _result(**overrides):
    r = ScanResult(
        file="x.npy", status="ok", error="",
        tilt=TiltResult(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.012, 0.65),
        rotation=RotationResult(0.0, 0.01, 30, ()),
        frame=Frame((100, 100), 0.0),
        pivot=PivotResult(18.18, 18.0, 12.9, 31.08, 0.045, 0.025, 0.05),
        cross1=_cross(), cross2=_cross(), xpander=_xpander(),
    )
    return dataclasses.replace(r, **overrides)


def test_clean_result_has_no_flags_and_not_faulty():
    r = _result()
    cfg = Config()
    assert geometric_flags(r, cfg) == () and nominal_flags(r, cfg) == ()
    assert not FaultReport().faulty


def test_noisy_plane_and_dome_flagged():
    r = _result(pivot=PivotResult(18.18, 18.0, 12.9, 31.08, 0.5, 0.025, 0.05),
                xpander=_xpander(nrms=9.0))
    assert set(geometric_flags(r, Config())) == {"plane1_noisy", "xpander_surface_noisy"}


def test_missing_elements_flagged():
    r = _result(cross2=NOT_FOUND, xpander=XpanderResult.not_found("no dome"))
    assert set(geometric_flags(r, Config())) == {"cross2_not_found", "xpander_not_found"}


def test_missing_planes_and_rotation_flagged():
    r = _result(rotation=None, pivot=None, cross1=None, cross2=None, xpander=None,
                missing=("plane1",))
    assert geometric_flags(r, Config()) == ("rotation_not_measured", "plane1_not_found")


def test_geometry_violations_flagged():
    r = _result(cross1=_cross(offset_um=2.0), xpander=_xpander(rx=826, ry=700, offset=5.0),
                pivot=PivotResult(18.18, 18.0, 12.9, 31.08, 0.045, 0.025, 1.0))
    assert set(geometric_flags(r, Config())) == {
        "cross1_off_axis", "apex_off_axis", "planes_not_parallel", "xpander_astigmatic"}


def test_out_of_spec_step():
    r = _result(pivot=PivotResult(17.5, 17.3, 12.9, 30.4, 0.045, 0.025, 0.05))
    assert nominal_flags(r, Config()) == ("pivot_step_out_of_spec",)


def test_out_of_spec_radius():
    r = _result(xpander=_xpander(rx=900.0, ry=826.0))
    assert nominal_flags(r, Config()) == ("rx_out_of_spec",)


def test_fault_report_faulty_ignores_statistics_alone():
    assert not FaultReport((), (), ("xpander_rx_um_outlier",)).faulty
    assert FaultReport(("plane1_noisy",), (), ()).faulty
    assert FaultReport((), ("rx_out_of_spec",), ()).faulty


def test_statistical_outlier():
    rows = [{"xpander_rx_um": v} for v in (820, 822, 825, 819, 821, 823, 900)]
    flags = statistical_flags(rows, Config())
    assert flags[-1] == ("xpander_rx_um_outlier",) and all(f == () for f in flags[:-1])


def test_statistics_need_five_files():
    assert statistical_flags([{"xpander_rx_um": v} for v in (1, 2, 100)], Config()) == [(), (), ()]


def test_statistics_skip_constant_metric():
    rows = [{"xpander_rx_um": 820.0} for _ in range(6)] + [{"xpander_rx_um": 820.0}]
    assert statistical_flags(rows, Config()) == [()] * 7


def test_metrics_keys_match_columns():
    cfg = Config()
    full = _result().metrics(cfg)
    empty = ScanResult(file="bad.npy").metrics(cfg)
    assert list(full) == list(METRIC_COLUMNS) and list(empty) == list(METRIC_COLUMNS)
    assert all(math.isnan(v) for v in empty.values())
    assert full["cross1_x_um"] == pytest.approx(500.0 * 0.252)
    assert full["xpander_r_squared"] == pytest.approx(0.9996)
    assert full["xpander_aperture_radius_um"] == pytest.approx(49.0)
    assert full["rotation_lines"] == 30
