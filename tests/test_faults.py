"""Tests for the result container and the three layers of fault checks."""

from __future__ import annotations

import math

import pytest
from helpers import fake_cross as _cross
from helpers import fake_result as _result
from helpers import fake_xpander as _xpander

from teramount_analysis.config import Config
from teramount_analysis.crosses import NOT_FOUND
from teramount_analysis.faults import geometric_flags, nominal_flags, statistical_flags
from teramount_analysis.pivot import PivotResult
from teramount_analysis.results import METRIC_COLUMNS, FaultReport, ScanResult
from teramount_analysis.xpander import XpanderResult


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
