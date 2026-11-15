"""Validation on the provided datasets (skipped when the folders are absent).

Dataset 2 file i is dataset 1 file i rotated about the array centre by a known
angle (APPLIED_ROTATION, established by image registration during data
exploration) plus a tilt plane, with some elements replaced by noisy versions.
So after correction every dataset-2 result must match its dataset-1 twin — an
end-to-end check of the tilt and rotation correction on real data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from teramount_analysis import Config, analyse_dataset
from teramount_analysis.io import discover_scans

pytestmark = [pytest.mark.realdata, pytest.mark.slow]

ROOT = Path(__file__).resolve().parents[1]
APPLIED_ROTATION = [1.0, 0, -0.25, 0.5, -1.0, 0.75, -0.75, 0.25, -0.5, 1.0, 0, -0.25, 0.5, -1.0,
                    0.75]
NOISY_XPANDER = {("t1", 6), ("t2", 3), ("t2", 13)}
NOISY_PIVOT = {("t1", 6), ("t2", 7)}
NOISY_FLAGS = {"plane1_noisy", "plane2_noisy", "xpander_surface_noisy"}


def _analyse(folder: str):
    path = ROOT / folder
    if not path.is_dir():
        pytest.skip(f"provided dataset {folder} not present")
    return analyse_dataset(discover_scans(path), Config())


@pytest.fixture(scope="module")
def t1_results():
    return _analyse("15_files_task_1")


@pytest.fixture(scope="module")
def t2_results():
    return _analyse("15_files_task_2")


@pytest.fixture(scope="module")
def t1(t1_results):
    return [r.metrics(Config()) for r in t1_results]


@pytest.fixture(scope="module")
def t2(t2_results):
    return [r.metrics(Config()) for r in t2_results]


def test_all_scans_analysed(t1_results, t2_results):
    assert [r.status for r in t1_results + t2_results] == ["ok"] * 30
    assert [r.file for r in t1_results] == [f"{i}.npy" for i in range(15)]


def test_task1_unrotated(t1):
    assert all(abs(m["rotation_deg"]) < 0.03 for m in t1)


def test_rotation_uses_many_edges(t1, t2):
    assert all(m["rotation_lines"] >= 20 for m in t1 + t2)


def test_task2_rotation_matches_applied(t1, t2):
    for i in range(15):
        d = t2[i]["rotation_deg"] - t1[i]["rotation_deg"]
        assert d == pytest.approx(APPLIED_ROTATION[i], abs=0.03), f"file {i}"


def test_tilt_only_in_task2(t1, t2):
    assert all(m["tilt_total_deg"] < 0.01 for m in t1)
    assert all(m["tilt_total_deg"] > 0.02 for m in t2)


def test_pivot_step_plausible(t1, t2):
    assert all(17.9 < m["pivot_height_diff_um"] < 18.4 for m in t1 + t2)


def test_task2_matches_task1_after_correction(t1, t2):
    for i in range(15):
        a, b = t1[i], t2[i]
        if ("t1", i) not in NOISY_PIVOT and ("t2", i) not in NOISY_PIVOT:
            assert b["pivot_height_diff_um"] == pytest.approx(a["pivot_height_diff_um"],
                                                              abs=0.03), f"file {i}"
            for n in (1, 2):  # canonical centres coincide (both frames rotate about the centre)
                assert (b[f"cross{n}_u_px"], b[f"cross{n}_v_px"]) == pytest.approx(
                    (a[f"cross{n}_u_px"], a[f"cross{n}_v_px"]), abs=0.5), f"file {i} cross {n}"
        tol = 0.01 if {("t1", i), ("t2", i)} & NOISY_XPANDER else 0.003
        assert b["xpander_rx_um"] == pytest.approx(a["xpander_rx_um"], rel=tol), f"file {i}"
        assert b["xpander_ry_um"] == pytest.approx(a["xpander_ry_um"], rel=tol), f"file {i}"


def test_planted_faults_flagged(t1_results, t2_results):
    def flags(r):
        return set(r.faults.geometric)

    assert NOISY_FLAGS <= flags(t1_results[6])
    assert "xpander_surface_noisy" in flags(t2_results[3])
    assert "xpander_surface_noisy" in flags(t2_results[13])
    assert {"plane1_noisy", "plane2_noisy"} <= flags(t2_results[7])
    assert not (NOISY_FLAGS & flags(t2_results[6]))  # clean twin of T1-6
    for i in (3, 7, 13):
        assert not (NOISY_FLAGS & flags(t1_results[i]))  # clean twins in dataset 1
