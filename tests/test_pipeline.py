"""End-to-end tests of the scan and dataset pipeline."""

from __future__ import annotations

import numpy as np
import pytest
from synthetic import make_scan

from teramount_analysis import Config, analyse_dataset, analyse_file, analyse_scan
from teramount_analysis.io import discover_scans


@pytest.mark.parametrize("phi,k", [(0.75, 0), (-0.5, 2)])
def test_end_to_end_synthetic(phi, k):
    z, t = make_scan(rotation_deg=phi, quarter_turns=k, slope_x=0.001, slope_y=-0.0015)
    r = analyse_scan(z, Config(), "syn")
    m = r.metrics(Config())
    assert r.status == "ok" and not r.faults.faulty, (r.error, r.faults)
    assert ((m["rotation_deg"] - t.rotation_deg + 180) % 360 - 180) == pytest.approx(0, abs=0.03)
    assert m["pivot_height_diff_um"] == pytest.approx(18.1, abs=0.02)
    assert (m["cross1_x_px"], m["cross1_y_px"]) == pytest.approx(t.cross1_xy_px, abs=0.3)
    assert (m["cross2_x_px"], m["cross2_y_px"]) == pytest.approx(t.cross2_xy_px, abs=0.3)
    assert m["xpander_rx_um"] == pytest.approx(820, rel=0.003)
    assert m["xpander_ry_um"] == pytest.approx(840, rel=0.003)
    assert m["tilt_x_deg"] == pytest.approx(np.degrees(np.arctan(0.001)), abs=0.002)


def test_global_offset_does_not_change_results():
    z, _ = make_scan(rotation_deg=0.5)
    a = analyse_scan(z, Config()).metrics(Config())
    b = analyse_scan(z + 100.0, Config()).metrics(Config())
    for key in ("pivot_height_diff_um", "xpander_rx_um", "cross2_x_px", "rotation_deg"):
        assert a[key] == pytest.approx(b[key], abs=1e-6)


def test_nan_dropouts_are_tolerated():
    z, _ = make_scan(nan_fraction=0.01)
    r = analyse_scan(z, Config())
    assert r.status == "ok"
    assert r.metrics(Config())["pivot_height_diff_um"] == pytest.approx(18.1, abs=0.03)


@pytest.mark.parametrize("z, message", [
    (np.zeros(500), "2-D"),
    (np.zeros((20, 20)), "small"),
    (np.full((300, 300), np.nan), "finite"),
    (np.full((100, 100), "a"), "numeric"),
    ([[1.0, 2.0], [3.0]], "array"),
])
def test_invalid_input_fails_with_a_clear_message(z, message):
    r = analyse_scan(z, Config(), "bad")
    assert r.status == "failed" and message in r.error, r.error
    assert "unexpected" not in r.error and r.faults is not None


def test_constant_scan_fails_cleanly():
    r = analyse_scan(np.zeros((300, 300)), Config(), "flat")
    assert r.status == "failed" and r.error and r.faults is not None


def test_missing_cross_gives_partial_result():
    z, _ = make_scan(cross2=False)
    r = analyse_scan(z, Config())
    assert r.status == "partial" and "cross 2" in r.error
    assert "cross2_not_found" in r.faults.geometric
    assert r.metrics(Config())["pivot_height_diff_um"] == pytest.approx(18.1, abs=0.03)


def test_clean_dome_near_border_is_not_flagged_noisy():
    # Cropping the top shrinks the fit aperture (and so the dome sag); a clean
    # surface must still not be reported as noisy (review finding I1).
    z, _ = make_scan(crop_top_um=44.0)
    r = analyse_scan(z, Config())
    assert r.xpander is not None and r.xpander.found
    assert r.xpander.aperture_radius_um < 35.0
    assert "xpander_surface_noisy" not in r.faults.geometric and not r.faults.faulty
    assert r.metrics(Config())["pivot_height_diff_um"] == pytest.approx(18.1, abs=0.03)


def test_noisy_dome_is_faulty():
    z, _ = make_scan(xpander_noise_um=0.2)
    r = analyse_scan(z, Config())
    assert "xpander_surface_noisy" in r.faults.geometric and r.faults.faulty


def test_unmeasured_rotation_is_a_warning_not_a_fault(monkeypatch):
    # Failing to measure the rotation is a limit of the analysis, not a chip defect.
    import teramount_analysis.pipeline as pipeline_module
    from teramount_analysis.errors import RotationError

    def no_edges(*args, **kwargs):
        raise RotationError("no straight edges found to measure the rotation")

    monkeypatch.setattr(pipeline_module, "estimate_rotation", no_edges)
    z, _ = make_scan()
    r = analyse_scan(z, Config())
    assert r.warnings == ("rotation_not_measured",)
    assert r.status == "ok" and not r.faults.faulty, (r.error, r.faults)
    assert "rotation_not_measured" not in r.faults.geometric


def test_ambiguous_ramp_is_reported_as_missing_ramp(monkeypatch):
    import teramount_analysis.pipeline as pipeline_module
    from teramount_analysis.errors import ElementNotFoundError

    def ambiguous(*args, **kwargs):
        raise ElementNotFoundError("Pivot ramp direction is ambiguous")

    monkeypatch.setattr(pipeline_module, "ramp_direction", ambiguous)
    z, _ = make_scan()
    r = analyse_scan(z, Config())
    assert r.status == "failed" and "ambiguous" in r.error
    assert r.faults.geometric == ("ramp_not_found",)


def test_rotation_correction_can_be_disabled():
    z, _ = make_scan()
    r = analyse_scan(z, Config(correct_rotation=False))
    assert r.rotation is None and r.metrics(Config())["rotation_deg"] == 0.0
    assert r.warnings == () and not r.faults.faulty


def test_unreadable_file_is_a_failed_row(tmp_path):
    bad = tmp_path / "bad.npy"
    bad.write_bytes(b"not numpy")
    r = analyse_file(bad, Config())
    assert r.status == "failed" and r.file == "bad.npy" and r.error


@pytest.mark.slow
def test_dataset_applies_statistics(tmp_path):
    for i in range(6):
        np.save(tmp_path / f"{i}.npy", make_scan(seed=i, rx_um=820 + i, ry_um=840)[0])
    np.save(tmp_path / "6.npy", make_scan(rx_um=950, ry_um=840)[0])
    seen = []
    res = analyse_dataset(discover_scans(tmp_path), Config(),
                          on_scan=lambda r: seen.append(r.debug is not None))
    assert seen == [True] * 7
    assert "xpander_rx_um_outlier" in res[-1].faults.statistical and res[0].debug is None
    assert all("xpander_rx_um_outlier" not in r.faults.statistical for r in res[:-1])
